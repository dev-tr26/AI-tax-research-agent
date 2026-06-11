import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
 
class PineconeStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pc = None
            cls._instance._index = None
        return cls._instance
 
    def connect(self):
        if self._pc is None:
            self._pc = Pinecone(api_key=settings.pinecone_api_key)
            self._ensure_index()
        return self

    def _ensure_index(self):
        existing = [idx.name for idx in self._pc.list_indexes()]
        if settings.pinecone_index_name not in existing:
            logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
            self._pc.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.embedding_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self._index = self._pc.Index(settings.pinecone_index_name)
        logger.info(f"Connected to Pinecone index: {settings.pinecone_index_name}")
        
        
    def upsert_chunks(self, chunks: List[Dict[str, Any]], namespace: str, batch_size: int = 100):
        #  list of chunks , each chunk has chunk_id , embedding, text , metadata
        
        if self._index is None:
            self.connect()
 
        vectors = []
        for chunk in chunks:
            meta = {**chunk.get("metadata", {}), "text": chunk["text"][:1000]}
            vectors.append({
                "id": chunk["chunk_id"],
                "values": chunk["embedding"],
                "metadata": meta,
            })
 
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self._index.upsert(vectors=batch, namespace=namespace)
            logger.debug(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors) ns={namespace}")
            
            
    def query(self, embedding: List[float], namespace: str, top_k : int =20, filter: Optional[Dict] = None,) -> List[Dict[str, Any]]:
        # semantic similarity search returns above items chunk_id, score, txt, metadata 
        if self._index is None:
            self.connect()
        
        resp = self._index.query(
            vector=embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True,
            filter=filter,
        )
        
        results = []
        for match in resp.matches:
            results.append({
                "chunk_id": match.id,
                "score": float(match.score),
                "text": match.metadata.pop("text", ""),
                "metadata": match.metadata,
            })
        return results
    
    def query_all_namespace(self,embedding: List[float], top_k: int =20,) -> List[Dict[str, Any]]:
        # querying both act and circular namespaces and merge
        act_results = self.query(
            embedding, settings.pinecone_namespace_act, top_k=top_k
        )
        circ_results = self.query(
            embedding, settings.pinecone_namespace_circular, top_k=top_k
        )
        merged = act_results + circ_results 
        merged.sort(key=lambda x: x["score"], reverse =True)
        return merged[:top_k]
    

    def fetch_by_ids(self, ids: List[str], namespace:str) -> Dict[str, Any]:
        # fetching specific chunk by id for citation verification
        if self._index is None:
            self.connect()
        resp = self._index.fetch(ids=ids, namespace=namespace)
        return {
            vid: {
                "chunk_id": vid,
                "text": vdata.metadata.get("text", ""),
                "metadata": vdata.metadata,
            }
            for vid, vdata in resp.vectors.items()
        }
        
    def index_stats(self) -> Dict:
        if self._index is None:
            self.connect()
        return self._index.describe_index_stats()
 
 
_pinecone_store = PineconeStore()
 
 
def get_pinecone_store() -> PineconeStore:
    return _pinecone_store.connect()