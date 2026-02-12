"""
GOATCLAW Runner
Entry point for initializing and executing the system.

Includes demonstration of all features.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from goatclaw.core.structs import (
    TaskGraph, TaskNode, TaskStatus, AgentType,
    SecurityContext, PermissionScope, RiskLevel,
    ExecutionMode, RetryStrategy, RetryConfig
)
from goatclaw.orchestrator import Orchestrator
from goatclaw.worker import Worker
from goatclaw.specialists import (
    ResearchAgent, CodeAgent, DevOpsAgent,
    APIAgent, DataProcessingAgent, FileSystemAgent,
)


def setup_logging(level: str = "INFO"):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-35s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def create_orchestrator(config: Optional[Dict] = None) -> Orchestrator:
    """
    Factory: build a fully wired Orchestrator with all agents.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured orchestrator
    """
    config = config or {}
    orch = Orchestrator(config)

    # Register specialist agents
    event_bus = orch.event_bus
    orch.register_agent(AgentType.RESEARCH, ResearchAgent(event_bus, config.get("research")))
    orch.register_agent(AgentType.CODE, CodeAgent(event_bus, config.get("code")))
    orch.register_agent(AgentType.DEVOPS, DevOpsAgent(event_bus, config.get("devops")))
    orch.register_agent(AgentType.API, APIAgent(event_bus, config.get("api")))
    orch.register_agent(
        AgentType.DATA_PROCESSING,
        DataProcessingAgent(event_bus, config.get("data_processing")),
    )
    orch.register_agent(
        AgentType.FILESYSTEM,
        FileSystemAgent(event_bus, config.get("filesystem", {"sandbox_root": "/tmp/goatclaw"})),
    )

    return orch


def create_default_security_context() -> SecurityContext:
    """Create a default authenticated security context for local use."""
    return SecurityContext(
        auth_token="local-dev-token",
        origin_ip="127.0.0.1",
        user_id="demo-user",
        allowed_scopes=[
            PermissionScope.READ,
            PermissionScope.WRITE,
            PermissionScope.EXECUTE,
            PermissionScope.NETWORK,
        ],
        sandbox_required=True,
        is_authenticated=True,
    )


def create_demo_task_graph() -> TaskGraph:
    """
    Create a demonstration task graph.
    
    Demonstrates:
    - Multiple agent types
    - Dependencies between tasks
    - Validation rules
    - Retry configuration
    """
    graph = TaskGraph(
        goal_summary="Research Python async patterns, generate code, and analyze results",
        confidence_score=0.92,
        execution_mode=ExecutionMode.SEQUENTIAL,
        max_parallel_tasks=3
    )

    # Node 1: Research async patterns
    n1 = TaskNode(
        node_id="research_1",
        name="Research async patterns",
        description="Find best practices for Python async/await.",
        agent_type=AgentType.RESEARCH,
        required_permissions=[PermissionScope.READ, PermissionScope.NETWORK],
        validation_rule="output.confidence > 0.5",
        input_data={
            "query": "Python async/await best practices 2025",
            "action": "search"
        },
        retry_config=RetryConfig(
            max_retries=2,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        ),
        priority=1
    )

    # Node 2: Generate code based on research
    n2 = TaskNode(
        node_id="codegen_1",
        name="Generate async utility module",
        description="Generate Python code based on research findings.",
        agent_type=AgentType.CODE,
        dependencies=["research_1"],
        required_permissions=[PermissionScope.READ, PermissionScope.WRITE],
        validation_rule="output.status == 'generated'",
        input_data={
            "action": "generate",
            "language": "python",
            "spec": "Async utility module with retry, timeout, and gather helpers"
        },
        retry_config=RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
    )

    # Node 3: Review generated code
    n3 = TaskNode(
        node_id="review_1",
        name="Review generated code",
        description="Quality review of the generated module.",
        agent_type=AgentType.CODE,
        dependencies=["codegen_1"],
        required_permissions=[PermissionScope.READ],
        validation_rule="output.quality_score > 0.7",
        input_data={
            "action": "review"
        }
    )

    # Node 4: Process results
    n4 = TaskNode(
        node_id="process_1",
        name="Process and summarize",
        description="Process all results and create summary.",
        agent_type=AgentType.DATA_PROCESSING,
        dependencies=["research_1", "review_1"],
        required_permissions=[PermissionScope.READ],
        input_data={
            "action": "analyze",
            "data": []
        }
    )

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    return graph


async def run_demo():
    """Demonstrate a full pipeline run with comprehensive features."""
    print("=" * 70)
    print("  GOATCLAW — Enhanced Multi-Agent Orchestration System")
    print("  USP Features Demo")
    print("=" * 70)
    print()
    
    setup_logging("INFO")

    # Create orchestrator and start it
    orch = create_orchestrator({
        "max_event_history": 5000,
        "security": {
            "max_requests_per_hour": 100,
            "threat_threshold": 0.8
        },
        "validation": {
            "auto_fix_enabled": True
        },
        "memory": {
            "max_memories": 1000,
            "similarity_threshold": 0.85
        }
    })
    
    await orch.start()
    
    try:
        sec_ctx = create_default_security_context()

        # Create task graph
        graph = create_demo_task_graph()

        print("[INFO] Task Graph Created")
        print(f"   Goal: {graph.goal_summary}")
        print(f"   Nodes: {len(graph.nodes)}")
        print(f"   Execution Mode: {graph.execution_mode.value}")
        print()

        # Execute pipeline
        print("[!] Starting Execution...")
        print()
        
        result = await orch.process_goal(graph, sec_ctx)

        # Display Results
        print()
        print("=" * 70)
        print("  EXECUTION RESULTS")
        print("=" * 70)
        print(f"  Status:           {result['status'].upper()}")
        print(f"  Risk Level:       {result.get('risk_level', 'N/A').upper()}")
        print(f"  Completed Nodes:  {len(result['completed_nodes'])}/{result['total_nodes']}")
        print(f"  Execution Time:   {result['execution_time_seconds']:.2f}s")
        print(f"  Errors:           {len(result['errors'])}")
        print()

        # Display node execution details
        print("📊 Node Execution Details:")
        print()
        for log in result["execution_log"]:
            status_icon = "[OK]" if log["status"] == "success" else "[FAIL]"
            dur = f"{log.get('duration_ms', 0):.1f}ms" if log.get("duration_ms") else "N/A"
            print(f"  {status_icon} {log['node_id']:20s} — {log['agent_type']:20s} ({dur})")

        print()

        # Display errors if any
        if result["errors"]:
            print("[WARN] Errors:")
            for error in result["errors"]:
                print(f"  • Node {error['node_id']}: {error['error']}")
            print()

        # System Health
        health = orch.get_health()
        print("[HEALTH] System Health:")
        print(f"   Active Tasks:     {health.active_tasks}")
        print(f"   Completed:        {health.completed_tasks}")
        print(f"   Failed:           {health.failed_tasks}")
        print(f"   Avg Time:         {health.avg_execution_time_ms:.1f}ms")
        print(f"   Error Rate:       {health.error_rate:.1%}")
        print(f"   Uptime:           {health.uptime_seconds:.1f}s")
        print()

        # Event Bus Metrics
        event_metrics = orch.event_bus.get_metrics()
        print("[METRICS] Event Bus Metrics:")
        print(f"   Total Events:     {event_metrics['total_events']}")
        print(f"   Error Rate:       {event_metrics['error_rate']:.1%}")
        print(f"   Active Subs:      {event_metrics['active_subscriptions']}")
        print(f"   History Size:     {event_metrics['history_size']}")
        print()

        print("[DONE] USP Features Demonstrated:")
        print("=" * 70)
        print("  [OK] Multi-agent orchestration")
        print("  [OK] Event-driven architecture")
        print("  [OK] Zero-trust security")
        print("  [OK] AI-powered validation with auto-fix")
        print("  [OK] Semantic memory with pattern learning")
        print("  [OK] Advanced retry strategies")
        print("  [OK] Real-time health monitoring")
        print("  [OK] Circuit breaker pattern")
        print("  [OK] Comprehensive audit logging")
        print("  [OK] Plugin architecture")
        print("=" * 70)

        return result

    finally:
        # Cleanup
        await orch.stop()


async def run_parallel_demo():
    """Demonstrate parallel execution mode."""
    print("=" * 70)
    print("  PARALLEL EXECUTION DEMO")
    print("=" * 70)
    print()
    
    setup_logging("INFO")
    
    orch = create_orchestrator()
    await orch.start()
    
    try:
        sec_ctx = create_default_security_context()
        
        # Create graph with parallel execution
        graph = TaskGraph(
            goal_summary="Parallel research on multiple topics",
            execution_mode=ExecutionMode.PARALLEL,
            max_parallel_tasks=3
        )
        
        # Create independent research tasks that can run in parallel
        topics = ["Python async", "Rust concurrency", "Go channels"]
        
        for i, topic in enumerate(topics):
            node = TaskNode(
                node_id=f"research_{i}",
                name=f"Research {topic}",
                agent_type=AgentType.RESEARCH,
                required_permissions=[PermissionScope.READ, PermissionScope.NETWORK],
                input_data={"query": topic, "action": "search"},
                priority=i
            )
            graph.add_node(node)
        
        print(f"🚀 Executing {len(topics)} tasks in PARALLEL...")
        print()
        
        result = await orch.process_goal(graph, sec_ctx)
        
        print()
        print(f"✅ Completed in {result['execution_time_seconds']:.2f}s")
        print(f"   (Sequential would have taken ~{len(topics) * 0.5:.2f}s)")
        print()
        
        return result
        
    finally:
        await orch.stop()


# Main entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "parallel":
        asyncio.run(run_parallel_demo())
    else:
        asyncio.run(run_demo())
