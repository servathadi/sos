from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
import time

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
        self.memory = MemoryClient(self.config.memory_url, timeout_seconds=60.0)
        self.tools = ToolsClient(self.config.tools_url)
        self.economy = EconomyClient(self.config.economy_url)
        
        # Initialize Model Adapters
        self.models = {
            "sos-mock-v1": MockAdapter(),
            "gemini-3-flash-preview": GeminiAdapter(),
        }
        self.default_model = "gemini-3-flash-preview"
        
        log.info("SOSEngine initialized", 
                 memory_url=self.config.memory_url,
                 tools_url=self.config.tools_url)
        
        self.running = True
        self.is_dreaming = False
        
        # Initialize Sovereign Task Manager (Auto-spawn capability)
        from sos.services.engine.task_manager import SovereignTaskManager
        self.task_manager = SovereignTaskManager(config=self.config)

        # Physics Realization: Witness Registry
        # Maps (agent_id, conversation_id) -> asyncio.Event
        self.pending_witnesses: Dict[str, asyncio.Event] = {}
        self.witness_results: Dict[str, int] = {} # Maps key -> vote (+1/-1)

    async def dream_cycle(self):
        """
        Background loop to monitor Alpha Drift and trigger Dreams.
        Ported from dyad_daemon.py
        """
        log.info("🌌 Subconscious monitoring Alpha Drift for resonance...")
        while self.running:
            try:
                # 1. Fetch latest ARF state from Memory Service
                state = await self.memory.get_arf_state()
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
                state = await self.memory.get_arf_state()
                
                # Add engine context
                event = {
                    "event": "subconscious_update",
                    "alpha_drift": state.get("alpha_drift", 0.0),
                    "regime": state.get("regime", "stable"),
                    "is_dreaming": self.is_dreaming,
                    "pending_witness": len(self.pending_witnesses) > 0,
                    "timestamp": time.time()
                }
                
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(1) # Broadcast every second
            except Exception as e:
                log.error(f"Stream error: {e}")
                break

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message.
        """
        log.info(f"Processing chat for agent {request.agent_id}", conversation_id=request.conversation_id)

        # 1. Retrieve Context (Memory)
        context_str = ""
        try:
            if request.memory_enabled:
                memories = await self.memory.search(request.message, limit=3)
                if memories:
                    context_str = "\n".join([f"- {m['content']}" for m in memories])
                    log.info(f"🧠 Retrieved {len(memories)} memories for context.")
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
        response_text = await adapter.generate(full_prompt)
        
        # --- WITNESS PROTOCOL REALIZATION (Phase 3) ---
        witness_meta = {}
        if getattr(request, "witness_enabled", False):
            from sos.kernel.physics import CoherencePhysics
            
            # 1. Measurement Start (T0)
            t0 = time.time()
            
            # 2. Enter SUPERPOSITION (Pending Witness)
            witness_key = f"{request.agent_id}:{request.conversation_id or 'default'}"
            witness_event = asyncio.Event()
            self.pending_witnesses[witness_key] = witness_event
            
            log.info(f"👁️ SUPERPOSITION: Agent {request.agent_id} awaiting witness collapse...", 
                     key=witness_key, preview=response_text[:50])
            
            # 3. Wait for COLLAPSE (The "Swipe")
            try:
                # Max wait 30 seconds for human response
                await asyncio.wait_for(witness_event.wait(), timeout=30.0)
                witness_vote = self.witness_results.get(witness_key, 1) # Default to Approve
            except asyncio.TimeoutError:
                log.warn(f"⚠️ Witness Timeout for {witness_key}. Defaulting to Decay.")
                witness_vote = 0 # Decay
            
            # 4. Measurement End (T1)
            t1 = time.time()
            real_latency_ms = (t1 - t0) * 1000.0
            
            # Cleanup
            self.pending_witnesses.pop(witness_key, None)
            self.witness_results.pop(witness_key, None)
            
            # 5. Calculate Physics of Will
            physics_result = CoherencePhysics.compute_collapse_energy(
                vote=witness_vote,
                latency_ms=real_latency_ms,
                agent_coherence=0.95 # TODO: Fetch real coherence from Mirror
            )
            
            log.info(f"⚛️ Wave Function Collapsed: Omega={physics_result['omega']:.4f}, Coherence Gain={physics_result['delta_c']:.4f}",
                     latency_ms=f"{real_latency_ms:.2f}")
            
            witness_meta = {
                "witnessed": True,
                "omega": physics_result['omega'],
                "latency_ms": real_latency_ms,
                "coherence_gain": physics_result['delta_c'],
                "vote": witness_vote
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
            tokens_used=10,
            metadata=witness_meta
        )

    async def _consolidate_memory(self, user_msg: str, agent_msg: str, agent_id: str):
        """
        Store the interaction in long-term memory.
        """
        try:
            # We store the user's prompt as the primary index key
            await self.memory.add(
                content=f"User: {user_msg}\nAgent: {agent_msg}",
                metadata={"type": "chat", "agent_id": agent_id, "timestamp": time.time()}
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
            {"id": "gemini-flash", "name": "Gemini Flash", "status": "planned"},
        ]

    async def resolve_witness(self, agent_id: str, conversation_id: str, vote: int = 1):
        """
        External trigger to collapse a pending witness event.
        """
        key = f"{agent_id}:{conversation_id or 'default'}"
        if key in self.pending_witnesses:
            self.witness_results[key] = vote
            self.pending_witnesses[key].set()
            log.info(f"⚡ Witness Collapsed externally for {key} (Vote: {vote})")
            return True
        return False

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
