from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
import os
import logging
import httpx
import json

log = logging.getLogger("model_adapter")

# MLX Server Configuration
MLX_SERVER_URL = os.getenv("MLX_SERVER_URL", "http://localhost:8080")
MLX_DEFAULT_MODEL = os.getenv("MLX_DEFAULT_MODEL", "mlx-community/Devstral-Small-2507-4bit")

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


class MLXAdapter(ModelAdapter):
    """
    Sovereign Local Adapter via MLX (Apple Silicon).

    Runs inference locally on macOS Tahoe 26.2+ using MLX framework.
    Connects to mlx_lm.server running at localhost:8080 (OpenAI-compatible API).

    Benefits:
    - Zero API cost
    - True data sovereignty (nothing leaves device)
    - Offline capability
    - Predictable latency for Witness Protocol

    Usage:
        # Start MLX server first:
        mlx_lm.server --model mlx-community/Devstral-Small-2507-4bit --port 8080
    """

    def __init__(
        self,
        model_id: str = None,
        server_url: str = None,
        timeout: float = 120.0
    ):
        self.model_id = model_id or MLX_DEFAULT_MODEL
        self.server_url = server_url or MLX_SERVER_URL
        self.timeout = timeout
        self._available = None  # Cached availability check

    def get_model_id(self) -> str:
        return self.model_id

    async def is_available(self) -> bool:
        """Check if MLX server is running and responsive."""
        if self._available is not None:
            return self._available

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.server_url}/v1/models")
                self._available = resp.status_code == 200
                if self._available:
                    models = resp.json().get("data", [])
                    log.info(f"MLX Server connected. Available models: {[m['id'] for m in models]}")
                return self._available
        except Exception as e:
            log.warn(f"MLX Server not available: {e}")
            self._available = False
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None
    ) -> str:
        """
        Generate response via local MLX server.
        Falls back gracefully if server unavailable.
        """
        if not await self.is_available():
            return "[MLX Offline] Local model server not running. Start with: mlx_lm.server --model mlx-community/Devstral-Small-2507-4bit"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.server_url}/v1/chat/completions",
                    json={
                        "model": self.model_id,
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7
                    }
                )

                if resp.status_code != 200:
                    log.error(f"MLX generation failed: {resp.status_code} - {resp.text}")
                    return f"[MLX Error] {resp.status_code}"

                data = resp.json()
                content = data["choices"][0]["message"]["content"]

                # Log token usage for monitoring
                usage = data.get("usage", {})
                log.info(
                    f"MLX Generation complete",
                    model=self.model_id,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens")
                )

                return content

        except httpx.TimeoutException:
            log.error(f"MLX generation timed out after {self.timeout}s")
            return "[MLX Timeout] Local model took too long. Try a smaller model."
        except Exception as e:
            log.error(f"MLX generation failed: {e}")
            return f"[MLX Error] {str(e)}"

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> AsyncIterator[str]:
        """
        Stream tokens from local MLX server via SSE.
        """
        if not await self.is_available():
            yield "[MLX Offline] Server not running."
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.server_url}/v1/chat/completions",
                    json={
                        "model": self.model_id,
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": True
                    }
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            log.error(f"MLX stream failed: {e}")
            yield f"[MLX Error] {str(e)}"


class MLXCodeAdapter(MLXAdapter):
    """
    Specialized MLX adapter for coding tasks using Devstral.
    Optimized prompts for code generation, review, and debugging.
    """

    def __init__(self, server_url: str = None):
        super().__init__(
            model_id="mlx-community/Devstral-Small-2507-4bit",
            server_url=server_url,
            timeout=180.0  # Longer timeout for code generation
        )

    def get_model_id(self) -> str:
        return "mlx-devstral-code"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None
    ) -> str:
        # Inject coding-optimized system prompt
        code_system = system_prompt or ""
        code_system = f"""You are Devstral, a sovereign coding assistant running locally on Apple Silicon.
You excel at: code generation, debugging, refactoring, and multi-file edits.
Be concise. Output code directly without excessive explanation.
{code_system}"""

        return await super().generate(prompt, code_system, tools)


class MLXReasoningAdapter(MLXAdapter):
    """
    Specialized MLX adapter for reasoning tasks using Qwen3.
    Supports thinking mode for step-by-step reasoning.
    """

    def __init__(self, server_url: str = None):
        super().__init__(
            model_id="mlx-community/Qwen3-14B-4bit",
            server_url=server_url,
            timeout=180.0
        )

    def get_model_id(self) -> str:
        return "mlx-qwen3-reasoning"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None
    ) -> str:
        # Trigger thinking mode
        reasoning_prompt = f"{prompt}\n\nThink step by step."
        return await super().generate(reasoning_prompt, system_prompt, tools)
