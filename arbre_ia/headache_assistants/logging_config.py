"""Configuration du logging pour l'audit des décisions médicales.

Ce module fournit un système de logging structuré pour:
1. Traçabilité des décisions médicales (audit trail)
2. Debugging du pipeline NLU
3. Monitoring des performances

Niveaux de log:
    - DEBUG: Détails du parsing NLU, scores de confiance
    - INFO: Décisions médicales, règles matchées
    - WARNING: Confiance basse, fallback embedding
    - ERROR: Erreurs de parsing, fichiers manquants
    - CRITICAL: Erreurs système bloquantes
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json


# Nom du logger principal
LOGGER_NAME = "headache_assistant"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_json: bool = False
) -> logging.Logger:
    """Configure le système de logging.

    Args:
        level: Niveau de log minimum (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Fichier de log optionnel
        enable_console: Afficher les logs en console
        enable_json: Utiliser le format JSON (pour parsing automatisé)

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Éviter les doublons si déjà configuré
    if logger.handlers:
        return logger

    # Format standard
    if enable_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Handler console
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Handler fichier
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class JsonFormatter(logging.Formatter):
    """Formatter JSON pour logs structurés."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage()
        }

        # Ajouter les données extra si présentes
        if hasattr(record, 'medical_data'):
            log_data["medical_data"] = record.medical_data

        return json.dumps(log_data, ensure_ascii=False)


def get_logger() -> logging.Logger:
    """Récupère le logger principal de l'application.

    Returns:
        Logger configuré (ou logger silencieux par défaut)
    """
    logger = logging.getLogger(LOGGER_NAME)

    # Si pas de handlers, configurer en mode SILENCIEUX par défaut
    # Les logs sont stockés en mémoire mais pas affichés en console
    # Utiliser setup_logging(enable_console=True) pour activer l'affichage
    if not logger.handlers:
        setup_logging(enable_console=False)

    return logger


def log_medical_decision(
    case_id: str,
    decision: str,
    rule_matched: Optional[str] = None,
    confidence: float = 0.0,
    urgency: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """Log une décision médicale pour l'audit trail.

    Cette fonction crée un enregistrement structuré de chaque décision
    pour permettre la traçabilité et l'audit médical.

    Args:
        case_id: Identifiant unique du cas
        decision: Décision prise (ex: "SCANNER_URGENT", "IRM_24H")
        rule_matched: Nom de la règle médicale qui a matché
        confidence: Score de confiance de la décision (0-1)
        urgency: Niveau d'urgence (emergency, urgent, routine)
        extra_data: Données supplémentaires pour l'audit
    """
    logger = get_logger()

    log_entry = {
        "case_id": case_id,
        "decision": decision,
        "rule_matched": rule_matched,
        "confidence": confidence,
        "urgency": urgency,
        "timestamp": datetime.utcnow().isoformat(),
        "extra": extra_data or {}
    }

    # Créer un LogRecord avec données médicales attachées
    logger.info(
        f"DECISION MEDICALE: {decision} (règle: {rule_matched}, urgence: {urgency}, confiance: {confidence:.0%})",
        extra={"medical_data": log_entry}
    )


def log_nlu_parsing(
    text: str,
    detected_fields: list,
    confidence: float,
    method: str = "rules"
) -> None:
    """Log les résultats du parsing NLU.

    Args:
        text: Texte analysé (tronqué pour les logs)
        detected_fields: Liste des champs détectés
        confidence: Score de confiance global
        method: Méthode utilisée (rules, embedding, hybrid)
    """
    logger = get_logger()

    # Tronquer le texte pour les logs
    text_preview = text[:100] + "..." if len(text) > 100 else text

    logger.debug(
        f"NLU [{method.upper()}]: {len(detected_fields)} champs détectés, "
        f"confiance {confidence:.0%} | '{text_preview}'"
    )


def log_error_with_context(
    error: Exception,
    context: str,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """Log une erreur avec contexte médical.

    Args:
        error: Exception survenue
        context: Contexte de l'erreur (ex: "parsing NLU", "chargement règles")
        extra_data: Données de debug supplémentaires
    """
    logger = get_logger()

    logger.error(
        f"ERREUR [{context}]: {type(error).__name__}: {error}",
        extra={"medical_data": {"context": context, "error_type": type(error).__name__, "extra": extra_data}},
        exc_info=True
    )
