import json
import logging
import os
import uuid
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from app.chroma_store import chroma_persist_settings, delete_collection, get_embeddings
from app.config import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        parts.append(chunk.strip())
        start = end - overlap
    return [p for p in parts if p]


def load_seed_documents(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ingest_file(seed_path: Path, clear: bool = False) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required for ingestion")

    if clear:
        delete_collection()

    items = load_seed_documents(seed_path)
    embeddings = get_embeddings()

    texts: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    doc_count = 0
    for item in items:
        raw = item.get("content", "")
        sections = item.get("sections")
        if sections:
            chunks_data = [(s.get("title"), s.get("text", "")) for s in sections]
        else:
            splits = chunk_text(raw)
            chunks_data = [(item.get("title"), sp) for sp in splits]

        doc_count += 1
        base_url = item.get("source_url", settings.suzuki_source_base_url)
        title = item.get("title", "Untitled")
        doc_type = item.get("doc_type", "support")
        model_name = item.get("model") or ""

        for sec_title, txt in chunks_data:
            txt = (txt or "").strip()
            if not txt:
                continue
            texts.append(txt[:12000])
            metadatas.append(
                {
                    "source_url": base_url,
                    "title": title,
                    "doc_type": doc_type,
                    "section_title": sec_title or "",
                    "model_name": model_name,
                    "product_family": str(item.get("product_family") or ""),
                    "region": str(item.get("region") or "IN"),
                }
            )
            ids.append(str(uuid.uuid4()))

    if not texts:
        return {"documents": doc_count, "chunks": 0}

    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        ids=ids,
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
        client_settings=chroma_persist_settings(),
    )
    return {"documents": doc_count, "chunks": len(texts)}


def default_seed_path() -> Path:
    env = os.environ.get("SEED_DATA_PATH")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "data" / "seed" / "documents.json",
        here.parent / "data" / "seed" / "documents.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[0]


def run_ingest(clear: bool = False) -> dict:
    from app.database import Base, engine

    Base.metadata.create_all(bind=engine)
    path = default_seed_path()
    if not path.is_file():
        raise FileNotFoundError(f"Seed file not found: {path}")
    return ingest_file(path, clear=clear)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--clear", action="store_true")
    args = p.parse_args()
    out = run_ingest(clear=args.clear)
    logger.info("Ingest complete: %s", out)
