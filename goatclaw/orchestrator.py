"""
GOATCLAW Orchestrator
Main execution engine with advanced features.

Enhanced with:
- Multi-mode execution (sequential, parallel, distributed)
- Real-time streaming updates
- Advanced error recovery
- Performance optimization
- Distributed task execution
"""

import asyncio
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import logging

from goatclaw.core.structs import (
    TaskGraph, TaskNode, TaskStatus, ExecutionLog,
    SecurityContext, PermissionScope, RiskLevel,
    AgentType, ExecutionMode, StreamingUpdate,
    HealthMetrics, PerformanceMetrics
)
from goatclaw.core.event_bus import EventBus, Event
from goatclaw.agents.base_agent import BaseAgent
from goatclaw.agents.security_agent import SecurityAgent
from goatclaw.agents.validation_agent import ValidationAgent
from goatclaw.agents.validation_agent import ValidationAgent
from goatclaw.agents.memory_agent import MemoryAgent
from goatclaw.database import db_manager, TaskGraphModel
from goatclaw.task_queue import task_queue
from goatclaw.core.metrics import metrics_manager
from goatclaw.core.billing import billing_manager
from goatclaw.core.logging_config import setup_logging
import json

setup_logging() # Defaults to INFO
logger = logging.getLogger("goatclaw.orchestrator")


