"""LangGraph RAG: retrieve → generate."""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.chroma_store import get_vectorstore
from app.config import settings
from app.schemas import ChatResponse, Citation, CTA

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Suzuki Owner Support for India (motorcycles & scooters).
Answer ONLY using the CONTEXT snippets. If context is insufficient, say what is missing and suggest contacting an authorized Suzuki service center or official support — do not invent warranty/service promises.
Return STRICT JSON with keys: intent, answer, confidence (high|medium|low), citations_used (array of integers 0-based index into context order), needs_handoff (boolean), cta (null or {type, label}), disclaimer (null or short text).
Intents: manual_query, service_schedule, warranty_query, service_center_lookup, service_booking_help, service_campaign_help, support_contact, escalation, general.
"""

STRUCTURED_SUFFIX = "\n\nRespond with valid JSON only, no markdown."


class RAGState(TypedDict, total=False):
    message: str
    vehicle_model: str | None
    context: str
    meta: list[dict[str, Any]]
    llm_raw: str
    response: ChatResponse


def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def _documents_to_context(docs: list[Document]) -> tuple[str, list[dict[str, Any]]]:
    blocks: list[str] = []
    meta: list[dict[str, Any]] = []
    for i, doc in enumerate(docs):
        m = doc.metadata
        sec = m.get("section_title") or ""
        blocks.append(
            f"[{i}] ({m.get('doc_type', '')}) {m.get('title', '')}"
            + (f" — {sec}" if sec else "")
            + f"\n{doc.page_content}"
        )
        meta.append({"index": i, "doc": m, "chunk_text": doc.page_content})
    return "\n\n".join(blocks), meta


def retrieve_node(state: RAGState) -> RAGState:
    vs = get_vectorstore()
    q = state.get("message") or ""
    vm = state.get("vehicle_model")
    if vm:
        q = f"[Vehicle model hint: {vm}] {q}"
    docs = vs.similarity_search(q, k=8)
    if not docs:
        out = ChatResponse(
            intent="general",
            answer=(
                "I do not have indexed owner-support content yet. "
                "Please run the ingestion script or contact Suzuki support via the official website."
            ),
            citations=[],
            confidence="low",
            cta=CTA(
                type="open_support",
                label="Visit Suzuki India",
                payload={"url": settings.suzuki_source_base_url},
            ),
            needs_handoff=True,
            disclaimer="Knowledge base is empty.",
        )
        return {"context": "", "meta": [], "response": out, "llm_raw": ""}

    ctx, meta = _documents_to_context(docs)
    return {"context": ctx, "meta": meta, "llm_raw": ""}


def generate_node(state: RAGState) -> RAGState:
    if state.get("response") is not None:
        return {}

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=0.2,
    )
    message = state.get("message") or ""
    context_str = state.get("context") or ""
    meta = state.get("meta") or []

    user_content = f"USER QUESTION:\n{message}\n\nCONTEXT:\n{context_str}{STRUCTURED_SUFFIX}"
    msg = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]
    )
    raw = msg.content if isinstance(msg.content, str) else str(msg.content)

    try:
        data = _parse_llm_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("LLM JSON parse failed: %s", e)
        data = {
            "intent": "general",
            "answer": raw[:2000],
            "confidence": "low",
            "citations_used": [],
            "needs_handoff": False,
            "cta": None,
            "disclaimer": None,
        }

    used = data.get("citations_used") or []
    citations: list[Citation] = []
    if isinstance(used, list):
        for idx in used:
            if isinstance(idx, int) and 0 <= idx < len(meta):
                m = meta[idx]["doc"]
                ch = meta[idx]["chunk_text"]
                excerpt = (ch[:280] + "…") if len(ch) > 280 else ch
                citations.append(
                    Citation(
                        title=str(m.get("title", "")),
                        doc_type=str(m.get("doc_type", "")),
                        source_url=str(m.get("source_url", "")),
                        section_title=m.get("section_title") or None,
                        excerpt=excerpt,
                    )
                )

    if not citations:
        for m in meta[:3]:
            doc = m["doc"]
            ch = m["chunk_text"]
            excerpt = (ch[:220] + "…") if len(ch) > 220 else ch
            citations.append(
                Citation(
                    title=str(doc.get("title", "")),
                    doc_type=str(doc.get("doc_type", "")),
                    source_url=str(doc.get("source_url", "")),
                    section_title=doc.get("section_title") or None,
                    excerpt=excerpt,
                )
            )

    cta = None
    raw_cta = data.get("cta")
    if isinstance(raw_cta, dict) and raw_cta.get("type") and raw_cta.get("label"):
        cta = CTA(type=str(raw_cta["type"]), label=str(raw_cta["label"]), payload=raw_cta.get("payload"))

    response = ChatResponse(
        intent=str(data.get("intent", "general")),
        answer=str(data.get("answer", "")).strip() or "No answer generated.",
        citations=citations,
        confidence=str(data.get("confidence", "medium")),
        cta=cta,
        needs_handoff=bool(data.get("needs_handoff", False)),
        disclaimer=data.get("disclaimer"),
    )
    return {"response": response, "llm_raw": raw}


def build_rag_graph():
    g = StateGraph(RAGState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


_rag_app = None


def get_rag_graph():
    global _rag_app
    if _rag_app is None:
        _rag_app = build_rag_graph()
    return _rag_app
