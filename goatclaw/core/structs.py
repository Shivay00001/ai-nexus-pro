"""
GOATCLAW Core Type Definitions
Foundational enums, data classes, and type aliases used across all modules.

Enhanced with:
- Multi-model LLM support
- Advanced retry strategies
- Performance metrics
- Distributed execution support
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable, Union
from datetime import datetime
import uuid


# ─── Enums ────────────────────────────────────────────────

class RiskLevel(Enum):
    """Risk classification for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Comprehensive task lifecycle states."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    RETRY = "retry"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"
    PAUSED = "paused"
    TIMEOUT = "timeout"


class AgentType(Enum):
    """All available agent types in the system."""
    PLANNER = "PlannerAgent"
    RESEARCH = "ResearchAgent"
    CODE = "CodeAgent"
    DEVOPS = "DevOpsAgent"
    BROWSER = "BrowserAgent"
    SHELL = "ShellAgent"
    FILESYSTEM = "FileSystemAgent"
    API = "APIAgent"
    DATA_PROCESSING = "DataProcessingAgent"
    SCHEDULER = "SchedulerAgent"
    MEMORY = "MemoryAgent"
    VALIDATION = "ValidationAgent"
    MONITOR = "MonitorAgent"
    SECURITY = "SecurityAgent"
    NOTIFIER = "NotifierAgent"
    DATABASE = "DatabaseAgent"
    ML = "MLAgent"


class NotificationChannel(Enum):
    """Supported notification channels."""
    API = "api"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    EMAIL = "email"
    VOICE = "voice"
    CONSOLE = "console"
    SLACK = "slack"
    WEBHOOK = "webhook"


class PermissionScope(Enum):
    """Permission scopes for security."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"
    NETWORK = "network"
    SECRET = "secret"
    DATABASE = "database"


class LLMProvider(Enum):
    """USP: Multi-model LLM support."""
    CLAUDE = "claude"
    GPT4 = "gpt4"
    GEMINI = "gemini"
    LLAMA = "llama"
    MIXTRAL = "mixtral"
    LOCAL = "local"


class RetryStrategy(Enum):
    """USP: Advanced retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"
    ADAPTIVE = "adaptive"


class ExecutionMode(Enum):
    """USP: Execution modes for flexibility."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DISTRIBUTED = "distributed"
    STREAMING = "streaming"


# ─── Data Classes ─────────────────────────────────────────

@dataclass
class LLMConfig:
    """USP: Multi-model LLM configuration."""
    provider: LLMProvider = LLMProvider.CLAUDE
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 60
    fallback_providers: List[LLMProvider] = field(default_factory=list)
    api_key: Optional[str] = None
    endpoint: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """USP: Detailed performance tracking."""
    execution_time_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_received: int = 0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RetryConfig:
    """USP: Configurable retry behavior."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retry_on_status: List[TaskStatus] = field(default_factory=lambda: [TaskStatus.FAILED, TaskStatus.TIMEOUT])


@dataclass
class TaskNode:
    """Enhanced task node with performance metrics and retry config."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    agent_type: AgentType = AgentType.PLANNER
    dependencies: List[str] = field(default_factory=list)
    required_permissions: List[PermissionScope] = field(default_factory=list)
    validation_rule: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    error_log: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    llm_config: Optional[LLMConfig] = None
    timeout_seconds: int = 300
    priority: int = 0  # Higher = more important
    tags: List[str] = field(default_factory=list)


@dataclass
class TaskGraph:
    """Enhanced DAG with execution modes and optimization."""
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal_summary: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    confidence_score: float = 0.0
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_parallel_tasks: int = 5
    total_estimated_time_seconds: Optional[float] = None
    actual_time_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: TaskNode):
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

    def get_ready_nodes(self) -> List[TaskNode]:
        """Return nodes whose dependencies are all satisfied."""
        ready = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            deps_met = all(
                self.nodes[dep].status == TaskStatus.SUCCESS
                for dep in node.dependencies
                if dep in self.nodes
            )
            if deps_met:
                ready.append(node)
        return ready

    def get_critical_path(self) -> List[str]:
        """USP: Calculate critical path for optimization."""
        # Simple implementation - can be enhanced with actual CPM algorithm
        if not self.execution_order:
            return []
        return self.execution_order


@dataclass
class ExecutionLog:
    """Enhanced execution log with streaming support."""
    log_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    graph_id: str = ""
    node_id: str = ""
    agent_type: str = ""
    action: str = ""
    input_snapshot: Dict[str, Any] = field(default_factory=dict)
    output_snapshot: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    parent_log_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class MemoryRecord:
    """Enhanced memory with semantic search support."""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    goal_summary: str = ""
    task_graph_snapshot: Optional[Dict] = None
    execution_logs: List[Dict] = field(default_factory=list)
    errors_and_resolutions: List[Dict] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    similarity_threshold: float = 0.85
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    ttl_hours: Optional[int] = None  # Time to live


@dataclass
class SecurityContext:
    """Enhanced security with zero-trust model."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    auth_token: Optional[str] = None
    origin_ip: Optional[str] = None
    allowed_scopes: List[PermissionScope] = field(default_factory=list)
    sandbox_required: bool = True
    rate_limit_remaining: int = 100
    rate_limit_window_seconds: int = 3600
    is_authenticated: bool = False
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    audit_trail: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    mfa_verified: bool = False


@dataclass
class NotificationPayload:
    """Enhanced notifications with templating."""
    channel: NotificationChannel = NotificationChannel.CONSOLE
    recipient: str = ""
    subject: str = ""
    body: str = ""
    severity: RiskLevel = RiskLevel.LOW
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    template_id: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    delivery_status: str = "pending"
    retry_count: int = 0


@dataclass
class ValidationResult:
    """Enhanced validation with detailed diagnostics."""
    node_id: str = ""
    rule: str = ""
    passed: bool = False
    expected: Any = None
    actual: Any = None
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence_score: float = 1.0
    suggestions: List[str] = field(default_factory=list)
    auto_fixable: bool = False


@dataclass
class HealthMetrics:
    """USP: Comprehensive system health monitoring."""
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_execution_time_ms: float = 0.0
    p95_execution_time_ms: float = 0.0
    p99_execution_time_ms: float = 0.0
    memory_records_count: int = 0
    uptime_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0
    throughput_tasks_per_minute: float = 0.0
    last_check: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheEntry:
    """USP: Intelligent caching for performance."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: int = 3600
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds


@dataclass
class PluginConfig:
    """USP: Plugin architecture for extensibility."""
    plugin_id: str
    name: str
    version: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class StreamingUpdate:
    """USP: Real-time streaming execution updates."""
    update_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    graph_id: str = ""
    node_id: str = ""
    update_type: str = "progress"  # progress, output, error, status
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence: int = 0


@dataclass
class Event:
    """Enhanced event with routing and priority."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    event_type: str = ""
    source: str = ""
    destination: Optional[str] = None  # For targeted events
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # 0=normal, 1=high, 2=critical
    ttl_seconds: int = 3600
    correlation_id: Optional[str] = None  # For request-response
    reply_to: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    ack_id: Optional[str] = None # Redis Stream ID for acknowledgement

    def is_expired(self) -> bool:
        """Check if event has expired."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "destination": self.destination,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "correlation_id": self.correlation_id,
            "headers": self.headers,
        }
