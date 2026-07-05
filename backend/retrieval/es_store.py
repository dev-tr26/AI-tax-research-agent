# elastic search BM25 keyword search with pinecone via reciprocal rank fusion

import logging
from typing import List, Dict,Any,Optional
from elasticsearch import AsyncElasticsearch
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ACT_MAPPING = {
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "english"},
            "act": {"type": "keyword"},
            "section": {"type": "keyword"},
            "sub_section": {"type": "keyword"},
            "clause": {"type": "keyword"},
            "proviso": {"type": "boolean"},
            "chunk_type": {"type": "keyword"},
            "domain": {"type": "keyword"},
            "effective_from": {"type": "date"},
            "last_amended": {"type": "date"},
        }
    },
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
}

CIRCULAR_MAPPING = {
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "english"},
            "circular_number": {"type": "keyword"},
            "issuing_authority": {"type": "keyword"},
            "subject": {"type": "text"},
            "effective_date": {"type": "date"},
            "chunk_type": {"type": "keyword"},
        }
    },
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
}

class ElasticsearchStore:
    _instance = None
 
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance
 
    def get_client(self) -> AsyncElasticsearch:
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                request_timeout=30,
            )
        return self._client
 
    async def ensure_indices(self):
        client = self.get_client()
        for idx_name, mapping in [
            (settings.elasticsearch_index_act, ACT_MAPPING),
            (settings.elasticsearch_index_circular, CIRCULAR_MAPPING),
        ]:
            if not await client.indices.exists(index=idx_name):
                await client.indices.create(index=idx_name, body=mapping)
                logger.info(f"Created ES index: {idx_name}")
 
    async def index_chunk(self, chunk: Dict[str, Any], index_name: str):
        client = self.get_client()
        doc = {"chunk_id": chunk["chunk_id"], "text": chunk["text"], **chunk.get("metadata", {})}
        await client.index(index=index_name, id=chunk["chunk_id"], document=doc)
 
    async def bulk_index(self, chunks: List[Dict[str, Any]], index_name: str):
        client = self.get_client()
        operations = []
        for chunk in chunks:
            operations.append({"index": {"_index": index_name, "_id": chunk["chunk_id"]}})
            operations.append({"chunk_id": chunk["chunk_id"], "text": chunk["text"], **chunk.get("metadata", {})})
        if operations:
            resp = await client.bulk(operations=operations)
            if resp.get("errors"):
                logger.warning("Some ES bulk indexing errors occurred")
 
    async def search(self, query: str, index_name: str, top_k: int = 20, filters: Optional[Dict] = None,) -> List[Dict[str, Any]]:
        # BM25 full-text search with optional term filters 
        client = self.get_client()
 
        must_clauses = [{"match": {"text": {"query": query, "operator": "or"}}}]
        filter_clauses = []
 
        if filters:
            for key, val in filters.items():
                filter_clauses.append({"term": {key: val}})
 
        body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses,
                }
            },
            "size": top_k,
            "_source": True,
        }
 
        resp = await client.search(index=index_name, body=body)
        results = []
        for hit in resp["hits"]["hits"]:
            src = hit["_source"]
            text = src.pop("text", "")
            results.append({
                "chunk_id": src.get("chunk_id", hit["_id"]),
                "score": float(hit["_score"]),
                "text": text,
                "metadata": src,
            })
        return results
 
    async def search_all_indices(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        act_results = await self.search(query, settings.elasticsearch_index_act, top_k)
        circ_results = await self.search(query, settings.elasticsearch_index_circular, top_k)
        merged = act_results + circ_results
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:top_k]
 
    async def get_by_id(self, chunk_id: str, index_name: str) -> Optional[Dict]:
        client = self.get_client()
        try:
            resp = await client.get(index=index_name, id=chunk_id)
            src = resp["_source"]
            text = src.pop("text", "")
            return {"chunk_id": chunk_id, "text": text, "metadata": src}
        except Exception:
            return None
 
 
_es_store = ElasticsearchStore()
 

def get_es_store() -> ElasticsearchStore:
    return _es_store