import logging
from typing import Optional, Dict, Any
from goatclaw.database import db_manager, UserAccountModel
from sqlalchemy import select, update

logger = logging.getLogger("goatclaw.core.billing")

class BillingManager:
    """
    USP: Monetize platform orchestration and specialist agents.
    Handles feature gating, credit deduction, and subscription tiers.
    """
    
    # Feature limits per tier
    TIER_LIMITS = {
        "free": {
            "max_concurrent_agents": 2,
            "max_nodes_per_graph": 5,
            "premium_agents": False
        },
        "pro": {
            "max_concurrent_agents": 10,
            "max_nodes_per_graph": 50,
            "premium_agents": True
        },
        "enterprise": {
            "max_concurrent_agents": 100,
            "max_nodes_per_graph": 500,
            "premium_agents": True
        }
    }

    # Costs in credits
    COSTS = {
        "orchestration_cycle": 0.1,  # Cost per task execution
        "premium_agent_activation": 1.0
    }

    async def get_user_account(self, user_id: str) -> Dict[str, Any]:
        """Get user account details."""
        async with await db_manager.get_session() as session:
            stmt = select(UserAccountModel).where(UserAccountModel.user_id == user_id)
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            
            if not account:
                # Create default free account
                account = UserAccountModel(user_id=user_id, balance_credits=0.0, tier="free")
                session.add(account)
                await session.commit()
            
            return {
                "user_id": account.user_id,
                "balance": account.balance_credits,
                "tier": account.tier
            }

    async def check_feature_access(self, user_id: str, feature: str, value: Any) -> bool:
        """Check if user tier allows access to a specific feature/value."""
        account = await self.get_user_account(user_id)
        limits = self.TIER_LIMITS.get(account["tier"], self.TIER_LIMITS["free"])
        
        limit_value = limits.get(feature)
        if limit_value is None:
            return False
            
        if isinstance(limit_value, bool):
            return limit_value == value if isinstance(value, bool) else limit_value
        
        return value <= limit_value

    async def deduct_credits(self, user_id: str, amount: float, reason: str) -> bool:
        """Deduct credits from user balance."""
        async with await db_manager.get_session() as session:
            stmt = select(UserAccountModel).where(UserAccountModel.user_id == user_id)
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            
            if not account:
                logger.error(f"Account not found for {user_id}")
                return False
                
            if account.balance_credits < amount:
                logger.warning(f"Insufficient credits for user {user_id}: {amount} requested")
                return False
            
            account.balance_credits -= amount
            await session.commit()
            logger.info(f"Deducted {amount} credits from {user_id} for {reason}")
            return True

    async def top_up(self, user_id: str, amount: float):
        """Add credits to user balance (Post-payment)."""
        async with await db_manager.get_session() as session:
            stmt = select(UserAccountModel).where(UserAccountModel.user_id == user_id)
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            
            if not account:
                account = UserAccountModel(user_id=user_id, balance_credits=amount, tier="free")
                session.add(account)
            else:
                account.balance_credits += amount
            
            await session.commit()
            logger.info(f"Topped up {amount} credits for {user_id}")

# Global Billing Manager Instance
billing_manager = BillingManager()
