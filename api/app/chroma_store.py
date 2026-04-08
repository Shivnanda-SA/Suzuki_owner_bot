from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    )


def chroma_persist_settings() -> ChromaSettings:
    """Same shape as langchain_community.vectorstores.Chroma uses for persist_directory."""
    cs = ChromaSettings(is_persistent=True, anonymized_telemetry=False)
    cs.persist_directory = settings.chroma_persist_dir
    return cs


def get_vectorstore() -> Chroma:
    _ensure_dir(settings.chroma_persist_dir)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
        client_settings=chroma_persist_settings(),
    )


def delete_collection() -> None:
    _ensure_dir(settings.chroma_persist_dir)
    # Must match LangChain Chroma client settings; PersistentClient() + from_texts() hits
    # "different settings" for the same persist path (chromadb singleton).
    client = chromadb.Client(chroma_persist_settings())
    try:
        client.delete_collection(settings.chroma_collection)
    except Exception as e:
        logger.debug("delete_collection: %s", e)
