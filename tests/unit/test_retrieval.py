"""
Unit tests for retrieval utilities — RRF merging and reranker scoring.
Run: pytest tests/unit/test_retrieval.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from backend.retrieval.reranker import reciprocal_rank_fusion


def make_chunk(chunk_id: str, score: float, text: str = "sample text") -> dict:
    return {
        "chunk_id": chunk_id,
        "score": score,
        "text": text,
        "metadata": {"section": chunk_id.split("_S")[-1] if "_S" in chunk_id else ""},
    }


class TestReciprocal_RankFusion:
    def test_merges_two_lists(self):
        vec = [make_chunk("ITA_S54", 0.95), make_chunk("ITA_S80C", 0.88)]
        kw  = [make_chunk("ITA_S80C", 0.75), make_chunk("ITA_S147", 0.60)]
        merged = reciprocal_rank_fusion([vec, kw], top_k=5)
        ids = [c["chunk_id"] for c in merged]
        # ITA_S80C appears in both lists — should rank highest via RRF
        assert "ITA_S80C" in ids
        assert ids.index("ITA_S80C") <= 1

    def test_deduplication(self):
        vec = [make_chunk("ITA_S54", 0.9), make_chunk("ITA_S54", 0.85)]
        kw  = [make_chunk("ITA_S54", 0.7)]
        merged = reciprocal_rank_fusion([vec, kw], top_k=10)
        ids = [c["chunk_id"] for c in merged]
        # Should appear exactly once
        assert ids.count("ITA_S54") == 1

    def test_top_k_respected(self):
        chunks_a = [make_chunk(f"A_{i}", 1.0 - i * 0.1) for i in range(10)]
        chunks_b = [make_chunk(f"B_{i}", 1.0 - i * 0.1) for i in range(10)]
        merged = reciprocal_rank_fusion([chunks_a, chunks_b], top_k=5)
        assert len(merged) == 5

    def test_rrf_score_attached(self):
        vec = [make_chunk("ITA_S54", 0.9)]
        merged = reciprocal_rank_fusion([vec], top_k=5)
        assert "rrf_score" in merged[0]
        assert merged[0]["rrf_score"] > 0

    def test_empty_list_handled(self):
        merged = reciprocal_rank_fusion([[], []], top_k=5)
        assert merged == []

    def test_single_list(self):
        vec = [make_chunk("ITA_S54", 0.9), make_chunk("ITA_S80C", 0.8)]
        merged = reciprocal_rank_fusion([vec], top_k=5)
        assert len(merged) == 2
        assert merged[0]["chunk_id"] == "ITA_S54"

    def test_k_parameter_effect(self):
        """Higher k → smaller RRF scores but same relative ordering."""
        vec = [make_chunk("ITA_S1", 0.9), make_chunk("ITA_S2", 0.8)]
        m60  = reciprocal_rank_fusion([vec], top_k=2, k=60)
        m600 = reciprocal_rank_fusion([vec], top_k=2, k=600)
        # Relative order same
        assert m60[0]["chunk_id"] == m600[0]["chunk_id"]
        # But scores differ
        assert m60[0]["rrf_score"] > m600[0]["rrf_score"]
