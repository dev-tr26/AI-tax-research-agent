import asyncio
import json 
import time 
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator
import uvicorn 
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
import logging
from config import get_settings
from db.database import init_db
from agents.pipeline import get_pipeline
from monitoring.metrics import get_metrics
from monitoring.routes import router as metrics_router
from api.sessions import router as sessions_router
from api.ingest import router as ingest_router
from utils.logging_config import setup_logging
from retrieval.embeddings import get_embedding_service
from retrieval.reranker import get_reranker


setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TaxAI starting up...")
    await init_db()

    asyncio.create_task(background_warmup())
    logger.info("Embedding model warm.")
    yield
    logger.info("TaxAI shutting down.")


async def background_warmup():
    try:
        from retrieval.embeddings import get_embedding_service
        get_embedding_service().embed_query("warmup")
    except Exception as e:
        logger.warning(e)

    try:
        from retrieval.reranker import get_reranker
        get_reranker()
    except Exception as e:
        logger.warning(e)

    try:
        from utils.section_index import get_section_index
        await get_section_index().build_from_pinecone()
    except Exception as e:
        logger.warning(e)
        
        
app = FastAPI(
    title="TaxAI — Indian Tax Research Platform",
    description="Agentic AI for Direct Tax (ITA 2025 + CBDT Circulars). Three-agent AutoGen pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(metrics_router)
app.include_router(sessions_router)
app.include_router(ingest_router)


@app.middleware("http")
async def add_latency_header(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    response.headers["X-Response-Time-Ms"] = str(int((time.monotonic() - t0) * 1000))
    return response


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    stream: bool = False
    

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "taxai", "version": "1.0.0"}


@app.post("/query", tags=["query"])
async def query_endpoint(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if len(req.query) > 2000:
        raise HTTPException(status_code=400, detail="Query too long (max 2000 chars).")

    if req.stream:
        return StreamingResponse(
            _sse_stream(req.query, req.session_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    pipeline = get_pipeline()
    
    try:
        t0 = time.monotonic()
        result = await pipeline.run(req.query, req.session_id)
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info(f"[/query] {elapsed}ms session={result.get('session_id','?')}")
        get_metrics().record_from_pipeline_result(req.query, result.get("session_id", ""), result)
        return result
    except Exception as e:
        logger.error(f"[/query] error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")



async def _sse_stream(query: str, session_id: Optional[str]) -> AsyncIterator[str]:
    def _evt(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    for stage, msg in [
        ("session",   "Initialising session..."),
        ("embedding", "Embedding query..."),
        ("retrieval", "Searching legal corpus..."),
    ]:
        yield _evt("status", {"stage": stage, "message": msg})
        await asyncio.sleep(0)

    pipeline = get_pipeline()
    try:
        result = await pipeline.run(query, session_id)
        yield _evt("status", {"stage": "validation", "message": "Verifying citations..."})
        await asyncio.sleep(0)
        get_metrics().record_from_pipeline_result(query, result.get("session_id", ""), result)
        yield _evt("result", result)
        yield _evt("done",   {"session_id": result["session_id"]})
    except Exception as e:
        logger.error(f"[SSE] error: {e}", exc_info=True)
        yield _evt("error", {"message": str(e)})




if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
