"""
Document parsers — PDF (PyMuPDF + pdfplumber) and HTML (BeautifulSoup4 + lxml).
Preserves section hierarchy for legal text chunking.

Manual-upload mode: place PDFs in backend/data/pdfs/
  ITA 2025      → backend/data/pdfs/ita_2025.pdf
  CBDT circulars → backend/data/pdfs/circulars/circular_<number>.pdf
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz          # PyMuPDF
import pdfplumber
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Section-level chunking patterns
# ─────────────────────────────────────────────────────────────────────────────

# Matches: "Section 2", "Section 2(22)", "Section 2(22)(e)", "Section 147A"
SECTION_PATTERN = re.compile(
    r"^\s*(?:section\s*)?(\d{1,3}[A-Z]?)(?:\s*\((\d+)\))?(?:\s*\(([a-z])\))?\s*[\.\-:]?\s*(.*)",
    re.IGNORECASE | re.MULTILINE,
)

# Chapter heading pattern
CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*CHAPTER\s+([IVXLCDM\d]+)\s*[-–—]?\s*([^\n]+)",
    re.MULTILINE,
)

# Proviso pattern — must stay with parent section, never split
PROVISO_PATTERN = re.compile(r"(?:^|\n)\s*Provided\s+that\b", re.MULTILINE)


# ─────────────────────────────────────────────────────────────────────────────
# PDF / HTML parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_pdf_with_pdfplumber(pdf_path: str) -> str:
    """
    Extract clean text from PDF preserving layout.
    Falls back to PyMuPDF if pdfplumber fails.
    """
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(page_text)
        full = "\n".join(text_parts)
        if len(full.strip()) < 100:
            raise ValueError("pdfplumber returned near-empty text — trying PyMuPDF")
        return full
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path}: {e}. Falling back to PyMuPDF.")
        return parse_pdf_with_pymupdf(pdf_path)


def parse_pdf_with_pymupdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz). More robust for scanned/complex PDFs."""
    text_parts = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text_parts.append(page.get_text("text"))
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF also failed for {pdf_path}: {e}")
    return "\n".join(text_parts)


def parse_html(html_content: str) -> str:
    """Parse HTML to clean text, stripping nav/footer/script/style."""
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup.find_all(["nav", "footer", "script", "style", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def parse_any_pdf(pdf_path: str) -> str:
    """
    Auto-select parser: try pdfplumber first, then PyMuPDF.
    Returns cleaned text or empty string on total failure.
    """
    path = Path(pdf_path)
    if not path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return ""
    if path.stat().st_size < 100:
        logger.warning(f"PDF too small, skipping: {pdf_path}")
        return ""
    return parse_pdf_with_pdfplumber(pdf_path)


# ─────────────────────────────────────────────────────────────────────────────
# ITA 2025 — Section-level chunker
# ─────────────────────────────────────────────────────────────────────────────

def chunk_income_tax_act(full_text: str) -> List[Dict[str, Any]]:
    """
    Chunk ITA 2025 at section level.
    Each chunk carries the full section text including all provisos.
    Provisos are NEVER split from their parent section.
    Metadata follows the assignment spec exactly.
    """
    chunks: List[Dict[str, Any]] = []
    lines = full_text.split("\n")

    current_section_num: Optional[str] = None
    current_sub_section: Optional[str] = None
    current_clause: Optional[str] = None
    current_text_lines: List[str] = []
    current_chapter: str = ""
    has_proviso: bool = False

    def flush_chunk():
        nonlocal current_section_num, current_sub_section, current_clause
        nonlocal current_text_lines, has_proviso

        if not current_section_num or not current_text_lines:
            return

        text = "\n".join(current_text_lines).strip()
        if len(text) < 20:
            current_text_lines = []
            has_proviso = False
            return

        # Build chunk_id: ITA_2025_S<num>[_<sub>][_<clause>]
        chunk_id = f"ITA_2025_S{current_section_num}"
        if current_sub_section:
            chunk_id += f"_{current_sub_section}"
        if current_clause:
            chunk_id += f"_{current_clause}"

        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "metadata": {
                "act": "Income Tax Act, 2025",
                "section": current_section_num,
                "sub_section": current_sub_section or "",
                "clause": current_clause or "",
                "proviso": has_proviso,
                "chapter": current_chapter,
                "chunk_type": "statutory",
                "domain": "Direct Tax",
                "effective_from": "2025-04-01",
                "last_amended": "2025-04-01",
            },
        })
        current_text_lines = []
        has_proviso = False

    for line in lines:
        # Detect chapter heading
        chapter_match = CHAPTER_PATTERN.match(line)
        if chapter_match:
            current_chapter = (
                f"Chapter {chapter_match.group(1)} - {chapter_match.group(2).strip()}"
            )

        # Detect new section — flush previous first
        sec_match = SECTION_PATTERN.search(line)

        if not sec_match:
            # fallback: detect numeric section headers like "2.", "2 -", "2 "
            fallback = re.match(r"^\s*(\d{1,3}[A-Z]?)\s*[\.\-\:\)]?\s+(.*)", line)
            if fallback:
                sec_match = fallback
    
        if sec_match:
            flush_chunk()
            current_section_num = sec_match.group(1)
            current_sub_section = sec_match.group(2)
            current_clause = sec_match.group(3)

        # Detect proviso (stays with parent section)
        if PROVISO_PATTERN.search(line):
            has_proviso = True

        current_text_lines.append(line)

    flush_chunk()  # flush final section

    logger.info(f"Chunked ITA 2025: {len(chunks)} section chunks")
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# CBDT Circular — metadata extractor + chunker
# ─────────────────────────────────────────────────────────────────────────────

