"""Build or verify the RAG knowledge base from the airline FAQ PDF."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.chains import get_rag_retriever
from app.pinecone_store import get_pinecone_vectorstore
from app.config import settings


def main() -> None:
    pdf_path = Path(settings.knowledge_base_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Knowledge base PDF not found: {pdf_path}")

    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required. Add it to your .env file.")

    print(f"Building RAG index from: {pdf_path.name}")
    print(f"Pinecone index: {settings.pinecone_index_name}")
    get_pinecone_vectorstore()
    retriever = get_rag_retriever()
    sample_docs = retriever.invoke("baggage policy")

    print(f"RAG index ready (Pinecone) with MMR retrieval (k={settings.rag_k}).")
    if sample_docs:
        print("Sample retrieved text:")
        print(sample_docs[0].page_content[:200].strip(), "...")


if __name__ == "__main__":
    main()
