"""
Sovereign Sandbox (The Simulator)
Provides an isolated environment for the agent to execute code safely.
Uses Docker containers to prevent harm to the host system.
"""

import docker
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SovereignSandbox:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
            self.enabled = True
        except Exception as e:
            logger.warning(f"SANDBOX_WARNING: Docker not available: {e}")
            self.enabled = False

    def run_code(self, code: str, language: str = "python", timeout: int = 10) -> Dict[str, Any]:
        """
        Executes code in an isolated container.
        """
        if not self.enabled:
            return {"error": "Sandbox disabled. Docker not running."}

        image = "python:3.9-slim"
        # For non-python code, we would need different images, but let's assume python for now.
        
        # Prepare command
        # We write code to a file inside the container or pass via -c
        # Passing via -c is tricky with multiline/escaping.
        # Better to echo to a file then run it.
        
        # Simple Python execution
        cmd = ["python", "-c", code]
        
        try:
            container = self.client.containers.run(
                image,
                command=cmd,
                detach=True,
                mem_limit="128m",
                # cpu_quota=50000, # 50% Execute limit
                network_mode="none" # No internet access by default for safety
            )
            
            try:
                # Wait for result
                result = container.wait(timeout=timeout)
                logs = container.logs().decode("utf-8")
                exit_code = result.get("StatusCode", 1)
                
                return {
                    "stdout": logs,
                    "exit_code": exit_code,
                    "success": exit_code == 0
                }
            except Exception as e: # Timeout
                container.kill()
                return {"error": f"Execution Timed Out: {e}"}
            finally:
                # Always cleanup
                try:
                    container.remove(force=True)
                except:
                    pass
                    
        except Exception as e:
            return {"error": f"Container Launch Failed: {e}"}
