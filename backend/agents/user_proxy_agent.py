import re
import logging
from typing import Optional, Dict, Any, List

from db.database import create_session, get_session_history, save_message

logger = logging.getLogger(__name__)

# keywords indicating follow-up refrence to prior context 
FOLLOW_UP_SIGNALS = [
    r"\bthis section\b",
    r"\bthat section\b",
    r"\babove case\b",
    r"\bthe ruling\b",
    r"\bthis ruling\b",
    r"\bmentioned above\b",
    r"\bprevious query\b",
    r"\bsame section\b",
    r"\bthe circular\b",
    r"\bthis circular\b",
    r"\bsame case\b",
    r"\bit\b",  # broad — only flag if prior context exists
]


FOLLOW_UP_RE = re.compile("|".join(FOLLOW_UP_SIGNALS), re.IGNORECASE)

class UserProxyAgent:
    """
    Manages user session lifecycle and query enrichment.
    Detects follow-up references and prepends prior context before
    passing the enriched query to the RetrievalAgent.
    """
    name = "UserProxy"
    
    def __init__(self):
        self.system_message = (
            "You are the interface between the user and the TaxAI research system. "
            "You manage session state, detect follow-up references, and present "
            "validated responses in structured format."
        )
        
    # main entry pt returns enriched query for retrieval agent 
    async def process_query(self, raw_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        session_id = await create_session(session_id)
        history = await get_session_history(session_id, limit=6)
        is_follow_up = self._detect_follow_up(raw_query, history)
        
        # enrich query if follow up 
        enriched_query = raw_query
        prior_context = ""
        if is_follow_up and history:
            prior_context = self._build_prior_context(history)
            enriched_query = f"{prior_context}\n\nCurrent question: {raw_query}"
            logger.info(f"[UserProxy] Follow-up detected. Context prepended. session={session_id}")
        else:
            logger.info(f"[UserProxy] New query. session={session_id}")

        await save_message(session_id, "user", raw_query)
        return {
            "session_id": session_id,
            "raw_query": raw_query,
            "enriched_query": enriched_query,
            "is_follow_up": is_follow_up,
            "prior_context": prior_context,
            "history": history,
        }
    
    def _detect_follow_up(self, query:str, history: List[Dict]) -> bool:
        if not history:
            return False
        
        return bool(FOLLOW_UP_RE.search(query))
    
    
    
    # summarize recent history for context prepending 
    def _build_prior_context(self, history: List[Dict]) -> str:
        lines = ["[Prior conversation context for refrence: ]"]
        for msg in history[-4:]: # last 4 msgs
            role = msg["role"].upper()
            content = msg["content"][:500] # truncte long msgs
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    
    # merge synthesis + validation into final structured response and save to history 
    async def format_final_response(self,session_id: str,raw_query: str,synthesis_result: Dict[str, Any],validation_result: Dict[str, Any],latency_ms: int,) -> Dict[str, Any]:
        final_answer = synthesis_result.get("final_answer", "")
        legal_reasoning = synthesis_result.get("legal_reasoning", "")
        supporting_refs = synthesis_result.get("supporting_refrences", "")
        confidence = validation_result.get("overall_confidence", "UNKNOWN")
        citations = validation_result.get("citations", [])
        unverified_count = validation_result.get("unverified_count", 0)

        # Build markdown response
        markdown_response = self._build_markdown(
            final_answer, legal_reasoning, supporting_refs,
            confidence, unverified_count
        )

        # Save assistant message
        await save_message(
            session_id, "assistant", markdown_response,
            citations=citations,
            confidence=confidence,
            latency_ms=latency_ms,
        )

        return {
            "session_id": session_id,
            "query": raw_query,
            "response": {
                "markdown": markdown_response,
                "final_answer": final_answer,
                "legal_reasoning": legal_reasoning,
                "supporting_references": supporting_refs,
                "confidence": confidence,
                "citations": citations,
                "unverified_count": unverified_count,
                "latency_ms": latency_ms,
            },
        }
    
    def _build_markdown(self,final_answer: str,legal_reasoning: str,supporting_refs: str,confidence: str,unverified_count: int,) -> str:
        disclamer = " For research purposes only. Consult a qualified  tax proffesional for specific advice"
        unverified_note = (f"\n\n> **{unverified_count} citation(s) could not be verified against the indexed corpus" if unverified_count > 0 else "")
        return f""" ## Final Answer
    
    {final_answer}
    ## Legal Reasoning 
    
    {legal_reasoning}
    
    ## Supporting Refrences
    
    {supporting_refs}
    
    ## Confidence and Disclaimer 
    
    **Confidence: {confidence}** | {disclamer}{unverified_note}"""