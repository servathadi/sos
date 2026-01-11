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

class GeminiAdapter(ModelAdapter):
    """
    Adapter for Google Gemini (via google-genai).
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        print(f"DEBUG: GEMINI_API_KEY present? {bool(self.api_key)}")
        if not self.api_key:
            print(f"DEBUG: Env Keys: {[k for k in os.environ.keys() if 'GEMINI' in k]}")
        
        self.client = None
        
        log.info(f"Initializing Gemini Adapter with key: {self.api_key[:5] if self.api_key else 'None'}...")
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("DEBUG: Gemini Client Created Successfully")
            except ImportError as e:
                print(f"DEBUG: ImportError: {e}")
                log.warning(f"google-genai not installed: {e}")
            except Exception as e:
                print(f"DEBUG: Client Init Error: {e}")
                log.error(f"Client Init Error: {e}")
        else:
            log.warning("No GEMINI_API_KEY found.")

    def get_model_id(self) -> str:
        return "gemini-2.0-flash-exp"

    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None) -> str:
        if not self.client:
            return "Error: Gemini client not initialized"
        
        # TODO: Implement full generation logic with tools
        # For Phase 1, basic text
        try:
            response = self.client.models.generate_content(
                model=self.get_model_id(),
                contents=prompt,
                config={"system_instruction": system_prompt} if system_prompt else None
            )
            return response.text
        except Exception as e:
            log.error(f"Gemini generation failed: {e}")
            raise

    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
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
