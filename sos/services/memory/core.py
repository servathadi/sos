import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

from sos.kernel import Config
from sos.observability.logging import get_logger

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
        self.encoder = None
        self._init_storage()

    def _init_storage(self):
        """
        Lazy load heavy dependencies to keep boot time fast.
        """
        try:
            # Mocking the heavy load for Phase 1 to ensure stability
            # In Phase 2, this will import chromadb and sentence_transformers
            log.info("Initializing Memory Core (Mock Mode for Phase 1)")
            self.vector_store = {} 
        except Exception as e:
            log.error("Failed to initialize vector store", error=str(e))

    async def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a memory engram.
        """
        item_id = f"mem_{int(time.time()*1000)}"
        log.info(f"Encoding memory: {content[:50]}...")
        
        # Mock storage
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
        results = []
        for mid, data in list(self.vector_store.items())[-limit:]:
            results.append(MemoryItem(
                id=mid,
                content=data["content"],
                metadata=data["metadata"],
                score=0.9
            ))
        return results

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "backend": "mock_chroma",
            "item_count": len(self.vector_store) if self.vector_store else 0
        }
