import logging

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.ingest import run_ingest
from app.models import Feedback as FeedbackModel
from app.rag_service import ensure_session, run_chat
from app.schemas import ChatRequest, ChatResponse, FeedbackRequest, HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Suzuki Owner Support API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = "ok"
    except Exception as e:
        logger.exception("DB health check failed")
        db_ok = f"error: {e}"
    return HealthResponse(status="ok", database=db_ok)


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    try:
        sess = ensure_session(db, body.session_id, body.vehicle_model)
        out = run_chat(db, body.message, body.vehicle_model)
        out.session_id = sess.id
        return out
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("chat failed")
        raise HTTPException(status_code=500, detail="Chat processing failed") from e


@app.post("/feedback")
def feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    row = FeedbackModel(
        chat_id=body.chat_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "id": str(row.id)}


@app.post("/admin/reindex")
def reindex(
    clear: bool = False,
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
):
    if settings.admin_token and x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        result = run_ingest(clear=clear)
        return {"ok": True, **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
