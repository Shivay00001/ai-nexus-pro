import json
import logging
from typing import Any, Dict, Optional, List
from goatclaw.agents.base_agent import BaseAgent
from goatclaw.core.event_bus import EventBus
from goatclaw.core.structs import TaskNode, TaskGraph, AgentType, ExecutionMode, SecurityContext

logger = logging.getLogger("goatclaw.agents.planner")

class PlannerAgent(BaseAgent):
    """
    USP: Dynamic goal decomposition and task graph generation.
    
    Transforms natural language goals into executable TaskGraphs.
    """
    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("PlannerAgent", event_bus, config)
        self._available_agents = [a.value for a in AgentType]

    async def plan(self, goal: str, context: SecurityContext) -> TaskGraph:
        """Generate a TaskGraph from a goal string."""
        logger.info(f"Planning goal: {goal}")
        
        prompt = f"""
        You are the GOATCLAW Planning Agent. Your task is to decompose a high-level goal into a sequence of actionable task nodes.
        
        Goal: {goal}
        
        Available Agent Types: {self._available_agents}
        
        Output format: A JSON object representing a TaskGraph with the following structure:
        {{
            "goal_summary": "...",
            "execution_mode": "sequential" | "parallel",
            "nodes": [
                {{
                    "node_id": "...",
                    "name": "...",
                    "agent_type": "...",
                    "input_data": {{ ... }},
                    "dependencies": ["node_id1", "..."]
                }}
            ]
        }}
        
        Rules:
        1. Use only the available agent types.
        2. Ensure all dependencies reference existing node_ids.
        3. Keep input_data relevant to the specific agent type.
        4. Output ONLY the JSON object.
        """
        
        response = await self._call_llm(prompt, system="You are an expert system architect.")
        
        try:
            # Extract JSON
            if "{" in response:
                json_part = response[response.find("{"):response.rfind("}")+1]
                data = json.loads(json_part)
            else:
                raise ValueError("No JSON found in LLM response")
                
            # Construct TaskGraph
            graph = TaskGraph(
                goal_summary=data.get("goal_summary", goal),
                execution_mode=ExecutionMode(data.get("execution_mode", "sequential"))
            )
            
            node_map = {}
            for node_data in data.get("nodes", []):
                node = TaskNode(
                    node_id=node_data.get("node_id"),
                    name=node_data.get("name"),
                    agent_type=AgentType(node_data.get("agent_type")),
                    input_data=node_data.get("input_data", {}),
                    dependencies=node_data.get("dependencies", [])
                )
                graph.add_node(node)
                node_map[node.node_id] = node
                
            return graph
            
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            # Fallback to a simple 1-node graph
            fallback_node = TaskNode(
                name="fallback_task",
                agent_type=AgentType.RESEARCH,
                input_data={"query": goal, "action": "search"}
            )
            fallback_graph = TaskGraph(goal_summary=goal)
            fallback_graph.add_node(fallback_node)
            return fallback_graph

    async def execute(self, task_node: TaskNode, context: SecurityContext) -> Dict[str, Any]:
        """Planner can also be executed as a node (self-correction/replanning)."""
        goal = task_node.input_data.get("goal", "")
        graph = await self.plan(goal, context)
        return {"status": "planned", "graph_id": graph.graph_id}
