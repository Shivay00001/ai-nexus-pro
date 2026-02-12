# GOATCLAW Quickstart Guide

Get up and running with GOATCLAW in 5 minutes!

## Step 1: Run the Demo

```bash
cd goatclaw
python -m runner
```

You should see:
```
============================================================
  GOATCLAW — Enhanced Multi-Agent Orchestration System
  USP Features Demo
============================================================

🚀 Starting Execution...

✅ research_1          — ResearchAgent       (123.4ms)
✅ codegen_1           — CodeAgent           (234.5ms)
✅ review_1            — CodeAgent           (156.2ms)
✅ process_1           — DataProcessingAgent (89.3ms)

Status: SUCCESS
```

## Step 2: Create Your First Task

Create a file `my_first_task.py`:

```python
import asyncio
from goatclaw.runner import create_orchestrator, create_default_security_context
from goatclaw.core.types import (
    TaskGraph, TaskNode, AgentType, 
    PermissionScope, ExecutionMode
)

async def main():
    # Initialize
    orch = create_orchestrator()
    await orch.start()
    
    ctx = create_default_security_context()
    
    # Create task graph
    graph = TaskGraph(
        goal_summary="My first GOATCLAW task",
        execution_mode=ExecutionMode.SEQUENTIAL
    )
    
    # Add a research task
    node = TaskNode(
        node_id="my_research",
        name="Research AI trends",
        description="Find latest AI developments",
        agent_type=AgentType.RESEARCH,
        required_permissions=[PermissionScope.READ, PermissionScope.NETWORK],
        input_data={
            "query": "Latest AI trends 2025",
            "action": "search"
        },
        validation_rule="output.confidence > 0.5",
        priority=1
    )
    
    graph.add_node(node)
    
    # Execute
    print("Executing task...")
    result = await orch.process_goal(graph, ctx)
    
    # Results
    print(f"\n✅ Task completed: {result['status']}")
    print(f"📊 Execution time: {result['execution_time_seconds']:.2f}s")
    
    await orch.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python my_first_task.py
```

## Step 3: Build a Multi-Step Workflow

Create `workflow.py`:

```python
import asyncio
from goatclaw.runner import create_orchestrator, create_default_security_context
from goatclaw.core.types import *

async def main():
    orch = create_orchestrator()
    await orch.start()
    ctx = create_default_security_context()
    
    # Create workflow
    graph = TaskGraph(goal_summary="Research → Code → Deploy")
    
    # Step 1: Research
    research = TaskNode(
        node_id="research",
        agent_type=AgentType.RESEARCH,
        input_data={"query": "Python best practices"}
    )
    
    # Step 2: Generate code (depends on research)
    code = TaskNode(
        node_id="code",
        agent_type=AgentType.CODE,
        dependencies=["research"],  # ← Dependency!
        input_data={
            "action": "generate",
            "spec": "Create a utility module"
        }
    )
    
    # Step 3: Deploy (depends on code)
    deploy = TaskNode(
        node_id="deploy",
        agent_type=AgentType.DEVOPS,
        dependencies=["code"],  # ← Dependency!
        input_data={
            "action": "deploy",
            "environment": "staging"
        }
    )
    
    graph.add_node(research)
    graph.add_node(code)
    graph.add_node(deploy)
    
    result = await orch.process_goal(graph, ctx)
    print(f"Workflow status: {result['status']}")
    
    await orch.stop()

asyncio.run(main())
```

## Step 4: Try Parallel Execution

```python
graph = TaskGraph(
    goal_summary="Parallel tasks",
    execution_mode=ExecutionMode.PARALLEL,  # ← Parallel mode!
    max_parallel_tasks=3
)

# These will run concurrently:
for i in range(5):
    node = TaskNode(
        node_id=f"task_{i}",
        agent_type=AgentType.RESEARCH,
        input_data={"query": f"Topic {i}"}
    )
    graph.add_node(node)
```

## Step 5: Add Validation & Retry

```python
from goatclaw.core.types import RetryConfig, RetryStrategy

node = TaskNode(
    node_id="robust_task",
    agent_type=AgentType.CODE,
    input_data={"action": "generate"},
    
    # Validation
    validation_rule="output.quality_score > 0.8",
    
    # Retry config
    retry_config=RetryConfig(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay_seconds=1.0,
        backoff_multiplier=2.0
    )
)
```

## Step 6: Monitor Health

```python
# Get system health
health = orch.get_health()
print(f"Active tasks: {health.active_tasks}")
print(f"Success rate: {1 - health.error_rate:.1%}")
print(f"Avg time: {health.avg_execution_time_ms:.1f}ms")

# Get agent metrics
agent_metrics = orch._agents[AgentType.CODE].get_metrics()
print(f"Agent success rate: {agent_metrics['success_rate']:.1%}")

# Get event bus metrics
event_metrics = orch.event_bus.get_metrics()
print(f"Events processed: {event_metrics['total_events']}")
```

## Common Patterns

### Pattern 1: Fan-Out Then Fan-In

```python
# Fan-out: Parallel research
research_nodes = []
for topic in ["Topic A", "Topic B", "Topic C"]:
    node = TaskNode(
        node_id=f"research_{topic}",
        agent_type=AgentType.RESEARCH,
        input_data={"query": topic}
    )
    graph.add_node(node)
    research_nodes.append(node.node_id)

# Fan-in: Combine results
combine = TaskNode(
    node_id="combine",
    agent_type=AgentType.DATA_PROCESSING,
    dependencies=research_nodes,  # Waits for all research
    input_data={"action": "analyze"}
)
graph.add_node(combine)
```

### Pattern 2: Conditional Execution

```python
# Use validation to control flow
check = TaskNode(
    node_id="check_condition",
    agent_type=AgentType.RESEARCH,
    validation_rule="output.should_proceed == True"
)

# This only runs if validation passes
next_step = TaskNode(
    node_id="conditional_task",
    dependencies=["check_condition"],
    agent_type=AgentType.CODE
)
```

### Pattern 3: Event-Driven Communication

```python
# Subscribe to events
async def on_task_complete(event):
    print(f"Task {event.payload['node_id']} completed!")

orch.event_bus.subscribe("task.*.completed", on_task_complete)

# Events are automatically published during execution
```

## Next Steps

1. Read the [README.md](README.md) for full documentation
2. Explore the [core/types.py](core/types.py) for all available options
3. Check [agents/](agents/) for agent implementations
4. Review [orchestrator.py](orchestrator.py) for execution logic

## Troubleshooting

**Q: Tasks not executing?**
A: Check that dependencies are satisfied and permissions are granted.

**Q: High failure rate?**
A: Increase retry limits or check validation rules.

**Q: Slow execution?**
A: Use `ExecutionMode.PARALLEL` for independent tasks.

**Q: Memory growing?**
A: Configure memory consolidation threshold.

## Support

- Create an issue on GitHub
- Check the examples in `runner.py`
- Review agent implementations in `agents/specialists.py`

---

**You're ready to build autonomous workflows with GOATCLAW! 🚀**
