import os
import uuid
import logging
from typing import List, Dict, Any, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

logger = logging.getLogger("goatclaw.vector_store")

class VectorStore:
    """
    USP: Professional Vector Database Interface with Qdrant and Local Fallback.
    """
    def __init__(self, collection_name: str = "memory_collection", dimension: int = 128):
        self.collection_name = collection_name
        self.dimension = dimension
        self.use_qdrant = HAS_QDRANT and os.getenv("QDRANT_HOST") is not None
        
        if self.use_qdrant:
            try:
                self.client = QdrantClient(
                    host=os.getenv("QDRANT_HOST", "localhost"),
                    port=int(os.getenv("QDRANT_PORT", 6333))
                )
                # Ensure collection exists
                self._ensure_collection()
                logger.info(f"Initialized Qdrant VectorStore (host={os.getenv('QDRANT_HOST')})")
            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant: {e}. Falling back to in-memory.")
                self.use_qdrant = False
        
        if not self.use_qdrant:
            self._storage: Dict[str, Dict[str, Any]] = {}
            logger.info(f"Initialized In-Memory VectorStore (dimension={dimension})")

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection_name)
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=self.dimension, distance=models.Distance.COSINE),
            )

    async def add_embedding(self, vector: List[float], payload: Dict[str, Any], id: Optional[str] = None) -> str:
        """Store an embedding."""
        point_id = id or str(uuid.uuid4())
        
        if self.use_qdrant:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
        else:
            self._storage[point_id] = {
                "vector": vector,
                "payload": payload
            }
        
        logger.debug(f"Stored embedding: {point_id}")
        return point_id

    async def search(self, vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        if self.use_qdrant:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit
            )
            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in results
            ]
        else:
            # Simple retrieval for memory mock (last N)
            results = []
            for point_id, data in list(self._storage.items())[-limit:]:
                results.append({
                    "id": point_id,
                    "score": 1.0, 
                    "payload": data["payload"]
                })
            return results

    async def delete(self, id: str):
        if self.use_qdrant:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[id])
            )
        else:
            if id in self._storage:
                del self._storage[id]

# Global Vector Store Instance
vector_store = VectorStore()
