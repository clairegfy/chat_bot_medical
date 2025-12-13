from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from .headache_assistants.dialogue import handle_user_message
from .headache_assistants.models import ChatMessage


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
