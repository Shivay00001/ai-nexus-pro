"""Distributed execution test -- no Redis required.

Uses the TaskQueue in-memory fallback and a single shared local EventBus
injected into both the Worker and the Orchestrator, so the full
push -> worker-execute -> publish -> orchestrator-collect loop runs
locally.
"""
import asyncio
import logging
import uuid

from goatclaw.core.event_bus import EventBus
from goatclaw.orchestrator import Orchestrator
from goatclaw.worker import Worker
from goatclaw.core.structs import (
    TaskGraph, TaskNode, AgentType, ExecutionMode,
    SecurityContext, PermissionScope,
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_distributed")


async def test_distributed_flow_without_redis(db):
    # One shared local bus: the worker publishes task.completed here and
    # the orchestrator's completion handler is subscribed here.
    shared_bus = EventBus(enable_persistence=False)
    await shared_bus.start()

    # Worker binds to the shared bus BEFORE setup() (setup creates agents
    # against self.event_bus).
    worker = Worker(worker_id="test_worker_1")
    worker.event_bus = shared_bus
    await worker.setup()
    worker_task = asyncio.create_task(worker.run())

    # Orchestrator binds to the same bus BEFORE start().
    orchestrator = Orchestrator(config={"distributed": True})
    orchestrator.event_bus = shared_bus
    await orchestrator.start()

    try:
        node1 = TaskNode(
            node_id="dist_task_1",
            name="task_1",
            agent_type=AgentType.DATA_PROCESSING,
            input_data={
                "action": "transform",
                "target_format": "json",
                "data": [{"hello": "distributed world"}],
            },
            priority=10,
        )
        node2 = TaskNode(
            node_id="dist_task_2",
            name="task_2",
            agent_type=AgentType.DATA_PROCESSING,
            input_data={
                "action": "clean",
                "data": [{"a": 1}, {"a": None}],
            },
            priority=5,
            dependencies=[node1.node_id],
        )

        graph = TaskGraph(
            goal_summary="Test Distributed Execution",
            nodes={node1.node_id: node1, node2.node_id: node2},
        )
        graph.graph_id = str(uuid.uuid4())
        graph.execution_mode = ExecutionMode.DISTRIBUTED

        ctx = SecurityContext(
            user_id="test-user",
            is_authenticated=True,
            allowed_scopes=[PermissionScope.ADMIN],
        )
        result = await asyncio.wait_for(
            orchestrator.process_goal(graph, ctx), timeout=120
        )

        assert result["status"] == "success", result.get("errors")
        assert set(result["completed_nodes"]) == {"dist_task_1", "dist_task_2"}
        assert result["total_nodes"] == 2
        assert result["execution_mode"] == "distributed"
    finally:
        await worker.shutdown()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await orchestrator.stop()
        await shared_bus.stop()
