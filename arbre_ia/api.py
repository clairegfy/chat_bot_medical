from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List

from .headache_assistants.dialogue import handle_user_message, get_session_info
from .headache_assistants.models import ChatMessage
from .headache_assistants.prescription import _format_prescription


app = FastAPI(title="API Arbre IA – Céphalées")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== SCHEMAS =========

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: List[dict] = []  # [{role, content}]

class ChatResponseAPI(BaseModel):
    session_id: Optional[str]
    message: str
    requires_more_info: bool
    dialogue_complete: bool
    imaging_recommendation: Optional[dict] = None


# ======== ENDPOINT =========

@app.post("/chat", response_model=ChatResponseAPI)
def chat(req: ChatRequest):
    # convertir l'historique en ChatMessage
    history_msgs = [
        ChatMessage(role=h["role"], content=h["content"])
        for h in req.history
    ]

    user_msg = ChatMessage(role="user", content=req.message)

    response = handle_user_message(
        history=history_msgs,
        new_message=user_msg,
        session_id=req.session_id
    )

    return {
        "session_id": response.session_id,
        "message": response.message,
        "requires_more_info": response.requires_more_info,
        "dialogue_complete": response.dialogue_complete,
        "imaging_recommendation": (
            response.imaging_recommendation.model_dump()
            if response.imaging_recommendation
            else None
        ),
    }

@app.get("/")
def root():
    return {"status": "ok", "message": "API Arbre IA en fonctionnement"}


# ======== ENDPOINT ORDONNANCE =========

class PrescriptionRequest(BaseModel):
    session_id: str
    doctor_name: str = "Dr. [NOM]"

@app.post("/prescription")
def generate_prescription_endpoint(req: PrescriptionRequest):
    """Génère une ordonnance à partir d'une session de dialogue terminée."""
    session_data = get_session_info(req.session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session introuvable")

    case = session_data.get("current_case")
    if not case:
        raise HTTPException(status_code=400, detail="Aucun cas clinique dans cette session")

    # Récupérer la recommandation en recalculant (ou depuis le cache si disponible)
    from .headache_assistants.rules_engine import decide_imaging
    try:
        recommendation = decide_imaging(case)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul de la recommandation: {e}")

    # Générer le contenu de l'ordonnance
    prescription_text = _format_prescription(case, recommendation, req.doctor_name)

    return PlainTextResponse(content=prescription_text, media_type="text/plain; charset=utf-8")


# ======== ENDPOINT LOG SESSION =========

@app.get("/session-log/{session_id}")
def get_session_log(session_id: str):
    """Récupère le log détaillé d'une session de dialogue."""
    session_data = get_session_info(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session introuvable")

    case = session_data.get("current_case")

    # Construire le log détaillé
    log_data = {
        "session_id": session_id,
        "message_count": session_data.get("message_count", 0),
        "asked_fields": session_data.get("asked_fields", []),
        "last_asked_field": session_data.get("last_asked_field"),
        "extraction_metadata": session_data.get("extraction_metadata", {}),
        "special_patterns_detected": session_data.get("accumulated_special_patterns", []),
        "case_data": case.model_dump() if case else None,
    }

    # Si le cas existe, ajouter l'analyse des red flags
    if case:
        log_data["analysis"] = {
            "has_red_flags": case.has_red_flags(),
            "is_emergency": case.is_emergency(),
            "profile": case.profile,
            "onset": case.onset,
        }

    return log_data