CIRCULAR_NUM_PATTERN = re.compile(
    r"Circular\s+(?:No\.?\s*)?(\d+(?:/\d{4})?)", re.IGNORECASE
)
DATE_PATTERN = re.compile(
    r"dated?\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)


def extract_circular_metadata(text: str) -> Tuple[str, str, str]:
    """
    Extract circular number, subject, and effective date from circular text.
    Returns (circular_number, subject, effective_date).
    """
    num_match = CIRCULAR_NUM_PATTERN.search(text)
    circular_number = num_match.group(1) if num_match else "UNKNOWN"

    date_match = DATE_PATTERN.search(text)
    effective_date = date_match.group(1) if date_match else ""

    subject_match = re.search(r"Subject\s*:\s*([^\n]+)", text, re.IGNORECASE)
    subject = subject_match.group(1).strip() if subject_match else text[:120].strip()

    return circular_number, subject, effective_date


def chunk_cbdt_circular(
    full_text: str,
    source_url: str = "",
    filename: str = "",
) -> List[Dict[str, Any]]:
    """
    Chunk a CBDT circular.
    - Short circular (< 12 000 chars) → single chunk.
    - Long circular → paragraph-level chunks.
    filename is used as fallback for circular number if not found in text.
    """
    circular_number, subject, effective_date = extract_circular_metadata(full_text)

    # If metadata extraction failed, try to extract number from filename
    # e.g. circular_359_1983.pdf → 359/1983
    if circular_number == "UNKNOWN" and filename:
        fn_match = re.search(r"(\d+)[_\-](\d{4})", Path(filename).stem)
        if fn_match:
            circular_number = f"{fn_match.group(1)}/{fn_match.group(2)}"
        else:
            fn_num = re.search(r"(\d+)", Path(filename).stem)
            if fn_num:
                circular_number = fn_num.group(1)

    safe_num = circular_number.replace("/", "_")

    base_meta = {
        "circular_number": circular_number,
        "issuing_authority": "CBDT",
        "subject": subject,
        "effective_date": effective_date,
        "source_url": source_url,
        "source_file": filename,
        "chunk_type": "circular",
        "domain": "Direct Tax",
        "act": "Income Tax Act, 2025",
    }

    # Short circular → single chunk
    if len(full_text) < 12000:
        return [{
            "chunk_id": f"CBDT_CIRC_{safe_num}",
            "text": full_text.strip(),
            "metadata": base_meta,
        }]

    # Long circular → paragraph chunks
    paragraphs = re.split(r"\n\s*\n", full_text)
    chunks = []
    para_idx = 1
    for para in paragraphs:
        para = para.strip()
        if len(para) < 50:
            continue
        chunks.append({
            "chunk_id": f"CBDT_CIRC_{safe_num}_P{para_idx}",
            "text": para,
            "metadata": {**base_meta, "paragraph": para_idx},
        })
        para_idx += 1

    logger.info(
        f"Chunked CBDT Circular {circular_number}: {len(chunks)} chunks "
        f"({'long' if len(chunks) > 1 else 'short'})"
    )
    return chunks
