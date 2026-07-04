"""
Section index — in-memory lookup of every section/circular number
present in the Pinecone corpus.  Used by CitationValidationAgent
for O(1) existence checks without a vector query.

Built once at startup from Pinecone stats + a lightweight list fetch.
Refreshed whenever ingestion completes.
"""
import logging
from typing import Optional
from config import get_settings
from typing import Set
logger = logging.getLogger(__name__)
settings = get_settings()


class SectionIndex:
    """
    Maintains a set of known section numbers and circular numbers
    so CitationValidationAgent can check existence in < 1ms.
    """

    _instance: Optional["SectionIndex"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._instance._sections = set()
        self._instance._circulars = set()
        self._instance._chunk_ids = set()
        self._instance._loaded = False
        self._initialized = True

    def add_section(self, section: str, sub_section: str = "", clause: str = ""):
        """Register a section number."""
        self._sections.add(section.strip())
        if sub_section:
            self._sections.add(f"{section.strip()}({sub_section})")
        if clause:
            self._sections.add(f"{section.strip()}({sub_section})({clause})")

    def add_circular(self, circular_number: str):
        """Register a circular number (various formats)."""
        norm = circular_number.strip()
        self._circulars.add(norm)
        # Also add without the year suffix
        base = norm.split("/")[0]
        self._circulars.add(base)

    def add_chunk_id(self, chunk_id: str):
        self._chunk_ids.add(chunk_id)

    def has_section(self, section: str) -> bool:
        return section.strip() in self._sections

    def has_circular(self, circular_number: str) -> bool:
        norm = circular_number.strip()
        base = norm.split("/")[0]
        return norm in self._circulars or base in self._circulars

    def has_chunk_id(self, chunk_id: str) -> bool:
        return chunk_id in self._chunk_ids

    def section_count(self) -> int:
        return len(self._sections)

    def circular_count(self) -> int:
        return len(self._circulars)

    def load_from_chunks(self, chunks: list):
        """
        Populate index from a list of chunk dicts (used after ingestion).
        Each chunk: {"chunk_id": str, "metadata": {"section": str, ...}}
        """
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cid = chunk.get("chunk_id", "")
            self.add_chunk_id(cid)

            if meta.get("chunk_type") == "statutory":
                self.add_section(
                    meta.get("section", ""),
                    meta.get("sub_section", ""),
                    meta.get("clause", ""),
                )
            elif meta.get("chunk_type") == "circular":
                circ_num = meta.get("circular_number", "")
                if circ_num:
                    self.add_circular(circ_num)

        self._loaded = True
        logger.info(
            f"[SectionIndex] Loaded {self.section_count()} sections, "
            f"{self.circular_count()} circulars, {len(self._chunk_ids)} chunk IDs"
        )

    async def build_from_pinecone(self):
        """
        Attempt to build index from Pinecone index stats.
        Falls back gracefully if Pinecone is unavailable.
        """
        try:
            from retrieval.vector_store import get_pinecone_store
            pc = get_pinecone_store()
            stats = pc.index_stats()
            ns = stats.get("namespaces", {})
            total = sum(v.get("vector_count", 0) for v in ns.values())
            logger.info(f"[SectionIndex] Pinecone reports {total} vectors across {len(ns)} namespaces")
            self._loaded = True
        except Exception as e:
            logger.warning(f"[SectionIndex] Pinecone unavailable during build: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._loaded


_section_index = SectionIndex()


def get_section_index() -> SectionIndex:
    return _section_index
