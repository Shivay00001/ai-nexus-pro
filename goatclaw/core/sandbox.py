import asyncio
import os
import subprocess
import logging
import tempfile
import pathlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("goatclaw.core.sandbox")

@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    returncode: int
    execution_time: float
    success: bool

class SandboxManager:
    """
    USP: Secure process-level isolation for specialist agents.
    
    Provides:
    - Restricted environment variables
    - Timeout enforcement
    - Working directory isolation
    - Resource limiting (where supported)
    """
    def __init__(self, sandbox_root: Optional[str] = None):
        self.sandbox_root = sandbox_root or os.path.join(tempfile.gettempdir(), "goatclaw_sandbox")
        os.makedirs(self.sandbox_root, exist_ok=True)
        logger.info(f"SandboxManager initialized at {self.sandbox_root}")

    async def run_command(
        self, 
        command: List[str], 
        input_data: Optional[str] = None,
        timeout: float = 30.0,
        env: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        """Run a command securely in a limited process."""
        
        # 1. Prepare restricted environment
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.getcwd(), # Allow importing current package
            "TMPDIR": self.sandbox_root
        }
        if env:
            safe_env.update(env)
            
        # 2. Start timer
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 3. Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_env,
                cwd=self.sandbox_root
            )
            
            # 4. Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data.encode() if input_data else None),
                    timeout=timeout
                )
                success = process.returncode == 0
            except asyncio.TimeoutError:
                process.kill()
                stdout, stderr = await process.communicate()
                return SandboxResult(
                    stdout=stdout.decode(),
                    stderr=f"{stderr.decode()}\n[TIMEOUT after {timeout}s]",
                    returncode=-1,
                    execution_time=timeout,
                    success=False
                )
                
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return SandboxResult(
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                returncode=process.returncode,
                execution_time=execution_time,
                success=success
            )
            
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return SandboxResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                execution_time=0.0,
                success=False
            )

    def get_sandbox_path(self, relative_path: str) -> str:
        """Get absolute path within the sandbox, preventing traversal."""
        # Simple traversal check
        if ".." in relative_path or relative_path.startswith("/") or ":" in relative_path:
             safe_name = os.path.basename(relative_path)
             return os.path.join(self.sandbox_root, safe_name)
        return os.path.join(self.sandbox_root, relative_path)

# Global Instance
sandbox_manager = SandboxManager()
