import aiohttp
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("goatclaw.core.ollama")

class OllamaClient:
    """
    Client for interacting with local Ollama models.
    USP: Local-first, cost-efficient model execution.
    """
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        logger.info(f"OllamaClient initialized with base_url: {base_url}")

    async def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        """Generate response from local model."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama error: {error_text}")
                        raise ValueError(f"Ollama API error: {response.status}")
                    
                    data = await response.json()
                    return data.get("response", "")
        except Exception as e:
            logger.error(f"Failed to communicate with Ollama: {e}")
            raise

    async def chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Chat with local model."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama error: {error_text}")
                        raise ValueError(f"Ollama API error: {response.status}")
                    
                    data = await response.json()
                    return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Failed to communicate with Ollama: {e}")
            raise

# Global Ollama Client Instance
ollama_client = OllamaClient()
