import time
from functools import lru_cache
from typing import Any
from uuid import uuid4

import numpy as np

from langchain_community.vectorstores.utils import maximal_marginal_relevance
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import ConfigDict, Field

from .config import settings


def get_embeddings_and_dimension() -> tuple[Embeddings, int]:
    """OpenAI embeddings when available (notebook default); else HuggingFace."""
    if settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        return (
            OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
            ),
            1536,
        )

    import os

    from langchain_huggingface import HuggingFaceEmbeddings

    if settings.hf_token:
        os.environ["HF_TOKEN"] = settings.hf_token
    return (
        HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
        384,
    )


def _wait_for_index_ready(pc, index_name: str, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        description = pc.describe_index(index_name)
        if description.status.get("ready"):
            return
        time.sleep(2)
    raise TimeoutError(f"Pinecone index '{index_name}' was not ready within {timeout}s.")


def ensure_pinecone_index(pc, index_name: str, dimension: int) -> None:
    from pinecone import ServerlessSpec

    if index_name in pc.list_indexes().names():
        return

    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
    )
    _wait_for_index_ready(pc, index_name)


def pinecone_vector_count(pc, index_name: str) -> int:
    stats = pc.Index(index_name).describe_index_stats()
    return int(stats.get("total_vector_count", 0) or 0)


def _metadata_from_document(doc: Document) -> dict[str, Any]:
    metadata = {"text": doc.page_content}
    for key, value in (doc.metadata or {}).items():
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
    return metadata


def upsert_documents(index, embeddings: Embeddings, documents: list[Document]) -> None:
    texts = [doc.page_content for doc in documents]
    vectors = embeddings.embed_documents(texts)
    payload = []
    for doc, values in zip(documents, vectors):
        payload.append(
            {
                "id": str(uuid4()),
                "values": values,
                "metadata": _metadata_from_document(doc),
            }
        )

    batch_size = 100
    for start in range(0, len(payload), batch_size):
        index.upsert(vectors=payload[start : start + batch_size])


def _matches_to_documents(matches: list[dict[str, Any]]) -> list[Document]:
    documents: list[Document] = []
    for match in matches:
        metadata = dict(match.get("metadata") or {})
        page_content = metadata.pop("text", "")
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


class PineconeMMRRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: Any
    embeddings: Embeddings
    k: int = 2
    fetch_k: int = 8
    lambda_mult: float = 0.8

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        query_vector = np.array(self.embeddings.embed_query(query), dtype=np.float32)
        response = self.index.query(
            vector=query_vector.tolist(),
            top_k=self.fetch_k,
            include_metadata=True,
        )
        matches = response.get("matches", [])
        if not matches:
            return []

        documents = _matches_to_documents(matches)
        if len(documents) <= self.k:
            return documents

        candidate_vectors = np.array(
            self.embeddings.embed_documents([doc.page_content for doc in documents]),
            dtype=np.float32,
        )
        selected = maximal_marginal_relevance(
            query_vector,
            candidate_vectors,
            k=self.k,
            lambda_mult=self.lambda_mult,
        )
        return [documents[i] for i in selected]


class PineconeVectorStore:
    def __init__(self, index, embeddings: Embeddings):
        self.index = index
        self.embeddings = embeddings

    def as_retriever(self, search_type: str = "mmr", search_kwargs: dict | None = None) -> PineconeMMRRetriever:
        search_kwargs = search_kwargs or {}
        if search_type != "mmr":
            raise ValueError("Only MMR retrieval is supported for the Pinecone vector store.")
        return PineconeMMRRetriever(
            index=self.index,
            embeddings=self.embeddings,
            k=search_kwargs.get("k", settings.rag_k),
            fetch_k=search_kwargs.get("fetch_k", settings.rag_fetch_k),
            lambda_mult=search_kwargs.get("lambda_mult", settings.rag_lambda_mult),
        )


@lru_cache(maxsize=1)
def get_pinecone_vectorstore() -> PineconeVectorStore:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required for RAG. Set it in your .env file.")

    from pinecone import Pinecone

    embeddings, dimension = get_embeddings_and_dimension()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_index_name

    ensure_pinecone_index(pc, index_name, dimension)
    index = pc.Index(index_name)

    if pinecone_vector_count(pc, index_name) == 0:
        from .knowledge_base import load_and_split_knowledge_base_documents

        upsert_documents(index, embeddings, load_and_split_knowledge_base_documents())

    return PineconeVectorStore(index=index, embeddings=embeddings)
