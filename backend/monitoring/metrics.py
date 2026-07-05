# metrics tracks per query latency , citation verification rates , hallucination counts
# used for P50 / P95 reporting and LangSmith dashboards

import statistics
import logging
from collections import defaultdict 
from collections import deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime,timezone
import uuid 

logger = logging.getLogger(__name__)

MAX_HISTORY = 500  # rolling window of recent queries

@dataclass
class QueryMetric:
    query_id: str
    session_id: str
    query_preview: str
    timestamp: str
    
# stage latencies (ms)
    embedding_ms: int = 0
    vector_retrieval_ms: int = 0
    keyword_retrieval_ms: int = 0
    rerank_ms: int = 0
    synthesis_ms: int = 0
    citation_validation_ms: int = 0
    total_ms: int = 0
    
# quality
    chunks_retrieved: int = 0
    citations_total: int = 0
    citations_verified: int = 0
    unverified_count: int = 0
    overall_confidence: str = "UNKNOWN"
    
# error
    error: Optional[str] = None
    

class MetricsCollector:
    """
    Thread-safe in-memory metrics store with rolling window.
    Exposes P50/P95 computations for all tracked stage latencies.
    """

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._records : deque = deque(maxlen=MAX_HISTORY) # type: ignore
            cls._instance._error_count = 0
            cls._instance._total_count = 0
        return cls._instance
    
    def record(self, metric: QueryMetric):
        self._records.append(metric)
        self._total_count += 1
        if metric.error:
            self._error_count += 1
        logger.debug(f"Recorded metric: {asdict(metric)}. Total count: {self._total_count}, Error count: {self._error_count}")
        
    def record_from_pipeline_result(self, query: str, session_id: str, result: Dict[str, Any]) -> QueryMetric:
        timings = result.get("timings", {})
        response = result.get("response", {})
        citations = response.get("citations", [])
        
        metric = QueryMetric(
            query_id = str(uuid.uuid4())[:8],
            session_id = session_id,
            query_preview=query[:80],
            timestamp = datetime.now(timezone.utc).isoformat(),
            embedding_ms=timings.get("embedding_ms", 0),
            vector_retrieval_ms=timings.get("vector_retrieval_ms", 0),
            keyword_retrieval_ms=timings.get("keyword_retrieval_ms", 0),
            rerank_ms=timings.get("rerank_ms", 0),
            synthesis_ms=timings.get("synthesis_ms", 0),
            citation_validation_ms=timings.get("citation_validation_ms", 0),
            total_ms=timings.get("total_ms", 0),
            chunks_retrieved=response.get("chunks_retrieved", 0),
            citations_total=len(citations),
            citations_verified=sum(1 for c in citations if c.get("verified")),
            unverified_count=sum(1 for c in citations if not c.get("verified")),
            overall_confidence=response.get("overall_confidence", "UNKNOWN")
        )
        self.record(metric)
        return metric
    
    def _extract_latencies(self, field: str)-> List[int]:
        return [getattr(record, field) for record in self._records if getattr(record, field, 0) > 0]
    
    def _percentile(self, data: List[int], pct: float) -> int:
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def summary(self) -> Dict[str, Any]:
        if not self._records:
            return {"message": "No queries recorded yet"}

        total_latencies = self._extract_latencies("total_ms")
        vec_latencies = self._extract_latencies("vector_retrieval_ms")
        cite_latencies = self._extract_latencies("citation_validation_ms")
        synth_latencies = self._extract_latencies("synthesis_ms")

        all_citations = sum(r.citations_total for r in self._records)
        all_verified = sum(r.citations_verified for r in self._records)
        hallucination_rate = (
            (all_citations - all_verified) / all_citations
            if all_citations > 0 else 0.0
        )

        confidence_dist = defaultdict(int)
        for r in self._records:
            confidence_dist[r.overall_confidence] += 1

        return {
            "total_queries": self._total_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._total_count, 1),
            "latency": {
                "end_to_end": {
                    "p50_ms": self._percentile(total_latencies, 50),
                    "p75_ms": self._percentile(total_latencies, 75),
                    "p95_ms": self._percentile(total_latencies, 95),
                    "p99_ms": self._percentile(total_latencies, 99),
                    "mean_ms": int(statistics.mean(total_latencies)) if total_latencies else 0,
                },
                "vector_retrieval": {
                    "p50_ms": self._percentile(vec_latencies, 50),
                    "p95_ms": self._percentile(vec_latencies, 95),
                    "mean_ms": int(statistics.mean(vec_latencies)) if vec_latencies else 0,
                },
                "citation_validation": {
                    "p50_ms": self._percentile(cite_latencies, 50),
                    "p95_ms": self._percentile(cite_latencies, 95),
                    "mean_ms": int(statistics.mean(cite_latencies)) if cite_latencies else 0,
                },
                "llm_synthesis": {
                    "p50_ms": self._percentile(synth_latencies, 50),
                    "p95_ms": self._percentile(synth_latencies, 95),
                    "mean_ms": int(statistics.mean(synth_latencies)) if synth_latencies else 0,
                },
            },
            "quality": {
                "total_citations": all_citations,
                "verified_citations": all_verified,
                "hallucination_rate": round(hallucination_rate, 4),
                "confidence_distribution": dict(confidence_dist),
            },
            "sla_compliance": {
                "p50_under_5s": self._percentile(total_latencies, 50) < 5000,
                "p95_under_10s": self._percentile(total_latencies, 95) < 10000,
                "vec_mean_under_800ms": int(statistics.mean(vec_latencies)) < 800 if vec_latencies else True,
                "cite_mean_under_1s": int(statistics.mean(cite_latencies)) < 1000 if cite_latencies else True,
            },
        }
        
    def recent(self, n: int = 20) -> List[Dict]:
        return [asdict(r) for r in list(self._records)[-n:]]
    
    

_metrics = MetricsCollector()

def get_metrics() -> MetricsCollector:
    return _metrics
