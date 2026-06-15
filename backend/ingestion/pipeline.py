# Ingestion pipeline — fetches ITA 2025 and CBDT Circulars, parses, chunks,
# embeds, and upserts to Pinecone + Elasticsearch

import asyncio
import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

import requests
import aiohttp
from tqdm import tqdm

from config import get_settings
from ingestion.parsers import (
    parse_pdf_with_pdfplumber, parse_html,
    chunk_income_tax_act, chunk_cbdt_circular,
)
from retrieval.embeddings import get_embedding_service
from retrieval.vector_store import get_pinecone_store
from retrieval.es_store import get_es_store
from db.database import init_db, log_ingestion, get_ingestion_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


# fetching 
def fetch_pdf(url:str, save_path: Path) -> str:
    # download pdf and returns local path 
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.exists():
        logger.info(f"PDF already cached : {save_path}")
        return str(save_path)
    logger.info(f"Downloading PDF : {url}")
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
        logger.info(f"Saved PDF : {save_path}")
        return str(save_path)
    
async def fetch_cbdt_circular_list(base_url: str) -> List[Dict]:
    # scrape CBDT circular listing pages for pdf links
    from bs4 import BeautifulSoup
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            html = await resp.text()

    soup = BeautifulSoup(html, 'lxml')
    circulars = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf") or "circular" in href.lower():
            full_url = href if href.startswith("http") else f"https://www.incometaxindia.gov.in{href}"
            circulars.append({
                "url": full_url,
                "title": link.get_text(strip=True),
            })
    logger.info(f"Found {len(circulars)} CBDT circular links")
    return circulars


# indexing Embed chunks and upsert to Pinecone + Elasticsearch.
async def index_chunks(chunks : List[Dict[str, Any]], namespace: str, es_index: str, batch_size: int = 50,):
    emb_service = get_embedding_service()
    pc_store = get_pinecone_store()
    es_store = get_es_store()
    
    success_count = 0
    total = len(chunks)
    
    for i in tqdm(range(0, total, batch_size), desc=f"Indexing {namespace}"):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        
        try: 
            embeddings = emb_service.embed_documents(texts)
            for chunk, emb in zip(batch, embeddings):
                chunk["embedding"] = emb 
            pc_store.upsert_chunks(batch, namespace=namespace)
            # elastic search bulk idx
            await es_store.bulk_index(batch, es_index)
            for chunk in batch:
                await log_ingestion(
                    chunk["chunk_id"], namespace, 
                    chunk["metadata"].get("source_url" , " "), "SUCCESS"
                )
                success_count += 1
        except Exception as e:
            logger.error(f"Batch {i//batch_size + 1} failed: {e}")
            for chunk in batch:
                await log_ingestion(chunk["chunk_id"], namespace, "", "FAILED", str(e))
    
    logger.info(f"Indexed {success_count}/{total} chunks for {namespace}")
    return success_count, total 

# ITA 2025 ingestion 
# fetch, parse, chunk, and index the Income Tax Act 2025
async def ingest_ita_2025():
    logger.info("=== Ingesting Income Tax Act 2025 ===")    
    pdf_path = Path(settings.pdf_cache_dir) / "ita_2025.pdf"
    try: 
        fetch_pdf(settings.ita_url, pdf_path)
        text = parse_pdf_with_pdfplumber(str(pdf_path))
    except Exception as e:
        logger.warning(f"PDF fetch failed ({e}), trying HTML extraction")
        resp = requests.get(settings.ita_url, timeout=30)
        text = parse_html(resp.text)
        
    if not text or len(text) < 1000:
        logger.error("ITA 2025 text extraction failed — check source URL")
        return

    chunks = chunk_income_tax_act(text)
    logger.info(f"Generated {len(chunks)} chunks from ITA 2025")

    es_store = get_es_store()
    await es_store.ensure_indices()

    success, total = await index_chunks(
        chunks,
        namespace=settings.pinecone_namespace_act,
        es_index=settings.elasticsearch_index_act,
    )
    logger.info(f"ITA 2025 ingestion complete: {success}/{total}")

# CBDT circulars ingestion

async def ingest_cbdt_circulars():
    logger.info("=== Ingesting CBDT Circulars ===")

    pdf_dir = Path(settings.pdf_cache_dir) / "circulars"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    circular_links = await fetch_cbdt_circular_list(settings.cbdt_circulars_url)
    all_chunks = []

    async with aiohttp.ClientSession() as session:
        for item in tqdm(circular_links, desc="Fetching circulars"):
            url = item["url"]
            safe_name = url.split("/")[-1] or "circular.pdf"
            local_path = pdf_dir / safe_name

            try:
                if not local_path.exists():
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        content = await resp.read()
                    with open(local_path, "wb") as f:
                        f.write(content)

                if url.endswith(".pdf"):
                    text = parse_pdf_with_pdfplumber(str(local_path))
                else:
                    text = parse_html(local_path.read_text(errors="replace"))

                chunks = chunk_cbdt_circular(text, source_url=url)
                all_chunks.extend(chunks)

            except Exception as e:
                logger.warning(f"Skipping {url}: {e}")

    logger.info(f"Total CBDT chunks: {len(all_chunks)}")

    es_store = get_es_store()
    await es_store.ensure_indices()

    success, total = await index_chunks(
        all_chunks,
        namespace=settings.pinecone_namespace_circular,
        es_index=settings.elasticsearch_index_circular,
    )
    logger.info(f"CBDT Circulars ingestion complete: {success}/{total}")


async def run_pipeline(source: str = "all"):
    await init_db()
    if source in ("all", "ita"):
        await ingest_ita_2025()
    if source in ("all", "cbdt"):
        await ingest_cbdt_circulars()
    
    stats = await get_ingestion_stats()
    logger.info(f"Ingestion Stats: {stats}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["all", "ita", "cbdt"], default="all")
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.source))