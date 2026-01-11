import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from sos.kernel import Config
from sos.observability.logging import get_logger
from sos.services.memory.backends import SQLiteMetadataStore
from sos.services.memory.vector_store import ChromaBackend

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
    Manages Vector Storage (ChromaDB) and Metadata (SQLite).
    """
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.vector_store = None
        self.metadata_store = None
        self._init_storage()

    def _init_storage(self):
        """
        Lazy load storage backends.
        """
        try:
            # Persistent Metadata
            self.metadata_store = SQLiteMetadataStore()
            
            # Vector Backend (Lazy Loaded internally)
            self.vector_store = ChromaBackend()
            log.info("Initializing Memory Core (SQLite + ChromaDB)")
            
        except Exception as e:
            log.error("Failed to initialize storage", error=str(e))

    async def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a memory engram.
        """
        item_id = f"mem_{int(time.time()*1000)}"
        log.info(f"Encoding memory: {content[:50]}...")
        
        metadata = metadata or {}
        
        # 1. Store Metadata (Persistent)
        if self.metadata_store:
            self.metadata_store.add(item_id, metadata)

        # 2. Store Vector (Real)
        if self.vector_store:
            self.vector_store.add(item_id, content, metadata)
            
        return item_id

    async def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """
        Semantic search for memories.
        """
        log.info(f"Searching memory for: {query}")
        
        results = []
        if self.vector_store:
            vector_results = self.vector_store.search(query, limit)
            
            # Map back to internal MemoryItem
            for v_item in vector_results:
                # Hydrate with richer metadata from SQLite if needed
                # For now, we trust the vector metadata
                results.append(MemoryItem(
                    id=v_item.id,
                    content=v_item.content,
                    metadata=v_item.metadata,
                    score=v_item.score
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
