"""Assistant médical pour l'évaluation des céphalées.

Ce package fournit une bibliothèque Python pour analyser les symptômes
de céphalées et recommander les examens d'imagerie appropriés.
"""

from .models import (
    HeadacheCase,
    ImagingRecommendation,
    ChatMessage,
    ChatResponse
)

from .rules_engine import RulesEngine
# Temporairement désactivés car ils utilisent encore les anciens modèles
# from .nlu import NLUEngine
# from .dialogue import DialogueManager

__version__ = "0.1.0"

__all__ = [
    # Modèles Pydantic
    "HeadacheCase",
    "ImagingRecommendation",
    "ChatMessage",
    "ChatResponse",
    
    # Moteurs
    "RulesEngine",
    # "NLUEngine",  # TODO: Mettre à jour pour utiliser HeadacheCase
    # "DialogueManager",  # TODO: Mettre à jour pour utiliser ChatMessage/ChatResponse
]

