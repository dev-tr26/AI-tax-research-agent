"""
Central configuration — all settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    google_api_key: str = ""
    reasoning_model: str = "llama-3.3-70b-versatile"   # Groq model ID
    fast_model: str = "gemini-2.0-flash"                # Gemini for classification

    # Embeddings
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dim: int = 1024

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "taxai-index"
    pinecone_namespace_act: str = "ita-2025"
    pinecone_namespace_circular: str = "cbdt-circulars"

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index_act: str = "taxai-act"
    elasticsearch_index_circular: str = "taxai-circulars"

    # SQLite
    sqlite_path: str = "./data/taxai.db"

    # Data
    data_dir: str = "./data"
    pdf_cache_dir: str = "./data/pdfs"

    # LangSmith
    langsmith_api_key: str = ""
    langsmith_project: str = "taxai"
    langchain_tracing_v2: bool = True

    # Retrieval
    retrieval_top_k_candidates: int = 20
    retrieval_top_k_final: int = 5
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Ingestion sources
    ita_url: str = "https://www.indiacode.nic.in/handle/123456789/1501"
    cbdt_circulars_url: str = "https://www.incometaxindia.gov.in/communications/circular/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()