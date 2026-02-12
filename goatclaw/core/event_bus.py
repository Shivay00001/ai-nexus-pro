"""
GOATCLAW Event Bus
Asynchronous publish/subscribe system for inter-agent communication.

Enhanced with:
- Distributed event streaming
- Event replay capability
- Priority queues
- Dead letter queue
- Event filtering and routing
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
import uuid
import logging
import json

from goatclaw.message_broker import broker
from goatclaw.core.structs import Event

logger = logging.getLogger("goatclaw.event_bus")





class EventBus:
    """
    USP: Advanced event bus with distributed support and reliability features.
    
    Features:
    - Priority-based event delivery
    - Event replay for debugging
    - Dead letter queue for failed events
    - Event filtering and routing
    - Metrics and monitoring
    """

    def __init__(self, max_history: int = 10000, enable_persistence: bool = False):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: deque = deque(maxlen=max_history)
        self._dead_letter_queue: deque = deque(maxlen=1000)
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._redis_task: Optional[asyncio.Task] = None
        self._enable_persistence = enable_persistence
        self._event_count = 0
        self._error_count = 0
        self._filters: List[Callable[[Event], bool]] = []
        self._interceptors: List[Callable[[Event], Event]] = []
        self.broker = broker
        self._event_counter = 0 # For PriorityQueue stability
        logger.info("EventBus initialized")

    async def start(self):
        """Start the event bus worker."""
        if self._running:
            return
        
        if self._enable_persistence:
            await self.broker.connect()
            self._redis_task = asyncio.create_task(self._poll_redis())
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")

    async def stop(self):
        """Stop the event bus worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        if self._redis_task:
             self._redis_task.cancel()
             try:
                 await self._redis_task
             except asyncio.CancelledError:
                 pass
        
        if self._enable_persistence:
            await self.broker.close()

        logger.info("EventBus stopped")

    def subscribe(self, event_type: str, handler: Callable[[Event], Coroutine]):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for (supports wildcards like "task.*")
            handler: Async function to handle the event
        """
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}, total handlers: {len(self._subscribers[event_type])}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed from {event_type}")

    async def publish(self, event: Event) -> str:
        """
        Publish an event to the bus.
        
        Args:
            event: Event to publish
            
        Returns:
            Event ID
        """
        # Apply interceptors
        for interceptor in self._interceptors:
            event = interceptor(event)

        # Apply filters
        for filter_func in self._filters:
            if not filter_func(event):
                logger.debug(f"Event {event.event_id} filtered out")
                return event.event_id

        # Check expiration
        if event.is_expired():
            logger.warning(f"Event {event.event_id} expired before publishing")
            self._dead_letter_queue.append(event)
            return event.event_id

        msg_id_out = event.event_id
        
        # Add to history
        self._event_history.append(event)
        self._event_count += 1
        
        if self._enable_persistence:
            # Publish to Redis
            try:
                await self.broker.publish(event.to_dict())
                logger.debug(f"Published event {event.event_id} to Redis")
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")
                # Fallback to local queue? 
                # Ideally we want to fail or queue locally.
                self._event_counter += 1
                await self._priority_queue.put((-event.priority, self._event_counter, event))
        else:
            # Local only
            self._event_counter += 1
            await self._priority_queue.put((-event.priority, self._event_counter, event))
        
        logger.debug(f"Published event {event.event_id} (type={event.event_type}, priority={event.priority})")
        return msg_id_out

    async def publish_and_wait(self, event: Event, timeout: float = 10.0) -> Optional[Event]:
        """
        USP: Publish event and wait for reply (request-response pattern).
        
        Args:
            event: Event to publish
            timeout: Max seconds to wait for response
            
        Returns:
            Reply event or None if timeout
        """
        correlation_id = str(uuid.uuid4())
        event.correlation_id = correlation_id
        
        # Create future for response
        response_future = asyncio.Future()
        
        # Subscribe to response
        async def response_handler(reply_event: Event):
            if reply_event.correlation_id == correlation_id:
                response_future.set_result(reply_event)
        
        self.subscribe(f"{event.event_type}.reply", response_handler)
        
        # Publish event
        await self.publish(event)
        
        # Wait for response
        try:
            reply = await asyncio.wait_for(response_future, timeout=timeout)
            return reply
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for reply to {event.event_id}")
            return None
        finally:
            self.unsubscribe(f"{event.event_type}.reply", response_handler)

    async def _process_events(self):
        """Background worker to process events from priority queue."""
        logger.info("Event processor started")
        while self._running:
            try:
                # Get event from queue (blocks until available)
                # Unpack 3-tuple (priority, counter, event)
                _, _, event = await asyncio.wait_for(
                    self._priority_queue.get(),
                    timeout=1.0
                )
                
                # Process event
                await self._dispatch_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.exception(f"Error processing event: {e}")
                self._error_count += 1

    async def _poll_redis(self):
        """Background task to poll events from Redis."""
        while self._running:
            try:
                events_data = await self.broker.consume(count=10)
                for data in events_data:
                    # Reconstruct Event object
                    try:
                        # Convert dict back to Event
                        # Note: timestamps might be strings now
                        if "timestamp" in data and isinstance(data["timestamp"], str):
                            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                        
                        ack_id = data.pop("_redis_id", None)
                        
                        event = Event(**data)
                        event.ack_id = ack_id
                        
                        # Deduplication check
                        if self._enable_persistence:
                            if await self.broker.is_duplicate(event.event_id):
                                logger.info(f"Skipping duplicate event {event.event_id}")
                                if ack_id:
                                    await self.broker.ack(ack_id)
                                continue
                        
                        # Put into local priority queue for processing
                        self._event_counter += 1
                        await self._priority_queue.put((-event.priority, self._event_counter, event))
                    except Exception as e:
                        logger.error(f"Failed to reconstruct event from redis data: {e}")
            except Exception as e:
                logger.error(f"Redis poll error: {e}")
                await asyncio.sleep(1) # Backoff

    async def _dispatch_event(self, event: Event):
        """Dispatch event to all matching subscribers."""
        handlers = self._get_matching_handlers(event.event_type)
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return

        # If event has destination, filter handlers
        if event.destination:
            handlers = [h for h in handlers if getattr(h, '__name__', '') == event.destination]

        # Call all handlers concurrently
        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call_handler(handler, event))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {handlers[i].__name__} failed: {result}")
                self._error_count += 1
                
                # Retry logic
                if event.retry_count < event.max_retries:
                    event.retry_count += 1
                    logger.info(f"Retrying event {event.event_id}, attempt {event.retry_count}")
                    self._event_counter += 1
                    await self._priority_queue.put((-(event.priority - 1), self._event_counter, event))
                else:
                    logger.error(f"Event {event.event_id} moved to dead letter queue after {event.retry_count} retries")
                    self._dead_letter_queue.append(event)
        
        # Acknowledge event in Redis if applicable
        if event.ack_id and self._enable_persistence:
            await self.broker.ack(event.ack_id)

    async def _safe_call_handler(self, handler: Callable, event: Event):
        """Safely call a handler with error handling."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.exception(f"Error in handler {handler.__name__}: {e}")
            raise

    def _get_matching_handlers(self, event_type: str) -> List[Callable]:
        """Get all handlers matching the event type (supports wildcards)."""
        handlers = []
        
        # Exact match
        if event_type in self._subscribers:
            handlers.extend(self._subscribers[event_type])
        
        # Wildcard match (e.g., "task.*" matches "task.started")
        for subscribed_type in self._subscribers:
            if subscribed_type.endswith(".*"):
                prefix = subscribed_type[:-2]
                if event_type.startswith(prefix):
                    handlers.extend(self._subscribers[subscribed_type])
            elif subscribed_type == "*":
                handlers.extend(self._subscribers[subscribed_type])
        
        return handlers

    def add_filter(self, filter_func: Callable[[Event], bool]):
        """Add an event filter. Events that don't pass are dropped."""
        self._filters.append(filter_func)

    def add_interceptor(self, interceptor: Callable[[Event], Event]):
        """Add an event interceptor to modify events before processing."""
        self._interceptors.append(interceptor)

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """
        USP: Get event history for debugging and replay.
        
        Args:
            event_type: Filter by event type (optional)
            limit: Max number of events to return
            
        Returns:
            List of historical events
        """
        events = list(self._event_history)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]

    async def replay_events(self, event_ids: List[str]):
        """
        USP: Replay specific events for debugging.
        
        Args:
            event_ids: List of event IDs to replay
        """
        for event in self._event_history:
            if event.event_id in event_ids:
                logger.info(f"Replaying event {event.event_id}")
                await self.publish(event)

    def get_dead_letter_queue(self) -> List[Event]:
        """Get events that failed processing."""
        return list(self._dead_letter_queue)

    async def retry_dead_letters(self, event_ids: Optional[List[str]] = None):
        """
        Retry events from dead letter queue.
        
        Args:
            event_ids: Specific events to retry (all if None)
        """
        to_retry = []
        
        for event in list(self._dead_letter_queue):
            if event_ids is None or event.event_id in event_ids:
                to_retry.append(event)
                self._dead_letter_queue.remove(event)
        
        for event in to_retry:
            event.retry_count = 0  # Reset retry count
            await self.publish(event)

    def get_metrics(self) -> Dict[str, Any]:
        """USP: Get event bus metrics for monitoring."""
        return {
            "total_events": self._event_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / max(self._event_count, 1),
            "active_subscriptions": sum(len(handlers) for handlers in self._subscribers.values()),
            "history_size": len(self._event_history),
            "dead_letter_size": len(self._dead_letter_queue),
            "queue_size": self._priority_queue.qsize(),
        }

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        logger.info("Event history cleared")

    async def wait_for_event(
        self,
        event_type: str,
        filter_func: Optional[Callable[[Event], bool]] = None,
        timeout: float = 30.0
    ) -> Optional[Event]:
        """
        Wait for a specific event to occur.
        
        Args:
            event_type: Type of event to wait for
            filter_func: Optional filter function
            timeout: Max seconds to wait
            
        Returns:
            Event or None if timeout
        """
        future = asyncio.Future()
        
        async def handler(event: Event):
            if filter_func is None or filter_func(event):
                if not future.done():
                    future.set_result(event)
        
        self.subscribe(event_type, handler)
        
        try:
            event = await asyncio.wait_for(future, timeout=timeout)
            return event
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe(event_type, handler)
