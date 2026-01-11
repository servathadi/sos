from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List

from sos import __version__
from sos.services.tools.core import ToolsCore

app = FastAPI(title="SOS Tools Service", version=__version__)
tools = ToolsCore()

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/list")
async def list_tools():
    return await tools.list_tools()

@app.post("/execute")
async def execute_tool(req: ToolRequest):
    try:
        result = await tools.execute(req.tool_name, req.arguments)
        return {"status": "success", "output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))