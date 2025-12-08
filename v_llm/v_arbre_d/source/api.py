from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .main import (
    analyse_texte_medical,
    decision_imagerie,
    get_contraindications_text,
)

app = FastAPI()

# CORS pour que React / Tauri puissent appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tu pourras restreindre plus tard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyseRequest(BaseModel):
    texte: str

class AnalyseResponse(BaseModel):
    f: dict
    decision: str
    contraindications: str

def _analyse_commune(texte: str) -> AnalyseResponse:
    """
    Logique commune : analyse + décision + contre-indications.
    Utilisée par tous les endpoints (/analyse, /, /chat).
    """
    f = analyse_texte_medical(texte)
    decision = decision_imagerie(f)
    contraindications = get_contraindications_text(f)
    return {
        "f": f,
        "decision": decision,
        "contraindications": contraindications,
    }

@app.get("/")
def root():
    """Petit endpoint de test."""
    return {"status": "ok", "message": "API arbre décisionnel OK"}


@app.post("/analyse", response_model=AnalyseResponse)
def analyse(req: AnalyseRequest):
    """Endpoint principal attendu par le frontend."""
    return _analyse_commune(req.texte)


@app.post("/", response_model=AnalyseResponse)
def analyse_racine(req: AnalyseRequest):
    """
    Alias : si le frontend envoie sur la racine '/', on traite quand même.
    """
    return _analyse_commune(req.texte)


@app.post("/chat", response_model=AnalyseResponse)
def analyse_chat(req: AnalyseRequest):
    """
    Alias supplémentaire : si l'ancien frontend utilise encore '/chat',
    on renvoie aussi la décision de l'arbre décisionnel.
    """
    return _analyse_commune(req.texte)

@app.get("/health")
def health():
    return {"status": "ok"}

