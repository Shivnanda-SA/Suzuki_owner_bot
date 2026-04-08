import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.rag_graph import get_rag_graph
from app.schemas import ChatResponse

logger = logging.getLogger(__name__)


def run_chat(_db: Session, message: str, vehicle_model: str | None) -> ChatResponse:
    graph = get_rag_graph()
    out = graph.invoke(
        {
            "message": message,
            "vehicle_model": vehicle_model,
        }
    )
    resp = out.get("response")
    if resp is None:
        raise RuntimeError("RAG graph returned no response")
    return resp


def ensure_session(db: Session, session_id: UUID | None, vehicle_model: str | None):
    from app.models import ChatSession

    if session_id:
        s = db.get(ChatSession, session_id)
        if s:
            return s
    s = ChatSession(vehicle_model=vehicle_model)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s
