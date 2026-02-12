import asyncio
import logging
import os
import uuid

# Set env vars
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_billing.db"
if os.path.exists("test_billing.db"):
    os.remove("test_billing.db")

import sys
import goatclaw
print(f"DEBUG: sys.path: {sys.path}")
print(f"DEBUG: goatclaw location: {goatclaw.__file__}")

from goatclaw.database import db_manager, UserAccountModel
from goatclaw.core.billing import billing_manager
from goatclaw.orchestrator import Orchestrator
from goatclaw.core.structs import TaskGraph, TaskNode, SecurityContext, PermissionScope, AgentType
from goatclaw.specialists import CodeAgent

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_monetization")

async def test_feature_gating():
    logger.info("--- Testing Feature Gating ---")
    user_id = "free_user_1"
    
    # 1. Create limited graph (5 nodes is limit for free)
    nodes = {f"n{i}": TaskNode(node_id=f"n{i}", agent_type=AgentType.CODE, input_data={}) for i in range(6)}
    graph = TaskGraph(goal_summary="Too many nodes", nodes=nodes)
    
    context = SecurityContext(user_id=user_id, allowed_scopes=[PermissionScope.ADMIN])
    
    orch = Orchestrator()
    try:
        await orch.process_goal(graph, context)
        logger.error("❌ Should have failed node count check")
    except PermissionError as e:
        logger.info(f"✅ Correctly blocked: {e}")

async def test_credit_deduction():
    logger.info("--- Testing Credit Deduction ---")
    user_id = "paying_user_1"
    
    # Top up
    await billing_manager.top_up(user_id, 10.0)
    
    # Run a simple task
    orch = Orchestrator()
    orch.register_agent(AgentType.CODE, CodeAgent(orch.event_bus))
    
    node = TaskNode(node_id="billing_task", agent_type=AgentType.CODE, input_data={"action": "generate", "spec": "print('hello')"})
    graph = TaskGraph(goal_summary="Test billing", nodes={"billing_task": node})
    context = SecurityContext(user_id=user_id, allowed_scopes=[PermissionScope.ADMIN])
    
    initial_balance = (await billing_manager.get_user_account(user_id))["balance"]
    logger.info(f"Initial Balance: {initial_balance}")
    
    await orch.process_goal(graph, context)
    
    final_balance = (await billing_manager.get_user_account(user_id))["balance"]
    logger.info(f"Final Balance: {final_balance}")
    
    expected_cost = billing_manager.COSTS["orchestration_cycle"]
    assert abs((initial_balance - final_balance) - expected_cost) < 0.0001
    logger.info("✅ Credit deduction works!")

async def main():
    try:
        await db_manager.init_db()
        await test_feature_gating()
        await test_credit_deduction()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
