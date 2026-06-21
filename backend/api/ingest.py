# ingestion api router -> triggers ingestion ,check stats, verify idx coverage 

import asyncio
import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from db.database import get_ingestion_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

class IngestionRequest(BaseModel):
    source: str = "all"  # "all" | "ita" | "cbdt"


# async ingestion pipeline triggers return job id , pipeline runs in background
@router.post("")
async def trigger_ingestion(req: IngestionRequest, background_tasks: BackgroundTasks):
    if req.source not in ("all", "ita", "cbdt"):
        raise HTTPException(status_code=400, detail="source must be 'all', 'ita', or 'cbdt'")

    job_id = str(uuid.uuid4())


    async def _run():
        try:
            from ingestion.pipeline import run_pipeline
            await run_pipeline(req.source)
        except Exception as e:
            logger.error(f"Ingestion pipeline failed (job={job_id}): {e}", exc_info=True)

    
    background_tasks.add_task(_run)
    logger.info(f"Ingestion triggered: source={req.source} job={job_id}")
    return {"job_id": job_id, "source": req.source, "status": "started"}


@router.get("/stats")
async def ingestion_stats():
    """Return ingestion counts by status (SUCCESS/FAILED) and Pinecone index stats."""
    stats = await get_ingestion_stats()
    pinecone_stats = {}
    try:
        from retrieval.vector_store import get_pinecone_store
        pinecone_stats = get_pinecone_store().index_stats()
    except Exception as e:
        logger.warning(f"Pinecone stats unavailable: {e}")

    return {"ingestion": stats, "pinecone": pinecone_stats}




@router.get("/coverage")
async def index_coverage():
    """
    Spot-check index coverage by querying 20 known ITA 2025 section numbers.
    Returns per-section retrieval result.
    """
    from retrieval.embeddings import get_embedding_service
    from retrieval.vector_store import get_pinecone_store
    from config import get_settings

    settings = get_settings()
    sample_sections = [
        "2", "4", "10", "14", "24", "28",
        "40", "40A", "45", "54", "54F", "56",
        "68", "70", "71", "74", "80C", "92",
        "147", "260A",
    ]
    
    
    emb = get_embedding_service()
    pc = get_pinecone_store()
    results = {}
    
    for sec in sample_sections:
        query = f"Section {sec} Income Tax Act 2025"
        vec = emb.embed_query(query)
        hits = pc.query(vec, namespace=settings.pinecone_namespace_act, top_k=1, filter={"section": {"$eq": sec}},)
        
        results[sec] = {
            "found": len(hits) > 0,
            "chunk_id": hits[0]["chunk_id"] if hits else None,
            "score": hits[0]["score"] if hits else 0,
        }
    
    coverage_pct = sum(1 for v in results.values() if v["found"]) / len(results) * 100
    return {
        "coverage_pct": round(coverage_pct, 1),
        "sections_checked": len(results),
        "sections_found": sum(1 for v in results.values() if v["found"]),
        "details": results,
    }