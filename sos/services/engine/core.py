from typing import Any, AsyncIterator, Dict, List, Optional

from sos.contracts.engine import (
    ChatRequest,
    ChatResponse,
    EngineContract,
    ToolCallRequest,
    ToolCallResult,
)
from sos.kernel import Config, Message, Response
from sos.clients.memory import MemoryClient
from sos.clients.tools import ToolsClient
from sos.clients.economy import EconomyClient
from sos.observability.logging import get_logger

log = get_logger("engine_core")


from sos.services.engine.adapters import MockAdapter, GeminiAdapter

class SOSEngine(EngineContract):
    """
    Concrete implementation of the SOS Engine.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        
        # Initialize Service Clients
        self.memory = MemoryClient(self.config.memory_url)
        self.tools = ToolsClient(self.config.tools_url)
        self.economy = EconomyClient(self.config.economy_url)
        
        # Initialize Model Adapters
        self.models = {
            "sos-mock-v1": MockAdapter(),
            "gemini-2.0": GeminiAdapter(),
        }
        self.default_model = "sos-mock-v1"
        
        log.info("SOSEngine initialized", 
                 memory_url=self.config.memory_url,
                 tools_url=self.config.tools_url)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message.
        """
        log.info(f"Processing chat for agent {request.agent_id}", conversation_id=request.conversation_id)

        # 1. Retrieve Context (Memory)
        context = []
        if request.memory_enabled:
            pass # TODO: Implement

        # 2. Select Model
        model_id = request.model or self.default_model
        adapter = self.models.get(model_id, self.models[self.default_model])

        # 3. Generate
        response_text = await adapter.generate(request.message)
        
        # 4. Tool Execution (Mock Logic)
        tool_calls = []
        if request.tools_enabled and "time" in request.message:
             tool_calls.append({"name": "get_current_time", "args": {}})

        # 5. Construct Response
        return ChatResponse(
            content=response_text,
            agent_id=request.agent_id,
            model_used=model_id,
            conversation_id=request.conversation_id or "new",
            tool_calls=tool_calls,
            tokens_used=10
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        Stream response tokens.
        """
        response = await self.chat(request)
        words = response.content.split(" ")
        for word in words:
            yield word + " "

    async def execute_tool(self, request: ToolCallRequest) -> ToolCallResult:
        """
        Delegate tool execution to Tools Service.
        """
        return await self.tools.execute(request)

    async def get_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "sos-mock-v1", "name": "SOS Mock Model", "status": "active"},
            {"id": "gemini-flash", "name": "Gemini Flash", "status": "planned"},
        ]

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "version": "0.1.0",
            "services": {
                "memory": "connected", # TODO: Real check
                "tools": "connected",
                "economy": "connected"
            }
        }

    async def handle_message(self, message: Message) -> Response:
        # TODO: Implement generic message handling
        return Response(content="Not implemented")
