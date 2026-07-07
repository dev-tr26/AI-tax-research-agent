"""
Unit tests for ingestion parsers and chunkers.
Run: pytest tests/unit/test_parsers.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from backend.ingestion.parsers import (
    chunk_income_tax_act,
    chunk_cbdt_circular,
    extract_circular_metadata,
)

# ── Sample text fixtures ──────────────────────────────────────────────────────

ITA_SAMPLE = """
CHAPTER I
PRELIMINARY

Section 1
Short title, extent and commencement.

(1) This Act may be called the Income Tax Act, 2025.
(2) It extends to the whole of India.
(3) It shall come into force on the 1st day of April, 2026.

Section 2
Definitions.

In this Act, unless the context otherwise requires,—
(1) "advance tax" means the advance tax payable in accordance with Chapter XVII-C;
(22) "dividend" includes—
(e) any payment by a company, not being a company in which the public are substantially interested, of any sum by way of advance or loan to a shareholder, being a person who is the beneficial owner of shares...
Provided that this sub-clause shall not apply if the loan or advance is made to a shareholder in the ordinary course of its business, where the lending of money is a substantial part of the business of the company;

Section 54
Profit on sale of property used for residence.

(1) Subject to the provisions of sub-section (2), where, in the case of an assessee being an individual or a Hindu undivided family, the capital gain arises from the transfer of a long-term capital asset, being buildings or lands appurtenant thereto, and being a residential house, the income of which is chargeable under the head "Income from house property" (hereafter in this section referred to as the original asset), and the assessee has within a period of one year before or two years after the date on which the transfer took place purchased, or has within a period of three years after that date constructed, a residential house, then, instead of the capital gain being charged to income-tax as income of the previous year in which the transfer took place...
Provided that the amount of the capital gain which is not utilised by the assessee for the purchase or construction of the new asset before the date of furnishing the return of income under section 139, shall be deposited by him before furnishing such return in a Capital Gains Account.
"""

CIRCULAR_SAMPLE = """
CIRCULAR NO. 359/1983
Subject: Clarification regarding availability of exemption under Section 54 of the Income Tax Act, 1961 where new house is purchased before the sale of the original house.

dated 10th May 1983

1. The Board has been considering the question whether the benefit of exemption under Section 54 of the Income Tax Act, 1961 is available to an assessee who purchases the new house before the date of sale of the original house.

2. The Board is of the opinion that the exemption under Section 54 is available even if the new residential house property is purchased one year before the sale of the original asset.

3. This circular may be brought to the notice of all field officers.
"""


class TestITAChunker:
    def test_produces_chunks(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        assert len(chunks) >= 2

    def test_chunk_has_required_fields(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        required_fields = ["chunk_id", "text", "metadata"]
        for chunk in chunks:
            for field in required_fields:
                assert field in chunk, f"Missing field: {field}"

    def test_metadata_structure(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        for chunk in chunks:
            meta = chunk["metadata"]
            assert meta["act"] == "Income Tax Act, 2025"
            assert meta["chunk_type"] == "statutory"
            assert meta["domain"] == "Direct Tax"
            assert "section" in meta

    def test_section_2_chunk_id(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        ids = [c["chunk_id"] for c in chunks]
        assert any("ITA_2025_S2" in i for i in ids)

    def test_section_54_present(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        s54 = [c for c in chunks if "54" in c["chunk_id"]]
        assert len(s54) >= 1

    def test_proviso_detected(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        # Section 54 has a Provided that clause
        s54 = [c for c in chunks if "54" in c["chunk_id"]]
        if s54:
            assert s54[0]["metadata"]["proviso"] is True

    def test_proviso_not_split_from_parent(self):
        """Proviso text must appear in the same chunk as the parent section."""
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        s54 = [c for c in chunks if "S54" in c["chunk_id"]]
        if s54:
            assert "Provided" in s54[0]["text"] or s54[0]["metadata"]["proviso"]

    def test_no_empty_chunks(self):
        chunks = chunk_income_tax_act(ITA_SAMPLE)
        for chunk in chunks:
            assert len(chunk["text"].strip()) >= 20


class TestCircularChunker:
    def test_produces_chunk(self):
        chunks = chunk_cbdt_circular(CIRCULAR_SAMPLE)
        assert len(chunks) >= 1

    def test_circular_number_extracted(self):
        chunks = chunk_cbdt_circular(CIRCULAR_SAMPLE)
        chunk = chunks[0]
        assert chunk["metadata"]["circular_number"] in ("359", "359/1983")

    def test_metadata_fields(self):
        chunks = chunk_cbdt_circular(CIRCULAR_SAMPLE)
        meta = chunks[0]["metadata"]
        assert meta["issuing_authority"] == "CBDT"
        assert meta["chunk_type"] == "circular"
        assert meta["domain"] == "Direct Tax"

    def test_chunk_id_format(self):
        chunks = chunk_cbdt_circular(CIRCULAR_SAMPLE)
        cid = chunks[0]["chunk_id"]
        assert cid.startswith("CBDT_CIRC_")

    def test_short_circular_single_chunk(self):
        short_text = CIRCULAR_SAMPLE[:500]
        chunks = chunk_cbdt_circular(short_text)
        assert len(chunks) == 1

    def test_extract_circular_metadata(self):
        num, subject, date = extract_circular_metadata(CIRCULAR_SAMPLE)
        assert "359" in num
        assert len(subject) > 5
