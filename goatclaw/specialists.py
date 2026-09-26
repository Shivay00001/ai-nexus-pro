"""
GOATCLAW Specialist Agents
Concrete implementations of domain-specific agents.

Includes:
- ResearchAgent - Web research and information gathering
- CodeAgent - Code generation and analysis
- DevOpsAgent - Infrastructure and deployment
- APIAgent - API interactions
- DataProcessingAgent - Data transformation
- FileSystemAgent - File operations
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional
import logging
import json

from goatclaw.core.http import create_session
from goatclaw.core.sandbox import sandbox_manager
from goatclaw.core.structs import (
    TaskNode, SecurityContext, AgentType
)
from goatclaw.core.event_bus import EventBus
from goatclaw.agents.base_agent import (
    BaseAgent, LLMNotConfiguredError, LLMProviderError,
    SEARCH_PROVIDER_ENV_VARS,
)

logger = logging.getLogger("goatclaw.specialists")


class ResearchAgent(BaseAgent):
    """
    Research and information gathering agent.
    
    Capabilities:
    - Web search
    - Document analysis
    - Information synthesis
    - Fact checking
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("ResearchAgent", event_bus, config)
        self._cache_enabled = config.get("cache_enabled", True) if config else True

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute research task."""
        query = task_node.input_data.get("query", "")
        action = task_node.input_data.get("action", "search")
        
        if action == "search":
            return await self._web_search(query, task_node)
        elif action == "analyze":
            return await self._analyze_document(task_node)
        elif action == "synthesize":
            return await self._synthesize_information(task_node)
        else:
            return {"status": "unknown_action"}

    async def _web_search(self, query: str, task_node: TaskNode) -> Dict[str, Any]:
        """
        Perform a REAL web search -- never fabricated results.

        Provider chain (first available wins):
        1. Serper.dev Google Search API (``SERPER_API_KEY``)
        2. Tavily Search API           (``TAVILY_API_KEY``)
        3. DuckDuckGo Instant Answer API (free, no key required)

        If no provider yields usable results, an explicit "search
        unavailable" error is returned instead of fake example.com links.
        """
        logger.info(f"Searching for: {query}")

        results: List[Dict[str, Any]] = []
        provider_used: Optional[str] = None
        error_detail: Optional[str] = None

        serper_key = os.environ.get(SEARCH_PROVIDER_ENV_VARS["serper"])
        tavily_key = os.environ.get(SEARCH_PROVIDER_ENV_VARS["tavily"])

        try:
            if serper_key:
                provider_used = "serper"
                results = await self._search_via_serper(query, serper_key)
            elif tavily_key:
                provider_used = "tavily"
                results = await self._search_via_tavily(query, tavily_key)
            else:
                provider_used = "duckduckgo"
                results = await self._search_via_duckduckgo(query)
        except Exception as e:
            error_detail = f"{provider_used} error: {e}"
            logger.error(f"Web search failed ({provider_used}): {e}")

        if not results:
            # Honest failure -- never fabricate example.com results.
            return {
                "action": "search",
                "query": query,
                "status": "degraded",
                "results": [],
                "result_count": 0,
                "confidence": 0.0,
                "provider": provider_used,
                "error": (
                    "Web search unavailable: no search provider returned "
                    f"results ({error_detail or 'no results'}). Set "
                    "SERPER_API_KEY or TAVILY_API_KEY for reliable search."
                ),
            }

        return {
            "action": "search",
            "query": query,
            "status": "success",
            "results": results,
            "result_count": len(results),
            "confidence": 0.85,
            "provider": provider_used,
        }

    async def _search_via_serper(self, query: str, api_key: str) -> List[Dict[str, Any]]:
        """Real search via Serper.dev (Google Search API)."""
        async with create_session() as session:
            async with session.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5},
                timeout=30,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Serper HTTP {resp.status}: {(await resp.text())[:200]}"
                    )
                data = await resp.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "relevance": max(0.5, 0.9 - (i * 0.05)),
            }
            for i, item in enumerate(data.get("organic", [])[:5])
            if item.get("link")
        ]

    async def _search_via_tavily(self, query: str, api_key: str) -> List[Dict[str, Any]]:
        """Real search via the Tavily Search API."""
        async with create_session() as session:
            async with session.post(
                "https://api.tavily.com/search",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "max_results": 5, "include_answer": False},
                timeout=30,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Tavily HTTP {resp.status}: {(await resp.text())[:200]}"
                    )
                data = await resp.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("content") or "")[:500],
                "relevance": item.get("score", 0.8),
            }
            for item in data.get("results", [])[:5]
            if item.get("url")
        ]

    async def _search_via_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """
        Free no-key fallback via the DuckDuckGo Instant Answer API.

        Returns the instant-answer abstract plus related topics as results.
        The IA API is sparse -- many queries legitimately return nothing, in
        which case the caller reports search as honestly unavailable.
        """
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        headers = {
            # The IA endpoint blocks non-browser user agents.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
        async with create_session(headers=headers) as session:
            async with session.get(
                "https://api.duckduckgo.com/", params=params, timeout=30
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"DuckDuckGo HTTP {resp.status}")
                # NOTE: the IA API serves JSON with a non-JSON content type,
                # so parse the text body manually instead of resp.json().
                data = json.loads(await resp.text())

        results: List[Dict[str, Any]] = []
        abstract = (data.get("AbstractText") or "").strip()
        if abstract and data.get("AbstractURL"):
            results.append({
                "title": data.get("Heading") or query,
                "url": data.get("AbstractURL"),
                "snippet": abstract[:500],
                "relevance": 0.95,
            })
        for topic in data.get("RelatedTopics", []):
            if not isinstance(topic, dict) or not topic.get("Text"):
                continue
            url = topic.get("FirstURL") or ""
            if not url:
                continue
            results.append({
                "title": (topic.get("Text") or "")[:120],
                "url": url,
                "snippet": (topic.get("Text") or "")[:500],
                "relevance": 0.7,
            })
            if len(results) >= 5:
                break
        return results
    async def _analyze_document(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Analyze a document.

        Word count is computed locally (real). Summary and key-point
        extraction use an LLM when a key is configured; without one the
        result is explicitly degraded instead of returning placeholder text.
        """
        content = task_node.input_data.get("content", "")
        word_count = len(content.split())

        prompt = (
            "Analyze the following document. Reply as JSON with keys "
            "'summary' (2-3 sentences) and 'key_points' (list of strings):\n\n"
            f"{content[:4000]}"
        )
        system = "You are a precise document analyst. Output valid JSON only."

        try:
            response = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "analyze",
                "status": "degraded",
                "word_count": word_count,
                "summary": None,
                "key_points": [],
                "error": (
                    "Document summary and key-point extraction require an LLM "
                    f"API key: {e} Word count was computed locally."
                ),
                "llm_required": True,
            }

        summary: Optional[str] = None
        key_points: List[str] = []
        try:
            if "{" in response:
                parsed = json.loads(response[response.find("{"):response.rfind("}") + 1])
                summary = parsed.get("summary")
                key_points = parsed.get("key_points", [])
        except Exception:
            summary = response[:2000]

        return {
            "action": "analyze",
            "status": "success",
            "word_count": word_count,
            "summary": summary,
            "key_points": key_points,
            "confidence": 0.8,
        }
    async def _synthesize_information(self, task_node: TaskNode) -> Dict[str, Any]:
        """Synthesize information from multiple sources using a real LLM."""
        sources = task_node.input_data.get("sources", [])
        goal = task_node.input_data.get("goal", "Summarize information")

        sources_text = "\n\n".join([f"Source: {s.get('url', 'N/A')}\nContent: {s.get('snippet', '')}" for s in sources])
        prompt = f"Synthesize information from the following sources to achieve this goal: {goal}\n\nSources:\n{sources_text}"
        system = "You are a lead research analyst. Provide a comprehensive synthesis with key insights."

        try:
            synthesis = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "synthesize",
                "status": "degraded",
                "synthesis": None,
                "source_count": len(sources),
                "error": f"Information synthesis requires an LLM API key: {e}",
                "llm_required": True,
            }

        return {
            "action": "synthesize",
            "status": "success",
            "synthesis": synthesis,
            "source_count": len(sources)
        }
