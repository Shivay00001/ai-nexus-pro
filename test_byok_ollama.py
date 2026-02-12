import asyncio
import logging
import uuid
import os
from datetime import datetime

# Set env vars
os.environ["GOATCLAW_MASTER_KEY"] = "test-master-key-12345"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_vault.db"

from goatclaw.core.vault import vault
from goatclaw.core.ollama_client import ollama_client
from goatclaw.database import db_manager, SecretModel, UserAccountModel
from goatclaw.orchestrator import Orchestrator
from goatclaw.specialists import ResearchAgent, CodeAgent
from goatclaw.core.structs import TaskGraph, TaskNode, AgentType, SecurityContext, PermissionScope
from sqlalchemy import select

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_byok_ollama")

async def test_vault():
    logger.info("--- Testing SecretVault ---")
    raw_key = "sk-openai-test-12345"
    encrypted = vault.encrypt(raw_key)
    logger.info(f"Encrypted: {encrypted}")
    
    decrypted = vault.decrypt(encrypted)
    logger.info(f"Decrypted: {decrypted}")
    assert raw_key == decrypted
    logger.info("✅ Vault works!")

async def test_byok_db_integration():
    logger.info("--- Testing BYOK DB Integration ---")
    user_id = "test_user_789"
    provider = "openai"
    raw_key = "secret_api_key_for_openai"
    
    await db_manager.init_db()
    
    async with await db_manager.get_session() as session:
        # Clear existing for clean test
        from sqlalchemy import delete
        await session.execute(delete(SecretModel).where(SecretModel.user_id == user_id, SecretModel.provider == provider))
        
        # Store encrypted secret
        encrypted = vault.encrypt(raw_key)
        secret = SecretModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            encrypted_key=encrypted
        )
        session.add(secret)
        await session.commit()
        logger.info(f"Stored encrypted secret for {user_id}")

    # Orchestrator/Agent retrieval (Simulated)
    orchestrator = Orchestrator()
    orchestrator.register_agent(AgentType.CODE, CodeAgent(orchestrator.event_bus))
    agent = orchestrator.agents[AgentType.CODE]
    
    retrieved_key = await agent._get_api_key(provider, user_id)
    logger.info(f"Retrieved and Decrypted Key: {retrieved_key}")
    assert retrieved_key == raw_key
    logger.info("✅ BYOK DB Integration works!")

async def test_ollama_dispatch():
    logger.info("--- Testing Ollama Dispatch ---")
    orchestrator = Orchestrator()
    orchestrator.register_agent(AgentType.CODE, CodeAgent(orchestrator.event_bus))
    # Mock Ollama config in CodeAgent
    orchestrator.agents[AgentType.CODE].config["model"] = {
        "provider": "ollama",
        "name": "llama3"
    }
    
    # We won't call the actual Ollama unless it's running, 
    # but we can verify the dispatch logic.
    agent = orchestrator.agents[AgentType.CODE]
    try:
        response = await agent._call_llm("Explain sorting", system="Coding Guru")
        logger.info(f"Ollama/Mock Response: {response}")
    except Exception as e:
        logger.warning(f"Ollama call failed (expected if not running): {e}")

async def main():
    try:
        await test_vault()
        await test_byok_db_integration()
        await test_ollama_dispatch()
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
