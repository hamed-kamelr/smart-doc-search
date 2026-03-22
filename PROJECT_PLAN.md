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

## Step-by-Step Implementation Plan

### Phase 1: Azure Portal Setup

#### Step 1.1 — Create Azure Storage Account + Blob Container
- **Where**: Azure Portal → search "Storage accounts" → Create
- **What it does**: Azure Blob Storage is cloud file storage. It holds your original documents (PDFs, CSVs, images) in the cloud so they are accessible from anywhere — not tied to your local machine. This is essential for production deployment and allows multiple services to access the same files.
- **Settings**:
  - Resource group: `rg-rag-chatbot` (create new)
  - Storage account name: `ragchatbotstorage1` (globally unique, lowercase, no hyphens)
  - Region: same as your OpenAI resource
  - Performance: Standard
  - Redundancy: LRS (Locally Redundant Storage) — cheapest, fine for dev
- **After creation**:
  1. Go to the resource → **Containers** (left sidebar under "Data storage")
  2. Click **+ Container** → Name: `documents` → Public access level: **Private**
  3. Go to **Access keys** (left sidebar under "Security + networking") → Copy **Connection string** (not just the key — you need the full connection string)

#### Step 1.2 — Create Azure AI Document Intelligence
- **Where**: Azure Portal → search "Document Intelligence" → Create
- **What it does**: Uses OCR and AI models to extract text, tables, and structure from PDFs and images. Without this, your images (invoices, charts) would be unsearchable binary files.
- **Settings**:
  - Resource group: `rg-rag-chatbot`
  - Region: same as your OpenAI resource
  - Name: `doc-intelligence-chatbot1`
  - Pricing tier: Free (F0) for testing
- **After creation**: Copy **Key 1** and **Endpoint** from "Keys and Endpoint" page

#### Step 1.3 — Create Azure AI Search
- **Where**: Azure Portal → search "AI Search" → Create
- **What it does**: Acts as your vector database. It stores document chunks alongside their vector embeddings and enables fast semantic + keyword search. When a user asks a question, this service finds the most relevant document chunks in milliseconds.
- **Settings**:
  - Resource group: `rg-rag-chatbot`
  - Service name: `search-rag-chatbot1`
  - Region: same as other resources
  - Pricing tier: Free for testing, Basic for larger datasets
- **After creation**: Copy **Admin Key** from "Keys" page and **URL** from Overview

#### Step 1.4 — Get OpenAI API Key
- **Where**: https://platform.openai.com → API Keys → Create Key
- **What it does**: Authenticates your chatbot to call GPT-4o for generating answers

---

### Phase 2: Local Environment Setup

#### Step 2.1 — Create Python Virtual Environment
```bash
cd /mnt/d/RAG
python3 -m venv venv
source venv/bin/activate
```
- **What it does**: Isolates project dependencies so they don't conflict with other Python projects on your system

#### Step 2.2 — Install Dependencies
```bash
pip install azure-ai-documentintelligence azure-search-documents azure-storage-blob openai python-dotenv pandas streamlit
```
- **Package purposes**:
  - `azure-storage-blob` — SDK to upload/download files to/from Azure Blob Storage
  - `azure-ai-documentintelligence` — SDK to call Document Intelligence for OCR
  - `azure-search-documents` — SDK to create indexes and upload/search documents
  - `openai` — SDK to call Azure OpenAI embeddings and OpenAI GPT-4o for answers
  - `python-dotenv` — Loads secrets from .env file into environment variables
  - `pandas` — Reads and processes CSV files into structured text
  - `streamlit` — Web UI framework for the chatbot interface

#### Step 2.3 — Configure .env File
- **What it does**: Centralizes all API keys and endpoints in one file, loaded at runtime
- **Keys needed**:
  - `AZURE_STORAGE_CONNECTION_STRING` + `BLOB_CONTAINER_NAME` (from Step 1.1)
  - `DOC_INTELLIGENCE_ENDPOINT` + `DOC_INTELLIGENCE_KEY` (from Step 1.2)
  - `SEARCH_ENDPOINT` + `SEARCH_ADMIN_KEY` + `SEARCH_INDEX_NAME` (from Step 1.3)
  - `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_KEY` + deployment name + API version (already have)
  - `OPENAI_API_KEY` (from Step 1.4)

---

### Phase 3: Upload Documents to Blob Storage

#### Step 3.1 — Write `upload_to_blob.py`
- **What it does**: Scans your local `sample_documents/synthetic_documents/` folder and uploads every file (PDFs, CSVs, images) to the `documents` container in Azure Blob Storage
- **Blob naming convention**: Files are uploaded with their subfolder path preserved, e.g.:
  - `pdfs/annual_report_1.pdf`
  - `csvs/customer_accounts.csv`
  - `images/invoice_1.png`
- **Why preserve folder structure**: Makes it easy to filter by file type later and keeps the container organized
- **Run once**: `python upload_to_blob.py`
- **Verification**: After running, go to Azure Portal → Storage Account → Containers → `documents` to see all uploaded files

---

### Phase 4: Create Search Index

#### Step 4.1 — Write `search_index.py`
- **What it does**: Defines the schema for your Azure AI Search index — what fields each document chunk has and how vector search is configured
- **Key concepts**:
  - Each chunk gets: `id`, `content` (text), `source_file`, `file_type`, `chunk_index`, `embedding` (1536-dim vector)
  - Uses **HNSW algorithm** (Hierarchical Navigable Small World) for fast approximate nearest neighbor search
  - 1536 dimensions matches `text-embedding-3-small` output
