# doc parsers - PDF (pymupdf + pdfplumber)
# preserves section heirarchy for legal text chunking 

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  
import pdfplumber
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# section level chunking pattern 

# Matches: "Section 2", "Section 2(22)", "Section 2(22)(e)", "Section 147A"
SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:SECTION|Section)\s+(\d+[A-Z]?)"
    r"(?:\s*\((\d+)\))?(?:\s*\(([a-z])\))?",
    re.MULTILINE,
)

# Chapter heading pattern
CHAPTER_PATTERN = re.compile(
    r"(?:^|\n)\s*CHAPTER\s+([IVXLCDM\d]+)\s*[-–—]?\s*([^\n]+)",
    re.MULTILINE,
)

# Proviso pattern
PROVISON_PATTERN = re.compile(r"(?:^|\n)\s*Provided\s+that\b", re.MULTILINE)


def parse_pdf_with_pdfplumber(pdf_path: str) -> str:
    """Extract clean text from PDF preserving layout. Fallback to PyMuPDF."""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path}: {e}. Falling back to PyMuPDF.")
        return parse_pdf_with_pymupdf(pdf_path)


def parse_pdf_with_pymupdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF."""
    text_parts = []
    doc = fitz.open(pdf_path)
    for page in doc:
        text_parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(text_parts)


def parse_html(html_content: str) -> str:
    """Parse HTML to clean text preserving headings."""
    soup = BeautifulSoup(html_content, "lxml")
    # Remove nav, footer, script, style
    for tag in soup.find_all(["nav", "footer", "script", "style", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


# ITA 2025 — Section-level chunker
# each chunk includes full section texts including all provisions, metadata attached per assignment spec
def chunk_income_tax_act(full_text: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = full_text.split("\n")
    current_section_num: Optional[str] = None 
    current_sub_section: Optional[str] = None
    current_clause: Optional[str] = None
    current_text_lines: List[str] = []
    current_chapter = ""
    has_provison = False
    
    def flush_chunk():
        nonlocal current_section_num, current_sub_section, current_clause, current_text_lines, has_provison
        if not current_section_num or not current_text_lines:
            return 
        
        text = "\n".join(current_text_lines).strip()
        if len(text) < 20:
            return 
        
        chunk_id = f"ITA_2025_S{current_section_num}"
        if current_sub_section:
            chunk_id += f"_{current_sub_section}"
        if current_clause:
            chunk_id += f"_{current_clause}"
            
        chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "metadat": {
                "act": "Income Tax Act, 2025",
                "session": current_section_num,
                "sub_section": current_sub_section or "",
                "clause": current_clause or "",
                "provision": has_provison,
                "chapter": current_chapter,
                "chunk_type" : "statutory",
                "domain": "Direct Tax",
                "effective_from": "2025-04-01",
                "last_amended": "2025-04-01",
            },
        })
        current_text_lines = []
        has_provison = False 
        
    for line in lines:
        chapter_match = CHAPTER_PATTERN.match(line)
        if chapter_match:
            current_chapter = f"Chapter {chapter_match.group(1)} - {chapter_match.group(2).strip()}"

        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            flush_chunk()
            current_section_num = sec_match.group(1)
            current_sub_section = sec_match.group(2)
            current_clause = sec_match.group(3)

        if PROVISON_PATTERN.search(line):
            has_provison = True

        current_text_lines.append(line)

    flush_chunk()  

    logger.info(f"Chunked ITA 2025: {len(chunks)} section chunks")
    return chunks



# CBDT circular chunker
CIRCULAR_NUM_PATTERN = re.compile(
    r"Circular\s+(?:No\.?\s*)?(\d+(?:/\d+)?)", re.IGNORECASE
)
DATE_PATTERN = re.compile(
    r"dated?\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    re.IGNORECASE,
)



# Extract clean text from PDF preserving layout,  Fallback to PyMuPDF
def parse_pdf_with_pdfplumber(pdf_path: str) -> str:
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"pdfplumber failed for {pdf_path}: {e}. Falling back to PyMuPDF.")
        return parse_pdf_with_pymupdf(pdf_path)



    # extract circular number , subject, effective date from txt 
def extract_circular_metadata(text: str) -> Tuple[str, str, str]:
    num_match = CIRCULAR_NUM_PATTERN.search(text)
    circular_number = num_match.group(1) if num_match else "UNKNOWN"

    date_match = DATE_PATTERN.search(text)
    effective_date = date_match.group(1) if date_match else ""

    # Subject is usually in the first 200 chars after "Subject:"
    subject_match = re.search(r"Subject\s*:\s*([^\n]+)", text, re.IGNORECASE)
    subject = subject_match.group(1).strip() if subject_match else text[:100].strip()

    return circular_number, subject, effective_date




# chunk CBDT circular for shirt circulars -> full circular as one chunk 
# for paralevel for long circulars > 3000 tokens 
def chunk_cbdt_circular(full_text: str, source_url: str = "") -> List[Dict[str, Any]]:
    circular_number, subject, effective_date = extract_circular_metadata(full_text)

    base_meta = {
        "circular_number": circular_number,
        "issuing_authority": "CBDT",
        "subject": subject,
        "effective_date": effective_date,
        "source_url": source_url,
        "chunk_type": "circular",
        "domain": "Direct Tax",
        "act": "Income Tax Act, 2025",
    }

    # Short circular — single chunk
    if len(full_text) < 12000:
        return [{
            "chunk_id": f"CBDT_CIRC_{circular_number.replace('/', '_')}",
            "text": full_text.strip(),
            "metadata": base_meta,
        }]

    # Long circular — paragraph chunks
    paragraphs = re.split(r"\n\s*\n", full_text)
    chunks = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) < 50:
            continue
        chunks.append({
            "chunk_id": f"CBDT_CIRC_{circular_number.replace('/', '_')}_P{i+1}",
            "text": para,
            "metadata": {**base_meta, "paragraph": i + 1},
        })

    logger.info(f"Chunked CBDT Circular {circular_number}: {len(chunks)} chunks")
    return chunks

        

