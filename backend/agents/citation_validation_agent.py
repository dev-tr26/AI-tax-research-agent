# anti hallucination prevented L: verifies unverified citation against the index corpus 
# assigns confidence scores and remove or flags unverified citations

import re 
import time
import logging
from typing import Dict, Any, List, Optional
from config import get_settings
from retrieval.vector_store import get_pinecone_store
from retrieval.es_store import get_es_store 


logger = logging.getLogger(__name__)
settings = get_settings()

# citation extractions

# Section patterns: "Section 54", "Section 2(22)(e)", "Section 147A", "S. 80C"
SECTION_RE = re.compile(
    r"\bS(?:ection|\.)\s*(\d+[A-Z]?)(?:\s*\((\d+)\))?(?:\s*\([a-z]\))?",
    re.IGNORECASE,
)


# Circular patterns: "Circular No. 495/1987", "CBDT Circular 12/2001", "Circular 359"
CIRCULAR_RE = re.compile(
    r"(?:CBDT\s+)?Circular\s+(?:No\.?\s*)?(\d+(?:/\d{4})?)",
    re.IGNORECASE,
)

# Case law patterns: "Kantilal Manilal vs CIT", "CIT v. Lovely Exports"
CASE_RE = re.compile(
    r"([A-Z][a-zA-Z\s&]+(?:vs?\.?|v\.)\s*(?:CIT|ITO|ACIT|ITAT|[A-Z][a-zA-Z\s]+))"
    r"(?:\s*\((?:SC|HC|ITAT|Bombay|Delhi|Madras|Calcutta)[^)]*\d{4}\))?",
    re.IGNORECASE,
)


