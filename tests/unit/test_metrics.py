"""
Unit tests for MetricsCollector.
Run: pytest tests/unit/test_metrics.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

from backend.monitoring.metrics import MetricsCollector, QueryMetric
from datetime import datetime, timezone


def make_metric(**kwargs) -> QueryMetric:
    defaults = dict(
        query_id="test-001",
        session_id="sess-abc",
        query_preview="test query",
        timestamp=datetime.now(timezone.utc).isoformat(),
        embedding_ms=180,
        vector_retrieval_ms=350,
        keyword_retrieval_ms=120,
        rerank_ms=280,
        synthesis_ms=2400,
        citation_validation_ms=420,
        total_ms=3800,
        chunks_retrieved=5,
        citations_total=4,
        citations_verified=4,
        unverified_count=0,
        overall_confidence="HIGH",
    )
    defaults.update(kwargs)
    return QueryMetric(**defaults)


@pytest.fixture(autouse=True)
def fresh_collector():
    """Give each test a clean collector by resetting the singleton's records."""
    from collections import deque
    collector = MetricsCollector()
    collector._records = deque(maxlen=500)
    collector._error_count = 0
    collector._total_count = 0
    yield collector


class TestMetricsRecording:
    def test_record_increments_count(self, fresh_collector):
        fresh_collector.record(make_metric())
        assert fresh_collector._total_count == 1

    def test_error_metric_increments_error_count(self, fresh_collector):
        fresh_collector.record(make_metric(error="Something broke"))
        assert fresh_collector._error_count == 1

    def test_multiple_records(self, fresh_collector):
        for i in range(5):
            fresh_collector.record(make_metric(query_id=f"q{i}", total_ms=3000 + i * 200))
        assert fresh_collector._total_count == 5


class TestLatencyPercentiles:
    def test_p50_calculation(self, fresh_collector):
        latencies = [1000, 2000, 3000, 4000, 5000]
        for i, ms in enumerate(latencies):
            fresh_collector.record(make_metric(query_id=f"q{i}", total_ms=ms))
        summary = fresh_collector.summary()
        p50 = summary["latency"]["end_to_end"]["p50_ms"]
        assert p50 == 3000  # median of 5 values

    def test_p95_higher_than_p50(self, fresh_collector):
        for i in range(20):
            fresh_collector.record(make_metric(query_id=f"q{i}", total_ms=1000 + i * 300))
        summary = fresh_collector.summary()
        lat = summary["latency"]["end_to_end"]
        assert lat["p95_ms"] >= lat["p50_ms"]

    def test_empty_returns_message(self, fresh_collector):
        summary = fresh_collector.summary()
        assert "message" in summary


class TestSLACompliance:
    def test_all_pass_when_fast(self, fresh_collector):
        for i in range(10):
            fresh_collector.record(make_metric(
                query_id=f"q{i}",
                total_ms=2000,
                vector_retrieval_ms=300,
                citation_validation_ms=400,
            ))
        summary = fresh_collector.summary()
        sla = summary["sla_compliance"]
        assert sla["p50_under_5s"] is True
        assert sla["p95_under_10s"] is True
        assert sla["vec_mean_under_800ms"] is True
        assert sla["cite_mean_under_1s"] is True

    def test_p50_fail_when_slow(self, fresh_collector):
        for i in range(10):
            fresh_collector.record(make_metric(query_id=f"q{i}", total_ms=7000))
        summary = fresh_collector.summary()
        assert summary["sla_compliance"]["p50_under_5s"] is False


class TestQualityMetrics:
    def test_hallucination_rate_zero_when_all_verified(self, fresh_collector):
        fresh_collector.record(make_metric(
            citations_total=5, citations_verified=5, unverified_count=0
        ))
        summary = fresh_collector.summary()
        assert summary["quality"]["hallucination_rate"] == 0.0

    def test_hallucination_rate_nonzero(self, fresh_collector):
        fresh_collector.record(make_metric(
            citations_total=4, citations_verified=2, unverified_count=2
        ))
        summary = fresh_collector.summary()
        assert summary["quality"]["hallucination_rate"] == 0.5

    def test_confidence_distribution_tracked(self, fresh_collector):
        fresh_collector.record(make_metric(overall_confidence="HIGH"))
        fresh_collector.record(make_metric(overall_confidence="MEDIUM"))
        fresh_collector.record(make_metric(overall_confidence="HIGH"))
        summary = fresh_collector.summary()
        dist = summary["quality"]["confidence_distribution"]
        assert dist.get("HIGH", 0) == 2
        assert dist.get("MEDIUM", 0) == 1
