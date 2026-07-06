# embed query -> vector search -> hybrid RRF -> cross-encoder rerank -> LLM synthesis
import time
import logging 
import json
from typing import Dict, Any, List, Optional

from config import get_settings

from retrieval.embeddings import get_embedding_service
from retrieval.vector_store import get_pinecone_store
from retrieval.es_store import get_es_store
from retrieval.reranker import get_reranker,reciprocal_rank_fusion
from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)
settings = get_settings()



SYNTHESIS_PROMPT = """You are a senior Indian tax law analyst. Your task is to answer a tax query using ONLY the retrieved legal text chunks below.

STRICT RULES:
1. Every claim must reference a specific section, circular, or case from the provided chunks.
2. Do NOT use knowledge from your training data. If the chunks don't contain the answer, say so explicitly.
3. Provisos must be cited alongside the main section — never omit them.
4. For Section 2(22)(e) deemed dividend, crystallisation timing is critical — state it precisely.
5. Format your response EXACTLY as shown below.

---RETRIEVED CHUNKS---
{chunks_text}
---END CHUNKS---

QUERY: {query}

Respond in this EXACT format:

FINAL_ANSWER:
[2-4 sentences. Take a clear position. Do not hedge into ambiguity.]

LEGAL_REASONING:
- Statutory Basis: [Act Name, Section, Sub-section, Clause, Proviso — cite specifically]
- Regulatory Guidance: [Circular/Notification number, issuing authority, date — if applicable]
- Judicial Position: [Case name, court, year — only if present in chunks]

SUPPORTING_REFERENCES:
[List each reference on its own line, prefixed with [Act], [Circular], or [Case Law]]

CITATIONS_JSON:
[JSON array of citation objects: {{"text": "...", "type": "act|circular|case", "chunk_id": "..."}}]
"""



# Performs hybrid semantic + keyword retrieval, reranks, and synthesises retrieved chunks into a structured draft response.
class RetrievalAgent:
    name = "RetrievalAgent"
    
    def __init__(self):
        self.system_message = (
            "You are the retrieval and synthesis core of TaxAI. "
            "You retrieve relevant legal text and synthesise accurate, citation-backed answers."
        )
    
    async def run(self, query_packet: Dict[str, Any]) -> Dict[str, Any]:
        # Main entry point returns synthesis result + retrieved chunks + latency
        query = query_packet["enriched_query"]
        raw_query = query_packet["raw_query"]
        
        timings = {}
        
        # embed query 
        
        t0 = time.monotonic()
        emb_service = get_embedding_service()
        query_embedding = emb_service.embed_query(query)
        timings["embedding_ms"] = int((time.monotonic() - t0) * 1000)
        logger.info(f"[RetrievalAgent] Embedding: {timings['embedding_ms']}ms")

        # vector search
        t0 = time.monotonic()
        pc_store = get_pinecone_store()
        vector_results = pc_store.query_all_namespace(query_embedding,top_k=settings.retrieval_top_k_candidates)
        timings["vector_retrieval_ms"] = int((time.monotonic() - t0) * 1000)
        logger.info(
            f"[RetrievalAgent] Vector retrieval: {timings['vector_retrieval_ms']}ms "
            f"({len(vector_results)} candidates)"
        )
        
        # keyword (elastic search) 
        t0 = time.monotonic()
        es_store  = get_es_store()
        keyword_results = await es_store.search_all_indices(raw_query, top_k=settings.retrieval_top_k_candidates)
        timings["keyword_retrieval_ms"] = int((time.monotonic() - t0) * 1000)
        logger.info(f"[RetrievalAgent] Keyword retrieval: {timings['keyword_retrieval_ms']}ms")

        # rrf (reciprocal rank fusion)
        merged = reciprocal_rank_fusion(
            [vector_results, keyword_results],
            top_k = settings.retrieval_top_k_candidates,
        )
        logger.info(f"[RetrievalAgent] RRF merged: {len(merged)} candidates")
        
        # cross encoder-rerank
        t0 = time.monotonic()
        reranker = get_reranker()
        top_chunks = reranker.rerank(raw_query, merged, top_k=settings.retrieval_top_k_final)
        timings["rerank_ms"] = int((time.monotonic() - t0) * 1000)
        logger.info(f"[RetrievalAgent] Reranked to {len(top_chunks)} chunks in {timings['rerank_ms']}ms")
        
        
        # llm synthesis
        t0 = time.monotonic()
        synthesis = await self._synthesise(raw_query, top_chunks)
        timings["synthesis_ms"] = int((time.monotonic() - t0) * 1000)
        logger.info(f"[RetrievalAgent] LLM synthesis: {timings['synthesis_ms']}ms")

        return {
            "query": raw_query,
            "top_chunks": top_chunks,
            "synthesis": synthesis,
            "timings": timings,
        }
        
        
        
    # call LLM with retrieved chunks and parse structured response 
    async def _synthesise(self, query: str, chunks: List[Dict]) -> Dict[str, Any]:
        chunks_text = "\n\n---\n\n".join([
            f"[CHUNK {i+1} | ID: {c['chunk_id']} | Score: {c.get('rerank_score', c.get('rrf_score', 0)):.3f}]\n"
            f"Source: {c['metadata'].get('act', 'CBDT')} | "
            f"Section: {c['metadata'].get('section', 'N/A')} | "
            f"Circular: {c['metadata'].get('circular_number', 'N/A')}\n\n"
            f"{c['text']}"
            for i, c in enumerate(chunks)
        ])

        prompt = SYNTHESIS_PROMPT.format(chunks_text=chunks_text, query=query)

        llm = get_llm_client()
        raw_response = await llm.complete(prompt, temperature=0.1)
        print(raw_response)

        return self._parse_synthesis(raw_response)
    
    
    # Parse LLM response into structured fields
    def _parse_synthesis(self, raw: str) -> Dict[str, Any]:
        result = {
            "final_answer": "",
            "legal_reasoning": "",
            "supporting_references": "",
            "raw_citations": [],
        }

        sections = {
            "FINAL_ANSWER": "final_answer",
            "LEGAL_REASONING": "legal_reasoning",
            "SUPPORTING_REFERENCES": "supporting_references",
        }

        current_section = None
        buffer = []

        for line in raw.split("\n"):
            stripped = line.strip()

            matched = False
            for marker, key in sections.items():
                if stripped.startswith(f"{marker}:"):
                    if current_section and buffer:
                        result[sections[current_section]] = "\n".join(buffer).strip()
                    current_section = marker
                    buffer = [stripped[len(marker)+1:].strip()]
                    matched = True
                    break

            if not matched:
                if stripped.startswith("CITATIONS_JSON:"):
                    if current_section and buffer:
                        result[sections[current_section]] = "\n".join(buffer).strip()
                    json_str = stripped[len("CITATIONS_JSON:"):].strip()
                    remaining = raw.split("CITATIONS_JSON:")[-1].strip()
                    try:
                        result["raw_citations"] = json.loads(remaining)
                    except Exception:
                        result["raw_citations"] = []
                    break
                elif current_section:
                    buffer.append(line)

        if current_section and buffer and not result.get(sections.get(current_section, "")):
            result[sections[current_section]] = "\n".join(buffer).strip()

        return result