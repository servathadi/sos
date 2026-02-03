
import os
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import uuid

logger = logging.getLogger("sos.client_grok")

class GrokClient:
    """
    Client for xAI Grok. 
    Supports 2M+ context and automatic prompt caching via OpenAI-compatible API.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.warning("XAI_API_KEY not found. Grok will be unavailable.")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1"
            )
        
        # Per-user conversation IDs for server-side cache isolation
        self._user_conv_ids: Dict[str, str] = {}

    def _get_conv_id(self, user_id: str) -> str:
        if user_id not in self._user_conv_ids:
            self._user_conv_ids[user_id] = str(uuid.uuid4())
        return self._user_conv_ids[user_id]

    async def chat(self, user_id: str, model: str, messages: List[Dict], tools: List[Any] = None) -> Optional[str]:
        if not self.client:
            return "Error: Grok API key not configured."

        try:
            # xAI uses 'x-grok-conv-id' header for context caching/continuity
            conv_id = self._get_conv_id(user_id)
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                extra_headers={
                    "x-grok-conv-id": conv_id
                }
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Grok chat failed: {e}")
            return f"Error: {str(e)}"
