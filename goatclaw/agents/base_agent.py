"""
GOATCLAW Base Agent
Abstract base class for all agents with lifecycle hooks and plugin support.

Enhanced with:
- Plugin architecture
- Lifecycle hooks
- Performance tracking
- Circuit breaker pattern
- Graceful degradation
"""

from abc import ABC, abstractmethod
import asyncio
import time
import uuid
import logging
import aiohttp
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from goatclaw.core.structs import (
    TaskNode, TaskStatus, PerformanceMetrics,
    SecurityContext, PermissionScope, PluginConfig
)
from goatclaw.core.event_bus import EventBus, Event
from goatclaw.core.metrics import metrics_manager
from goatclaw.core.vault import vault
from goatclaw.core.ollama_client import ollama_client
from goatclaw.core.billing import billing_manager

logger = logging.getLogger("goatclaw.base_agent")


@dataclass
class CircuitBreakerState:
    """USP: Circuit breaker for fault tolerance."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    failure_threshold: int = 5
    timeout_seconds: int = 60
    success_threshold: int = 2
    consecutive_successes: int = 0

    def should_attempt(self) -> bool:
        """Check if we should attempt execution."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = "half-open"
                    self.consecutive_successes = 0
                    return True
            return False
        
        # half-open
        return True

    def record_success(self):
        """Record successful execution."""
        self.consecutive_successes += 1
        
        if self.state == "half-open" and self.consecutive_successes >= self.success_threshold:
            self.state = "closed"
            self.failure_count = 0
            logger.info(f"Circuit breaker reset to closed")
        
        if self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.consecutive_successes = 0
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class BaseAgent(ABC):
    """
    Enhanced abstract base class for all GOATCLAW agents.
    
    Features:
    - Lifecycle hooks (before/after execution)
    - Plugin system for extensibility
    - Performance tracking
    - Circuit breaker pattern
    - Event-driven communication
    """

    def __init__(
        self,
        agent_type: str,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_type = agent_type
        self.event_bus = event_bus
        self.config = config or {}
        self.enabled = True
        self._execution_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_execution_time_ms = 0.0
        self._plugins: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_success": [],
            "on_failure": [],
            "on_retry": [],
        }
        self._circuit_breaker = CircuitBreakerState()
        self._cache: Dict[str, Any] = {}
        
        logger.info(f"Initialized {self.agent_type}")

    @abstractmethod
    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """
        Execute the agent's task.
        
        Args:
            task_node: Task to execute
            context: Security context
            
        Returns:
            Execution result
        """
        pass

    async def run(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """
        Main execution wrapper with lifecycle hooks and error handling.
        
        This method wraps execute() with:
        - Circuit breaker
        - Lifecycle hooks
        - Performance tracking
        - Error handling
        """
        if not self.enabled:
            raise RuntimeError(f"Agent {self.agent_type} is disabled")

        # Check circuit breaker
        if not self._circuit_breaker.should_attempt():
            raise RuntimeError(f"Circuit breaker is open for {self.agent_type}")

        # Check permissions
        await self._check_permissions(task_node, context)

        # Before hooks
        await self._run_hooks("before_execute", task_node, context)

        start_time = datetime.utcnow()
        result = None
        error = None

        try:
            # Publish start event
            await self.event_bus.publish(Event(
                event_type=f"task.{task_node.node_id}.started",
                source=self.agent_type,
                payload={
                    "node_id": task_node.node_id,
                    "agent_type": self.agent_type
                }
            ))

            # Execute with caching
            cache_key = self._get_cache_key(task_node)
            if cache_key and cache_key in self._cache:
                logger.debug(f"Cache hit for {cache_key}")
                result = self._cache[cache_key]
            else:
                result = await self.execute(task_node, context)
                if cache_key:
                    self._cache[cache_key] = result

            # Record success
            self._circuit_breaker.record_success()
            self._success_count += 1
            task_node.status = TaskStatus.SUCCESS

            # Success hooks
            await self._run_hooks("on_success", task_node, context, result)

            # Publish success event
            await self.event_bus.publish(Event(
                event_type=f"task.{task_node.node_id}.completed",
                source=self.agent_type,
                payload={
                    "node_id": task_node.node_id,
                    "status": "success",
                    "result": result
                }
            ))

        except Exception as e:
            error = e
            self._circuit_breaker.record_failure()
            self._failure_count += 1
            task_node.status = TaskStatus.FAILED
            task_node.error_log.append(str(e))

            # Failure hooks
            await self._run_hooks("on_failure", task_node, context, error)

            # Publish failure event
            await self.event_bus.publish(Event(
                event_type=f"task.{task_node.node_id}.failed",
                source=self.agent_type,
                payload={
                    "node_id": task_node.node_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                priority=1  # High priority for failures
            ))

            # Check if should retry
            if task_node.retries < task_node.retry_config.max_retries:
                task_node.retries += 1
                task_node.status = TaskStatus.RETRY
                await self._run_hooks("on_retry", task_node, context)
                
                # Publish retry event
                await self.event_bus.publish(Event(
                    event_type=f"task.{task_node.node_id}.retry",
                    source=self.agent_type,
                    payload={
                        "node_id": task_node.node_id,
                        "retry_count": task_node.retries,
                        "error": str(e)
                    }
                ))

            logger.exception(f"Error executing {task_node.node_id}: {e}")
            raise

        finally:
            # Calculate metrics
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000
            
            self._execution_count += 1
            self._total_execution_time_ms += execution_time_ms

            # Update task metrics
            task_node.metrics.execution_time_ms = execution_time_ms
            task_node.started_at = start_time
            task_node.completed_at = end_time
            # After hooks
            await self._run_hooks("after_execute", task_node, context, result, error)

            # USP: Platform Monetization - Deduct credits for orchestration cycle
            # Deduct credits if billing manager available
            if hasattr(self, "billing_manager") and self.billing_manager:
                await self.billing_manager.deduct_credits(context.user_id, 1.0) # Specialization cost
                metrics_manager.record_credits(1.0)
            
            # Record execution metrics
            metrics_manager.increment_task_count(self.agent_type, "success" if not error else "failed")
            metrics_manager.record_task_latency(self.agent_type, execution_time_ms / 1000.0)

        return result or {}

    async def _get_api_key(self, provider: str, user_id: str) -> Optional[str]:
        """USP: Securely retrieve and decrypt user API key for the given provider."""
        from goatclaw.database import db_manager, SecretModel
        from sqlalchemy import select
        
        async with await db_manager.get_session() as session:
            stmt = select(SecretModel).where(
                SecretModel.user_id == user_id, 
                SecretModel.provider == provider
            )
            result = await session.execute(stmt)
            secret_record = result.scalar_one_or_none()
            
            if secret_record:
                return vault.decrypt(secret_record.encrypted_key)
        return None

    async def _call_llm(self, prompt: str, system: Optional[str] = None, model_config: Optional[Dict] = None) -> str:
        """Helper to call LLM based on provider config."""
        model_config = model_config or self.config.get("model", {})
        provider = model_config.get("provider", "openai")
        model_name = model_config.get("name", "gpt-4")

        # Record API call metric
        metrics_manager.record_api_call(provider)

        if provider == "ollama":
            return await ollama_client.generate(model_name, prompt, system)
        
        # USP: Generic API Dispatcher for OpenAI/Anthropic
        api_key = await self._get_api_key(provider, "system_orchestrator") # Use system key or user context?
        # In multi-tenant, we'd get context.user_id here
        
        if not api_key:
            # Fallback for testing/demos
            logger.warning(f"No API key found for {provider}, using simulated response.")
            return f"Simulated response from {provider}:{model_name} (No key found)"

        try:
            async with aiohttp.ClientSession() as session:
                # Provider Endpoints
                PROVIDERS = {
                    "openai": "https://api.openai.com/v1/chat/completions",
                    "kimi": "https://api.moonshot.cn/v1/chat/completions",
                    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
                    "deepseek": "https://api.deepseek.com/v1/chat/completions",
                }

                if provider in PROVIDERS or model_config.get("base_url"):
                    url = model_config.get("base_url") or PROVIDERS.get(provider)
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system or "You are a helpful AI specialist."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": model_config.get("temperature", 0.7)
                    }
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["choices"][0]["message"]["content"]
                        else:
                            error = await resp.text()
                            raise Exception(f"{provider.capitalize()} error {resp.status}: {error}")

                elif provider == "anthropic":
                    url = "https://api.anthropic.com/v1/messages"
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }
                    payload = {
                        "model": model_name,
                        "system": system or "You are a helpful AI specialist.",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1024
                    }
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["content"][0]["text"]
                        else:
                            error = await resp.text()
                            raise Exception(f"Anthropic error {resp.status}: {error}")

                else:
                    raise ValueError(f"Unsupported provider: {provider}")

        except Exception as e:
            logger.error(f"LLM call failed for {provider}: {e}")
            return f"Error calling {provider}: {str(e)}"

    async def _check_permissions(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ):
        """Check if security context has required permissions."""
        for required_perm in task_node.required_permissions:
            if required_perm not in context.allowed_scopes:
                raise PermissionError(
                    f"Missing permission: {required_perm.value} for {self.agent_type}"
                )

    def _get_cache_key(self, task_node: TaskNode) -> Optional[str]:
        """Generate cache key for task node. Override in subclasses."""
        return None

    async def _run_hooks(
        self,
        hook_name: str,
        *args,
        **kwargs
    ):
        """Run all registered hooks for a lifecycle event."""
        hooks = self._hooks.get(hook_name, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in {hook_name} hook: {e}")

    def register_hook(
        self,
        hook_name: str,
        hook_func: Callable
    ):
        """
        Register a lifecycle hook.
        
        Args:
            hook_name: Name of hook (before_execute, after_execute, on_success, on_failure, on_retry)
            hook_func: Function to call
        """
        if hook_name not in self._hooks:
            raise ValueError(f"Unknown hook: {hook_name}")
        
        self._hooks[hook_name].append(hook_func)
        logger.debug(f"Registered hook {hook_name} for {self.agent_type}")

    def load_plugin(self, plugin_config: PluginConfig):
        """
        USP: Load a plugin to extend agent functionality.
        
        Args:
            plugin_config: Plugin configuration
        """
        if not plugin_config.enabled:
            return

        self._plugins[plugin_config.plugin_id] = {
            "config": plugin_config,
            "instance": None  # Placeholder for actual plugin instance
        }
        
        logger.info(f"Loaded plugin {plugin_config.name} v{plugin_config.version}")

    def unload_plugin(self, plugin_id: str):
        """Unload a plugin."""
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            logger.info(f"Unloaded plugin {plugin_id}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        USP: Get agent performance metrics.
        
        Returns:
            Dictionary of metrics
        """
        avg_time = (
            self._total_execution_time_ms / self._execution_count
            if self._execution_count > 0
            else 0.0
        )
        
        success_rate = (
            self._success_count / self._execution_count
            if self._execution_count > 0
            else 0.0
        )

        return {
            "agent_type": self.agent_type,
            "enabled": self.enabled,
            "execution_count": self._execution_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_time,
            "total_execution_time_ms": self._total_execution_time_ms,
            "circuit_breaker_state": self._circuit_breaker.state,
            "cache_size": len(self._cache),
            "plugins_loaded": len(self._plugins),
        }

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker."""
        self._circuit_breaker = CircuitBreakerState()
        logger.info(f"Circuit breaker reset for {self.agent_type}")

    def clear_cache(self):
        """Clear agent cache."""
        self._cache.clear()
        logger.info(f"Cache cleared for {self.agent_type}")

    def enable(self):
        """Enable the agent."""
        self.enabled = True
        logger.info(f"Enabled {self.agent_type}")

    def disable(self):
        """Disable the agent."""
        self.enabled = False
        logger.info(f"Disabled {self.agent_type}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the agent.
        
        Returns:
            Health status
        """
        return {
            "agent_type": self.agent_type,
            "status": "healthy" if self.enabled and self._circuit_breaker.state == "closed" else "degraded",
            "enabled": self.enabled,
            "circuit_breaker": self._circuit_breaker.state,
            "last_execution": self._execution_count > 0,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.agent_type}, enabled={self.enabled})"
