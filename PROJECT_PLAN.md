# Azure RAG Chatbot with GPT-4o — Project Plan

## Goal
Build a chatbot that answers questions about large documents (PDFs, CSVs, images) using Azure services for document processing, embedding, and search, with OpenAI GPT-4o as the LLM for generating answers. Documents are stored in Azure Blob Storage as the central source of truth.

---

## Architecture

```
Local Documents (PDF, CSV, Images)
        │
        ▼
┌─────────────────────────┐
│ Azure Blob Storage       │  ← Central document store (upload once)
│ (Container: "documents") │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Azure AI Document        │  ← Extracts text from PDFs & images (OCR)
│ Intelligence             │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Chunking & Preprocessing │  ← Splits text into searchable chunks
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Azure OpenAI Embeddings  │  ← Converts chunks into 1536-dim vectors
│ (text-embedding-3-small) │     (already deployed)
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Azure AI Search          │  ← Stores vectors + text for fast retrieval
│ (Vector Index)           │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ User Question → Embed    │  ← Query flow: embed question → vector search
│ → Search → GPT-4o Answer │     → retrieve top chunks → GPT-4o generates answer
└─────────────────────────┘
```

---

## Azure Resources Needed

| Resource | Purpose | Status |
|---|---|---|
| Azure Blob Storage | Central document store — holds all PDFs, CSVs, images | Need to create |
| Azure OpenAI (text-embedding-3-small) | Generate vector embeddings for text chunks | Already deployed |
| Azure AI Document Intelligence | OCR — extract text from PDFs and images | Need to create |
| Azure AI Search | Vector database to store and search embeddings | Need to create |
| OpenAI API (GPT-4o) | LLM to generate answers from retrieved context | API key configured |

---

## Project File Structure

```
/mnt/d/RAG/
├── .env                        ← All API keys and endpoints (never commit)
├── .gitignore                  ← Ignore .env, venv, __pycache__
├── PROJECT_PLAN.md             ← This file
├── requirements.txt            ← Python dependencies
├── upload_documents.py          ← Uploads local documents to Azure Blob Storage
├── create_index.py              ← Creates the Azure AI Search index schema
├── ingest_documents.py          ← Downloads from Blob, extracts, chunks, embeds, uploads to Search
├── app.py                       ← Streamlit web UI (main entry point)
├── venv/                       ← Python virtual environment
└── sample_documents/   ← Local source documents (uploaded to Blob)
    └── synthetic_documents/
        ├── pdfs/               ← 19 PDFs (reports, policies, manuals, papers)
        ├── csvs/               ← 5 CSVs (customers, employees, inventory, sales, financials)
        └── images/             ← 10 PNGs (invoices, charts, org chart, flowchart)
```

---

## Implementation Phases

### Phase 1: Azure Infrastructure
Provision the required Azure services: Blob Storage (document store), Document Intelligence (OCR), and AI Search (vector index). Configure all API keys and endpoints in `.env`.

### Phase 2: Environment Setup
Create a Python virtual environment and install dependencies from `requirements.txt`.

### Phase 3: Document Ingestion
Upload source documents to Blob Storage, create the AI Search index schema, then run the ingestion pipeline — which extracts text (OCR for PDFs/images, pandas for CSVs), chunks it, generates embeddings via Azure OpenAI, and indexes everything into AI Search.

### Phase 4: Chatbot & UI
Implement hybrid search (vector + keyword) to retrieve relevant chunks, pass them to GPT-4o for grounded answer generation, and serve the interface via Streamlit.

### Phase 5: Testing
Validate retrieval across all document types (PDF, CSV, image), cross-document queries, and out-of-scope questions.

---

## Execution Order

```
1. python upload_documents.py   ← Upload documents to Blob Storage
2. python create_index.py       ← Create AI Search index schema
3. python ingest_documents.py   ← Extract, chunk, embed, and index documents
4. streamlit run app.py         ← Launch the web UI
```

---

## Data Flow

```
INGEST (one-time):
  Local files  → Blob Storage
  PDF / Image  → Document Intelligence (OCR) → text
  CSV          → pandas                      → text
  text         → chunking (800w, 200w overlap) → chunks
  chunks       → Azure OpenAI embeddings     → vectors
  vectors + metadata                         → AI Search index

QUERY (per request):
  User question → embedding → AI Search (hybrid) → top chunks
  chunks + question         → GPT-4o             → cited answer
```

---

## Estimated Costs

| Service | Tier | Notes |
|---|---|---|
| Blob Storage | Free (5 GB / 12 months) | Well within limits |
| Document Intelligence | Free F0 (500 pages/month) | Sufficient for testing |
| AI Search | Free (50 MB, 3 indexes) | Sufficient for testing |
| Azure OpenAI Embeddings | ~$0.02 / 1M tokens | Negligible |
| OpenAI GPT-4o | ~$2.50–$10 / 1M tokens | Cents per conversation |

---

## Potential Enhancements
- Multi-turn conversation history
- In-app document upload with automatic re-ingestion
- User authentication
- Deployment to Azure App Service
