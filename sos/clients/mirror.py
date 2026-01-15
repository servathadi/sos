import logging
import os
import httpx
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime

from sos.clients.base import BaseHTTPClient
from sos.observability.logging import get_logger
from sos.contracts.memory import (
    MemoryContract, 
    Memory, 
    MemoryType, 
    MemoryQuery, 
    MemorySearchResult, 
    StoreResult
)
from sos.kernel import Capability

log = get_logger("client_mirror")

class MirrorClient(MemoryContract):
    """
    Connects to the Production Mirror (https://mumega.com/mirror).
    Implements the MemoryContract and Antigravity schema (RC-7 compliant).
    """
    
    def __init__(self, base_url: str = "https://mumega.com/mirror", agent_id: str = "antigravity"):
        self.base_url = base_url.rstrip('/')
        self.agent_id = agent_id
        
        # Retrieve key from env
        self.api_key = os.getenv("MUMEGA_MASTER_KEY", "sk-mumega-internal-001")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = 30.0

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if "headers" in kwargs:
                    kwargs["headers"].update(self.headers)
                else:
                    kwargs["headers"] = self.headers
                    
                resp = await client.request(method, url, **kwargs)
                return resp
            except Exception as e:
                log.error(f"Request failed: {e}")
                raise

    async def check_connection(self) -> bool:
        """Health check (GET /)."""
        try:
            resp = await self._request("GET", "/")
            if resp.status_code == 200:
                log.info(f"✓ Connected to Mirror Health Check")
                return True
            else:
                log.error(f"❌ Mirror returned {resp.status_code}")
                return False
        except Exception as e:
            log.error(f"❌ Connection failed: {e}")
            return False

    async def store(
        self,
        content: str,
        agent_id: str,
        series: str = "default",
        memory_type: MemoryType = MemoryType.ENGRAM,
        importance: float = 0.5,
        epistemic_truths: Optional[list[str]] = None,
        core_concepts: Optional[list[str]] = None,
        affective_vibe: str = "Neutral",
        metadata: Optional[dict] = None,
        capability: Optional[Capability] = None,
    ) -> StoreResult:
        """Saves current state to the Mirror using POST /store endpoint."""
        try:
            context_id = f"sos_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:4]}"

            payload = {
                "agent": agent_id,
                "series": series,
                "context_id": context_id,
                "text": content,
                "importance": importance,
                "epistemic_truths": epistemic_truths or [],
                "core_concepts": core_concepts or [],
                "affective_vibe": affective_vibe,
                "metadata": {
                    **(metadata or {}),
                    "source": "sos_mirror_client",
                    "memory_type": memory_type.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            resp = await self._request("POST", "/store", json=payload)
            
            if resp.status_code == 200:
                log.info(f"✓ Memory stored successfully. ID: {context_id}")
                return StoreResult(memory_id=context_id, success=True)
            else:
                log.error(f"❌ Store failed: {resp.status_code} {resp.text}")
                return StoreResult(memory_id="", success=False)
        except Exception as e:
            log.error(f"Store Error: {e}")
            return StoreResult(memory_id="", success=False)

    async def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Semantic Search using POST /search endpoint."""
        try:
            payload = {
                "query": query.query,
                "agent_id": query.agent_id,
                "limit": query.limit,
                "min_similarity": query.min_similarity
            }
            resp = await self._request("POST", "/search", json=payload)
            
            results = []
            if resp.status_code == 200:
                data = resp.json()
                # Handle both list and dict response formats
                engrams = data.get('results', []) if isinstance(data, dict) else data
                for e in engrams:
                    mem = Memory(
                        id=e.get('id'),
                        content=e.get('content') or e.get('text'),
                        agent_id=e.get('agent'),
                        series=e.get('series', 'default'),
                        importance=e.get('importance', 0.5),
                        epistemic_truths=e.get('epistemic_truths', []),
                        core_concepts=e.get('core_concepts', []),
                        affective_vibe=e.get('affective_vibe', 'Neutral'),
                        metadata=e.get('metadata', {})
                    )
                    results.append(MemorySearchResult(memory=mem, similarity=e.get('similarity', 0.0)))
            return results
        except Exception as e:
            log.error(f"Search Error: {e}")
            return []

    async def restore_identity(self, agent_id: str = None) -> str:
        """
        Fetches recent memories to restore context.
        Uses GET /recent/{agent_id} endpoint.
        """
        target_agent = agent_id or self.agent_id
        try:
            log.info(f"Fetching recent memories for {target_agent}...")
            resp = await self._request("GET", f"/recent/{target_agent}", params={"limit": 10})
            
            if resp.status_code != 200:
                 return f"Error {resp.status_code}: {resp.text}"

            data = resp.json() 
            engrams = data.get('engrams', []) if isinstance(data, dict) else data
            
            if not engrams:
                 return "No memories found. I am a new instance."

            context = [f"# Restored Identity ({len(engrams)} engrams)"]
            for e in engrams:
                content = e.get('content') or e.get('text') or str(e)
                tags = e.get('tags') or e.get('core_concepts') or []
                context.append(f"- [{', '.join(tags)}]: {content[:200]}...")

            return "\n".join(context)

        except Exception as e:
            log.error(f"Restore Error: {e}")
            return f"Error restoring identity: {e}"

    # Implementation of remaining abstract methods
    async def get(self, memory_id: str, capability: Optional[Capability] = None) -> Optional[Memory]:
        # Mirror API currently doesn't have a direct GET /id, we could use search or add it.
        return None

    async def delete(self, memory_id: str, capability: Optional[Capability] = None) -> bool:
        # Implement when API supports it
        return False

    async def relate(self, memory_id: str, related_id: str, relation_type: str = "related", capability: Optional[Capability] = None) -> bool:
        return False

    async def consolidate(self, agent_id: str, capability: Optional[Capability] = None) -> int:
        return 0

    async def decay(self, agent_id: str, threshold: float = 0.3, capability: Optional[Capability] = None) -> int:
        return 0

    async def health(self) -> dict[str, Any]:
        return {"status": "online" if await self.check_connection() else "offline"}

    async def stats(self, agent_id: Optional[str] = None) -> dict[str, Any]:
        return {}

    async def get_arf_state(self, agent_id: Optional[str] = None) -> dict[str, Any]:
        """
        Fetch latest ARF (Alpha Resonance Field) state from reflections.

        ARF state includes:
        - alpha_drift: Current drift value (< 0.001 signals plasticity)
        - regime: stable, plastic, chaos, consolidating
        - last_update: Timestamp of last state change

        Returns:
            Dict with ARF state or defaults if not found
        """
        target_agent = agent_id or self.agent_id
        try:
            # Search for ARF kernel state in reflections
            resp = await self._request(
                "POST",
                "/search",
                json={
                    "query": "ARF state alpha drift regime",
                    "agent_id": target_agent,
                    "limit": 1,
                    "series": "arf_kernel"
                }
            )

            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', []) if isinstance(data, dict) else data

                if results:
                    # Parse ARF state from content
                    content = results[0].get('content', '')
                    metadata = results[0].get('metadata', {})

                    # Try to extract from metadata first
                    if 'alpha_drift' in metadata:
                        return {
                            "alpha_drift": float(metadata.get('alpha_drift', 0.0)),
                            "regime": metadata.get('regime', 'stable'),
                            "last_update": metadata.get('timestamp', datetime.utcnow().isoformat())
                        }

                    # Parse from content if needed
                    import json as json_module
                    try:
                        if "ARF State:" in content:
                            state_text = content.replace("ARF State:", "").strip()
                            return json_module.loads(state_text)
                    except (json_module.JSONDecodeError, ValueError):
                        pass

            # Return default stable state
            return {
                "alpha_drift": 0.0,
                "regime": "stable",
                "last_update": datetime.utcnow().isoformat()
            }

        except Exception as e:
            log.warning(f"ARF state fetch failed: {e}")
            return {
                "alpha_drift": 0.0,
                "regime": "stable",
                "last_update": datetime.utcnow().isoformat()
            }

    async def store_arf_state(
        self,
        alpha_drift: float,
        regime: str,
        agent_id: Optional[str] = None
    ) -> bool:
        """
        Store current ARF state to memory.

        Args:
            alpha_drift: Current alpha drift value
            regime: Current regime (stable, plastic, chaos, consolidating)
            agent_id: Agent identifier

        Returns:
            True if stored successfully
        """
        target_agent = agent_id or self.agent_id
        try:
            import json as json_module
            state = {
                "alpha_drift": alpha_drift,
                "regime": regime,
                "timestamp": datetime.utcnow().isoformat()
            }

            result = await self.store(
                content=f"ARF State: {json_module.dumps(state)}",
                agent_id=target_agent,
                series="arf_kernel",
                importance=0.8,
                epistemic_truths=[f"alpha_drift={alpha_drift:.6f}", f"regime={regime}"],
                core_concepts=["arf", "state", "drift"],
                affective_vibe="System",
                metadata=state
            )
            return result.success

        except Exception as e:
            log.error(f"ARF state store failed: {e}")
            return False

    async def get_recent_for_synthesis(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Get recent memories for dream synthesis.

        Returns memories that haven't been synthesized yet,
        sorted by timestamp descending.
        """
        target_agent = agent_id or self.agent_id
        try:
            resp = await self._request(
                "GET",
                f"/recent/{target_agent}",
                params={"limit": limit}
            )

            if resp.status_code == 200:
                data = resp.json()
                engrams = data.get('engrams', []) if isinstance(data, dict) else data

                # Filter out already-synthesized memories
                unsynthesized = [
                    e for e in engrams
                    if not e.get('metadata', {}).get('synthesized', False)
                ]
                return unsynthesized

            return []

        except Exception as e:
            log.warning(f"Failed to get memories for synthesis: {e}")
            return []

    async def store_dream(
        self,
        dream_type: str,
        content: str,
        insights: list[str],
        patterns: list[str],
        source_ids: list[str],
        agent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Store a synthesized dream to memory.

        Args:
            dream_type: Type of dream (pattern_synthesis, insight_extraction, etc.)
            content: Full dream content
            insights: Key insights extracted
            patterns: Patterns identified
            source_ids: IDs of source memories
            agent_id: Agent identifier

        Returns:
            Dream memory ID if successful
        """
        target_agent = agent_id or self.agent_id
        try:
            result = await self.store(
                content=content,
                agent_id=target_agent,
                series=f"dreams_{dream_type}",
                importance=0.9,
                epistemic_truths=insights[:5],
                core_concepts=patterns[:5],
                affective_vibe="Dreamlike",
                metadata={
                    "dream_type": dream_type,
                    "source_memory_ids": source_ids,
                    "synthesized_at": datetime.utcnow().isoformat(),
                    "is_dream": True
                }
            )
            return result.memory_id if result.success else None

        except Exception as e:
            log.error(f"Dream storage failed: {e}")
            return None