import os
import io
import hashlib
import time
import pandas as pd
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.search.documents import SearchClient
from openai import AzureOpenAI

load_dotenv()

# --- Clients ---
blob_service = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
container_client = blob_service.get_container_client(os.getenv("BLOB_CONTAINER_NAME"))

doc_intel_client = DocumentIntelligenceClient(
    endpoint=os.getenv("DOC_INTELLIGENCE_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("DOC_INTELLIGENCE_KEY")),
)

search_client = SearchClient(
    endpoint=os.getenv("SEARCH_ENDPOINT"),
    index_name=os.getenv("SEARCH_INDEX_NAME"),
    credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)
embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")


# --- Text Extraction ---
def extract_text_doc_intelligence(blob_bytes, blob_name):
    """Extract text from PDF or image using Azure Document Intelligence."""
    print(f"  Extracting text with Document Intelligence...")
    poller = doc_intel_client.begin_analyze_document(
        "prebuilt-read",
        io.BytesIO(blob_bytes),
        content_type="application/octet-stream",
    )
    result = poller.result()
    return result.content or ""


def extract_text_csv(blob_bytes, blob_name):
    """Extract text from CSV using pandas."""
    print(f"  Parsing CSV with pandas...")
    df = pd.read_csv(io.BytesIO(blob_bytes))
    lines = []
    for i, row in df.iterrows():
        row_text = ", ".join(f"{col}={val}" for col, val in row.items())
        lines.append(f"Row {i + 1}: {row_text}")
    return "\n".join(lines)


# --- Chunking ---
def chunk_text(text, chunk_size=800, overlap=200):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# --- Embedding ---
def get_embeddings(texts):
    """Get embeddings for a list of texts from Azure OpenAI."""
    response = openai_client.embeddings.create(input=texts, model=embedding_deployment)
    return [item.embedding for item in response.data]


# --- Main Pipeline ---
def make_id(source_file, chunk_index):
    """Generate a stable document ID."""
    raw = f"{source_file}_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest():
    blobs = list(container_client.list_blobs())
    print(f"Found {len(blobs)} blobs in container.\n")

    all_documents = []

    for blob in blobs:
        name = blob.name
        print(f"Processing: {name}")

        # Download blob
        blob_data = container_client.download_blob(name).readall()

        # Determine file type and extract text
        lower_name = name.lower()
        if lower_name.endswith(".pdf") or lower_name.endswith(".png") or lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
            file_type = "pdf" if lower_name.endswith(".pdf") else "image"
            text = extract_text_doc_intelligence(blob_data, name)
        elif lower_name.endswith(".csv"):
            file_type = "csv"
            text = extract_text_csv(blob_data, name)
        else:
            print(f"  Skipping unsupported file type.")
            continue

        if not text.strip():
            print(f"  No text extracted, skipping.")
            continue

        # Chunk
        chunks = chunk_text(text)
        print(f"  Extracted {len(text)} chars → {len(chunks)} chunks")

        # Build documents for search index
        for i, chunk in enumerate(chunks):
            all_documents.append({
                "id": make_id(name, i),
                "content": chunk,
                "source_file": name,
                "file_type": file_type,
                "chunk_index": i,
            })

    # Embed and upload in batches
    batch_size = 16  # embedding batch size
    print(f"\nEmbedding and uploading {len(all_documents)} chunks...")

    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i : i + batch_size]
        texts = [doc["content"] for doc in batch]

        embeddings = get_embeddings(texts)
        for doc, emb in zip(batch, embeddings):
            doc["embedding"] = emb

        search_client.upload_documents(documents=batch)
        print(f"  Uploaded batch {i // batch_size + 1} ({len(batch)} chunks)")
        time.sleep(0.5)  # rate limit buffer

    print(f"\nDone! {len(all_documents)} chunks indexed in '{os.getenv('SEARCH_INDEX_NAME')}'.")


if __name__ == "__main__":
    ingest()