- **Run once**: `python search_index.py`

---

### Phase 5: Document Ingestion Pipeline

#### Step 5.1 — Write `ingest.py` with Blob download + text extraction
- **Blob download**: Lists all blobs in the `documents` container and downloads each file to a temporary local path (or streams it in memory) for processing
- **PDF & Image extraction**: Sends files to Azure Document Intelligence using the `prebuilt-read` model. This model handles multi-page PDFs, tables, headers, and OCR for images (printed/handwritten text, invoices, charts)
- **CSV extraction**: Uses pandas to read CSVs and convert each row into readable text format like `"Row 1: column1=value1, column2=value2"`. This preserves structured data in a format the embedding model and LLM can understand

#### Step 5.2 — Add chunking logic
- **What it does**: Splits extracted text into overlapping chunks of ~800 words with 200-word overlap
- **Why chunk**: Embedding models have token limits (8191 tokens). Smaller chunks also mean more precise retrieval — search finds the exact relevant paragraph, not a whole 50-page document
- **Why overlap**: Prevents losing information at chunk boundaries. If a key sentence spans two chunks, overlap ensures both chunks contain it

#### Step 5.3 — Add embedding and upload logic
- **Embedding**: Each chunk is sent to Azure OpenAI `text-embedding-3-small`, which returns a 1536-dimensional vector capturing the semantic meaning of the text
- **Upload**: Chunks (with text + vector + metadata) are uploaded to Azure AI Search in batches of 100
- **Run once**: `python ingest.py` (takes a few minutes for all documents)

---

### Phase 6: Build the RAG Chatbot

#### Step 6.1 — Write `chatbot.py` with retrieval logic (HYBRID search)
- **What it does**: Takes the user's question, converts it to a vector using the same embedding model, and searches Azure AI Search
- **Hybrid search**: Combines vector search (finds semantically similar content) with keyword search (catches exact matches like names, IDs, product codes). This gives better results than either alone
- **Returns**: Top 5 most relevant document chunks with scores

#### Step 6.2 — Add GPT-4o generation logic
- **What it does**: Sends the retrieved chunks + user question to GPT-4o with a system prompt that instructs it to:
  - Only use information from the provided context (prevents hallucination)
  - Cite source files in the answer
  - Say "I don't know" if context is insufficient
  - Be precise with numbers from CSVs
- **Model**: `gpt-4o` (fast, capable, cost-effective)

#### Step 6.3 — Add interactive chat loop
- **What it does**: Provides a terminal-based chat interface where users type questions and get answers with source citations

---

### Phase 7: Testing

#### Step 7.1 — Test PDF retrieval
- Ask: "What is the remote work policy?"
- Expected: Answer from `policy_remote_work.pdf` with citation

#### Step 7.2 — Test CSV retrieval
- Ask: "Show me the top 5 customers by account balance"
- Expected: Answer from `customer_accounts.csv` with specific numbers

#### Step 7.3 — Test image/OCR retrieval
- Ask: "What does the revenue bar chart show?"
- Expected: Answer from `chart_bar_revenue.png` based on OCR-extracted text

#### Step 7.4 — Test cross-document questions
- Ask: "Summarize all company policies"
- Expected: Answer combining multiple policy PDFs with citations

#### Step 7.5 — Test "I don't know" behavior
- Ask: "What is the weather today?"
- Expected: GPT-4o says it doesn't have that information in the documents

---

## Execution Order Summary

```
1. python upload_documents.py    ← Upload documents to Azure Blob Storage
2. python create_index.py       ← Create the search index schema (run once)
3. python ingest_documents.py   ← Download from Blob → extract → chunk → embed → upload to Search
4. streamlit run app.py         ← Launch the web UI!
```

---

## Data Flow Summary

```
UPLOAD (one-time, Phase 3):
  Local files → Azure Blob Storage ("documents" container)

INGEST (one-time, Phase 5):
  Blob Storage → download files
  PDF/Image    → Azure Document Intelligence (OCR) → raw text
  CSV          → pandas parsing                    → raw text
  raw text     → chunk (800 words, 200 overlap)    → chunks
  chunks       → Azure OpenAI embedding             → 1536-dim vectors
  vectors + text + metadata                         → Azure AI Search index

QUERY (every question, Phase 6):
  User question → Azure OpenAI embedding            → query vector
  query vector  → Azure AI Search (hybrid)          → top 5 chunks
  chunks + question → GPT-4o                        → grounded answer with citations
```

---

## Estimated Costs (Free Tier)

| Service | Free Tier Limit | Enough for this project? |
|---|---|---|
| Blob Storage (LRS) | 5 GB free for 12 months | Yes (our docs are ~1 MB total) |
| Document Intelligence (F0) | 500 pages/month | Yes (our docs are small) |
| AI Search (Free) | 50 MB storage, 3 indexes | Yes for testing |
| Azure OpenAI (text-embedding-3-small) | Pay-per-use (~$0.02/1M tokens) | Very cheap |
| OpenAI GPT-4o | Pay-per-use (~$2.50/$10 per 1M tokens) | A few cents per conversation |

---

## Next Steps After Basic Chatbot Works
- Add conversation history (multi-turn chat)
- Build a web UI (Streamlit or Gradio)
- Add document upload capability via the web UI (upload directly to Blob, trigger re-ingestion)
- Implement user authentication
- Deploy to Azure App Service