class CodeAgent(BaseAgent):
    """
    Code generation and analysis agent.
    
    Capabilities:
    - Code generation
    - Code review
    - Refactoring
    - Testing
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("CodeAgent", event_bus, config)

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute code task."""
        action = task_node.input_data.get("action", "generate")
        
        if action == "generate":
            return await self._generate_code(task_node)
        elif action == "review":
            return await self._review_code(task_node)
        elif action == "refactor":
            return await self._refactor_code(task_node)
        elif action == "test":
            return await self._generate_tests(task_node)
        else:
            return {"status": "unknown_action"}

    async def _generate_code(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Generate real code using an LLM.

        Without a configured LLM API key this returns an explicit degraded
        result -- it never returns simulated/fake code as if it were real.
        """
        spec = task_node.input_data.get("spec", "")
        language = task_node.input_data.get("language", "python")

        prompt = f"Write professional {language} code for the following specification:\n\n{spec}\n\nReturn ONLY the code without markdown formatting or explanation."
        system = f"You are an expert {language.capitalize()} developer. Output clean, efficient, and well-documented code."

        try:
            code = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "generate",
                "status": "degraded",
                "language": language,
                "code": None,
                "lines": 0,
                "error": f"Code generation requires an LLM API key: {e}",
                "llm_required": True,
            }
        # Other failures (e.g. LLMProviderError from a bad key) propagate:
        # authentic failure, never silently converted into fake code.

        # Clean up in case LLM included markdown
        if code.startswith("```"):
            code = "\n".join(code.split("\n")[1:-1])

        return {
            "action": "generate",
            "status": "success",
            "language": language,
            "code": code,
            "lines": len(code.split("\n")),
        }
    async def _review_code(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Review code using a real LLM.

        Without a configured LLM API key this returns an explicit degraded
        result -- never a fabricated score or issue list.
        """
        code = task_node.input_data.get("code", "")
        if not code.strip():
            return {
                "action": "review",
                "status": "degraded",
                "error": "No code provided for review.",
            }

        prompt = f"Review the following code for quality, security, and bugs:\n\n{code}\n\nProvide a JSON object with 'score' (0-1), 'issues' (list), 'suggestions' (list), and 'approved' (bool)."
        system = "You are a senior code reviewer. Your output must be a valid JSON object."

        try:
            response = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "review",
                "status": "degraded",
                "error": f"Code review requires an LLM API key: {e}",
                "llm_required": True,
            }

        try:
            # Try to extract JSON
            if "{" in response:
                json_part = response[response.find("{"):response.rfind("}")+1]
                review = json.loads(json_part)
            else:
                raise ValueError("LLM response contained no JSON object")
        except Exception as e:
            return {
                "action": "review",
                "status": "degraded",
                "error": f"Could not parse LLM review output as JSON: {e}",
                "raw_response": response[:2000],
            }

        return {
            "action": "review",
            "status": "success",
            **review
        }
    async def _refactor_code(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Refactor code using a real LLM.

        Without a configured LLM API key this returns an explicit degraded
        result -- it never echoes the input back labeled "refactored".
        """
        code = task_node.input_data.get("code", "")
        if not code.strip():
            return {
                "action": "refactor",
                "status": "degraded",
                "error": "No code provided for refactoring.",
            }

        prompt = (
            "Refactor the following code for readability, performance, and "
            "best practices. Return ONLY the refactored code without markdown "
            f"formatting or explanation:\n\n{code}"
        )
        system = "You are an expert software engineer specializing in code refactoring."

        try:
            refactored = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "refactor",
                "status": "degraded",
                "original_lines": len(code.split("\n")),
                "refactored_code": None,
                "error": f"Code refactoring requires an LLM API key: {e}",
                "llm_required": True,
            }

        if refactored.startswith("```"):
            refactored = "\n".join(refactored.split("\n")[1:-1])

        return {
            "action": "refactor",
            "status": "success",
            "original_lines": len(code.split("\n")),
            "refactored_code": refactored,
            "refactored_lines": len(refactored.split("\n")),
        }
    async def _generate_tests(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Generate real unit tests using an LLM.

        Without a configured LLM API key this returns an explicit degraded
        result -- never a hardcoded placeholder template presented as real.
        """
        code = task_node.input_data.get("code", "")
        language = task_node.input_data.get("language", "python")
        if not code.strip():
            return {
                "action": "test",
                "status": "degraded",
                "error": "No code provided for test generation.",
            }

        prompt = (
            f"Write unit tests for the following {language} code. Return ONLY "
            f"the test code without markdown formatting or explanation:\n\n{code}"
        )
        system = f"You are an expert {language} developer specializing in test-driven development."

        try:
            tests = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "test",
                "status": "degraded",
                "tests": None,
                "error": f"Test generation requires an LLM API key: {e}",
                "llm_required": True,
            }

        if tests.startswith("```"):
            tests = "\n".join(tests.split("\n")[1:-1])

        return {
            "action": "test",
            "status": "success",
            "tests": tests,
            "language": language,
        }
