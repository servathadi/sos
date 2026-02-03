from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import time
import logging
from sos.contracts.engine import ChatRequest
from sos.services.engine.core import SOSEngine

router = APIRouter(prefix="/v1", tags=["openai"])
logger = logging.getLogger("sos.openai")

class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "sos-core"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    user: Optional[str] = None
    stream: Optional[bool] = False

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: ChatCompletionUsage

def get_engine():
    from sos.services.engine.app import engine
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return engine

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    engine: SOSEngine = Depends(get_engine)
):
    logger.info(f"OpenAI Request: {len(request.messages)} messages from {request.user}")

    last_user_msg = next((m for m in reversed(request.messages) if m.role == "user"), None)
    content = last_user_msg.content if last_user_msg else "Hello"
    user_id = request.user or "openai_client"
    
    sos_request = ChatRequest(
        message=content,
        user_id=user_id,
        stream=request.stream,
        metadata={"openai_model": request.model}
    )

    try:
        result = await engine.chat(sos_request)
        response_text = result.response
    except Exception as e:
        logger.error(f"Engine error: {e}")
        response_text = f"Error: {str(e)}"

    return ChatCompletionResponse(
        id=f"chatcmpl-{int(time.time())}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionResponseChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ],
        usage=ChatCompletionUsage()
    )

@router.get("/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "sos-core", "object": "model", "owned_by": "sos"},
            {"id": "river-v1", "object": "model", "owned_by": "sos"}
        ]
    }