class CitationValidationAgent:
    '''
    parses the synthesised response , extract all legal citations verifies each against pinecone + elasticsearch idx and assigns confidence scores 
    '''

    name = "CitationValidationAgent"
    
    def __init__(self):
        self.system_message = (
             "You are the citation verification firewall for TaxAI. "
            "You verify every legal citation against the indexed corpus "
            "and remove or flag any citation not traceable to a retrieved chunk."
        )
        
    async def run(self,synthesis_result: Dict[str, Any], top_chunks: List[Dict[str, Any]], )-> Dict[str, Any]:
        # main entry returns validation schema : citations [], overall_confidence, unverified count
        t0 = time.monotonic()
        
        response_text = (
            synthesis_result.get("final_answer", "") + " " +
            synthesis_result.get("legal_reasoning", "") + " " +
            synthesis_result.get("supporting_references", "")
        )
        
        raw_citations = synthesis_result.get("raw_citations", [])
        
        # extract all citations from text
        extracted = self._extract_citations(response_text)
            
        # merge with LLM provided citations
        all_citations = self._merge_citations(extracted, raw_citations, top_chunks)
        
        #verify each citations
        verified_citations = []
        for citation in all_citations:
            verified = await self._verify_citation(citation, top_chunks)
            verified_citations.append(verified)
            
        # compute overall confidence
        unverified = [c for c in verified_citations if not c["verified"]]
        overall = self._compute_overall_confidence(verified_citations)
        
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info( 
            f"[CitationValidation] {len(verified_citations)} citations | "
            f"{len(unverified)} unverified | {elapsed_ms}ms"
        )
        
        return {
            "citations": verified_citations,
            "overall_confidence": overall,
            "unverified_count": len(unverified),
            "validation_latency_ms": elapsed_ms,
        }
        
    def _extract_citations(self, text:str) -> List[Dict]:
        # extract section , circular, and case citations from text 
        citations = []
        
        for m in SECTION_RE.finditer(text):
            citations.append({
                "text": m.group(0).strip(),
                "type": "act",
                "section": m.group(1),
                "sub_section": m.group(2) or "",
                "chunk_id_hint": f"ITA_2025_S{m.group(1)}" + ( f"_{m.group(2)}" if m.group(2) else ""),
        })
            
        for m in CIRCULAR_RE.finditer(text):
            circ_num = m.group(1).replace("/", "_")
            citations.append({
                "text": m.group(0).strip(),
                "type": "circular",
                "circular_number": m.group(1),
                "chunk_id_hint": f"CBDT_CIRC_{circ_num}",
        })
        
        for m in CASE_RE.finditer(text):
            case_text = m.group(0).strip()
            if len(case_text) > 8:  # Filter noise
                citations.append({
                    "text": case_text,
                    "type": "case",
                    "chunk_id_hint": None,
        })
    
         # duplicate by text 
        seen = set()
        unique = []           
        for c in citations:
            if c["text"] not in seen:
                seen.add(c["text"])
                unique.append(c)
        
        return unique
    
    def _merge_citations(self,extracted: List[Dict], raw_citations: List[Dict], top_chunks: List[Dict],) -> List[Dict]:
        # merge extracted _ LLm- provided citations
        all_texts = {c["text"] for c in extracted}
        for rc in raw_citations:
            if rc.get("text") and rc["text"] not in all_texts:
                extracted.append({
                    "text": rc["text"],
                    "type": rc.get("type", "act"),
                    "chunk_id_hint": rc.get("chunk_id", None),
                })
                all_texts.add(rc["text"])
        
        return extracted 
    
    async def _verify_citation(self, citation: Dict, top_chunks: List[Dict]) -> Dict[str, Any]:
        """
        Verify a single citation against:
        1. Retrieved top_chunks (direct match — HIGH confidence)
        2. Pinecone metadata lookup (chunk_id prefix — MEDIUM confidence)
        3. Not found — LOW confidence, mark unverified
        """
        
        hint = citation.get("chunk_id_hint")
        ctype = citation.get("type", "act")
        
        # check if chunk_id_hint matches a retrieved chunk
        for chunk in top_chunks:
            if hint and chunk["chunk_id"].startswith(hint[:15]):
                return {
                    **citation,
                    "verified": True,
                    "confidence": round(0.85 + chunk.get("rerank_score", 0.1) * 0.15, 3),
                    "source_chunk_id": chunk["chunk_id"],
                }
           
            # Text-level match
            if citation["text"][:20].lower() in chunk["text"].lower():
                return {
                    **citation,
                    "verified": True,
                    "confidence": 0.75,
                    "source_chunk_id": chunk["chunk_id"],
                }

        # Try Pinecone fetch by hint 
        if hint:
            try:
                pc = get_pinecone_store()
                namespace = (
                    settings.pinecone_namespace_act
                    if ctype == "act"
                    else settings.pinecone_namespace_circular
                )
                result = pc.fetch_by_ids([hint], namespace=namespace)
                if hint in result:
                    return {
                        **citation,
                        "verified": True,
                        "confidence": 0.68,
                        "source_chunk_id": hint,
                    }
            except Exception as e:
                logger.debug(f"Pinecone fetch failed for {hint}: {e}")

        # Elasticsearch fallback for act sections 
        if ctype == "act" and citation.get("section"):
            try:
                es = get_es_store()
                result = await es.get_by_id(hint, settings.elasticsearch_index_act)
                if result:
                    return {
                        **citation,
                        "verified": True,
                        "confidence": 0.60,
                        "source_chunk_id": hint,
                    }
            except Exception:
                pass

        # Case law citations can't be directly verified (no case law index)
        # Mark as MEDIUM with explicit note
        if ctype == "case":
            return {
                **citation,
                "verified": False,
                "confidence": 0.40,
                "source_chunk_id": None,
                "note": "Case law not in indexed corpus — verify independently",
            }

        # Not found
        return {
            **citation,
            "verified": False,
            "confidence": 0.10,
            "source_chunk_id": None,
            "note": "Citation not traceable to indexed corpus",
        }

    def _compute_overall_confidence(self, citations: List[Dict]) -> str:
        if not citations:
            return "LOW"
        verified = [c for c in citations if c["verified"]]
        ratio = len(verified) / len(citations)
        avg_conf = sum(c.get("confidence", 0) for c in verified) / max(len(verified), 1)

        if ratio >= 0.85 and avg_conf >= 0.75:
            return "HIGH"
        elif ratio >= 0.60 and avg_conf >= 0.55:
            return "MEDIUM"
        else:
            return "LOW"
