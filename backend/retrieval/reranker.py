# cross order reranker - takes top 20 chunks and reranks to top 5
# uses cross-encoder/ms-macro-MiniLM-L-6-v2  
# implemented reciprocal rank fusion to merge vector + keyword results

import logging
from typing import List, Dict, Any, Tuple 
from config import get_settings
from sentence_transformers import CrossEncoder
from functools import lru_cache

logger = logging.getLogger(__name__)
settings = get_settings()

class Reranker:
    _instance = None 
    _model : CrossEncoder = None 
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        
        return cls._instance 
    
    def load(self):
        if self._model is None:
            logger.info(f"Loading reranker: {settings.reranker_model}")
            self._model = CrossEncoder(settings.reranker_model, max_length=512)
            logger.info("Reranker loaded")
        return self
    
    
    def rerank(self, query:str, candidates: List[Dict[str, Any]], top_k: int =5) -> List[Dict[str, Any]]:
        # score all chunks returns top_k sorted by relanvance
        if self._model is None:
            self.load()
        if not candidates:
            return []
        
        pairs = [(query, c["text"]) for c in candidates]
        scores = self._model.predict(pairs, show_progress_bar=False)
        
        for chunk, score in zip(candidates, scores):
            chunk["rerank_score"] = float(score)
            
        
        reranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return reranked[:top_k]
    
    def reciprocal_rank_fusion(result_lists: List[List[Dict[str, Any]]], k: int = 60, top_k: int = 20,) -> List[Dict[str, Dict]]: 
        # merge multiple ranked result lists using ,RRF k =60
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict] = {}
        
        for result_list in result_lists:
            for rank,chunk in enumerate(result_list):
                cid = chunk["chunk_id"]
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
                if cid not in chunk_map:
                    chunk_map[cid] = chunk
                    
        merged = []
        for cid,rrf_score in sorted(scores.item(), key=lambda x: x[1], reverse=True):
            entry = {**chunk_map[cid], "rrf_score": rrf_score}
            merged.append(entry)
            
        return merged[:top_k]
 
 

_reranker = Reranker()
 
 
def get_reranker() -> Reranker:
    return _reranker.load()