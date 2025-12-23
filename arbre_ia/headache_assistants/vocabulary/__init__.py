"""
Medical vocabulary module for clinical NLU.

This module provides domain-specific vocabulary detection for clinical
headache assessment, including:

- Base detection infrastructure (DetectionResult, normalization)
- Clinical signs vocabulary (fever, meningeal, HTIC, deficit, seizure)
- Context vocabulary (pregnancy, trauma, immunosuppression, cancer)
- Onset vocabulary (thunderclap, progressive, chronic)

Architecture:
    The vocabulary module is organized by clinical domain:
    - base.py: Core detection classes and text normalization
    - clinical_signs.py: Red flag symptom detection
    - contexts.py: Risk context detection
    - onset.py: Onset pattern detection

    Each domain module provides vocabulary classes that implement
    consistent detection patterns with confidence scoring.

Clinical Notes:
    Vocabulary detection is the foundation of the NLU system.
    Each term is carefully mapped to its clinical significance,
    with explicit handling of:
    - Synonyms (e.g., "fièvre", "fébrile", "hyperthermie")
    - Negations (e.g., "apyrétique", "pas de fièvre")
    - Medical acronyms (e.g., "HTIC", "RDN", "HSA")
    - Threshold values (e.g., ≥38°C for fever)

Usage:
    >>> from headache_assistants.vocabulary import DetectionResult
    >>> from headache_assistants.vocabulary import FeverVocabulary
    >>>
    >>> vocab = FeverVocabulary()
    >>> result = vocab.detect("Patient fébrile à 39°C")
    >>> result.detected, result.value
    (True, True)

See Also:
    - medical_vocabulary.py: Main facade class
    - nlu_hybrid.py: NLU pipeline using these vocabularies
"""

from .base import (
    DetectionResult,
    normalize_text,
    ConceptCategory,
)

__all__ = [
    "DetectionResult",
    "normalize_text",
    "ConceptCategory",
]
