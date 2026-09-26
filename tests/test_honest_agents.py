"""Honesty tests for the agent layer.

Every test below asserts that the system does NOT fabricate results:
LLM-dependent actions without a key must report degraded/unavailable,
search with no coverage must say so explicitly, and validation rules
must evaluate real dict outputs inside a hardened sandbox.
"""
import pytest

from goatclaw.agents.validation_agent import ValidationAgent
from goatclaw.agents.planner_agent import PlannerAgent
from goatclaw.core.structs import TaskNode, AgentType, SecurityContext
from goatclaw.specialists import ResearchAgent, CodeAgent


def _node(agent_type, input_data, validation_rule=None):
    return TaskNode(
        node_id="test_node",
        agent_type=agent_type,
        input_data=input_data,
        validation_rule=validation_rule,
    )


# ---------------------------------------------------------------------------
# Validation: dict-aware rules + sandbox
# ---------------------------------------------------------------------------

async def test_validation_dict_attribute_rule(event_bus):
    """The reported defect: rules like ``output.confidence > 0.5`` on dict
    outputs used to raise AttributeError. They must now evaluate."""
    agent = ValidationAgent(event_bus)
    node = _node(
        AgentType.RESEARCH,
        {},
        validation_rule="output.confidence > 0.5",
    )
    node.output_data = {"confidence": 0.85, "status": "ok"}
    result = await agent.execute(node, None)
    assert result["valid"] is True


async def test_validation_nested_dict_and_subscript(event_bus):
    agent = ValidationAgent(event_bus)
    node = _node(
        AgentType.RESEARCH,
        {},
        validation_rule="output.nested.x == 1 and output['status'] == 'ok'",
    )
    node.output_data = {"nested": {"x": 1}, "status": "ok"}
    result = await agent.execute(node, None)
    assert result["valid"] is True


async def test_validation_failing_rule(event_bus):
    agent = ValidationAgent(event_bus)
    node = _node(AgentType.RESEARCH, {}, validation_rule="output.confidence < 0.5")
    node.output_data = {"confidence": 0.9}
    result = await agent.execute(node, None)
    assert result["valid"] is False


@pytest.mark.parametrize("evil", [
    "output.__class__.__name__ == 'dict'",
    "__import__('os').system('id')",
    "eval('1+1')",
    "open('/etc/passwd').read()",
    "getattr(output, 'keys')()",
])
async def test_validation_sandbox_blocks_escapes(event_bus, evil):
    """Dunder access, imports, eval/exec, open, and getattr must be
    rejected by the sandbox -- never executed."""
    agent = ValidationAgent(event_bus)
    node = _node(AgentType.RESEARCH, {}, validation_rule=evil)
    node.output_data = {"confidence": 0.9}
    result = await agent.execute(node, None)
    assert result["valid"] is False
    assert "sandbox" in result["message"].lower() or "rejected" in result["message"].lower()


# ---------------------------------------------------------------------------
# CodeAgent: no LLM key -> honest degraded, never fake code
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("action,extra", [
    ("generate", {"spec": "reverse a string", "language": "python"}),
    ("review", {"code": "x = 1"}),
    ("refactor", {"code": "x = 1"}),
    ("test", {"code": "x = 1"}),
])
async def test_codeagent_no_key_is_honestly_degraded(event_bus, db, no_llm_keys, action, extra):
    agent = CodeAgent(event_bus)
    node = _node(AgentType.CODE, {"action": action, **extra})
    result = await agent.execute(node, None)
    assert result["status"] == "degraded", result
    assert result.get("llm_required") is True
    assert "API key" in (result.get("error") or "")


# ---------------------------------------------------------------------------
# ResearchAgent: real search, no fabrication
# ---------------------------------------------------------------------------

async def test_search_no_fabrication_on_sparse_query(event_bus, db, no_llm_keys):
    """A query no free provider can answer must return an explicit
    'unavailable' error -- never example.com placeholder links."""
    agent = ResearchAgent(event_bus)
    node = _node(
        AgentType.RESEARCH,
        {"action": "search", "query": "Python async/await best practices 2025"},
    )
    result = await agent.execute(node, None)
    assert result["status"] == "degraded"
    assert result["results"] == []
    error = result.get("error") or ""
    assert "Web search unavailable" in error
    assert "SERPER_API_KEY" in error
    # No fabricated links, ever.
    for hit in result["results"]:
        assert "example.com" not in hit.get("url", "")


async def test_search_returns_real_results(event_bus, db, no_llm_keys):
    """A query the free DuckDuckGo fallback genuinely covers must return
    real results with real URLs."""
    import aiohttp

    agent = ResearchAgent(event_bus)
    node = _node(
        AgentType.RESEARCH,
        {"action": "search", "query": "Python programming language"},
    )
    try:
        result = await agent.execute(node, None)
    except (aiohttp.ClientError, OSError) as e:
        pytest.skip(f"network unavailable for live search test: {e}")
    assert result["status"] == "success", result.get("error")
    assert result["result_count"] >= 1
    first = result["results"][0]
    assert first["url"].startswith("http")
    assert "example.com" not in first["url"]
    assert result["provider"] == "duckduckgo"


# ---------------------------------------------------------------------------
# Planner: no LLM key -> explicitly degraded fallback graph
# ---------------------------------------------------------------------------

async def test_planner_fallback_marked_degraded(event_bus, db, no_llm_keys):
    planner = PlannerAgent(event_bus)
    ctx = SecurityContext(user_id="test-user", is_authenticated=True)
    graph = await planner.plan("Write a python function to reverse a string", ctx)
    assert graph.metadata.get("degraded") is True
    reason = graph.metadata.get("degradation_reason") or ""
    assert "OPENAI_API_KEY" in reason
    assert len(graph.nodes) == 1  # single-node heuristic fallback


# ---------------------------------------------------------------------------
# Memory: persistence round-trip (json + to_dict)
# ---------------------------------------------------------------------------

async def test_memory_store_and_recall_roundtrip(event_bus, db):
    from goatclaw.agents.memory_agent import MemoryAgent

    agent = MemoryAgent(event_bus)
    store_node = _node(AgentType.MEMORY, {
        "action": "store",
        "category": "test",
        "goal_summary": "honesty roundtrip probe",
        "tags": ["probe"],
    })
    stored = await agent.execute(store_node, None)
    assert stored["stored"] is True
    record_id = stored["record_id"]

    recall_node = _node(AgentType.MEMORY, {
        "action": "recall",
        "record_id": record_id,
    })
    recalled = await agent.execute(recall_node, None)
    assert recalled["found"] is True
    assert recalled["record"]["goal_summary"] == "honesty roundtrip probe"
