import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from sos.kernel import Config
from sos.observability.logging import get_logger
from sos.services.memory.backends import SQLiteMetadataStore
from sos.services.memory.vector_store import ChromaBackend

from sos.services.memory.monitor import CoherenceMonitor

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
        self.monitor = CoherenceMonitor()
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
        
        # 0. Measure Coherence (Alpha Drift) 
        # Check similarity to existing memories *before* adding
        if self.vector_store:
            try:
                # Search for nearest neighbor (1-NN)
                results = self.vector_store.search(content, limit=1)
                
                if results and len(results) > 0:
                    best_score = results[0].score # Similarity (0..1)
                else:
                    # First memory or empty store = Maximum Novelty (or Neutral)
                    best_score = 0.5 
                
                state = self.monitor.update(best_score)
                log.info(f"🧠 ARF State Update | Score: {best_score:.4f} | Alpha: {state.alpha_norm:.4f} | Regime: {state.regime}")
                
            except Exception as e:
                log.warn(f"Coherence check failed: {e}")

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
        Now returns REAL FRC 841.004 metrics.
        """
        state = self.monitor.get_state()
        
        return {
            "alpha_drift": state.alpha_norm,
            "regime": state.regime,
            "coherence_raw": state.coherence,
            "timestamp": state.timestamp
        }

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "backend": "mock_chroma",
            "item_count": self.vector_store.count() if self.vector_store else 0
        }
