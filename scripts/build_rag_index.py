"""Build or verify the RAG knowledge base from the airline FAQ PDF."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.chains import get_vectorstore
from app.config import settings


def main() -> None:
    pdf_path = Path(settings.knowledge_base_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Knowledge base PDF not found: {pdf_path}")

    print(f"Building RAG index from: {pdf_path.name}")
    vectorstore = get_vectorstore()
    sample_docs = vectorstore.similarity_search("baggage policy", k=1)
    store_type = type(vectorstore).__name__

    print(f"RAG index ready ({store_type}).")
    if sample_docs:
        print("Sample retrieved text:")
        print(sample_docs[0].page_content[:200].strip(), "...")


if __name__ == "__main__":
    main()
