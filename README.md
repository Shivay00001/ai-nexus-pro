# GOATCLAW 🚀

**Greatest Of All Time - Coordinated Large-scale Autonomous Workflows**

An advanced multi-agent orchestration system with production-grade features for autonomous task execution, self-healing workflows, and intelligent automation.

---

## 🌟 Unique Selling Points (USPs)

### 1. **Multi-Model LLM Support**
- Seamless switching between Claude, GPT-4, Gemini, Llama, and local models
- Automatic fallback to backup providers
- Cost optimization through model selection

### 2. **Advanced Event-Driven Architecture**
- Asynchronous publish/subscribe event bus
- Event replay for debugging
- Dead letter queue for failed events
- Priority-based event processing

### 3. **Zero-Trust Security**
- Multi-factor authentication support
- Sliding window rate limiting
- Real-time threat detection
- Comprehensive audit logging
- IP blocking and threat scoring

### 4. **AI-Powered Validation with Auto-Fix**
- Semantic validation using LLMs
- Automatic error correction
- Schema validation
- Custom validation rules

### 5. **Semantic Memory & Learning**
- Vector embeddings for semantic search
- Pattern recognition from past executions
- Learning from failures
- Knowledge graph construction

### 6. **Multi-Mode Execution**
- Sequential: Step-by-step execution
- Parallel: Concurrent task processing
- Distributed: Cross-worker execution (coming soon)
- Streaming: Real-time progress updates

### 7. **Circuit Breaker & Self-Healing**
- Automatic failure detection
- Graceful degradation
- Configurable retry strategies (exponential, fibonacci, adaptive)
- Self-healing workflows

### 8. **Plugin Architecture**
- Extensible agent system
- Lifecycle hooks (before/after execution, on success/failure)
- Custom validator registration
- Easy integration of new capabilities

### 9. **Real-Time Monitoring**
- Performance metrics per agent
- Health checks
- Execution tracing
- Resource usage tracking

