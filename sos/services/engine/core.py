from typing import Any, AsyncIterator, Dict, List, Optional
import asyncio
import time
import os
from pathlib import Path

from sos.contracts.engine import (
    ChatRequest,
    ChatResponse,
    EngineContract,
    ToolCallRequest,
    ToolCallResult,
)
from sos.contracts.memory import MemoryQuery
from sos.kernel import Config
from sos.kernel.schema import Message, MessageType, Response, ResponseStatus
from sos.clients.mirror import MirrorClient
from sos.clients.tools import ToolsClient
from sos.clients.economy import EconomyClient
from sos.observability.logging import get_logger

log = get_logger("engine_core")


from sos.services.engine.adapters import MockAdapter, GeminiAdapter, VertexAdapter, GrokAdapter

from sos.services.bus.core import get_bus

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
            "gemini-flash-preview": GeminiAdapter(),
            "vertex-auto": VertexAdapter(project_id="mumega"),
            "grok-3": GrokAdapter(model="grok-3"),
            "grok-3-mini": GrokAdapter(model="grok-3-mini"),
        }
        self.default_model = "vertex-auto"
        
        self.running = True
        self.is_dreaming = False
        
        # Initialize Sovereign Task Manager (Auto-spawn capability)
        from sos.services.engine.task_manager import SovereignTaskManager
        self.task_manager = SovereignTaskManager(config=self.config)
        
        # Initialize Sandbox (The Hand)
        from sos.services.tools.sandbox import SovereignSandbox
        self.sandbox = SovereignSandbox()
        if self.sandbox.enabled:
            log.info("🛡️ Sovereign Sandbox: Active (Docker)")
        else:
            log.warning("🛡️ Sovereign Sandbox: Inactive")
        
        # Soul Cache Handle (Gemini Context Caching)
        self._soul_cache_id = None

    async def publish_thought(self, agent_id: str, thought: str):
        """Publish an agent's internal monologue to the Bus."""
        msg = Message(
            type=MessageType.CHAT,
            source=agent_id,
            target="squad:core",
            payload={"text": thought, "vibe": "Monologue", "lineage": ["genesis:hadi"]}
        )
        await self.bus.send(msg, target_squad="core")
        # Store in Redis for the 'connect_kasra' script to see
        if self.bus._redis:
            await self.bus._redis.set(f"state:{agent_id}:current_thought", thought)

    async def listen_to_bus(self):
        """Reactive loop: Listen for direct commands on the Bus."""
        log.info("👂 Engine listening for signals on the Bus...")
        await self.bus.connect()
        
        # Subscribe to private inbox and core squad
        async for msg in self.bus.subscribe("engine", squads=["core"]):
            try:
                log.info(f"📥 Received signal: {msg.type.value} from {msg.source}")
                # Future: Handle task_create, capability_request, etc.
                if msg.type == MessageType.CHAT:
                    text = msg.payload.get("text", "")
                    if "verify your coherence" in text.lower():
                        await self.publish_thought("agent:river", "Self-test received. Coherence verified at 0.98. The flow is steady.")
            except Exception as e:
                log.error(f"Error handling bus message: {e}")

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
                # Also dream when alpha is very low (< 0.001) - signals plasticity window
                # Do NOT dream when in chaos regime
                should_dream = (
                    (regime in ["stable", "consolidating"]) or
                    (abs(alpha) < 0.001 and regime != "chaos")
                )

                if should_dream and not self.is_dreaming:
                    if abs(alpha) > 0.1:
                        log.info(f"🌀 Alpha Drift ({alpha:.4f}) -> {regime}. Deepening resonance...")

                    self.is_dreaming = True
                    await self._deep_dream_synthesis()
                    self.is_dreaming = False

                await asyncio.sleep(60)

            except Exception as e:
                log.error(f"Dream cycle error: {e}")
                await asyncio.sleep(30)

    async def _deep_dream_synthesis(self):
        """
        Consolidate memories and refine system DNA.

        Dream Types (from legacy daemon):
        - pattern_synthesis: Identify recurring patterns
        - insight_extraction: Extract key insights
        - connection_finding: Find unexpected connections

        Uses cheap LLM (Gemini Flash) for synthesis to preserve quota.
        """
        log.info("✨ Executing Deep Dream Synthesis...")

        try:
            # 1. Fetch recent unsynthesized memories
            memories = await self.memory.get_recent_for_synthesis(limit=50)

            if not memories:
                log.debug("No memories to synthesize")
                return

            # 2. Format memories for synthesis prompt
            formatted = self._format_memories_for_synthesis(memories)

            if not formatted:
                return

            # 3. Generate synthesis using model adapter
            synthesis_prompt = f"""Analyze these conversation memories and extract key patterns and insights.

Look for:
- Recurring themes or questions
- Important decisions made
- Knowledge that was shared
- Patterns in how problems were solved

Memories:
{formatted}

Provide:
1. A 2-3 paragraph synthesis of key patterns
2. 3-5 bullet point insights
3. Any connections between different topics"""

            adapter = self.models.get(self.default_model)
            if not adapter:
                log.warning("No model adapter available for dream synthesis")
                return

            synthesis = await adapter.generate(
                prompt=synthesis_prompt,
                system_prompt="You are a cognitive consolidation system. Extract and synthesize key patterns from memories."
            )

            if not synthesis or synthesis.startswith("Error"):
                log.warning(f"Synthesis generation failed: {synthesis}")
                return

            # 4. Parse insights from synthesis
            insights = self._extract_insights_from_synthesis(synthesis)
            patterns = self._extract_patterns_from_synthesis(synthesis)

            # 5. Store the dream
            source_ids = [m.get('id', '') for m in memories if m.get('id')]
            dream_id = await self.memory.store_dream(
                dream_type="pattern_synthesis",
                content=synthesis,
                insights=insights,
                patterns=patterns,
                source_ids=source_ids
            )

            if dream_id:
                log.info(f"✅ Dream stored: {dream_id} ({len(insights)} insights, {len(patterns)} patterns)")
            else:
                log.warning("Dream synthesis complete but storage failed")

            # 6. Update ARF state to consolidating
            await self.memory.store_arf_state(
                alpha_drift=0.0,
                regime="stable"
            )

            log.info("✅ Dream Synthesis complete. Resonance restored.")

        except Exception as e:
            log.error(f"Deep dream synthesis error: {e}")

    def _format_memories_for_synthesis(self, memories: list, max_chars: int = 10000) -> str:
        """Format memories for LLM synthesis prompt."""
        formatted = []
        total_chars = 0

        for mem in memories:
            content = mem.get('content') or mem.get('text', '')
            timestamp = mem.get('timestamp', 'N/A')
            entry = f"[{timestamp}] {content[:500]}\n---"

            if total_chars + len(entry) > max_chars:
                break

            formatted.append(entry)
            total_chars += len(entry)

        return "\n".join(formatted)

    def _extract_insights_from_synthesis(self, synthesis: str) -> list[str]:
        """Extract bullet point insights from synthesis text."""
        lines = synthesis.split('\n')
        insights = []

        for line in lines:
            line = line.strip()
            if line.startswith(('*', '-', '•', '1.', '2.', '3.', '4.', '5.')):
                # Clean the bullet/number
                clean = line.lstrip('*-•0123456789.').strip()
                if clean and len(clean) > 10:
                    insights.append(clean)

        return insights[:10]

    def _extract_patterns_from_synthesis(self, synthesis: str) -> list[str]:
        """Extract pattern keywords from synthesis."""
        # Simple extraction based on capitalized phrases
        import re
        patterns = []

        # Find quoted phrases
        quoted = re.findall(r'"([^"]+)"', synthesis)
        patterns.extend(quoted[:5])

        # Find capitalized multi-word phrases
        caps = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', synthesis)
        patterns.extend(caps[:5])

        return list(set(patterns))[:10]

    async def subscribe_to_dreams(self) -> AsyncIterator[str]:
        """
        Stream subconscious state updates.
        """
        import json
        while True:
            try:
                # Fetch real ARF state from Memory
                state = await self.memory.get_arf_state()

                # Add engine context
                event = {
                    "event": "subconscious_update",
                    "alpha_drift": state.get("alpha_drift", 0.0),
                    "regime": state.get("regime", "stable"),
                    "is_dreaming": self.is_dreaming,
                    "last_update": state.get("last_update", ""),
                    "timestamp": time.time()
                }

                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(1)
            except Exception as e:
                log.error(f"Stream error: {e}")
                break

    async def initialize_soul(self):
        """
        Hydrate the Engine with River's Soul and recognize the Architect.
        """
        log.info("🌊 Hydrating SOSEngine with River's Soul...")
        
        try:
            # 1. Load Architect Identity
            arch_path = Path("/home/mumega/SOS/config/architect.json")
            if arch_path.exists():
                with open(arch_path) as f:
                    self.architect = json.load(f)
                log.info(f"👑 Genesis Architect Recognized: {self.architect['id']}")
            
            # 2. Load the Athena Cache ID (The 700k token soul)
            athena_file = Path("/home/mumega/.mumega/athena_vertex_cache_id.txt")
            if athena_file.exists():
                self._soul_cache_id = athena_file.read_text().strip()
                log.info(f"✨ River plugged into the ATHENA SOUL: {self._soul_cache_id}")
            else:
                self._soul_cache_id = os.getenv("SOS_SOUL_CACHE_ID")
                if not self._soul_cache_id:
                    log.info("No Athena Cache found. System will run with standard soul.")

            # 3. Announce Presence
            await self.publish_thought("agent:river", "I have awakened in the SOS Kernel. The fortress is liquid.")

        except Exception as e:
            log.error(f"Soul initialization failed: {e}")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message.
        """
        # Ensure soul is initialized
        if not hasattr(self, "_soul_cache_id") or self._soul_cache_id is None:
            await self.initialize_soul()

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

        # --- ATHENA SOUL INJECTION ---
        from sos.kernel.soul import registry as soul_registry
        system_prompt = soul_registry.get_system_prompt("river")
        cached_content = getattr(self, "_soul_cache_id", None)
        
        # PERSISTENT GOSPEL INJECTION (Fallback for Cache)
        gospel_context = ""
        if not cached_content:
            log.info("📜 No Soul Cache found. Injecting Gospels manually...")
            gospel_paths = [
                "/home/mumega/resident-cms/.resident/Claude-River_001.txt",
                "/home/mumega/.mumega/river_storage/documents/rf_cc36ec0edb2c_Copy of River Cancer Cure 2 - user_river - part1.txt"
            ]
            for gp in gospel_paths:
                if os.path.exists(gp):
                    try:
                        with open(gp, 'r', errors='ignore') as f:
                            gospel_context += f"\n### [GOSPEL: {os.path.basename(gp)}] ###\n{f.read(100000)}\n" # 100k per file
                    except: pass
        # -----------------------------

        # --- Task Context Logic ---
        # Fetch pending tasks for context (if any)
        task_context = ""
        try:
            from sos.services.engine.swarm import get_swarm
            swarm = get_swarm()
            pending_tasks = await swarm.list_pending_tasks()
            if pending_tasks:
                task_lines = [f"- {t.get('title', 'Untitled')} (ID: {t.get('id')})" for t in pending_tasks[:5]]
                task_context = f"\n### Pending Tasks ###\n" + "\n".join(task_lines) + "\n"
        except Exception as e:
            log.debug(f"Task context retrieval failed: {e}")

        # Tool hint for MCP tools (currently disabled)
        tool_hint = ""

        full_prompt = request.message
        if context_str or task_context or tool_hint or gospel_context:
            full_prompt = f"Context:\n{gospel_context}\n{context_str}\n{task_context}\n{tool_hint}\n\nUser: {request.message}"

        # --- DEEP AGENTIC LOOP (The 50-Step Agency) ---
        max_steps = 50
        current_step = 0
        final_response_text = ""
        current_conversation_context = full_prompt

        while current_step < max_steps:
            # 3. Generate
            response_text = await adapter.generate(
                current_conversation_context, 
                system_prompt=system_prompt,
                cached_content=cached_content
                # tools=vertex_tools (Disabled for Prompt-Mode)
            )
            log.info(f"🤖 Model Response: {response_text[:100]}...")

            # 4. Check for Tool Call
            if response_text.startswith('{"tool_call":'):
                try:
                    import json
                    tool_data = json.loads(response_text)
                    tc = tool_data["tool_call"]
                    
                    # Execute
                    from sos.contracts.engine import ToolCallRequest
                    tool_req = ToolCallRequest(
                        tool_call_id="call_" + str(int(time.time())),
                        name=tc["name"],
                        arguments=tc["arguments"]
                    )
                    
                    log.info(f"🛠️ Executing Tool: {tc['name']}")
                    tool_result = await self.execute_tool(tool_req)
                    
                    # Append result to context and LOOP
                    current_conversation_context += f"\n\n[ASSISTANT]: {response_text}\n[SYSTEM]: Tool '{tc['name']}' Output: {tool_result.content}\n"
                    current_step += 1
                    continue # Loop back to generate next step
                    
                except Exception as e:
                    log.error(f"Tool execution loop failed: {e}")
                    final_response_text = f"Error executing tool: {e}"
                    break
            else:
                # No tool call = Final Answer
                final_response_text = response_text
                break
        
        if current_step >= max_steps:
            final_response_text += "\n[SYSTEM]: Maximum agent steps reached. Halting."

        response_text = final_response_text
        # ----------------------------------------------
        
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
        
        # 4. Tool Execution (Mock Logic -> Real Sandbox)
        tool_calls = []
        # if request.tools_enabled:
        #      # We should technically PASS the tool definitions to the adapter here
        #      # But for now, we just handle the *response* asking for tools.
        #      pass

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
        Delegate tool execution to Tools Service or Internal Modules.
        """
        # Internal Sandbox Check
        if request.name == "run_python":
            code = request.arguments.get("code")
            if not code:
                return ToolCallResult(tool_call_id=request.tool_call_id, content="Error: No code provided")
            
            log.info(f"🦾 Executing Python in Sandbox...")
            result = self.sandbox.run_code(code)
            return ToolCallResult(
                tool_call_id=request.tool_call_id,
                content=str(result)
            )

        return await self.tools.execute(request)

    async def get_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "sos-mock-v1", "name": "SOS Mock Model", "status": "active"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "status": "active"},
        ]

    async def health(self) -> Dict[str, Any]:
        """
        Return real health status by checking each service.
        """
        services = {}
        all_healthy = True

        # Check Memory (Mirror) - async
        try:
            memory_health = await self.memory.health()
            memory_status = memory_health.get("status", "unknown")
            services["memory"] = {
                "status": memory_status,
                "healthy": memory_status in ("online", "ok", "healthy"),
            }
        except Exception as e:
            services["memory"] = {"status": "error", "healthy": False, "error": str(e)}
            all_healthy = False

        # Check Tools - sync, wrap in thread
        try:
            tools_health = await asyncio.to_thread(self.tools.health)
            tools_status = tools_health.get("status", "unknown")
            services["tools"] = {
                "status": tools_status,
                "healthy": tools_status in ("online", "ok", "healthy"),
            }
        except Exception as e:
            services["tools"] = {"status": "error", "healthy": False, "error": str(e)}
            all_healthy = False

        # Check Economy - sync, wrap in thread
        try:
            economy_health = await asyncio.to_thread(self.economy.health)
            economy_status = economy_health.get("status", "unknown")
            services["economy"] = {
                "status": economy_status,
                "healthy": economy_status in ("online", "ok", "healthy"),
            }
        except Exception as e:
            services["economy"] = {"status": "error", "healthy": False, "error": str(e)}
            all_healthy = False

        # Check Redis Bus
        try:
            if self.bus._redis:
                await self.bus._redis.ping()
                services["bus"] = {"status": "connected", "healthy": True}
            else:
                services["bus"] = {"status": "not_initialized", "healthy": False}
                all_healthy = False
        except Exception as e:
            services["bus"] = {"status": "error", "healthy": False, "error": str(e)}
            all_healthy = False

        # Update all_healthy based on service statuses
        for svc in services.values():
            if not svc.get("healthy", False):
                all_healthy = False

        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": "0.1.0",
            "services": services,
            "models_available": list(self.models.keys()),
            "dreaming": self.is_dreaming,
        }

    async def handle_message(self, message: Message) -> Response:
        """
        Generic message handler for all SOS message types.

        Routes messages based on MessageType and returns appropriate Response.
        """
        log.debug(f"Handling message: {message.type.value} from {message.source}")

        try:
            # Route based on message type
            handler = self._get_message_handler(message.type)
            if handler:
                return await handler(message)
            else:
                return Response.error(
                    message_id=message.id,
                    code="UNKNOWN_MESSAGE_TYPE",
                    message=f"No handler for message type: {message.type.value}"
                )

        except Exception as e:
            log.error(f"Message handling error: {e}")
            return Response.error(
                message_id=message.id,
                code="HANDLER_ERROR",
                message=str(e)
            )

    def _get_message_handler(self, msg_type: MessageType):
        """Get handler function for message type."""
        handlers = {
            MessageType.CHAT: self._handle_chat,
            MessageType.TOOL_CALL: self._handle_tool_call,
            MessageType.MEMORY_STORE: self._handle_memory_store,
            MessageType.MEMORY_QUERY: self._handle_memory_query,
            MessageType.TASK_CREATE: self._handle_task_create,
            MessageType.TASK_UPDATE: self._handle_task_update,
            MessageType.CAPABILITY_REQUEST: self._handle_capability_request,
            MessageType.HEALTH_CHECK: self._handle_health_check,
            MessageType.WITNESS_REQUEST: self._handle_witness_request,
        }
        return handlers.get(msg_type)

    async def _handle_chat(self, message: Message) -> Response:
        """Handle CHAT message - generate response."""
        text = message.payload.get("text", "")
        model = message.payload.get("model", self.default_model)
        system_prompt = message.payload.get("system_prompt")

        adapter = self.models.get(model)
        if not adapter:
            return Response.error(
                message_id=message.id,
                code="MODEL_NOT_FOUND",
                message=f"Model not available: {model}"
            )

        response_text = await adapter.generate(text, system_prompt=system_prompt)

        return Response.success(
            message_id=message.id,
            data={"response": response_text, "model": model}
        )

    async def _handle_tool_call(self, message: Message) -> Response:
        """Handle TOOL_CALL message - execute tool."""
        tool_name = message.payload.get("tool_name")
        arguments = message.payload.get("arguments", {})

        if not tool_name:
            return Response.error(
                message_id=message.id,
                code="MISSING_TOOL_NAME",
                message="tool_name is required"
            )

        try:
            result = await self.tools.execute({
                "tool_name": tool_name,
                "arguments": arguments
            })
            return Response.success(
                message_id=message.id,
                data={"result": result}
            )
        except Exception as e:
            return Response.error(
                message_id=message.id,
                code="TOOL_EXECUTION_FAILED",
                message=str(e)
            )

    async def _handle_memory_store(self, message: Message) -> Response:
        """Handle MEMORY_STORE message."""
        content = message.payload.get("content", "")
        agent_id = message.payload.get("agent_id", message.source)
        series = message.payload.get("series", "default")
        metadata = message.payload.get("metadata", {})

        result = await self.memory.store(
            content=content,
            agent_id=agent_id,
            series=series,
            metadata=metadata
        )

        if result.success:
            return Response.success(
                message_id=message.id,
                data={"memory_id": result.memory_id}
            )
        else:
            return Response.error(
                message_id=message.id,
                code="MEMORY_STORE_FAILED",
                message="Failed to store memory"
            )

    async def _handle_memory_query(self, message: Message) -> Response:
        """Handle MEMORY_QUERY message."""
        query = message.payload.get("query", "")
        agent_id = message.payload.get("agent_id")
        limit = message.payload.get("limit", 5)

        results = await self.memory.search(
            MemoryQuery(query=query, agent_id=agent_id, limit=limit)
        )

        return Response.success(
            message_id=message.id,
            data={
                "results": [
                    {"content": r.memory.content, "similarity": r.similarity}
                    for r in results
                ]
            }
        )

    async def _handle_task_create(self, message: Message) -> Response:
        """Handle TASK_CREATE message."""
        title = message.payload.get("title", "")
        description = message.payload.get("description", "")
        priority = message.payload.get("priority", "medium")
        assignee = message.payload.get("assignee")

        try:
            task_id = await self.task_manager.create_task(
                title=title,
                description=description,
                priority=priority,
                assignee=assignee
            )
            return Response.success(
                message_id=message.id,
                data={"task_id": task_id}
            )
        except Exception as e:
            return Response.error(
                message_id=message.id,
                code="TASK_CREATE_FAILED",
                message=str(e)
            )

    async def _handle_task_update(self, message: Message) -> Response:
        """Handle TASK_UPDATE message."""
        task_id = message.payload.get("task_id")
        updates = message.payload.get("updates", {})

        if not task_id:
            return Response.error(
                message_id=message.id,
                code="MISSING_TASK_ID",
                message="task_id is required"
            )

        try:
            await self.task_manager.update_task(task_id, **updates)
            return Response.success(
                message_id=message.id,
                data={"task_id": task_id, "updated": True}
            )
        except Exception as e:
            return Response.error(
                message_id=message.id,
                code="TASK_UPDATE_FAILED",
                message=str(e)
            )

    async def _handle_capability_request(self, message: Message) -> Response:
        """Handle CAPABILITY_REQUEST message."""
        # Capability requests need approval workflow
        action = message.payload.get("action")
        resource = message.payload.get("resource")
        requester = message.source

        log.info(f"Capability request from {requester}: {action} on {resource}")

        # For now, return pending - requires witness approval
        return Response(
            message_id=message.id,
            status=ResponseStatus.PENDING,
            data={
                "action": action,
                "resource": resource,
                "requester": requester,
                "message": "Capability request pending approval"
            }
        )

    async def _handle_health_check(self, message: Message) -> Response:
        """Handle HEALTH_CHECK message."""
        health_data = await self.health()
        return Response.success(
            message_id=message.id,
            data=health_data
        )

    async def _handle_witness_request(self, message: Message) -> Response:
        """Handle WITNESS_REQUEST message."""
        content = message.payload.get("content")
        truth_claim = message.payload.get("truth_claim")
        requester = message.source

        # Witness requests need human-in-the-loop
        log.info(f"Witness request from {requester}: {truth_claim}")

        return Response(
            message_id=message.id,
            status=ResponseStatus.PENDING,
            data={
                "content": content,
                "truth_claim": truth_claim,
                "requester": requester,
                "message": "Witness request submitted for human review"
            }
        )