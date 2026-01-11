import os
import json
import logging
import asyncio
import sys
# import docker # Removed for native mode
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sos.kernel import Config
from sos.observability.logging import get_logger

log = get_logger("tools_mcp")

app = FastAPI()

# Input Models
class WebSearchRequest(BaseModel):
    query: str
    count: int = 5
    provider: str = "auto"


# IMAGE_NAME = "sos-tools:latest" # Docker disabled for native mode

async def run_native_tool(script: str, args: List[str], env: Dict[str, str]) -> Dict[str, Any]:
    """
    Run a python script natively (via subprocess).
    WARNING: This runs without a sandbox. Ensure inputs are trusted.
    """
    try:
        # Resolve script path relative to this file's directory/docker
        # The scripts are still in the 'docker' folder, we just run them here.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, "docker", script)
        
        if not os.path.exists(script_path):
            return {"error": f"Tool script not found: {script}"}

        log.info(f"Executing native tool: {script}")
        
        # Merge current env with tool env (to get PATH, etc) but allow overrides
        full_env = os.environ.copy()
        full_env.update(env)

        proc = await asyncio.create_subprocess_exec(
            sys.executable, script_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return {"error": f"Tool execution failed: {stderr.decode()}"}
            
        return json.loads(stdout.decode())
        
    except Exception as e:
        log.error("Native execution error", error=str(e))
        return {"error": f"Execution Error: {str(e)}"}


@app.post("/tools/web_search")
async def web_search(req: WebSearchRequest):
    """
    Execute a web search (Native Mode).
    """
    # 1. Fetch Key from Kernel/Env
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    env_vars = {}
    if tavily_key:
        env_vars["TAVILY_API_KEY"] = tavily_key
        
    # 2. Run Native
    result = await run_native_tool(
        script="web_search.py",
        args=[req.query, "--count", str(req.count), "--provider", req.provider],
        env=env_vars
    )
    
    return result

@app.get("/health")
def health():
    return {"status": "ok", "mode": "native"}

