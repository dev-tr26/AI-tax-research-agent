# using free HF BAAI/bge-large-en-v1.5 embeddings

import numpy as np 
import logging 
from typing import Union, List 
from functools import lru_cache
from config import get_settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
settings = get_settings()

class EmbeddingService:
    _instance = None
    _model: SentenceTransformer  = None 
    
    def __new__(cls):
        if cls.instance is None:
            cls._instance = super().__new__(cls)
            
        return cls._instance
    
    def load(self):
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(
                settings.embedding_model,
                device="cpu",
            )
            logger.info("Embedding model loadded. ")
        return self 
    
    def embed(self, texts: Union[str, List[str]], batch_size : int =32) -> np.ndarray:
        # return float 32 array 
        if self._model is None:
            self.load()
        
        if isinstance(texts, str):
            texts = [texts]
            
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        
        return embeddings.astype(np.float32)
    
    def embed_query(self, query: str) -> List[float]:
        # embed single query with BGE query prefix 
        prefixed = f"Represent this sentence for searching relevant passages: {query}"
        vec = self.embed(prefixed)[0]
        return vec.tolist()
    

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        # batch of doc chunks 
        vecs = self.embed(docs)
        return vecs.tolist()
    

_embedding_service = EmbeddingService()

def get_embedding_service() -> EmbeddingService:
    return _embedding_service.load()
