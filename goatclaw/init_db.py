import asyncio
import logging
from goatclaw.database import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("goatclaw.init_db")

async def init_db():
    """Initialize database tables."""
    try:
        logger.info("Creating tables...")
        await db_manager.init_db()
        
        # Seed demo user for CLI
        from goatclaw.database import UserAccountModel
        async with await db_manager.get_session() as session:
            # Check if demo-user exists
            from sqlalchemy import select
            stmt = select(UserAccountModel).where(UserAccountModel.user_id == "demo-user")
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                logger.info("Seeding demo-user with 1000 credits...")
                demo_user = UserAccountModel(
                    user_id="demo-user",
                    balance_credits=1000.0,
                    tier="enterprise"
                )
                session.add(demo_user)
                await session.commit()
        
        logger.info("Database initialized and demo-user seeded successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Hint about connection string
        logger.info("Ensure DATABASE_URL environment variable is set correctly.")

if __name__ == "__main__":
    asyncio.run(init_db())
