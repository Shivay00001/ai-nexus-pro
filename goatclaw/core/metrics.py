import time
import logging
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Optional dependencies for enterprise observability
try:
    from prometheus_client import Counter, Gauge, Histogram, Summary
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False

logger = logging.getLogger("goatclaw.core.metrics")

class MetricsManager:
    """
    USP: Centralized metrics and tracing manager for enterprise observability.
    """
    def __init__(self):
        self._enabled = HAS_PROMETHEUS
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
        
        if HAS_PROMETHEUS:
            self._init_prometheus_metrics()
            
        if HAS_OPENTELEMETRY:
            self._init_tracing()

    def _init_prometheus_metrics(self):
        """Initialize core platform metrics."""
        self._counters["tasks_total"] = Counter("goatclaw_tasks_total", "Total tasks processed", ["agent_type", "status"])
        self._gauges["active_workers"] = Gauge("goatclaw_active_workers", "Number of currently active workers")
        self._gauges["queue_size"] = Gauge("goatclaw_queue_size", "Current task queue depth")
        self._histograms["task_latency"] = Histogram("goatclaw_task_latency_seconds", "Task processing latency", ["agent_type"])
        self._counters["api_calls_total"] = Counter("goatclaw_api_calls_total", "Total external API calls", ["provider"])
        self._counters["credits_deducted"] = Counter("goatclaw_credits_deducted_total", "Total USP credits deducted")

    def _init_tracing(self):
        """Initialize OpenTelemetry tracing."""
        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer("goatclaw")
        # For production, we'd add OTLP exporter here
        # For now, console output if debug enabled
        if os.getenv("GOATCLAW_DEBUG_TRACING", "").lower() == "true":
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)

    def increment_task_count(self, agent_type: str, status: str):
        if self._enabled:
            self._counters["tasks_total"].labels(agent_type=agent_type, status=status).inc()

    def update_queue_size(self, size: int):
        if self._enabled:
            self._gauges["queue_size"].set(size)

    def record_task_latency(self, agent_type: str, duration: float):
        if self._enabled:
            self._histograms["task_latency"].labels(agent_type=agent_type).observe(duration)

    def record_api_call(self, provider: str):
        if self._enabled:
            self._counters["api_calls_total"].labels(provider=provider).inc()

    def record_credits(self, amount: float):
        if self._enabled:
            self._counters["credits_deducted"].inc(amount)

    def start_span(self, name: str):
        """Start an OpenTelemetry span."""
        if HAS_OPENTELEMETRY:
            return self.tracer.start_as_current_span(name)
        return None # In a real implementation, we'd return a mock context manager

# Global Instance
metrics_manager = MetricsManager()