### 10. **Production-Grade Design**
- Comprehensive error handling
- Extensive logging
- Configurable timeouts
- Memory consolidation
- Cache management

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [Agent Types](#agent-types)
- [Configuration](#configuration)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     GOATCLAW                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │ Orchestrator │◄────────┤  Event Bus   │             │
│  └──────┬───────┘         └──────────────┘             │
│         │                                                │
│         ├───► Security Agent (Zero-Trust)               │
│         ├───► Validation Agent (AI-Powered)             │
│         ├───► Memory Agent (Semantic Search)            │
│         │                                                │
│         └───► Specialist Agents:                        │
│               • Research Agent                          │
│               • Code Agent                              │
│               • DevOps Agent                            │
│               • API Agent                               │
│               • Data Processing Agent                   │
│               • FileSystem Agent                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Modularity**: Each agent is independent and composable
2. **Scalability**: Event-driven architecture supports horizontal scaling
3. **Reliability**: Circuit breakers and retries ensure fault tolerance
4. **Observability**: Comprehensive logging and metrics
5. **Security**: Zero-trust model with fine-grained permissions

---

## 💻 Installation

### Prerequisites

- Python 3.9+
- pip

### Install

```bash
# Clone the repository
git clone https://github.com/your-org/goatclaw.git
cd goatclaw

# Install dependencies (if you have a requirements.txt)
pip install -r requirements.txt

# Or run directly
python -m goatclaw.runner
```

---

## 🚀 Quick Start

### Basic Example

```python
import asyncio
from goatclaw.runner import create_orchestrator, create_default_security_context
from goatclaw.core.types import TaskGraph, TaskNode, AgentType, PermissionScope

async def main():
    # Create orchestrator
    orch = create_orchestrator()
    await orch.start()
    
    # Create security context
    ctx = create_default_security_context()
    
    # Build task graph
    graph = TaskGraph(goal_summary="Research and analyze data")
    
    node = TaskNode(
        node_id="research_1",
        name="Research Topic",
        agent_type=AgentType.RESEARCH,
        required_permissions=[PermissionScope.READ],
        input_data={"query": "Python async patterns", "action": "search"}
    )
    graph.add_node(node)
    
    # Execute
    result = await orch.process_goal(graph, ctx)
    print(f"Status: {result['status']}")
    
    await orch.stop()

asyncio.run(main())
```

### Run Demo

```bash
# Sequential execution demo
python -m goatclaw.runner

# Parallel execution demo
python -m goatclaw.runner parallel
```

---

## 🧩 Core Components

### 1. Event Bus

Asynchronous publish/subscribe system for agent communication.

```python
from goatclaw.core.event_bus import EventBus, Event

bus = EventBus()
await bus.start()

# Subscribe
async def handler(event: Event):
    print(f"Received: {event.event_type}")

bus.subscribe("task.started", handler)

# Publish
await bus.publish(Event(
    event_type="task.started",
    payload={"node_id": "task_1"}
))
```

**Features:**
- Priority queues
- Event replay
- Dead letter queue
- Wildcard subscriptions
- Request-response pattern

### 2. Security Agent

Zero-trust security enforcement.

```python
from goatclaw.agents.security_agent import SecurityAgent

security = SecurityAgent(event_bus, config={
    "max_requests_per_hour": 100,
    "threat_threshold": 0.8
})

# Rate limiting
result = await security.execute(
    TaskNode(input_data={"action": "check_rate_limit"}),
    context
)

# Risk assessment
risk = await security.execute(
    TaskNode(input_data={"action": "assess_risk"}),
    context
)
```

**Features:**
- Sliding window rate limiting
- Threat scoring
- IP blocking
- Audit logging
- Session management

### 3. Validation Agent

AI-powered output validation.

```python
from goatclaw.agents.validation_agent import ValidationAgent

validator = ValidationAgent(event_bus, config={
    "auto_fix_enabled": True
})

# Validate output
node.validation_rule = "output.confidence > 0.8"
result = await validator.execute(node, context)
```

**Validation Types:**
- Schema validation
- Type checking
- Range validation
- Format validation (email, URL, UUID)
- Custom expressions
- Semantic validation (AI-powered)

### 4. Memory Agent

Semantic memory with pattern learning.

```python
from goatclaw.agents.memory_agent import MemoryAgent

memory = MemoryAgent(event_bus, config={
    "max_memories": 10000,
    "similarity_threshold": 0.85
})

# Store memory
await memory.execute(
    TaskNode(input_data={
        "action": "store",
        "goal_summary": "Task completed",
        "task_graph": {...}
    }),
    context
)

# Semantic search
results = await memory.execute(
    TaskNode(input_data={
        "action": "search",
        "query": "similar task"
    }),
    context
)
```

**Features:**
- Vector embeddings
- Pattern recognition
- Failure analysis
- Knowledge graph
- Memory consolidation

---

## 🤖 Agent Types

### Research Agent
- Web search
- Document analysis
- Information synthesis

### Code Agent
- Code generation
- Code review
- Refactoring
- Test generation

### DevOps Agent
- Deployment
- Infrastructure provisioning
- System monitoring

### API Agent
- REST API calls
- GraphQL queries
- Rate limiting

### Data Processing Agent
- ETL operations
- Data cleaning
- Format conversion

### FileSystem Agent
- File operations (sandboxed)
- Directory management

---

## ⚙️ Configuration

### Orchestrator Configuration

```python
config = {
    "max_event_history": 10000,
    "security": {
        "max_requests_per_hour": 100,
        "threat_threshold": 0.8,
        "session_timeout": 3600
    },
    "validation": {
        "auto_fix_enabled": True
    },
    "memory": {
        "max_memories": 10000,
        "similarity_threshold": 0.85,
        "consolidation_threshold": 100
    }
}

orch = create_orchestrator(config)
```

### Security Context

```python
from goatclaw.core.types import SecurityContext, PermissionScope

context = SecurityContext(
    user_id="user123",
    auth_token="token",
    origin_ip="192.168.1.1",
    allowed_scopes=[
        PermissionScope.READ,
        PermissionScope.WRITE,
        PermissionScope.EXECUTE
    ],
    is_authenticated=True,
    mfa_verified=True
)
```

### Retry Configuration

```python
from goatclaw.core.types import RetryConfig, RetryStrategy

retry_config = RetryConfig(
    max_retries=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay_seconds=1.0,
    max_delay_seconds=60.0,
    backoff_multiplier=2.0,
    jitter=True
)

node.retry_config = retry_config
```

---

## 📚 Examples

### Example 1: Multi-Step Workflow

```python
graph = TaskGraph(
    goal_summary="Research, code, and deploy",
    execution_mode=ExecutionMode.SEQUENTIAL
)

# Step 1: Research
research = TaskNode(
    node_id="research",
    agent_type=AgentType.RESEARCH,
    input_data={"query": "microservices patterns"}
)

# Step 2: Generate code (depends on research)
code = TaskNode(
    node_id="codegen",
    agent_type=AgentType.CODE,
    dependencies=["research"],
    input_data={"action": "generate"}
)

# Step 3: Deploy (depends on code)
deploy = TaskNode(
    node_id="deploy",
    agent_type=AgentType.DEVOPS,
    dependencies=["codegen"],
    input_data={"action": "deploy"}
)

graph.add_node(research)
graph.add_node(code)
graph.add_node(deploy)

result = await orch.process_goal(graph, ctx)
```

### Example 2: Parallel Execution

```python
graph = TaskGraph(
    goal_summary="Parallel research tasks",
    execution_mode=ExecutionMode.PARALLEL,
    max_parallel_tasks=5
)

topics = ["Python", "Rust", "Go", "JavaScript", "TypeScript"]

for topic in topics:
    node = TaskNode(
        node_id=f"research_{topic}",
        agent_type=AgentType.RESEARCH,
        input_data={"query": f"{topic} best practices"}
    )
    graph.add_node(node)

result = await orch.process_goal(graph, ctx)
```

### Example 3: Custom Validation

```python
# Register custom validator
def validate_price(config, output, task_node):
    price = output.get("price", 0)
    return {
        "valid": 0 < price < 1000,
        "message": f"Price ${price} is {'valid' if 0 < price < 1000 else 'invalid'}"
    }

validator.register_custom_validator("price_check", validate_price)

# Use in task
node.validation_rule = "price_check: {}"
```

---

## 📊 Monitoring & Metrics

### Health Check

```python
health = orch.get_health()
print(f"Active: {health.active_tasks}")
print(f"Completed: {health.completed_tasks}")
print(f"Failed: {health.failed_tasks}")
print(f"Error Rate: {health.error_rate:.1%}")
print(f"Uptime: {health.uptime_seconds}s")
```

### Agent Metrics

```python
metrics = agent.get_metrics()
print(f"Executions: {metrics['execution_count']}")
print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Avg Time: {metrics['avg_execution_time_ms']}ms")
print(f"Circuit Breaker: {metrics['circuit_breaker_state']}")
```

### Event Bus Metrics

```python
metrics = event_bus.get_metrics()
print(f"Total Events: {metrics['total_events']}")
print(f"Error Rate: {metrics['error_rate']:.1%}")
print(f"Queue Size: {metrics['queue_size']}")
```

---

## 🔒 Security Features

### Rate Limiting

```python
# Automatic rate limiting per user/IP
# Configurable limits and windows
# Sliding window algorithm
# Automatic blocking of abusive IPs
```

### Audit Logging

```python
# All security events are logged
logs = security_agent.get_audit_logs(
    user_id="user123",
    action="permission_check"
)

for log in logs:
    print(f"{log['timestamp']}: {log['action']} - {log['allowed']}")
```

### Threat Detection

```python
# Automatic threat scoring
# Pattern-based detection
# Configurable thresholds
# Real-time alerting
```

---

## 🚢 Deployment

### Docker (Coming Soon)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "-m", "goatclaw.runner"]
```

### Kubernetes (Coming Soon)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: goatclaw
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: goatclaw
        image: goatclaw:latest
```

---

## 🎯 Roadmap

- [ ] GraphQL API layer
- [ ] Web dashboard for monitoring
- [ ] Distributed execution across workers
- [ ] Integration with popular LLM APIs
- [ ] Plugin marketplace
- [ ] Advanced scheduling (cron-like)
- [ ] Multi-tenancy support
- [ ] Real-time collaboration features

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 💬 Support

- Issues: [GitHub Issues](https://github.com/your-org/goatclaw/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/goatclaw/discussions)
- Email: support@goatclaw.io

---

## 🙏 Acknowledgments

Built with ❤️ using modern Python async patterns and best practices from the distributed systems community.

---

**GOATCLAW** - Autonomous workflows, intelligent execution, production-ready.
