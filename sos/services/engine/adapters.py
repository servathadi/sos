from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
import os
import logging

log = logging.getLogger("model_adapter")

class ModelAdapter(ABC):
    """
    Abstract adapter for AI Model Providers.
    """
    @abstractmethod
    def get_model_id(self) -> str:
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None) -> str:
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
        pass

from sos.kernel.rotator import KeyRotator

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google Gemini (via google-genai) with Auto-Rotation.
    """
    def __init__(self, api_key: str = None):
        self.rotator = KeyRotator("gemini")
        self.client = None
        self._init_client()

    def _init_client(self):
        key = self.rotator.get_key()
        if key:
            try:
                from google import genai
                self.client = genai.Client(api_key=key)
            except ImportError:
                log.warn("google-genai not installed.")

    def get_model_id(self) -> str:
        # Default to Gemini 3 Flash Preview as requested
        return "gemini-3-flash-preview"

    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None) -> str:
        if not self.client:
            return "Error: Gemini client not initialized"
        
        # Implementation of rotation logic on 429
        attempts = 0
        max_attempts = self.rotator.key_count or 1

        while attempts < max_attempts:
            try:
                response = self.client.models.generate_content(
                    model=self.get_model_id(),
                    contents=prompt,
                    config={"system_instruction": system_prompt} if system_prompt else None
                )
                return response.text
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    log.warn(f"Rate limit hit on key {self.rotator.current_index}. Rotating...")
                    self.rotator.rotate()
                    self._init_client()
                    attempts += 1
                    continue
                log.error(f"Gemini generation failed: {e}")
                raise
        
        return "Error: All Gemini keys exhausted (Rate Limit)."

    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
        # TODO: Implement rotation for streaming
        if not self.client:
            yield "Error: Gemini client not initialized"
            return

        try:
            response = self.client.models.generate_content_stream(
                model=self.get_model_id(),
                contents=prompt
            )
            for chunk in response:
                yield chunk.text
        except Exception as e:
            log.error(f"Gemini stream failed: {e}")
            yield f"[Error: {e}]"

class MockAdapter(ModelAdapter):
    """
    Offline mock adapter for testing.
    """
    def get_model_id(self) -> str:
        return "sos-mock-v1"

    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None) -> str:
        return f"Mock Response to: {prompt}"

    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
        yield "Mock "
        yield "Streaming "
        yield "Response"
