import asyncio
import logging
import uuid
import os
from datetime import datetime

# Set env vars for simulated env
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_distributed.db" 
os.environ["REDIS_URL"] = "redis://localhost:6379"
# Note: This requires a running Redis instance.

from goatclaw.orchestrator import Orchestrator
from goatclaw.worker import Worker
from goatclaw.core.structs import TaskGraph, TaskNode, AgentType, ExecutionMode, TaskStatus
from goatclaw.database import db_manager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_distributed")

async def main():
    logger.info("Starting Distributed Execution Test...")
    
    # 1. Initialize infra
    await db_manager.init_db()
    
    # 2. Start Worker (Background)
    worker = Worker(worker_id="test_worker_1")
    await worker.setup()
    worker_task = asyncio.create_task(worker.run())
    logger.info("Worker started.")

    # 3. Start Orchestrator
    orchestrator = Orchestrator(config={"distributed": True})
    await orchestrator.start()
    logger.info("Orchestrator started.")

    try:
        # 4. Create Task Graph
        graph_id = str(uuid.uuid4())
        
        node1 = TaskNode(
            name="task_1",
            agent_type=AgentType.CODE,
            input_data={"instruction": "print('Hello from Distributed World!')"},
            priority=10
        )
        
        node2 = TaskNode(
            name="task_2",
            agent_type=AgentType.CODE,
            input_data={"instruction": "return 'Success'"},
            priority=5,
            dependencies=[node1.node_id]
        )
        
        graph = TaskGraph(
            goal_summary="Test Distributed Execution",
            nodes={
                node1.node_id: node1,
                node2.node_id: node2
            }
        )
        graph.graph_id = graph_id
        graph.execution_mode = ExecutionMode.DISTRIBUTED
        
        logger.info(f"Submitting Graph {graph_id}...")
        
        # 5. Process Goal
        result = await orchestrator.process_goal(graph, security_context=None)
        
        # 6. Verify
        logger.info("Execution Result:")
        print(result)
        
        if result["status"] == "success":
            logger.info("✅ Distributed Execution Successful!")
        else:
            logger.error("❌ Distributed Execution Failed.")
        
    finally:
        # Cleanup
        logger.info("Shutting down...")
        await worker.shutdown()
        worker_task.cancel()
        await orchestrator.stop()
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
