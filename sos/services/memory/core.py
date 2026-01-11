import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from sos.kernel import Config
from sos.observability.logging import get_logger
from sos.services.memory.backends import SQLiteMetadataStore

log = get_logger("memory_core")

@dataclass
class MemoryItem:
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float = 0.0

class MemoryCore:
    """
    The Hippocampus of the Sovereign OS.
    Manages Vector Storage (Short-term) and Mirror Sync (Long-term).
    """
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.vector_store = None
        self.metadata_store = None
        self._init_storage()

    def _init_storage(self):
        """
        Lazy load heavy dependencies to keep boot time fast.
        """
        try:
            # Persistent Metadata
            self.metadata_store = SQLiteMetadataStore()
            
            # Mocking the heavy load for Phase 1 to ensure stability
            # In Phase 2, this will import chromadb and sentence_transformers
            log.info("Initializing Memory Core (SQLite + Mock Vector)")
            self.vector_store = {} 
        except Exception as e:
            log.error("Failed to initialize vector store", error=str(e))

    async def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a memory engram.
        """
        item_id = f"mem_{int(time.time()*1000)}"
        log.info(f"Encoding memory: {content[:50]}...")
        
        # 1. Store Metadata (Persistent)
        if self.metadata_store:
            self.metadata_store.add(item_id, metadata or {})

        # 2. Store Vector (Mock)
        self.vector_store[item_id] = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        return item_id

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """
        Semantic search for memories.
        """
        log.info(f"Searching memory for: {query}")
        
        # Mock retrieval: return recent items
        # In Phase 2, this uses vector similarity
        results = []
        
        # Use Metadata Store for rich filtering if needed
        # For now, we iterate the mock vector store
        for mid, data in list(self.vector_store.items())[-limit:]:
            # Hydrate with persistent metadata if available
            meta = data["metadata"]
            if self.metadata_store:
                stored_meta = self.metadata_store.get(mid)
                if stored_meta:
                    meta = stored_meta.raw_metadata

            results.append(MemoryItem(
                id=mid,
                content=data["content"],
                metadata=meta,
                score=0.9
            ))
        return results

    async def get_arf_state(self) -> Dict[str, Any]:
        """
        Fetch the current ARF (Alpha Drift) state.
        In Phase 1, returns a simulated state based on current time.
        """
        # Simulation: Alpha drift fluctuates between -0.005 and 0.005
        # |alpha| < 0.001 triggers dreaming
        import math
        alpha = 0.005 * math.sin(time.time() / 100)
        regime = "stable" if abs(alpha) > 0.001 else "plastic"
        
        return {
            "alpha_drift": alpha,
            "regime": regime,
            "timestamp": time.time()
        }

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "backend": "mock_chroma",
            "item_count": len(self.vector_store) if self.vector_store else 0
        }
