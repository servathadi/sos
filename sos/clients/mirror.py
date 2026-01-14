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