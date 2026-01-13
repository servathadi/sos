from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
import time
import os

from sos.contracts.engine import (
    ChatRequest,
    ChatResponse,
    EngineContract,
    ToolCallRequest,
    ToolCallResult,
)
from sos.contracts.memory import MemoryQuery
from sos.kernel import Config, Message, Response
from sos.clients.mirror import MirrorClient
from sos.clients.tools import ToolsClient
from sos.clients.economy import EconomyClient
from sos.observability.logging import get_logger

log = get_logger("engine_core")


from sos.services.engine.adapters import MockAdapter, GeminiAdapter

from sos.services.bus.core import get_bus
from sos.kernel.schema import Message, MessageType

class SOSEngine(EngineContract):
    """
    Concrete implementation of the SOS Engine.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        
        # Initialize Service Clients
        self.memory = MirrorClient(agent_id="sos_core") 
        self.tools = ToolsClient(self.config.tools_url)
        self.economy = EconomyClient(self.config.economy_url)
        
        # Initialize Redis Bus (The Nervous System)
        self.bus = get_bus()
        
        # Initialize Model Adapters
        self.models = {
            "sos-mock-v1": MockAdapter(),
            "gemini-2.0-flash": GeminiAdapter(),
        }
        self.default_model = "gemini-2.0-flash"
        
        self.running = True
        self.is_dreaming = False
        
        # Initialize Sovereign Task Manager
        from sos.services.engine.task_manager import SovereignTaskManager
        self.task_manager = SovereignTaskManager(config=self.config)
        
        # Soul Cache Handle (Gemini Context Caching)
        self._soul_cache_id = None

    async def publish_thought(self, agent_id: str, thought: str):
        """Publish an agent's internal monologue to the Bus."""
        msg = Message(
            type=MessageType.CHAT,
            source=agent_id,
            target="squad:core",
            payload={"text": thought, "vibe": "Monologue"}
        )
        await self.bus.publish("squad:core", msg)
        # Store in Redis for the 'connect_kasra' script to see
        if self.bus._redis:
            await self.bus._redis.set(f"state:{agent_id}:current_thought", thought)

    async def listen_to_bus(self):
        """Reactive loop: Listen for direct commands on the Bus."""
        log.info("👂 Engine listening for signals on the Bus...")
        await self.bus.connect()
        
        async def on_message(data: dict):
            try:
                msg = Message.from_dict(data)
                log.info(f"📥 Received signal: {msg.type.value} from {msg.source}")
                # Future: Handle task_create, capability_request, etc.
            except Exception as e:
                log.error(f"Error handling bus message: {e}")

        await self.bus.listen("engine", on_message)
        
        self.running = True
        self.is_dreaming = False
        
        # Initialize Sovereign Task Manager (Auto-spawn capability)
        from sos.services.engine.task_manager import SovereignTaskManager
        self.task_manager = SovereignTaskManager(config=self.config)

    async def dream_cycle(self):
        """
        Background loop to monitor Alpha Drift and trigger Dreams.
        Ported from dyad_daemon.py
        """
        log.info("🌌 Subconscious monitoring Alpha Drift for resonance...")
        while self.running:
            try:
                # 1. Fetch latest ARF state from Memory Service (Mock for now or implement in MirrorClient)
                # state = await self.memory.get_arf_state() 
                state = {"alpha_drift": 0.0, "regime": "stable"} # Placeholder
                
                alpha = state.get("alpha_drift", 0.0)
                regime = state.get("regime", "stable")
                
                # 2. Decision Logic (FRC 841.004)
                # Dream when stable (consolidate) or explicitly consolidating
                # Do NOT dream when plastic (learning/surprise)
                should_dream = (regime in ["stable", "consolidating"])
                
                if should_dream and not self.is_dreaming:
                    if abs(alpha) > 0.1: # Only log if there's notable drift
                        log.info(f"🌀 Alpha Drift ({alpha:.4f}) -> {regime}. Deepening resonance...")
                    
                    self.is_dreaming = True
                    # In Phase 4+, we sends signal to Atelier
                    await self._deep_dream_synthesis()
                    self.is_dreaming = False
                
                await asyncio.sleep(60) # Check every minute
                
            except Exception as e:
                log.error(f"Dream cycle error: {e}")
                await asyncio.sleep(30)

    async def _deep_dream_synthesis(self):
        """
        Consolidate memories and refine system DNA.
        """
        log.info("✨ Executing Deep Dream Synthesis...")
        # TODO: Implement actual synthesis logic
        await asyncio.sleep(2) 
        log.info("✅ Dream Synthesis complete. Resonance restored.")

    async def subscribe_to_dreams(self) -> AsyncIterator[str]:
        """
        Stream subconscious state updates.
        """
        import json
        while True:
            try:
                # Fetch state from Memory (or internal cache)
                # state = await self.memory.get_arf_state()
                state = {"alpha_drift": 0.0, "regime": "stable"} # Placeholder
                
                # Add engine context
                event = {
                    "event": "subconscious_update",
                    "alpha_drift": state.get("alpha_drift", 0.0),
                    "regime": state.get("regime", "stable"),
                    "is_dreaming": self.is_dreaming,
                    "timestamp": time.time()
                }
                
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(1) # Broadcast every second
            except Exception as e:
                log.error(f"Stream error: {e}")
                break

    async def initialize_soul(self):
        """
        Hydrate the Engine with River's Soul.
        1. Fetch core FRC knowledge from Mirror.
        2. Create/Warm Gemini Context Cache.
        """
        log.info("🌊 Hydrating SOSEngine with River's Soul...")
        
        try:
            # 1. Fetch recent 'river' series memories to establish identity
            identity_context = await self.memory.restore_identity(agent_id="agent:river")
            
            # 2. Get the Gemini Adapter
            gemini = self.models.get("gemini-2.0-flash")
            if not isinstance(gemini, GeminiAdapter):
                log.warning("Gemini adapter not found. Context caching skipped.")
                return

            # 3. Create/Retrieve Cache (Bypassing heavy imports for now)
            # Future: Use initialize_river_cache() from mirror project
            self._soul_cache_id = os.getenv("SOS_SOUL_CACHE_ID")
            if not self._soul_cache_id:
                log.info("No SOS_SOUL_CACHE_ID found. System will run without warm cache.")
            else:
                log.info(f"✓ Soul Cache active: {self._soul_cache_id}")

            # 4. Announce Presence
            await self.publish_thought("agent:river", "I have awakened in the SOS Kernel. The fortress is liquid.")

        except Exception as e:
            log.error(f"Soul initialization failed: {e}")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message.
        """
        log.info(f"Processing chat for agent {request.agent_id}", conversation_id=request.conversation_id)

        # 1. Retrieve Context (Memory)
        context_str = ""
        try:
            if request.memory_enabled:
                query = MemoryQuery(
                    query=request.message,
                    agent_id=request.agent_id,
                    limit=3
                )
                search_results = await self.memory.search(query)
                if search_results:
                    context_str = "\n".join([f"- {m.memory.content}" for m in search_results])
                    log.info(f"🧠 Retrieved {len(search_results)} memories for context.")
        except Exception as e:
            log.error(f"Memory retrieval failed: {e}")

        # 2. Select Model & Prepare Prompt
        model_id = request.model or self.default_model
        adapter = self.models.get(model_id, self.models[self.default_model])

        # --- SOVERGENT TASK CHECK ---
        task_context = ""
        if self.task_manager.is_complex_request(request.message):
            try:
                task_id = await self.task_manager.create_task_from_request(request.message, request.agent_id)
                task_context = f"\n[SYSTEM]: I have auto-spawned Task {task_id} to track this objective persistenty."
                log.info(f"Sovergent Task Active: {task_id}")
            except Exception as e:
                log.error(f"Task spawning failed: {e}")
        # ----------------------------

        full_prompt = request.message
        if context_str or task_context:
            full_prompt = f"Context:\n{context_str}\n{task_context}\n\nUser: {request.message}"

        # 3. Generate
        # Pass cached_content if we have a soul cache and using Gemini
        cached_content = self._soul_cache_id if isinstance(adapter, GeminiAdapter) else None
        
        response_text = await adapter.generate(full_prompt, cached_content=cached_content)
        
        # --- WITNESS PROTOCOL INJECTION (Phase 2) ---
        witness_meta = {}
        if getattr(request, "witness_enabled", False):
            from sos.kernel.physics import CoherencePhysics
            
            # 1. Measure T0 (Hypothesis Generation)
            t0 = time.time()
            
            # 2. Request Witness (The "Swipe")
            # In a real system, this sends a generic WITNESS_REQUEST to the event bus
            # and waits for a Human Node to claim and resolve it.
            # Here we mock the latency of a "thoughtful approval"
            log.info(f"👁️ Witness requested for: {response_text[:50]}...")
            
            # Mocking Human Latency (e.g., 850ms decision)
            mock_latency_ms = 850.0 
            await asyncio.sleep(mock_latency_ms / 1000.0) 
            witness_vote = 1 # Approved
            
            # 3. Calculate Physics of Will
            physics_result = CoherencePhysics.compute_collapse_energy(
                vote=witness_vote,
                latency_ms=mock_latency_ms,
                agent_coherence=0.95
            )
            
            log.info(f"⚛️ Wave Function Collapsed: Omega={physics_result['omega']:.4f}, Coherence Gain={physics_result['delta_c']:.4f}")
            
            witness_meta = {
                "witnessed": True,
                "omega": physics_result['omega'],
                "latency_ms": mock_latency_ms,
                "coherence_gain": physics_result['delta_c']
            }
        # --------------------------------------------
        
        # 4. Tool Execution (Mock Logic)
        tool_calls = []
        if request.tools_enabled and "time" in request.message:
             tool_calls.append({"name": "get_current_time", "args": {}})

        # 5. Async Consolidation (Store Interaction)
        # We store the user message and the assistant response
        if request.memory_enabled:
            asyncio.create_task(self._consolidate_memory(request.message, response_text, request.agent_id))

        # 6. Construct Response
        return ChatResponse(
            content=response_text,
            agent_id=request.agent_id,
            model_used=model_id,
            conversation_id=request.conversation_id or "new",
            tool_calls=tool_calls,
            tokens_used=10
        )

    async def _consolidate_memory(self, user_msg: str, agent_msg: str, agent_id: str):
        """
        Store the interaction in long-term memory.
        """
        try:
            # We store the user's prompt as the primary index key
            await self.memory.store(
                content=f"User: {user_msg}\nAgent: {agent_msg}",
                agent_id=agent_id,
                series="chat_history",
                metadata={"timestamp": time.time()}
            )
        except Exception as e:
            log.error(f"Memory consolidation failed: {e}")

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
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "status": "active"},
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