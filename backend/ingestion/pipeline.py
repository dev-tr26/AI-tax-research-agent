"""
Ingestion pipeline — Manual PDF upload mode.

HOW TO ADD DOCUMENTS:
─────────────────────
  ITA 2025 PDF:
    Place file at:  backend/data/pdfs/ita_2025.pdf

  CBDT Circulars:
    Place files at: backend/data/pdfs/circulars/
    Any .pdf file is accepted.
    Examples:
      Circular-1-2025.pdf
      Circular-359-1983.pdf

Run:
    python -m ingestion.pipeline --source all
    python -m ingestion.pipeline --source ita
    python -m ingestion.pipeline --source cbdt

Required:  PINECONE_API_KEY in backend/.env
Optional:  Elasticsearch (pipeline continues without it)
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

from tqdm import tqdm

from config import get_settings
from ingestion.parsers import (
    parse_any_pdf,
    chunk_income_tax_act,
    chunk_cbdt_circular,
)
from db.database import init_db, log_ingestion, get_ingestion_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ── Silence noisy ES / transport retry logs immediately on import ─────────────
for _noisy in (
    "elastic_transport",
    "elastic_transport.transport",
    "elastic_transport._node",
    "elasticsearch",
    "elasticsearch.helpers",
):
    logging.getLogger(_noisy).setLevel(logging.CRITICAL)


# ─────────────────────────────────────────────────────────────────────────────
# Preflight checks
# ─────────────────────────────────────────────────────────────────────────────

def _check_pinecone_key() -> bool:
    """Return True if Pinecone API key is set, else log clear instructions."""
    if not settings.pinecone_api_key or settings.pinecone_api_key.strip() == "":
        logger.error(
            "\n"
            "  ✗  PINECONE_API_KEY is not set.\n\n"
            "  HOW TO FIX:\n"
            "  1. Sign up free at https://app.pinecone.io\n"
            "  2. Create a project → copy your API key\n"
            "  3. Open:  backend/.env\n"
            "  4. Set:   PINECONE_API_KEY=your_key_here\n"
            "  5. Re-run the pipeline\n"
        )
        return False
    return True


async def _check_elasticsearch() -> bool:
    """
    Quick single-attempt ping to Elasticsearch.
    Returns True if reachable, False otherwise.
    Suppresses all retry/connection log noise.
    """
    try:
        from elasticsearch import AsyncElasticsearch
        # max_retries=0 → single attempt, no retry spam
        client = AsyncElasticsearch(
            hosts=[settings.elasticsearch_url],
            request_timeout=3,
            max_retries=0,
            retry_on_timeout=False,
        )
        alive = await client.ping()
        await client.close()
        return alive
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Core indexing
# ─────────────────────────────────────────────────────────────────────────────

async def index_chunks(
    chunks: List[Dict[str, Any]],
    namespace: str,
    es_index: str,
    batch_size: int = 50,
    use_es: bool = False,
) -> Tuple[int, int]:
    """
    Embed each chunk and upsert to Pinecone.
    Also bulk-indexes to Elasticsearch if use_es=True.
    Returns (success_count, total).
    """
    if not chunks:
        logger.warning(f"No chunks to index for namespace={namespace}")
        logger.info(f"Sample chunks: {[c['chunk_id'] for c in chunks[:5]]}")
        logger.info(f"Chunk sizes: min={min(len(c['text']) for c in chunks)}, max={max(len(c['text']) for c in chunks)}")
        return 0, 0

    from retrieval.embeddings import get_embedding_service
    from retrieval.vector_store import get_pinecone_store

    emb_service = get_embedding_service()
    pc_store = get_pinecone_store()

    # Only import ES store if we're actually going to use it
    es_store = None
    if use_es:
        from retrieval.es_store import get_es_store
        es_store = get_es_store()

    success_count = 0
    total = len(chunks)

    for i in tqdm(range(0, total, batch_size), desc=f"  Indexing [{namespace}]"):
        batch = chunks[i: i + batch_size]
        texts = [c["text"] for c in batch]

        try:
            # 1. Embed batch
            embeddings = emb_service.embed_documents(texts)
            for chunk, emb in zip(batch, embeddings):
                chunk["embedding"] = emb

            # 2. Pinecone upsert
            pc_store.upsert_chunks(batch, namespace=namespace)
            stats = pc_store.index_stats()
            print(stats)

            # 3. Elasticsearch (optional, never fatal)
            if es_store:
                try:
                    await es_store.bulk_index(batch, es_index)
                except Exception as es_err:
                    logger.debug(f"ES bulk index skipped: {es_err}")

            # 4. Log success to SQLite
            for chunk in batch:
                await log_ingestion(
                    chunk["chunk_id"],
                    namespace,
                    chunk["metadata"].get("source_url", "local"),
                    "SUCCESS",
                )
                success_count += 1

        except Exception as e:
            logger.error(f"Batch {i // batch_size + 1} failed: {e}")
            for chunk in batch:
                await log_ingestion(
                    chunk["chunk_id"], namespace, "", "FAILED", str(e)
                )

    logger.info(
        f"  Indexed {success_count}/{total} chunks "
        f"→ Pinecone[{namespace}]"
        + (f" + ES[{es_index}]" if use_es else "")
    )
    return success_count, total


# ─────────────────────────────────────────────────────────────────────────────
# ITA 2025 ingestion
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_ita_2025(use_es: bool = False):
    """
    Parse the Income Tax Act 2025 from a locally placed PDF and index it.

    Expected file:
        backend/data/pdfs/ita_2025.pdf
    """
    logger.info("=" * 55)
    logger.info("Ingesting Income Tax Act 2025")
    logger.info("=" * 55)

    pdf_path = Path(settings.pdf_cache_dir) / "ita_2025.pdf"

    if not pdf_path.exists():
        logger.error(
            f"\n"
            f"  ✗  ITA 2025 PDF not found at:\n"
            f"       {pdf_path.resolve()}\n\n"
            f"  HOW TO FIX:\n"
            f"  1. Download the PDF from:\n"
            f"       https://www.incometaxindia.gov.in/pages/acts/income-tax-act.aspx\n"
            f"  2. Rename it to:  ita_2025.pdf\n"
            f"  3. Place it at:   {pdf_path.resolve()}\n"
            f"  4. Re-run:  python -m ingestion.pipeline --source ita\n"
        )
        return

    logger.info(f"Parsing: {pdf_path.name} ({pdf_path.stat().st_size // 1024} KB)")
    text = parse_any_pdf(str(pdf_path))

    if not text or len(text.strip()) < 500:
        logger.error(
            "Text extraction returned too little content.\n"
            "  The PDF may be image-based (scanned). "
            "Try a text-selectable PDF from incometaxindia.gov.in"
        )
        return

    logger.info(f"Extracted {len(text):,} characters from PDF")

    chunks = chunk_income_tax_act(text)
    if not chunks:
        logger.error("Chunking produced 0 chunks — check if PDF has proper section headings.")
        return
    logger.info(f"Generated {len(chunks)} section chunks")

    # Setup ES indices if available
    if use_es:
        try:
            from retrieval.es_store import get_es_store
            await get_es_store().ensure_indices()
        except Exception as e:
            logger.warning(f"ES index setup failed (skipping): {e}")
            use_es = False

    success, total = await index_chunks(
        chunks,
        namespace=settings.pinecone_namespace_act,
        es_index=settings.elasticsearch_index_act,
        use_es=use_es,
    )
    logger.info(f"✓ ITA 2025 complete: {success}/{total} chunks indexed\n")


# ─────────────────────────────────────────────────────────────────────────────
# CBDT Circulars ingestion
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_cbdt_circulars(use_es: bool = False):
    """
    Parse all CBDT circular PDFs from the local circulars folder and index them.

    Expected folder:
        backend/data/pdfs/circulars/   (any *.pdf files inside)
    """
    logger.info("=" * 55)
    logger.info("Ingesting CBDT Circulars")
    logger.info("=" * 55)

    circulars_dir = Path(settings.pdf_cache_dir) / "circulars"

    if not circulars_dir.exists():
        circulars_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(
            f"\n"
            f"  Folder created: {circulars_dir.resolve()}\n\n"
            f"  HOW TO ADD CIRCULARS:\n"
            f"  1. Download circular PDFs from:\n"
            f"       https://www.incometaxindia.gov.in/communications/circular/\n"
            f"  2. Place each .pdf in: {circulars_dir.resolve()}\n"
            f"  3. Re-run: python -m ingestion.pipeline --source cbdt\n"
        )
        return

    pdf_files = sorted(circulars_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(
            f"\n"
            f"  ✗  No PDF files found in: {circulars_dir.resolve()}\n\n"
            f"  HOW TO ADD CIRCULARS:\n"
            f"  1. Download circular PDFs from:\n"
            f"       https://www.incometaxindia.gov.in/communications/circular/\n"
            f"  2. Place each .pdf in: {circulars_dir.resolve()}\n"
            f"  3. Re-run: python -m ingestion.pipeline --source cbdt\n"
        )
        return

    logger.info(f"Found {len(pdf_files)} PDF file(s)")

    all_chunks: List[Dict[str, Any]] = []
    skipped = 0

    for pdf_path in tqdm(pdf_files, desc="  Parsing circulars"):
        logger.info(f"  Parsing: {pdf_path.name}")
        text = parse_any_pdf(str(pdf_path))

        if not text or len(text.strip()) < 50:
            logger.warning(f"  Skipping {pdf_path.name}: empty or unreadable")
            skipped += 1
            continue

        chunks = chunk_cbdt_circular(text, source_url="", filename=pdf_path.name)

        if not chunks:
            logger.warning(f"  Skipping {pdf_path.name}: chunking produced 0 results")
            skipped += 1
            continue

        logger.info(f"  {pdf_path.name} → {len(chunks)} chunk(s)")
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.error(
            "All circular PDFs were empty or unreadable.\n"
            "  Confirm PDFs are text-based (not scanned images)."
        )
        return

    logger.info(
        f"Total: {len(all_chunks)} chunks from "
        f"{len(pdf_files) - skipped}/{len(pdf_files)} files"
        + (f" ({skipped} skipped)" if skipped else "")
    )

    # Setup ES indices if available
    if use_es:
        try:
            from retrieval.es_store import get_es_store
            await get_es_store().ensure_indices()
        except Exception as e:
            logger.warning(f"ES index setup failed (skipping): {e}")
            use_es = False

    success, total = await index_chunks(
        all_chunks,
        namespace=settings.pinecone_namespace_circular,
        es_index=settings.elasticsearch_index_circular,
        use_es=use_es,
    )
    logger.info(f"✓ CBDT Circulars complete: {success}/{total} chunks indexed\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(source: str = "all"):
    """
    Full ingestion pipeline with upfront validation.
    Fails immediately with clear instructions if Pinecone key is missing.
    Gracefully skips Elasticsearch if it is not running.
    """
    await init_db()

    # ── 1. Validate Pinecone API key FIRST — hard requirement ────────────────
    if not _check_pinecone_key():
        sys.exit(1)

    # ── 2. Check Elasticsearch — soft requirement (single quiet ping) ─────────
    logger.info(f"Checking Elasticsearch at {settings.elasticsearch_url} ...")
    es_up = await _check_elasticsearch()

    if es_up:
        logger.info("  ✓ Elasticsearch is running — hybrid search enabled")
    else:
        logger.warning(
            "  ✗ Elasticsearch not reachable — "
            "proceeding with Pinecone-only mode.\n"
            "    Keyword/hybrid search will be unavailable.\n"
            "    To enable it later: docker compose up -d elasticsearch"
        )

    # ── 3. Run ingestion ──────────────────────────────────────────────────────
    if source in ("all", "ita"):
        await ingest_ita_2025(use_es=es_up)

    if source in ("all", "cbdt"):
        await ingest_cbdt_circulars(use_es=es_up)

    # ── 4. Final summary ──────────────────────────────────────────────────────
    stats = await get_ingestion_stats()

    logger.info("=" * 55)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 55)
    for status, count in stats.items():
        icon = "✓" if status == "SUCCESS" else "✗"
        logger.info(f"  {icon}  {status:<10} : {count} chunks")
    logger.info(f"  Pinecone     : connected (index={settings.pinecone_index_name})")
    logger.info(f"  Elasticsearch: {'up' if es_up else 'not running (optional)'}")
    logger.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TaxAI ingestion pipeline — manual PDF mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SETUP BEFORE RUNNING:
  1. Set PINECONE_API_KEY in backend/.env
  2. Place PDFs:
       ITA 2025:       backend/data/pdfs/ita_2025.pdf
       CBDT Circulars: backend/data/pdfs/circulars/*.pdf

EXAMPLES:
  python -m ingestion.pipeline --source all
  python -m ingestion.pipeline --source ita
  python -m ingestion.pipeline --source cbdt
        """,
    )
    parser.add_argument(
        "--source",
        choices=["all", "ita", "cbdt"],
        default="all",
        help="Which source to ingest (default: all)",
    )
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.source))
