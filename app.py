import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_clients():
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from openai import AzureOpenAI, OpenAI

    search = SearchClient(
        endpoint=os.getenv("SEARCH_ENDPOINT"),
        index_name=os.getenv("SEARCH_INDEX_NAME"),
        credential=AzureKeyCredential(os.getenv("SEARCH_ADMIN_KEY")),
    )
    azure_oai = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return search, azure_oai, oai

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided document context.

Rules:
- Only use information from the provided context to answer questions.
- Always cite the source file(s) in your answer (e.g. [Source: pdfs/policy_remote_work.pdf]).
- If the context does not contain enough information to answer, say "I don't have enough information in the documents to answer that."
- Be precise with numbers, especially from CSV data.
- Keep answers clear and concise.
- Use markdown formatting for better readability (bullet points, bold, headers where appropriate)."""


def hybrid_search(query, top_k=5):
    from azure.search.documents.models import VectorizedQuery

    search_client, azure_openai_client, _ = get_clients()
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    response = azure_openai_client.embeddings.create(input=[query], model=embedding_deployment)
    query_vector = response.data[0].embedding

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )

    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top_k,
        select=["content", "source_file", "file_type", "chunk_index"],
    )

    chunks = []
    for result in results:
        chunks.append({
            "content": result["content"],
            "source_file": result["source_file"],
            "file_type": result["file_type"],
            "score": result["@search.score"],
        })
    return chunks


def generate_answer_stream(question, chunks):
    _, _, openai_client = get_clients()

    context = "\n\n---\n\n".join(
        f"[Source: {c['source_file']}]\n{c['content']}" for c in chunks
    )

    return openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.3,
        max_tokens=1024,
        stream=True,
    )


def get_file_icon(source):
    if source.endswith(".pdf"):
        return "red", "PDF"
    elif source.endswith(".csv"):
        return "green", "CSV"
    else:
        return "blue", "IMG"


def get_blob_url(source_file):
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from datetime import datetime, timedelta, timezone

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER_NAME")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    account_name = blob_service_client.account_name
    account_key = blob_service_client.credential.account_key

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=source_file,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    return f"https://{account_name}.blob.core.windows.net/{container_name}/{source_file}?{sas_token}"


# --- Page Config ---
st.set_page_config(
    page_title="DocChat",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS ---
st.markdown("""
<style>
    /* Hide defaults */
    #MainMenu, footer, header { visibility: hidden; }

    /* Main container */
    .block-container {
        max-width: 900px !important;
        padding-top: 2rem !important;
    }

    /* Logo & Title */
    .logo-area {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 0.5rem 0 0.2rem 0;
    }
    .logo-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: white;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
    .logo-text {
        font-size: 1.75rem;
        font-weight: 800;
        color: #1e1b4b;
        letter-spacing: -0.5px;
    }
    .logo-sub {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 400;
        margin-top: -2px;
    }

    /* Divider */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        margin: 1rem 0 1.5rem 0;
    }

    /* Welcome */
    .welcome-box {
        background: linear-gradient(135deg, #f8faff 0%, #f0f0ff 100%);
        border: 1px solid #e0e7ff;
        border-radius: 20px;
        padding: 2.5rem 2rem;
        text-align: center;
        margin: 1.5rem 0 2rem 0;
    }
    .welcome-emoji {
        font-size: 3rem;
        margin-bottom: 0.8rem;
    }
    .welcome-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e1b4b;
        margin-bottom: 0.4rem;
    }
    .welcome-desc {
        font-size: 0.95rem;
        color: #64748b;
        max-width: 500px;
        margin: 0 auto 1.5rem auto;
        line-height: 1.6;
    }

    /* Example cards */
    .examples-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.8rem;
    }
    .example-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        max-width: 600px;
        margin: 0 auto;
    }
    .example-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 0.85rem;
        color: #475569;
        text-align: left;
        transition: all 0.2s ease;
        cursor: default;
    }
    .example-card:hover {
        border-color: #6366f1;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
    }
    .example-icon {
        margin-right: 6px;
    }

    /* Source chips */
    .sources-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 12px;
    }
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 4px 12px 4px 6px;
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    a.chip:hover {
        border-color: #6366f1;
        background: #f0f0ff;
        color: #4338ca;
        box-shadow: 0 2px 6px rgba(99, 102, 241, 0.15);
    }
    .chip-badge {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 8px;
        font-size: 0.65rem;
        font-weight: 700;
        color: white;
    }
    .chip-badge.red { background: #ef4444; }
    .chip-badge.green { background: #22c55e; }
    .chip-badge.blue { background: #3b82f6; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #fafafe 0%, #f5f3ff 100%);
    }
    .sidebar-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e1b4b;
        margin-bottom: 0.3rem;
    }
    .sidebar-desc {
        font-size: 0.82rem;
        color: #64748b;
        line-height: 1.5;
        margin-bottom: 1rem;
    }

    /* Stat cards */
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 8px;
    }
    .stat-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 8px;
        text-align: center;
    }
    .stat-num {
        font-size: 1.4rem;
        font-weight: 800;
        color: #6366f1;
    }
    .stat-lbl {
        font-size: 0.7rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stats-row {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
    }

    /* Powered by */
    .powered-by {
        text-align: center;
        font-size: 0.72rem;
        color: #cbd5e1;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("""
    <div class="sidebar-title">Settings</div>
    <div class="sidebar-desc">Adjust how DocChat searches and responds.</div>
    """, unsafe_allow_html=True)

    top_k = st.slider("Number of results", min_value=1, max_value=10, value=5, help="How many document chunks to retrieve per question")

    st.markdown("---")

    st.markdown('<div class="sidebar-title">Document Library</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="stats-grid">
        <div class="stat-box"><div class="stat-num">33</div><div class="stat-lbl">Documents</div></div>
        <div class="stat-box"><div class="stat-num">150</div><div class="stat-lbl">Chunks</div></div>
    </div>
    <div class="stats-row">
        <div class="stat-box"><div class="stat-num">18</div><div class="stat-lbl">PDFs</div></div>
        <div class="stat-box"><div class="stat-num">5</div><div class="stat-lbl">CSVs</div></div>
        <div class="stat-box"><div class="stat-num">10</div><div class="stat-lbl">Images</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if st.button("Clear Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("""
    <div class="powered-by">
        Powered by Azure AI Search + GPT-4o
    </div>
    """, unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="logo-area">
    <div class="logo-icon">D</div>
    <div>
        <div class="logo-text">DocChat</div>
        <div class="logo-sub">AI-powered document assistant</div>
    </div>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# --- Welcome Screen ---
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-box">
        <div class="welcome-emoji">&#128218;</div>
        <div class="welcome-title">What would you like to know?</div>
        <div class="welcome-desc">
            I can search through your PDFs, spreadsheets, and images to find answers instantly.
            Just type your question below or click an example.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;font-size:0.75rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem;">Try asking</div>', unsafe_allow_html=True)

    examples = [
        ("What is the remote work policy?", "What is the remote work policy?"),
        ("Show me top customers by balance", "Show me top customers by balance"),
        ("What does the revenue chart show?", "What does the revenue chart show?"),
        ("Summarize all company policies", "Summarize all company policies"),
    ]

    col1, col2 = st.columns(2)
    for i, (label, query) in enumerate(examples):
        with col1 if i % 2 == 0 else col2:
            if st.button(label, key=f"example_{i}", use_container_width=True):
                st.session_state.pending_question = query
                st.rerun()

# --- Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=None):
        st.markdown(msg["content"])
        if msg.get("sources"):
            chips_html = ""
            for s in msg["sources"]:
                color, label = get_file_icon(s)
                name = s.split("/")[-1]
                url = get_blob_url(s)
                chips_html += f'<a href="{url}" target="_blank" class="chip"><span class="chip-badge {color}">{label}</span>{name}</a>'
            st.markdown(f'<div class="sources-row">{chips_html}</div>', unsafe_allow_html=True)

# --- Chat Input ---
question = st.chat_input("Ask anything about your documents...")

if st.session_state.pending_question:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=None):
        st.markdown(question)

    with st.chat_message("assistant", avatar=None):
        with st.spinner("Searching documents..."):
            chunks = hybrid_search(question, top_k=top_k)

        if not chunks:
            answer = "I couldn't find any relevant documents for your question. Try rephrasing or asking something else."
            st.markdown(answer)
            sources = []
        else:
            stream = generate_answer_stream(question, chunks)
            answer = st.write_stream(
                chunk.choices[0].delta.content or ""
                for chunk in stream
                if chunk.choices[0].delta.content is not None
            )
            sources = list(dict.fromkeys(c["source_file"] for c in chunks))

            if sources:
                chips_html = ""
                for s in sources:
                    color, label = get_file_icon(s)
                    name = s.split("/")[-1]
                    url = get_blob_url(s)
                    chips_html += f'<a href="{url}" target="_blank" class="chip"><span class="chip-badge {color}">{label}</span>{name}</a>'
                st.markdown(f'<div class="sources-row">{chips_html}</div>', unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
