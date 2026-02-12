import json
import logging
import asyncio
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from redis.asyncio import Redis
from goatclaw.core.structs import TaskNode, TaskStatus

logger = logging.getLogger("goatclaw.task_queue")

class TaskQueue:
    """
    Redis-backed Distributed Task Queue.
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[Redis] = None
        self.queue_key = "goatclaw_task_queue"
        self.processing_key = "goatclaw_task_processing"
        
        # In-memory fallback
        self._memory_queue = asyncio.Queue()
        
    async def connect(self):
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)
        try:
            await self.redis.ping()
            logger.info(f"TaskQueue connected to {self.redis_url}")
        except Exception as e:
            logger.error(f"TaskQueue connection failed: {e}")
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def push_task(self, task_node: TaskNode, graph_id: str, priority: int = 0):
        """Push a task to the queue."""
        # Robust serialization for TaskNode and nested dataclasses
        def _serialize_task(obj):
            from dataclasses import asdict, is_dataclass
            from enum import Enum
            from datetime import datetime
            
            if isinstance(obj, dict):
                return {k: _serialize_task(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize_task(v) for v in obj]
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, datetime):
                return obj.isoformat()
            if is_dataclass(obj):
                return _serialize_task(asdict(obj))
            return obj

        task_payload = {
            "node": _serialize_task(task_node),
            "graph_id": graph_id,
            "queued_at": datetime.utcnow().isoformat(),
            "priority": priority
        }
        
        payload_json = json.dumps(task_payload)
        
        if not self.redis:
            await self._memory_queue.put(payload_json)
            logger.debug(f"Pushed task {task_node.node_id} to memory queue")
            return
            
        # Use LPUSH (Left Push)
        await self.redis.lpush(self.queue_key, payload_json)
        logger.debug(f"Pushed task {task_node.node_id} to queue")

    async def pop_task(self, timeout:int = 0) -> Optional[Dict[str, Any]]:
        """
        Pop a task from the queue (blocking).
        Moves task to processing list (RPOPLPUSH pattern for reliability).
        """
        if not self.redis:
            try:
                # Use block=True with timeout for memory queue
                # Convert timeout 0 (block forever) to None for asyncio.Queue.get()?
                # Actually asyncio.Queue doesn't have timeout, we use wait_for
                if timeout > 0:
                    payload = await asyncio.wait_for(self._memory_queue.get(), timeout=timeout)
                else:
                    payload = await self._memory_queue.get()
                
                if payload:
                    return json.loads(payload)
            except asyncio.TimeoutError:
                return None
            except Exception as e:
                logger.error(f"Memory queue pop error: {e}")
                return None
            
        # BRPOPLPUSH: Block until item available, pop from queue, push to processing
        # Returns payload or None
        # Note: redis-py rpoplpush is deprecated for newer redis versions (BLMOVE), 
        # but broadly compatible.
        try:
            # Using brpoplpush for reliability
            updated_payload = await self.redis.brpoplpush(
                self.queue_key, 
                self.processing_key, 
                timeout=timeout
            )
            
            if updated_payload:
                return json.loads(updated_payload)
                
        except Exception as e:
            logger.error(f"Error popping task: {e}")
            
        return None

    async def get_queue_size(self) -> int:
        """USP: Get number of pending tasks for backpressure logic."""
        if not self.redis:
            return self._memory_queue.qsize()
        
        try:
            return await self.redis.llen(self.queue_key)
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0

    async def complete_task(self, task_payload_json: str):
        """Remove task from processing list upon completion."""
        # LREM
        if self.redis:
            await self.redis.lrem(self.processing_key, 0, task_payload_json)

# Global Instance
task_queue = TaskQueue()
