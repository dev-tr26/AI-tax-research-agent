# Coordinates UserProxyAgent ->  RetrievalAgent ->  CitationValidationAgent
#  orchestrator handles message passing loop 
# each agent is autogen conversableagent with defined message contracts

import time
import logging 
import json
from typing import Optional, Dict, Any, AsyncIterator

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken

from agents.user_proxy_agent import UserProxyAgent
from agents.citation_validation_agent import CitationValidationAgent
from agents.retrieval_agent import RetrievalAgent 
from utils.llm_client import get_llm_client 
from utils.tracing import trace_pipeline

logger = logging.getLogger(__name__)


class TaxAIPipeline:
    '''
    orchestrates the 3 agent pipeline for each user query 
    messgae passing is explicit : each agent receives a define input ans returns a defined output schema 
    '''
    def __init__(self):
        self.user_proxy = UserProxyAgent()
        self.retrieval_agent = RetrievalAgent()
        self.citation_agent = CitationValidationAgent()
        
    @trace_pipeline
    async def run(self, query: str, session_id : Optional[str]=None) -> Dict[str, Any]:
        # full pipeline execution , returns structured response with citations and latency breakdown 
        pipeline_start = time.monotonic()
        timings = {}
        
        logger.info(f"[Pipeline] START query='{query[:80]}....'  session={session_id}")
    
        # userProxy Agent session + query enrichment 
        t0 = time.monotonic()
        query_packet = await self.user_proxy.process_query(query, session_id)
        timings["user_proxy_ms"] = int((time.monotonic() - t0) * 1000)
        session_id = query_packet["session_id"]
        
        logger.info(
            f"[Pipeline] UserProxy done. session={session_id}"
            f"follow_up={query_packet['is_follow_up']}"
            f"t={timings['user_proxy_ms']} ms"
        )
        
        # retrieval agent embed -> search -> rerank ->synthesis 
        t0 = time.monotonic()
        retrieval_result = await self.retrieval_agent.run(query_packet)
        timings["retrieval_ms"] = int((time.monotonic() - t0) * 1000)
        timings.update(retrieval_result["timings"])
        
        logger.info(
            f"[Pipeline] Retrieval Agent done. chunks={len(retrieval_result['top_chunks'])}"
            f"t={timings['retrieval_ms']} ms"
        )
        
        # citation Validation agent : verifies all citations
        
        t0 = time.monotonic()
        validation_result = await self.citation_agent.run(
            retrieval_result["synthesis"],
            retrieval_result["top_chunks"],
        )
        timings["citation_validation_ms"] = int((time.monotonic() - t0) * 1000)
        
        logger.info(
            f"[Pipeline] CitationValidation done. "
            f"citations={len(validation_result['citations'])} "
            f"unverified={validation_result['unverified_count']} "
            f"confidence={validation_result['overall_confidence']} "
            f"t={timings['citation_validation_ms']}ms"
        )
        
        # userproxy agent - formats and persist final response
        
        total_ms = int((time.monotonic() - pipeline_start) * 1000)
        timings["total_ms"] = total_ms
        
        final_response = await self.user_proxy.format_final_response(
            session_id=session_id,
            raw_query=query,
            synthesis_result=retrieval_result["synthesis"],
            validation_result=validation_result,
            latency_ms = total_ms,
        )
        
        final_response["timings"] = timings
        final_response["top_chunks"] = [
            {
                "chunk_id": c["chunk_id"],
                "text": c["text"][:300],
                "metadat": c["metadata"],
                "score": c.get("rerank_score", c.get("rrf_score", 0)),
            }
            for c in retrieval_result["top_chunks"]
        ]
        
        logger.info(
            f"[Pipeline] COMPLETE total={total_ms}ms "
            f"session={session_id} confidence={validation_result['overall_confidence']}"
        )
        
        # agent trace dump for debug 
        self._log_agent_trace(query, query_packet, retrieval_result, validation_result, total_ms)
        
        return final_response
    
    
    def _log_agent_trace(self, query: str, query_packet: Dict, retrieval_result: Dict, validation_result: Dict, total_ms: int,):
        # loging full agent interaction trace for submission requirement 
        
        trace = {
            "query": query,
            "agent_1_user_proxy": {
                "input": query,
                "output": {
                    "session_id": query_packet["session_id"],
                    "is_follow_up": query_packet["is_follow_up"],
                    "enriched_query_preview": query_packet["enriched_query"][:200],
                },
            },
            "agent_2_retrieval": {
                "input": {"enriched_query": query_packet["enriched_query"][:200]},
                "output": {
                    "chunks_retrieved": len(retrieval_result["top_chunks"]),
                    "chunk_ids": [c["chunk_id"] for c in retrieval_result["top_chunks"]],
                    "synthesis_preview": retrieval_result["synthesis"].get("final_answer", "")[:200],
                    "timings": retrieval_result["timings"],
                },
            },
            "agent_3_citation_validation": {
                "input": {"citations_to_verify": len(retrieval_result["synthesis"].get("raw_citations", []))},
                "output": {
                    "citations": validation_result["citations"][:3],
                    "overall_confidence": validation_result["overall_confidence"],
                    "unverified_count": validation_result["unverified_count"],
                    "latency_ms": validation_result["validation_latency_ms"],
                },
            },
            "total_latency_ms": total_ms,
        }
        logger.info(f"[AGENT_TRACE] {json.dumps(trace, indent=2)}")


# singleton pipeline instance
_pipeline: Optional[TaxAIPipeline] = None 


def get_pipeline()-> TaxAIPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TaxAIPipeline()
        
    return _pipeline