class Orchestrator:
    """
    USP: Advanced orchestrator with multi-mode execution and self-healing.
    
    Features:
    - Sequential, parallel, and distributed execution
    - Real-time streaming updates
    - Advanced retry strategies
    - Performance optimization
    - Self-healing workflows
    - Intelligent task scheduling
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.event_bus = EventBus(
            max_history=self.config.get("max_event_history", 10000),
            enable_persistence=self.config.get("distributed", False)
        )
        
        # Core agents
        self._agents: Dict[AgentType, BaseAgent] = {}
        self._security_agent = SecurityAgent(self.event_bus, self.config.get("security"))
        self._validation_agent = ValidationAgent(self.event_bus, self.config.get("validation"))
        self._memory_agent = MemoryAgent(self.event_bus, self.config.get("memory"))
        
        # Execution state
        self._active_graphs: Dict[str, TaskGraph] = {}
        self._execution_logs: Dict[str, List[ExecutionLog]] = defaultdict(list)
        self._streaming_updates: Dict[str, List[StreamingUpdate]] = defaultdict(list)
        
        # Metrics
        self._start_time = datetime.utcnow()
        self._total_tasks_executed = 0
        self._total_tasks_failed = 0
        self._total_execution_time_ms = 0.0
        
        logger.info("Orchestrator initialized")

    async def start(self):
        """Start the orchestrator and event bus."""
        await self.event_bus.start()
        await task_queue.connect()
        logger.info("Orchestrator started")

    async def stop(self):
        """Stop the orchestrator and event bus."""
        await self.event_bus.stop()
        await task_queue.close()
        logger.info("Orchestrator stopped")

    @property
    def agents(self) -> Dict[AgentType, BaseAgent]:
        """USP: Public access to registered agents for monitoring and debugging."""
        return self._agents

    def register_agent(self, agent_type: AgentType, agent: BaseAgent):
        """
        Register a specialist agent.
        
        Args:
            agent_type: Type of agent
            agent: Agent instance
        """
        self._agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type.value}")

    async def process_goal(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """
        Main entry point for processing a task graph.
        
        Args:
            task_graph: Task graph to execute
            security_context: Security context
            
        Returns:
        """
        security_context = security_context or SecurityContext(
            user_id="system_orchestrator",
            is_authenticated=True,
            allowed_scopes=[PermissionScope.ADMIN]
        )
        graph_id = task_graph.graph_id
        self._active_graphs[graph_id] = task_graph
        
        # Persist initial state
        await self._persist_graph(task_graph)
        
        try:
            # Publish start event
            await self.event_bus.publish(Event(
                event_type="graph.started",
                source="Orchestrator",
                payload={
                    "graph_id": graph_id,
                    "goal": task_graph.goal_summary,
                    "node_count": len(task_graph.nodes)
                },
                priority=1
            ))
            
            # Risk assessment
            risk_result = await self._assess_risk(task_graph, security_context)
            task_graph.risk_level = RiskLevel[risk_result["risk_level"].upper()]
            
            # Tier-based Feature Gating
            node_count = len(task_graph.nodes)
            if not await billing_manager.check_feature_access(
                security_context.user_id, "max_nodes_per_graph", node_count
            ):
                raise PermissionError(
                    f"Task graph complexity (nodes: {node_count}) exceeds your tier limits."
                )

            # Execute based on mode
            if task_graph.execution_mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel(task_graph, security_context)
            elif task_graph.execution_mode == ExecutionMode.STREAMING:
                result = await self._execute_streaming(task_graph, security_context)
            elif task_graph.execution_mode == ExecutionMode.DISTRIBUTED:
                result = await self._execute_distributed(task_graph, security_context)
            else:
                # Default to sequential
                result = await self._execute_sequential(task_graph, security_context)
            
            # Store in memory
            await self._store_execution_memory(task_graph, result, security_context)
            
            # Final persist
            await self._persist_graph(task_graph)
            
            # Publish completion event
            await self.event_bus.publish(Event(
                event_type="graph.completed",
                source="Orchestrator",
                payload={
                    "graph_id": graph_id,
                    "status": result["status"],
                    "error_count": len(result["errors"])
                },
                priority=1
            ))
            
            return result
            
        except Exception as e:
            logger.exception(f"Error processing graph {graph_id}: {e}")
            
            await self.event_bus.publish(Event(
                event_type="graph.failed",
                source="Orchestrator",
                payload={
                    "graph_id": graph_id,
                    "error": str(e)
                },
                priority=2
            ))
            
            raise
        
        finally:
            # Cleanup
            if graph_id in self._active_graphs:
                del self._active_graphs[graph_id]

    async def _execute_sequential(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute tasks sequentially based on dependencies."""
        graph_id = task_graph.graph_id
        start_time = datetime.utcnow()
        
        errors = []
        completed_nodes = set()
        
        while True:
            # Get ready nodes
            ready_nodes = self._get_ready_nodes(task_graph, completed_nodes)
            
            if not ready_nodes:
                # Check if all nodes are complete
                if len(completed_nodes) == len(task_graph.nodes):
                    break
                
                # Check if we're stuck
                pending_nodes = [n for n in task_graph.nodes.values() if n.status == TaskStatus.PENDING]
                if pending_nodes:
                    # We're stuck - some dependencies failed
                    break
                
                break
            
            # Execute ready nodes
            for node in ready_nodes:
                try:
                    await self._execute_node(node, task_graph, security_context)
                    completed_nodes.add(node.node_id)
                except Exception as e:
                    logger.exception(f"Node {node.node_id} failed: {e}")
                    node.status = TaskStatus.FAILED
                    errors.append({
                        "node_id": node.node_id,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # Calculate final status
        all_success = all(node.status == TaskStatus.SUCCESS for node in task_graph.nodes.values())
        final_status = "success" if all_success else "partial_failure" if completed_nodes else "failed"
        
        task_graph.status = TaskStatus.SUCCESS if all_success else TaskStatus.FAILED
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "graph_id": graph_id,
            "goal": task_graph.goal_summary,
            "status": final_status,
            "risk_level": task_graph.risk_level.value,
            "completed_nodes": list(completed_nodes),
            "total_nodes": len(task_graph.nodes),
            "errors": errors,
            "execution_log": [log.__dict__ for log in self._execution_logs[graph_id]],
            "validation_results": [],
            "execution_time_seconds": execution_time
        }

    async def _execute_parallel(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """
        USP: Execute independent tasks in parallel for speed.
        
        Executes tasks concurrently when they don't depend on each other.
        """
        graph_id = task_graph.graph_id
        start_time = datetime.utcnow()
        
        errors = []
        completed_nodes = set()
        
        while True:
            # Get ready nodes
            ready_nodes = self._get_ready_nodes(task_graph, completed_nodes)
            
            if not ready_nodes:
                if len(completed_nodes) == len(task_graph.nodes):
                    break
                break
            
            # Execute ready nodes in parallel
            tasks = [
                self._execute_node(node, task_graph, security_context)
                for node in ready_nodes[:task_graph.max_parallel_tasks]
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                node = ready_nodes[i]
                if isinstance(result, Exception):
                    logger.exception(f"Node {node.node_id} failed: {result}")
                    node.status = TaskStatus.FAILED
                    errors.append({
                        "node_id": node.node_id,
                        "error": str(result),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    completed_nodes.add(node.node_id)
        
        # Calculate final status
        all_success = all(node.status == TaskStatus.SUCCESS for node in task_graph.nodes.values())
        final_status = "success" if all_success else "partial_failure" if completed_nodes else "failed"
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "graph_id": graph_id,
            "goal": task_graph.goal_summary,
            "status": final_status,
            "risk_level": task_graph.risk_level.value,
            "completed_nodes": list(completed_nodes),
            "total_nodes": len(task_graph.nodes),
            "errors": errors,
            "execution_log": [log.__dict__ for log in self._execution_logs[graph_id]],
            "validation_results": [],
            "execution_time_seconds": execution_time,
            "execution_mode": "parallel"
        }

    async def _execute_streaming(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """
        USP: Execute with real-time streaming updates.
        
        Provides progress updates as tasks execute.
        """
        # Similar to sequential but publishes streaming updates
        return await self._execute_sequential(task_graph, security_context)

    async def _execute_distributed(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """
        USP: Execute across distributed workers.
        Pushes independent tasks to Redis Task Queue.
        """
        graph_id = task_graph.graph_id
        start_time = datetime.utcnow()
        
        errors = []
        completed_nodes = set()
        
        # Subscribe to task completion events for this graph
        task_results = {}
        
        async def task_completion_handler(event: Event):
            payload = event.payload
            if payload.get("graph_id") == graph_id:
                node_id = payload.get("node_id")
                if payload.get("status") == "success":
                    task_results[node_id] = payload.get("result")
                else:
                    task_results[node_id] = Exception(payload.get("error"))
        
        self.event_bus.subscribe("task.completed", task_completion_handler)
        self.event_bus.subscribe("task.failed", task_completion_handler)
        
        total_credits_used = 0.0
        max_credits = self.config.get("max_credits", 1000.0)
        
        try:
            while True:
                # Cost Budgeting Check
                if total_credits_used >= max_credits:
                    logger.error(f"Cost Budget Exceeded: {total_credits_used}/{max_credits}. Terminating orchestration.")
                    errors.append({"node_id": "GLOBAL", "error": "Cost budget exceeded"})
                    break

                # Get ready nodes
                ready_nodes = self._get_ready_nodes(task_graph, completed_nodes)
                
                if not ready_nodes:
                    if len(completed_nodes) == len(task_graph.nodes):
                        break
                        
                    # Check if we're stuck
                    pending = [n for n in task_graph.nodes.values() if n.status == TaskStatus.PENDING]
                    running = [n for n in task_graph.nodes.values() if n.status == TaskStatus.RUNNING]
                    
                    if not running and pending:
                         # Stuck
                         break
                    if not running and not pending:
                         break
                         
                    # Wait for results
                    await asyncio.sleep(0.1)
                    
                    # Process received results
                    now = datetime.utcnow()
                    for node_id, result in list(task_results.items()):
                         if node_id in completed_nodes:
                             continue
                             
                         node = task_graph.nodes[node_id]
                         
                         # SLA Timeout Check
                         if node.status == TaskStatus.RUNNING and node.started_at:
                             timeout = node.timeout_seconds or 60.0
                             if (now - node.started_at).total_seconds() > timeout:
                                 logger.error(f"SLA Violation: Node {node_id} timed out")
                                 node.status = TaskStatus.FAILED
                                 errors.append({"node_id": node_id, "error": f"SLA Timeout ({timeout}s)"})
                                 continue

                         if isinstance(result, Exception):
                             logger.error(f"Node {node_id} failed remotely: {result}")
                             node.status = TaskStatus.FAILED
                             errors.append({"node_id": node_id, "error": str(result)})
                         else:
                             node.output_data = result
                             node.status = TaskStatus.SUCCESS
                             completed_nodes.add(node_id)
                             
                         # Persist update
                         await self._persist_graph(task_graph)
                         
                    continue
                
                # Backpressure check
                queue_size = await task_queue.get_queue_size()
                metrics_manager.update_queue_size(queue_size)
                
                if queue_size > self.config.get("max_queue_size", 100):
                    logger.warning(f"Backpressure: Queue size ({queue_size}) exceeds threshold. Throttling dispatch.")
                    await asyncio.sleep(1.0)
                    continue

                # Dispatch ready nodes
                for node in ready_nodes:
                    if node.status != TaskStatus.RUNNING: # Prevent double dispatch
                        # Increment credit usage before dispatch
                        total_credits_used += 1.0 # Standard cost per task
                        
                        node.status = TaskStatus.RUNNING
                        await task_queue.push_task(node, graph_id, priority=node.priority)
                        logger.info(f"Dispatched node {node.node_id} to worker queue")
                        
                        # Persist status change
                        await self._persist_graph(task_graph)

        finally:
            self.event_bus.unsubscribe("task.completed", task_completion_handler)
            self.event_bus.unsubscribe("task.failed", task_completion_handler)

        # Calculate final status
        all_success = all(node.status == TaskStatus.SUCCESS for node in task_graph.nodes.values())
        final_status = "success" if all_success else "partial_failure" if completed_nodes else "failed"
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "graph_id": graph_id,
            "goal": task_graph.goal_summary,
            "status": final_status,
            "risk_level": task_graph.risk_level.value,
            "completed_nodes": list(completed_nodes),
            "total_nodes": len(task_graph.nodes),
            "errors": errors,
            "execution_log": [], # Exec logs are on workers, need aggregation
            "execution_time_seconds": execution_time,
            "execution_mode": "distributed"
        }

    async def _execute_node(
        self,
        node: TaskNode,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute a single task node."""
        start_time = datetime.utcnow()
        node.status = TaskStatus.RUNNING
        node.started_at = start_time
        
        # Create execution log
        log = ExecutionLog(
            graph_id=task_graph.graph_id,
            node_id=node.node_id,
            agent_type=node.agent_type.value,
            action="execute",
            input_snapshot=node.input_data.copy(),
            status=TaskStatus.RUNNING,
            timestamp=start_time
        )
        self._execution_logs[task_graph.graph_id].append(log)
        
        # Publish streaming update
        await self._publish_streaming_update(
            task_graph.graph_id,
            node.node_id,
            "status",
            {"status": "running"}
        )
        
        # Persist state update
        await self._persist_graph(task_graph)
        
        try:
            # Get agent
            agent = self._get_agent(node.agent_type)
            
            # Execute with retry logic
            result = await self._execute_with_retry(agent, node, security_context)
            
            # Update node
            node.output_data = result
            node.status = TaskStatus.SUCCESS
            node.completed_at = datetime.utcnow()
            
            # Update log
            log.status = TaskStatus.SUCCESS
            log.output_snapshot = result.copy()
            log.duration_ms = (node.completed_at - start_time).total_seconds() * 1000
            
            # Validate if rule exists
            if node.validation_rule:
                validation_result = await self._validation_agent.run(node, security_context)
                
                if not validation_result.get("valid"):
                    # Validation failed
                    node.status = TaskStatus.FAILED
                    raise ValueError(f"Validation failed: {validation_result.get('message')}")
            
            # Publish success update
            await self._publish_streaming_update(
                task_graph.graph_id,
                node.node_id,
                "output",
                result
            )
            
            self._total_tasks_executed += 1
            
            return result
            
        except Exception as e:
            # Update node
            node.status = TaskStatus.FAILED
            node.completed_at = datetime.utcnow()
            node.error_log.append(str(e))
            
            # Persist state update (failure)
            await self._persist_graph(task_graph)
            
            # Update log
            log.status = TaskStatus.FAILED
            log.error_message = str(e)
            log.duration_ms = (node.completed_at - start_time).total_seconds() * 1000
            
            # Publish error update
            await self._publish_streaming_update(
                task_graph.graph_id,
                node.node_id,
                "error",
                {"error": str(e)}
            )
            
            self._total_tasks_failed += 1
            
            raise

    async def _execute_with_retry(
        self,
        agent: BaseAgent,
        node: TaskNode,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute node with retry logic."""
        max_retries = node.retry_config.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                result = await agent.run(node, security_context)
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    # Calculate delay
                    delay = self._calculate_retry_delay(node, attempt)
                    
                    logger.warning(
                        f"Node {node.node_id} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay}s: {e}"
                    )
                    
                    node.retries = attempt + 1
                    
                    # Wait before retry
                    await asyncio.sleep(delay)
                else:
                    raise

    def _calculate_retry_delay(self, node: TaskNode, attempt: int) -> float:
        """Calculate retry delay based on strategy."""
        config = node.retry_config
        
        if config.strategy.value == "fixed":
            return config.initial_delay_seconds
        
        elif config.strategy.value == "linear":
            return config.initial_delay_seconds * (attempt + 1)
        
        elif config.strategy.value == "exponential_backoff":
            delay = config.initial_delay_seconds * (config.backoff_multiplier ** attempt)
            delay = min(delay, config.max_delay_seconds)
            
            # Add jitter
            if config.jitter:
                import random
                delay *= (0.5 + random.random())
            
            return delay
        
        elif config.strategy.value == "fibonacci":
            fib = [1, 1]
            for i in range(attempt):
                fib.append(fib[-1] + fib[-2])
            return config.initial_delay_seconds * fib[min(attempt, len(fib) - 1)]
        
        else:
            return config.initial_delay_seconds

    def _get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get agent instance by type."""
        if agent_type == AgentType.SECURITY:
            return self._security_agent
        elif agent_type == AgentType.VALIDATION:
            return self._validation_agent
        elif agent_type == AgentType.MEMORY:
            return self._memory_agent
        elif agent_type in self._agents:
            return self._agents[agent_type]
        else:
            raise ValueError(f"Agent not registered: {agent_type.value}")

    def _get_ready_nodes(
        self,
        task_graph: TaskGraph,
        completed: Set[str]
    ) -> List[TaskNode]:
        """Get nodes that are ready to execute."""
        ready = []
        
        for node in task_graph.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are complete
            deps_met = all(dep in completed for dep in node.dependencies)
            
            if deps_met:
                ready.append(node)
        
        # Sort by priority
        ready.sort(key=lambda n: n.priority, reverse=True)
        
        return ready

    async def _assess_risk(
        self,
        task_graph: TaskGraph,
        security_context: SecurityContext
    ) -> Dict[str, Any]:
        """Assess risk level of task graph."""
        # Create temporary node for risk assessment
        temp_node = TaskNode(
            name="risk_assessment",
            agent_type=AgentType.SECURITY,
            input_data={
                "action": "assess_risk",
                "task_graph": task_graph
            },
            required_permissions=[]
        )
        
        # Find highest risk node
        max_risk_score = 0.0
        
        for node in task_graph.nodes.values():
            temp_node.input_data = {
                "action": "assess_risk"
            }
            temp_node.required_permissions = node.required_permissions
            
            result = await self._security_agent.execute(temp_node, security_context)
            risk_score = result.get("risk_score", 0.0)
            max_risk_score = max(max_risk_score, risk_score)
        
        # Determine overall risk level
        if max_risk_score >= 0.8:
            risk_level = "critical"
        elif max_risk_score >= 0.6:
            risk_level = "high"
        elif max_risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "risk_score": max_risk_score
        }

    async def _store_execution_memory(
        self,
        task_graph: TaskGraph,
        result: Dict[str, Any],
        security_context: SecurityContext
    ):
        """Store execution in memory for learning."""
        memory_node = TaskNode(
            name="store_memory",
            agent_type=AgentType.MEMORY,
            input_data={
                "action": "store",
                "goal_summary": task_graph.goal_summary,
                "task_graph": task_graph.__dict__,
                "execution_logs": result.get("execution_log", []),
                "errors": result.get("errors", []),
                "category": "orchestrated_execution",
                "tags": [f"risk:{task_graph.risk_level.value}", f"status:{result['status']}"]
            }
        )
        
        try:
            await self._memory_agent.execute(memory_node, security_context)
        except Exception as e:
            logger.exception(f"Failed to store memory: {e}")

    async def _publish_streaming_update(
        self,
        graph_id: str,
        node_id: str,
        update_type: str,
        data: Dict[str, Any]
    ):
        """Publish real-time streaming update."""
        update = StreamingUpdate(
            graph_id=graph_id,
            node_id=node_id,
            update_type=update_type,
            data=data,
            sequence=len(self._streaming_updates[graph_id])
        )
        
        self._streaming_updates[graph_id].append(update)
        
        await self.event_bus.publish(Event(
            event_type=f"stream.{update_type}",
            source="Orchestrator",
            payload=update.__dict__
        ))

    def get_health(self) -> HealthMetrics:
        """Get system health metrics."""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        avg_time = (
            self._total_execution_time_ms / self._total_tasks_executed
            if self._total_tasks_executed > 0
            else 0.0
        )
        
        error_rate = (
            self._total_tasks_failed / self._total_tasks_executed
            if self._total_tasks_executed > 0
            else 0.0
        )
        
        return HealthMetrics(
            active_tasks=len(self._active_graphs),
            completed_tasks=self._total_tasks_executed,
            failed_tasks=self._total_tasks_failed,
            avg_execution_time_ms=avg_time,
            uptime_seconds=uptime,
            error_rate=error_rate
        )

    async def _persist_graph(self, task_graph: TaskGraph):
        """Persist graph state to database."""
        try:
            state_json = self._serialize_graph(task_graph)
            
            async with await db_manager.get_session() as session:
                # Upsert logic (merge)
                await session.merge(TaskGraphModel(
                    id=task_graph.graph_id,
                    status=task_graph.status.value if hasattr(task_graph.status, 'value') else str(task_graph.status),
                    state_json=state_json,
                    updated_at=datetime.utcnow()
                ))
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to persist graph state: {e}")

    def _serialize_graph(self, task_graph: TaskGraph) -> str:
        """Serialize task graph to JSON safely."""
        # Simple serialization helper
        def default(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            if hasattr(o, "value"): # Enum
                return o.value
            if hasattr(o, "__dict__"):
                return o.__dict__
            return str(o)
            
        return json.dumps(task_graph.__dict__, default=default)
