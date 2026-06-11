# TaxAI — Next-Generation Indian Tax Research Platform

An agentic, citation-verified AI tax research system for Direct Tax (Income Tax Act, 2025) and CBDT Circulars.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Next.js 14 Frontend                          │
│  QueryInterface → StreamingResponse → CitationPanel → HistoryPanel │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ REST / SSE
┌─────────────────────────▼───────────────────────────────────────────┐
│                     FastAPI Backend                                  │
│  /query (SSE stream)  /sessions  /ingest  /health                  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│               AutoGen v0.4+ Multi-Agent Pipeline                    │
│                                                                      │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │ UserProxy    │───▶│ RetrievalAgent   │───▶│ CitationValid.   │  │
│  │ Agent        │    │ (RAG Executor)   │    │ Agent            │  │
│  │              │◀───│                  │◀───│                  │  │
│  │ - Session    │    │ - Pinecone vec   │    │ - Verify cites   │  │
│  │ - Follow-up  │    │ - ES hybrid      │    │ - Confidence     │  │
│  │ - Formatting │    │ - BGE embeddings │    │ - Hallucination  │  │
│  └──────────────┘    │ - Reranking      │    │   firewall       │  │
│                      └──────────────────┘    └──────────────────┘  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                       Data Layer                                     │
│  Pinecone (vectors) │ Elasticsearch (hybrid) │ SQLite (sessions)   │
│  LangSmith (traces) │ BGE-large embeddings   │ File cache (PDFs)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Interaction Flow

```
User Query
    │
    ▼
UserProxyAgent
  ├─ Create/resume session (SQLite)
  ├─ Detect follow-up references ("this section", "above case")
  ├─ Prepend prior context if follow-up
    │
    ▼
RetrievalAgent
  ├─ Embed query (BGE-large-en-v1.5)
  ├─ Pinecone ANN search (top-20 candidates)
  ├─ Elasticsearch BM25 keyword search (top-20)
  ├─ Reciprocal Rank Fusion (merge results)
  ├─ Cross-encoder rerank → top-5 chunks
  ├─ LLM synthesis (Groq Llama 3.3 70B / Gemini 2.0 Flash)
    │
    ▼
CitationValidationAgent
  ├─ Parse all section / circular / case citations
  ├─ Verify each against Pinecone metadata
  ├─ Score confidence: HIGH / MEDIUM / LOW
  ├─ Remove or flag UNVERIFIED citations
    │
    ▼
UserProxyAgent → Structured Response → Frontend SSE Stream
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| Agent Framework | AutoGen v0.4+ (autogen-agentchat) |
| LLM (Reasoning) | Groq: Llama 3.3 70B / Gemini 2.0 Flash |
| Embeddings | BAAI/bge-large-en-v1.5 (HuggingFace, free) |
| Vector Store | Pinecone (serverless) |
| Hybrid Search | Elasticsearch 8.x |
| Database | SQLite (sessions + ingestion logs) |
| PDF Parsing | PyMuPDF (fitz) + pdfplumber |
| HTML Parsing | BeautifulSoup4 + lxml |
| Monitoring | LangSmith (free tier) |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Elasticsearch)
- Pinecone account (free tier)
- Groq API key (free tier)
- Google AI API key (Gemini)
- LangSmith API key (free tier)

### 1. Clone & Install

```bash
git clone <repo>
cd taxai

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Environment Variables

```bash
# backend/.env
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=taxai-index
GROQ_API_KEY=your_key
GOOGLE_API_KEY=your_key
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=taxai
ELASTICSEARCH_URL=http://localhost:9200
SQLITE_PATH=./data/taxai.db
DATA_DIR=./data
```

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Elasticsearch

```bash
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

### 4. Run Ingestion Pipeline

```bash
cd backend
python -m ingestion.pipeline --source all
# Takes 20-40 minutes for full ingestion
# Progress logged to console and SQLite
```

### 5. Start Backend

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

### 6. Start Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:3000
```