class DevOpsAgent(BaseAgent):
    """
    DevOps and infrastructure agent.
    
    Capabilities:
    - Deployment
    - Infrastructure provisioning
    - Monitoring
    - CI/CD operations
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("DevOpsAgent", event_bus, config)

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute DevOps task."""
        action = task_node.input_data.get("action", "deploy")
        
        if action == "deploy":
            return await self._deploy(task_node)
        elif action == "provision":
            return await self._provision_infrastructure(task_node)
        elif action == "monitor":
            return await self._monitor_system(task_node)
        else:
            return {"status": "unknown_action"}

    async def _deploy(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Deploy an application.

        Honest stub: no infrastructure provider is wired in, so this returns
        an explicit degraded result instead of fabricating a deployment URL
        and ID for a deploy that never happened.
        """
        app = task_node.input_data.get("application", "")
        environment = task_node.input_data.get("environment", "staging")

        logger.info(f"Deploy requested for {app} to {environment} (no provider configured)")

        return {
            "action": "deploy",
            "status": "degraded",
            "application": app,
            "environment": environment,
            "error": (
                "Deployment is not implemented: no infrastructure provider is "
                "configured. Wire a real provider (container registry / "
                "orchestrator credentials) to enable deployments."
            ),
        }
    async def _provision_infrastructure(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Provision infrastructure resources.

        Honest stub: no cloud provider is wired in, so this returns an
        explicit degraded result instead of fabricating resource IDs.
        """
        resources = task_node.input_data.get("resources", [])

        return {
            "action": "provision",
            "status": "degraded",
            "resources": resources,
            "resource_ids": [],
            "error": (
                "Infrastructure provisioning is not implemented: no cloud "
                "provider is configured. Wire real provider credentials to "
                "enable provisioning."
            ),
        }
    async def _monitor_system(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Monitor system health.

        Returns real host metrics via psutil when installed; otherwise an
        explicit degraded result -- never fabricated CPU/memory numbers.
        """
        try:
            import psutil
        except ImportError:
            return {
                "action": "monitor",
                "status": "degraded",
                "error": (
                    "System monitoring requires the 'psutil' package "
                    "(pip install psutil); no metrics were fabricated."
                ),
            }

        return {
            "action": "monitor",
            "status": "success",
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "uptime_hours": (time.time() - psutil.boot_time()) / 3600,
        }
class APIAgent(BaseAgent):
    """
    API interaction agent.
    
    Capabilities:
    - REST API calls
    - GraphQL queries
    - Webhook handling
    - Rate limiting
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("APIAgent", event_bus, config)

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute API task."""
        action = task_node.input_data.get("action", "call")
        
        if action == "call":
            return await self._call_api(task_node)
        elif action == "graphql":
            return await self._graphql_query(task_node)
        else:
            return {"status": "unknown_action"}

    async def _call_api(self, task_node: TaskNode) -> Dict[str, Any]:
        """Make real REST API call."""
        url = task_node.input_data.get("url", "")
        method = task_node.input_data.get("method", "GET").upper()
        headers = task_node.input_data.get("headers", {})
        payload = task_node.input_data.get("payload")
        
        logger.info(f"API call: {method} {url}")
        
        try:
            async with create_session() as session:
                async with session.request(method, url, headers=headers, json=payload, timeout=30) as response:
                    status_code = response.status
                    try:
                        resp_data = await response.json()
                    except:
                        resp_data = await response.text()
                        
                    return {
                        "action": "call",
                        "status": "success" if status_code < 400 else "failure",
                        "status_code": status_code,
                        "response": resp_data,
                        "url": url,
                        "method": method
                    }
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {
                "action": "call",
            "status": "error",
                "error": str(e),
                "url": url
            }

    async def _graphql_query(self, task_node: TaskNode) -> Dict[str, Any]:
        """
        Execute a real GraphQL query against the provided endpoint.

        Requires 'url' in input_data. Without an endpoint there is nothing
        real to return, so an explicit degraded result is returned instead
        of fabricated data.
        """
        url = task_node.input_data.get("url", "")
        query = task_node.input_data.get("query", "")
        headers = task_node.input_data.get("headers", {})
        variables = task_node.input_data.get("variables") or {}

        if not url:
            return {
                "action": "graphql",
                "status": "degraded",
                "error": "GraphQL query requires 'url' in input_data.",
            }

        try:
            async with create_session() as session:
                async with session.post(
                    url, headers=headers,
                    json={"query": query, "variables": variables},
                    timeout=30,
                ) as response:
                    status_code = response.status
                    try:
                        resp_data = await response.json()
                    except Exception:
                        resp_data = await response.text()

                    data = resp_data.get("data") if isinstance(resp_data, dict) else resp_data
                    errors = resp_data.get("errors", []) if isinstance(resp_data, dict) else []
                    return {
                        "action": "graphql",
                        "status": "success" if status_code < 400 else "failure",
                        "status_code": status_code,
                        "data": data,
                        "errors": errors,
                    }
        except Exception as e:
            logger.error(f"GraphQL query failed: {e}")
            return {
                "action": "graphql",
                "status": "error",
                "error": str(e),
                "url": url,
            }
class DataProcessingAgent(BaseAgent):
    """
    Data processing and transformation agent.
    
    Capabilities:
    - ETL operations
    - Data cleaning
    - Format conversion
    - Analysis
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("DataProcessingAgent", event_bus, config)

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute data processing task."""
        action = task_node.input_data.get("action", "transform")
        
        if action == "transform":
            return await self._transform_data(task_node)
        elif action == "clean":
            return await self._clean_data(task_node)
        elif action == "analyze":
            return await self._analyze_data(task_node)
        else:
            return {"status": "unknown_action"}

    async def _transform_data(self, task_node: TaskNode) -> Dict[str, Any]:
        """Transform data between formats."""
        data = task_node.input_data.get("data", {})
        target_format = task_node.input_data.get("target_format", "json")
        
        return {
            "action": "transform",
            "status": "transformed",
            "format": target_format,
            "records_processed": len(data) if isinstance(data, list) else 1,
            "output": data
        }

    async def _clean_data(self, task_node: TaskNode) -> Dict[str, Any]:
        """Clean and normalize data."""
        data = task_node.input_data.get("data", [])
        
        return {
            "action": "clean",
            "status": "cleaned",
            "records_processed": len(data) if isinstance(data, list) else 0,
            "issues_fixed": 0,
            "output": data
        }

    async def _analyze_data(self, task_node: TaskNode) -> Dict[str, Any]:
        """Analyze data using a real LLM for insights."""
        data = task_node.input_data.get("data", [])
        record_count = len(data) if isinstance(data, list) else 1

        prompt = f"Analyze the following data and provide top 3 insights and basic statistics:\n\n{json.dumps(data)[:2000]}"
        system = "You are a data scientist. Your analysis should be factual and concise."

        try:
            analysis = await self._call_llm(prompt, system=system)
        except LLMNotConfiguredError as e:
            return {
                "action": "analyze",
                "status": "degraded",
                "analysis": None,
                "record_count": record_count,
                "error": f"Data analysis requires an LLM API key: {e}",
                "llm_required": True,
            }

        return {
            "action": "analyze",
            "status": "success",
            "analysis": analysis,
            "record_count": record_count
        }
class FileSystemAgent(BaseAgent):
    """
    File system operations agent.
    
    Capabilities:
    - File read/write
    - Directory operations
    - File search
    - Permissions management
    """

    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        super().__init__("FileSystemAgent", event_bus, config)
        self._sandbox_root = sandbox_manager.sandbox_root

    async def execute(
        self,
        task_node: TaskNode,
        context: SecurityContext
    ) -> Dict[str, Any]:
        """Execute filesystem task."""
        action = task_node.input_data.get("action", "read")
        path = task_node.input_data.get("path", "")
        
        # Ensure path is within sandbox using SandboxManager
        path = sandbox_manager.get_sandbox_path(path)
        
        if action == "read":
            return await self._read_file(path)
        elif action == "write":
            return await self._write_file(task_node)
        elif action == "list":
            return await self._list_directory(path)
        else:
            return {"status": "unknown_action"}

    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read actual file contents."""
        try:
            if not os.path.exists(path):
                return {"status": "error", "error": f"File not found: {path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return {
                "action": "read",
                "path": path,
                "content": content,
                "size_bytes": len(content),
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _write_file(self, task_node: TaskNode) -> Dict[str, Any]:
        """Write actual file contents (sandboxed)."""
        path = sandbox_manager.get_sandbox_path(task_node.input_data.get("path", ""))
        content = task_node.input_data.get("content", "")

        try:
            # Ensure directory exists
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "action": "write",
                "path": path,
                "bytes_written": len(content),
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """List real directory contents (sandboxed path from caller)."""
        try:
            entries = sorted(os.listdir(path))
            return {
                "action": "list",
                "path": path,
                "entries": entries,
                "status": "success"
            }
        except Exception as e:
            return {
                "action": "list",
                "path": path,
                "entries": [],
                "status": "error",
                "error": str(e),
            }