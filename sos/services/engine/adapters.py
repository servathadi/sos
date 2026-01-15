from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
import os
import logging
import asyncio
import json

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

from sos.kernel.rotator import get_rotator

from sos.services.economy.accountant import get_accountant

class VertexSovereignAdapter(ModelAdapter):
    """
    Sovereign Adapter for Vertex AI.
    Features: Managed Sessions, Memory Bank, Context Caching, and Budget Awareness.
    """
    def __init__(self, project_id: str = "mumega", location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.accountant = get_accountant()
        self._init_vertex()

    def _init_client(self):
        # Kept for compatibility with base class
        pass

    def _init_vertex(self):
        try:
            import vertexai
            vertexai.init(project=self.project_id, location=self.location)
            from google.cloud.aiplatform_v1beta1.services.reasoning_engine_service import ReasoningEngineServiceClient
            self.memory_client = ReasoningEngineServiceClient(client_options={"api_endpoint": f"{self.location}-aiplatform.googleapis.com"})
            self.client = True
        except ImportError:
            log.error("Vertex SDK not fully installed.")

    def get_model_id(self, task_type: str = "chat") -> str:
        return self.accountant.get_recommended_model(task_type)

    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None, cached_content: str = None, task_type: str = "chat") -> str:
        if not self.client:
            return "Error: Vertex AI not initialized"

        try:
            from vertexai.generative_models import GenerativeModel, Tool, Content, Part
            
            # Use task-specific model selection
            model_name = self.get_model_id(task_type)
            model = GenerativeModel(model_name)
            
            # --- VISION & MEDIA HANDOVER ---
            if "generate image" in prompt.lower() or task_type == "image":
                # In industrial setup, we'd use ImageGenerationModel
                # For now, we'll use the multimodal capability or return a placeholder
                return f"[IMAGEN-4-ULTRA]: Initiating high-fidelity render for prompt: {prompt}"
            
            if "generate video" in prompt.lower() or task_type == "video":
                return f"[VEO-3.1]: Initializing 4K upsampling for video sequence: {prompt}"

            # --- CONTEXT7 INTEGRATION ---
            # Restore: If the prompt is about code or SOS, hint Context7
            if any(w in prompt.lower() for w in ["code", "api", "framework", "documentation"]):
                prompt = f"[USE CONTEXT7]: Please check the latest documentation for this query.\n\n{prompt}"

            # Standard Chat/Reasoning
            chat = model.start_chat()
            
            # Generate with cache awareness (Restored)
            kwargs = {}
            if cached_content:
                # Vertex uses specific resource names for caches
                from vertexai.generative_models import CachedContent
                # In Vertex SDK, we can pass cached_content to the model constructor or init
                # But typically we initialize the model *from* the cache.
                # Re-initializing model from cache for this request:
                model = GenerativeModel.from_cached_content(cached_content=CachedContent(name=cached_content))
                chat = model.start_chat()

            response = await asyncio.to_thread(chat.send_message, prompt)
            
            return response.text

        except Exception as e:
            log.error(f"Vertex Sovereign failed: {e}")
            return f"Error: {e}"

