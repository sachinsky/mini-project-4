from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import settings


def load_and_split_knowledge_base_documents() -> list[Document]:
    pdf_path = Path(settings.knowledge_base_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Knowledge base PDF not found: {pdf_path}")

    loader = PyMuPDFLoader(str(pdf_path))
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
    return splitter.split_documents(docs)
