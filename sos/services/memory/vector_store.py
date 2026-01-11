import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sos.observability.logging import get_logger

log = get_logger("vector_store")

@dataclass
class VectorItem:
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float

class ChromaBackend:
    """
    Production-grade Vector Store using ChromaDB and SentenceTransformers.
    Implements Lazy Loading to protect boot time.
    """
    def __init__(self, persist_dir: str = "data/vector_db"):
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None
        self._model = None
        self._is_loaded = False

    def _lazy_load(self):
        """
        Load heavy dependencies only when first needed.
        """
        if self._is_loaded:
            return

        log.info("⏳ Loading Vector Core (ChromaDB + Transformers)...")
        start = time.time()
        
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            # Initialize Model
            # Using all-MiniLM-L6-v2 for speed/quality balance
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Initialize Chroma
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = self._client.get_or_create_collection(
                name="sos_memory",
                metadata={"hnsw:space": "cosine"}
            )
            
            self._is_loaded = True
            log.info(f"✅ Vector Core Loaded in {time.time() - start:.2f}s")
            
        except Exception as e:
            log.error("Failed to load Vector Core", error=str(e))
            raise

    def add(self, item_id: str, content: str, metadata: Dict[str, Any]) -> None:
        self._lazy_load()
        
        # Generate embedding
        embedding = self._model.encode(content).tolist()
        
        # Store
        self._collection.upsert(
            ids=[item_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata]
        )

    def search(self, query: str, limit: int = 5) -> List[VectorItem]:
        self._lazy_load()
        
        # Embed query
        query_embedding = self._model.encode(query).tolist()
        
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )
        
        items = []
        if results['ids']:
            # Chroma returns list of lists
            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for i in range(len(ids)):
                # Convert cosine distance to similarity score (approx)
                score = 1 - distances[i]
                items.append(VectorItem(
                    id=ids[i],
                    content=documents[i],
                    metadata=metadatas[i],
                    score=score
                ))
                
        return items

    def count(self) -> int:
        if not self._is_loaded:
            return 0
        return self._collection.count()