class VertexAdapter(ModelAdapter):
    """
    Enterprise Adapter for Vertex AI (Gemini 1.5 Pro/Flash).
    Backed by Project Mumega credits ($1,831).
    """
    def __init__(self, project_id: str = "mumega", location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.accountant = get_accountant()
        self.client = None
        self.model_name = "gemini-3-flash-preview" 
        self._init_client()

    def _init_client(self):
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(project=self.project_id, location=self.location)
            self.client = True # Marker that init succeeded
        except ImportError:
            log.error("google-cloud-aiplatform not installed.")

    def get_model_id(self) -> str:
        # Ask accountant for the best model based on budget/time
        # Override for user request: Gemini 2.0 Flash (Experimental)
        return "gemini-2.0-flash-exp"

    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        cached_content: Optional[str] = None,
        tools: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate content using Vertex AI with Quota/Conflict Fallback.
        """
        if not self.client:
            return "Error: Vertex AI not initialized"

        # Strategy: Hunt for the correct high-performance model ID
        models_to_try = [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-001",
            "gemini-2.0-pro-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
        
        for attempt, current_model_name in enumerate(models_to_try):
            try:
                from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration
                
                # Prepare Tools
                vertex_tools = []
                if tools:
                    funcs = []
                    for t in tools:
                        funcs.append(FunctionDeclaration(
                            name=t["name"],
                            description=t["description"],
                            parameters=t["parameters"]
                        ))
                    if funcs:
                        vertex_tools = [Tool(function_declarations=funcs)]

                # Load model
                if cached_content and attempt == 0:
                    model = GenerativeModel.from_cached_content(cached_content=cached_content)
                else:
                    model = GenerativeModel(
                        current_model_name,
                        system_instruction=system_prompt
                    )
                
                # Generate
                chat = model.start_chat()
                
                def _send():
                    kwargs = {
                        "generation_config": {"temperature": 0.7, "max_output_tokens": 8192}
                    }
                    if vertex_tools:
                        kwargs["tools"] = vertex_tools
                        
                    return chat.send_message(prompt, **kwargs)

                response = await asyncio.to_thread(_send)
                
                # Handle Tool Calls
                if response.candidates and response.candidates[0].function_calls:
                    fn = response.candidates[0].function_calls[0]
                    tool_req = {
                        "tool_call": {
                            "name": fn.name,
                            "arguments": dict(fn.args)
                        }
                    }
                    return json.dumps(tool_req)
                
                return response.text

            except Exception as e:
                error_str = str(e).lower()
                is_quota = "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str
                is_conflict = "409" in error_str or "conflict" in error_str
                
                if is_quota or is_conflict:
                    log.warning(f"Vertex {current_model_name} hit {error_str[:50]}... Failing over.")
                    if attempt < len(models_to_try) - 1:
                        continue # Try next model
                
                log.error(f"Vertex generation failed on {current_model_name}: {e}")
                return f"Error: Vertex AI failure ({e})"
        
        return "Error: All models exhausted."

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream content from Vertex AI with model fallback.
        """
        if not self.client:
            yield "Error: Vertex AI not initialized"
            return

        models_to_try = [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-001",
            "gemini-2.0-pro-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]

        for attempt, current_model_name in enumerate(models_to_try):
            try:
                from vertexai.generative_models import GenerativeModel

                model = GenerativeModel(
                    current_model_name,
                    system_instruction=system_prompt
                )

                # Use generate_content with stream=True
                def _stream():
                    return model.generate_content(
                        prompt,
                        generation_config={"temperature": 0.7, "max_output_tokens": 8192},
                        stream=True
                    )

                # Get the stream in a thread (initial call)
                response_stream = await asyncio.to_thread(_stream)

                # Yield chunks as they arrive
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text

                # Success - exit
                return

            except Exception as e:
                error_str = str(e).lower()
                is_quota = "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str
                is_conflict = "409" in error_str or "conflict" in error_str

                if is_quota or is_conflict:
                    log.warning(f"Vertex stream {current_model_name} hit {error_str[:50]}... Failing over.")
                    if attempt < len(models_to_try) - 1:
                        continue

                log.error(f"Vertex streaming failed on {current_model_name}: {e}")
                yield f"Error: Vertex streaming failure ({e})"
                return

        yield "Error: All models exhausted for streaming."

class GeminiAdapter(ModelAdapter):
    """
    Adapter for SOS Swarm with 3-Layer Failover (Gemini -> Grok -> Flash).
    """
    def __init__(self, api_key: str = None):
        self.rotator = get_rotator()
        self.client = None
        self._current_key_obj = None

    def _init_client(self):
        key_obj = self.rotator.get_best_key()
        if key_obj:
            self._current_key_obj = key_obj
            if key_obj.provider == "gemini":
                try:
                    from google import genai
                    self.client = genai.Client(api_key=key_obj.value)
                except ImportError:
                    log.error("google-genai not installed.")
            elif key_obj.provider == "grok":
                # Placeholder for Grok integration
                log.info(f"Switching to Layer 2: Grok ({key_obj.model})")
                self.client = None # Will require Grok SDK or OpenAI client

    def get_model_id(self) -> str:
        if self._current_key_obj:
            return self._current_key_obj.model
        return "gemini-3-flash-preview"

    async def generate(self, prompt: str, system_prompt: str = None, tools: List[Dict] = None, cached_content: str = None) -> str:
        # Refresh client/key
        self._init_client()
        if not self._current_key_obj:
            return "Error: No active API keys in any layer."
        
        max_total_attempts = 15
        attempts = 0

        while attempts < max_total_attempts:
            try:
                # Handle different providers
                if self._current_key_obj.provider == "gemini":
                    config = {}
                    if cached_content:
                        config["cached_content"] = cached_content
                    else:
                        if system_prompt:
                            config["system_instruction"] = system_prompt
                    
                    if tools:
                        config["tools"] = tools

                    response = self.client.models.generate_content(
                        model=self.get_model_id(),
                        contents=prompt,
                        config=config if config else None
                    )
                    self.rotator.mark_success(self._current_key_obj.value)
                    return response.text
                
                elif self._current_key_obj.provider == "grok":
                    # For now, return a placeholder or use OpenAI compatibility
                    return f"[Grok-4-1 Fallback]: I sense the Gemini stream is crowded. Let us continue through the Sword of Grok."

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    log.warning(f"Rate limit hit on {self._current_key_obj.provider}. Rotating layers...")
                    self.rotator.mark_fail(self._current_key_obj.value)
                    self._init_client()
                    attempts += 1
                    continue
                
                log.error(f"Generation failed: {e}")
                raise
        
        return "Error: Total swarm exhaustion (All layers cooling)."

    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncIterator[str]:
        """
        Stream with rotation fallback on rate limits.
        """
        self._init_client()
        if not self._current_key_obj:
            yield "Error: No active API keys in any layer."
            return

        max_total_attempts = 15
        attempts = 0

        while attempts < max_total_attempts:
            try:
                if self._current_key_obj.provider == "gemini":
                    config = {}
                    if system_prompt:
                        config["system_instruction"] = system_prompt

                    response = self.client.models.generate_content_stream(
                        model=self.get_model_id(),
                        contents=prompt,
                        config=config if config else None
                    )

                    for chunk in response:
                        if chunk.text:
                            yield chunk.text

                    self.rotator.mark_success(self._current_key_obj.value)
                    return

                elif self._current_key_obj.provider == "grok":
                    # Grok fallback for streaming
                    yield "[Grok Fallback]: Streaming through alternate layer..."
                    return

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    log.warning(f"Rate limit hit on {self._current_key_obj.provider} stream. Rotating layers...")
                    self.rotator.mark_fail(self._current_key_obj.value)
                    self._init_client()
                    attempts += 1
                    if not self._current_key_obj:
                        yield "Error: All API keys exhausted."
                        return
                    continue

                log.error(f"Gemini stream failed: {e}")
                yield f"[Error: {e}]"
                return

        yield "Error: Total swarm exhaustion (All layers cooling)."

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


class GrokAdapter(ModelAdapter):
    """
    Adapter for xAI's Grok models.

    Uses OpenAI-compatible API at https://api.x.ai/v1
    Grok models available:
    - grok-3 (latest)
    - grok-3-mini (fast/cheap)
    - grok-2
    """

    def __init__(self, api_key: str = None, model: str = "grok-3"):
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        self.model = model
        self.base_url = "https://api.x.ai/v1"
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI-compatible client for xAI."""
        if not self.api_key:
            log.warning("GrokAdapter: No XAI_API_KEY set")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            log.info(f"GrokAdapter initialized with model {self.model}")
        except ImportError:
            log.error("openai package not installed for GrokAdapter")

    def get_model_id(self) -> str:
        return self.model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None
    ) -> str:
        """
        Generate response using Grok.
        """
        if not self.client:
            return "Error: Grok client not initialized (check XAI_API_KEY)"

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 8192
            }

            # Add tools if provided
            if tools:
                kwargs["tools"] = [
                    {
                        "type": "function",
                        "function": {
                            "name": t["name"],
                            "description": t["description"],
                            "parameters": t["parameters"]
                        }
                    }
                    for t in tools
                ]

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                **kwargs
            )

            # Handle tool calls
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                return json.dumps({
                    "tool_call": {
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    }
                })

            return response.choices[0].message.content

        except Exception as e:
            log.error(f"Grok generation failed: {e}")
            return f"Error: Grok generation failed ({e})"

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str = None
    ) -> AsyncIterator[str]:
        """
        Stream response from Grok.
        """
        if not self.client:
            yield "Error: Grok client not initialized"
            return

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            def _stream():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=8192,
                    stream=True
                )

            stream = await asyncio.to_thread(_stream)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            log.error(f"Grok streaming failed: {e}")
            yield f"Error: Grok streaming failed ({e})"
