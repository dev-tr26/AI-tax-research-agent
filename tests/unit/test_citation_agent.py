"""
Unit tests for CitationValidationAgent.
Run: pytest tests/unit/test_citation_agent.py -v
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from backend.agents.citation_validation_agent import CitationValidationAgent


@pytest.fixture
def agent():
    return CitationValidationAgent()


SAMPLE_CHUNKS = [
    {
        "chunk_id": "ITA_2025_S54",
        "text": "Section 54. Profit on sale of property used for residence — where a capital gain arises from the transfer of a long-term capital asset...",
        "metadata": {"section": "54", "act": "Income Tax Act, 2025"},
        "rerank_score": 0.92,
    },
    {
        "chunk_id": "CBDT_CIRC_359_1983",
        "text": "CBDT Circular No. 359 dated 1983 — clarification on Section 54 exemption for purchase before sale...",
        "metadata": {"circular_number": "359/1983", "issuing_authority": "CBDT"},
        "rerank_score": 0.78,
    },
    {
        "chunk_id": "ITA_2025_S2_22",
        "text": "Section 2(22)(e). 'Dividend' includes any payment by a company...",
        "metadata": {"section": "2", "sub_section": "22", "clause": "e"},
        "rerank_score": 0.85,
    },
]


class TestCitationExtraction:
    def test_extract_act_section(self, agent):
        text = "As per Section 54 of the Income Tax Act, 2025, the exemption is available."
        citations = agent._extract_citations(text)
        act_cites = [c for c in citations if c["type"] == "act"]
        assert len(act_cites) >= 1
        assert any("54" in c["text"] for c in act_cites)

    def test_extract_circular(self, agent):
        text = "CBDT Circular No. 359/1983 clarifies the position on pre-purchase."
        citations = agent._extract_citations(text)
        circ_cites = [c for c in citations if c["type"] == "circular"]
        assert len(circ_cites) >= 1
        assert any("359" in c["text"] for c in circ_cites)

    def test_extract_case_law(self, agent):
        text = "The Supreme Court in Kantilal Manilal vs CIT held that deemed dividend crystallises at payment."
        citations = agent._extract_citations(text)
        case_cites = [c for c in citations if c["type"] == "case"]
        assert len(case_cites) >= 1

    def test_no_duplicate_citations(self, agent):
        text = "Section 54 applies. Under Section 54, the exemption..."
        citations = agent._extract_citations(text)
        texts = [c["text"] for c in citations]
        assert len(texts) == len(set(texts))


class TestCitationVerification:
    @pytest.mark.asyncio
    async def test_high_confidence_on_chunk_match(self, agent):
        citation = {
            "text": "Section 54, Income Tax Act, 2025",
            "type": "act",
            "section": "54",
            "chunk_id_hint": "ITA_2025_S54",
        }
        result = await agent._verify_citation(citation, SAMPLE_CHUNKS)
        assert result["verified"] is True
        assert result["confidence"] >= 0.75
        assert result["source_chunk_id"] == "ITA_2025_S54"

    @pytest.mark.asyncio
    async def test_circular_verification(self, agent):
        citation = {
            "text": "CBDT Circular No. 359/1983",
            "type": "circular",
            "circular_number": "359/1983",
            "chunk_id_hint": "CBDT_CIRC_359_1983",
        }
        result = await agent._verify_citation(citation, SAMPLE_CHUNKS)
        assert result["verified"] is True

    @pytest.mark.asyncio
    async def test_case_law_marked_unverified(self, agent):
        citation = {
            "text": "Some Random Case vs CIT (SC 1990)",
            "type": "case",
            "chunk_id_hint": None,
        }
        result = await agent._verify_citation(citation, SAMPLE_CHUNKS)
        assert result["verified"] is False
        assert result["confidence"] < 0.6

    @pytest.mark.asyncio
    async def test_nonexistent_section_unverified(self, agent):
        citation = {
            "text": "Section 999",
            "type": "act",
            "section": "999",
            "chunk_id_hint": "ITA_2025_S999",
        }
        with patch("agents.citation_validation_agent.get_pinecone_store") as mock_pc:
            mock_index = MagicMock()
            mock_index.fetch_by_ids.return_value = {}
            mock_pc.return_value = mock_index
            with patch("agents.citation_validation_agent.get_es_store") as mock_es:
                mock_es.return_value.get_by_id = AsyncMock(return_value=None)
                result = await agent._verify_citation(citation, [])
                assert result["verified"] is False


class TestOverallConfidence:
    def test_all_verified_high_confidence(self, agent):
        citations = [
            {"verified": True, "confidence": 0.95},
            {"verified": True, "confidence": 0.88},
            {"verified": True, "confidence": 0.90},
        ]
        level = agent._compute_overall_confidence(citations)
        assert level == "HIGH"

    def test_mixed_gives_medium(self, agent):
        citations = [
            {"verified": True,  "confidence": 0.85},
            {"verified": False, "confidence": 0.10},
            {"verified": True,  "confidence": 0.70},
        ]
        level = agent._compute_overall_confidence(citations)
        assert level in ("MEDIUM", "LOW")

    def test_all_unverified_gives_low(self, agent):
        citations = [
            {"verified": False, "confidence": 0.10},
            {"verified": False, "confidence": 0.15},
        ]
        level = agent._compute_overall_confidence(citations)
        assert level == "LOW"

    def test_empty_citations(self, agent):
        level = agent._compute_overall_confidence([])
        assert level == "LOW"
