import asyncio
import logging
import signal
import os
import json
from datetime import datetime
from typing import Dict, Any

from goatclaw.task_queue import task_queue
from goatclaw.core.event_bus import EventBus, Event
from goatclaw.core.structs import (
    TaskNode, TaskStatus, AgentType, SecurityContext,
    PerformanceMetrics, RetryConfig, PermissionScope
)
from goatclaw.message_broker import broker as event_broker
from goatclaw.core.metrics import metrics_manager
from goatclaw.database import db_manager

# Import Agents (Reuse logic)
from goatclaw.agents.validation_agent import ValidationAgent
from goatclaw.agents.memory_agent import MemoryAgent
from goatclaw.agents.security_agent import SecurityAgent
from goatclaw.specialists import CodeAgent, ResearchAgent, DataProcessingAgent

from goatclaw.core.logging_config import setup_logging
setup_logging(level=logging.INFO)
logger = logging.getLogger("goatclaw.worker")

class Worker:
    """
    Distributed Worker Node.
    Consumes tasks from Redis TaskQueue and executes them.
    """
    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"worker_{os.getpid()}"
        self.running = False
        self._stop_event = asyncio.Event()
        
        # Initialize Event Bus (Publish only mode basically)
        self.event_bus = EventBus(enable_persistence=True)
        
        # Agents Map
        self.agents = {}


    async def setup(self):
        """Initialize connections and agents."""
        logger.info(f"Worker {self.worker_id} starting up...")
        
        # Connect Infra
        await task_queue.connect()
        await db_manager.init_db() # Ensure DB conn
        await self.event_bus.start() # Connects to Redis Broker
        
        # Init Agents
        # Note: In a real system, we might only load specific agents per worker
        self.security_agent = SecurityAgent(self.event_bus)
        self.validation_agent = ValidationAgent(self.event_bus)
        self.memory_agent = MemoryAgent(self.event_bus)
        
        self.agents = {
            AgentType.SECURITY: self.security_agent,
            AgentType.VALIDATION: self.validation_agent,
            AgentType.MEMORY: self.memory_agent,
            AgentType.CODE: CodeAgent(self.event_bus),
            AgentType.RESEARCH: ResearchAgent(self.event_bus),
            AgentType.DATA_PROCESSING: DataProcessingAgent(self.event_bus),
            AgentType.FILESYSTEM: FileSystemAgent(self.event_bus),
            AgentType.API: APIAgent(self.event_bus),
            AgentType.DEVOPS: DevOpsAgent(self.event_bus)
        }
        
        logger.info("Worker initialized and ready.")

    async def run(self):
        """Main worker loop."""
        self.running = True
        metrics_manager._gauges["active_workers"].inc()
        
        try:
            while self.running:
                try:
                    # 1. Pop Task (Blocking wait)
                    task_data = await task_queue.pop_task(timeout=5)
                    
                    if not task_data:
                        continue # Heartbeat / Check run flag
                    
                    logger.info(f"Worker {self.worker_id} received task")
                    
                    await self.process_task(task_data)
                    
                except Exception as e:
                    logger.error(f"Worker loop error: {e}")
                    await asyncio.sleep(1)
        finally:
            metrics_manager._gauges["active_workers"].dec()
            self.running = False

    async def process_task(self, task_data: Dict[str, Any]):
        """Execute the task."""
        try:
            # Deserialize
            node_dict = task_data.get("node")
            graph_id = task_data.get("graph_id")
            
            # Reconstruct TaskNode with proper type casting
            def convert_enum(val, enum_class):
                if val is None: return None
                if isinstance(val, enum_class): return val
                if isinstance(val, dict): return enum_class(val["value"])
                return enum_class(val)

            # Fix enums and nested dataclasses
            node_dict["agent_type"] = convert_enum(node_dict.get("agent_type"), AgentType)
            node_dict["status"] = convert_enum(node_dict.get("status"), TaskStatus)
            
            if "required_permissions" in node_dict:
                node_dict["required_permissions"] = [
                    convert_enum(p, PermissionScope) for p in node_dict["required_permissions"]
                ]
            
            if "retry_config" in node_dict and isinstance(node_dict["retry_config"], dict):
                node_dict["retry_config"] = RetryConfig(**node_dict["retry_config"])
            
            if "metrics" in node_dict and isinstance(node_dict["metrics"], dict):
                node_dict["metrics"] = PerformanceMetrics(**node_dict["metrics"])
            
            # Reconstruct datetime
            for dt_field in ["started_at", "completed_at"]:
                if node_dict.get(dt_field) and isinstance(node_dict[dt_field], str):
                    node_dict[dt_field] = datetime.fromisoformat(node_dict[dt_field])

            node = TaskNode(**node_dict)
            
            logger.info(f"Executing node {node.node_id} ({node.agent_type})")
            
            # Create context (In prod, pass this in task_data)
            context = SecurityContext(user_id="distributed_execution", allowed_scopes=[])
            
            # Get Agent
            agent = self.agents.get(node.agent_type)
            if not agent:
                raise ValueError(f"Unknown agent type: {node.agent_type}")
                
            # Execute
            result = await agent.run(node, context)
            
            # Publish Success Event
            await self.event_bus.publish(Event(
                event_type="task.completed",
                source=self.worker_id,
                payload={
                    "graph_id": graph_id,
                    "node_id": node.node_id,
                    "result": result,
                    "status": "success"
                }
            ))
            logger.info(f"Task {node.node_id} completed successfully")

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            # Publish Failure Event
            await self.event_bus.publish(Event(
                event_type="task.failed",
                source=self.worker_id,
                payload={
                    "graph_id": graph_id,
                    "node_id": node_dict.get("node_id", "unknown"),
                    "error": str(e)
                }
            ))

    async def shutdown(self):
        logger.info("Worker shutting down...")
        self.running = False
        await task_queue.close()
        await self.event_bus.stop()
        await db_manager.close()

if __name__ == "__main__":
    worker = Worker()
    
    loop = asyncio.get_event_loop()
    
    # Signal handling (Unix)
    try:
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(worker.shutdown()))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(worker.shutdown()))
    except NotImplementedError:
        # Windows doesn't support add_signal_handler fully
        pass

    try:
        loop.run_until_complete(worker.setup())
        loop.run_until_complete(worker.run())
    except KeyboardInterrupt:
        loop.run_until_complete(worker.shutdown())
