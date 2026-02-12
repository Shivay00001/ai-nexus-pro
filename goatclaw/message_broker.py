import os
import json
import asyncio
import logging
import uuid
from typing import Optional, Dict, List, Any, Callable
from redis.asyncio import Redis
from goatclaw.core.structs import Event # Assuming Event type is available or will be imported

logger = logging.getLogger("goatclaw.message_broker")

class MessageBroker:
    """
    Redis-backed Message Broker using Streams.
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[Redis] = None
        self.stream_key = "goatclaw_events"
        self.consumer_group = "goatclaw_group"
        # Unique consumer name for this instance
        # Unique consumer name for this instance
        self.consumer_name = f"consumer_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        
        # In-memory fallback
        self._memory_queue = asyncio.Queue()
        self._processed_ids = set()

    async def connect(self):
        """Connect to Redis and ensure consumer group exists."""
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
            # Create consumer group (ignore if exists)
            try:
                await self.redis.xgroup_create(
                    self.stream_key, 
                    self.consumer_group, 
                    id="0", 
                    mkstream=True
                )
            except Exception as e:
                # Group might already exist
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Could not create consumer group: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None # Fallback to in-memory if needed

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def publish(self, event_dict: Dict[str, Any]) -> str:
        """Publish event to Redis Stream."""
        if not self.redis:
            await self._memory_queue.put(event_dict)
            return f"mem_{uuid.uuid4()}"
        
        # Helper to serialize complex objects
        def _serialize(obj):
            from datetime import datetime
            from enum import Enum
            from dataclasses import is_dataclass, asdict
            
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize(v) for v in obj]
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, datetime):
                return obj.isoformat()
            if is_dataclass(obj):
                return _serialize(asdict(obj))
            return obj

        entry = {
            k: (json.dumps(_serialize(v)) if isinstance(v, (dict, list, tuple)) or is_dataclass(v) else str(_serialize(v)))
            for k, v in event_dict.items()
        }
        
        # XADD
        msg_id = await self.redis.xadd(self.stream_key, entry)
        return msg_id

    async def consume(self, count: int = 1) -> List[Dict[str, Any]]:
        """Consume events from the group."""
        if not self.redis:
            events = []
            while not self._memory_queue.empty() and len(events) < count:
                events.append(await self._memory_queue.get())
            if not events:
                await asyncio.sleep(0.1)
            return events

        try:
            # Read from consumer group
            streams = await self.redis.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                {self.stream_key: ">"}, # ">" means new messages
                count=count,
                block=1000 # Block for 1s
            )
            
            events = []
            if streams:
                for _, messages in streams:
                    for msg_id, data in messages:
                        # Parse back
                        parsed = {}
                        for k, v in data.items():
                            try:
                                parsed[k] = json.loads(v)
                            except:
                                parsed[k] = v
                        
                        # Add internal redis ID if needed
                        parsed["_redis_id"] = msg_id
                        events.append(parsed)
            
            return events
            
        except Exception as e:
            logger.error(f"Error consuming events: {e}")
            return []

    async def ack(self, msg_id: str):
        """Acknowledge message processing."""
        if self.redis:
            await self.redis.xack(self.stream_key, self.consumer_group, msg_id)

    async def is_duplicate(self, event_id: str, ttl: int = 3600) -> bool:
        """
        Check if event is duplicate using Redis SETNX.
        Returns True if already processed.
        Mark as processed if not.
        """
        if not self.redis:
            is_new = event_id not in self._processed_ids
            if is_new:
                self._processed_ids.add(event_id)
            return not is_new
            
        key = f"processed:{event_id}"
        # setnx returns 1 if set (new), 0 if exists (duplicate)
        # We want to set it.
        # Use set(..., nx=True)
        is_new = await self.redis.set(key, "1", nx=True, ex=ttl)
        return not is_new

# Global Broker Instance
broker = MessageBroker()
