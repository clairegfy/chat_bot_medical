"""
Base vocabulary infrastructure for clinical NLU.

This module provides the foundational classes and utilities for
medical vocabulary detection, including:

- DetectionResult: Standardized output for all vocabulary detection
- ConceptCategory: Enum for clinical concept categorization
- Text normalization utilities for French medical text

Design Principles:
    1. Immutable detection results for audit trail
    2. Confidence scoring for uncertain detections
    3. Source tracking for explainability
    4. French-specific text normalization

Clinical Notes:
    The DetectionResult class implements three-state logic:
    - detected=True, value=True: Finding confirmed present
    - detected=True, value=False: Finding confirmed absent (negation)
    - detected=False: Finding not detected in text

    This distinction is critical because "not detected" should
    trigger a clarification question, while "confirmed absent"
    should inform clinical decision-making.

Usage:
    >>> from headache_assistants.vocabulary.base import DetectionResult, normalize_text
    >>>
    >>> # Normalize French text
    >>> text = normalize_text("Fièvre à 39°C")
    >>> print(text)
    fievre a 39°c
    >>>
    >>> # Create detection result
    >>> result = DetectionResult(
    ...     detected=True,
    ...     value=True,
    ...     confidence=0.95,
    ...     matched_term="fièvre",
    ...     source="keyword"
    ... )
    >>> result.is_reliable()
    True

See Also:
    - clinical_signs.py: Vocabularies using this base
    - contexts.py: Context vocabularies using this base
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from enum import Enum


class ConceptCategory(str, Enum):
    """
    Clinical concept categories for vocabulary organization.

    This enum categorizes medical concepts by their clinical
    significance in headache assessment.

    Categories:
        ONSET: Headache onset patterns (thunderclap, progressive)
        SYMPTOM: Clinical symptoms (fever, nausea, photophobia)
        SIGN: Clinical signs (meningeal, papilledema, deficit)
        CONTEXT: Risk contexts (pregnancy, trauma, cancer)
        TEMPORAL: Duration and timing (acute, chronic)
        SEVERITY: Pain intensity and urgency
        LOCATION: Anatomical headache location

    Example:
        >>> category = ConceptCategory.SIGN
        >>> if category == ConceptCategory.SIGN:
        ...     print("Physical examination finding")
    """

    ONSET = "onset"
    SYMPTOM = "symptom"
    SIGN = "sign"
    CONTEXT = "context"
    TEMPORAL = "temporal"
    SEVERITY = "severity"
    LOCATION = "location"


@dataclass(frozen=True)
class DetectionResult:
    """
    Immutable result of vocabulary detection.

    This dataclass represents the outcome of attempting to detect
    a clinical concept in text. It is designed to be immutable
    (frozen) for audit trail integrity.

    Attributes:
        detected: Whether any relevant term was found in text
        value: The clinical value if detected (True/False for boolean concepts,
               or specific value for enums like onset type)
        confidence: Confidence score (0.0-1.0) for the detection
        matched_term: The exact term that triggered detection
        source: How the detection was made (keyword, pattern, embedding, etc.)
        metadata: Additional context for debugging and audit

    Three-State Logic:
        - detected=True, value=True: Concept confirmed PRESENT
        - detected=True, value=False: Concept confirmed ABSENT (negation detected)
        - detected=False: Concept not mentioned in text

    Confidence Interpretation:
        - 0.90-1.00: Very high confidence (exact keyword match)
        - 0.80-0.89: High confidence (strong pattern match)
        - 0.60-0.79: Medium confidence (fuzzy match or context inference)
        - 0.40-0.59: Low confidence (weak pattern, possible ambiguity)
        - <0.40: Very low confidence (should not be used for decisions)

    Example:
        >>> # Positive detection
        >>> result = DetectionResult(
        ...     detected=True,
        ...     value=True,
        ...     confidence=0.95,
        ...     matched_term="fièvre",
        ...     source="keyword"
        ... )
        >>> result.detected, result.value
        (True, True)

        >>> # Negation detection
        >>> result = DetectionResult(
        ...     detected=True,
        ...     value=False,
        ...     confidence=0.92,
        ...     matched_term="apyrétique",
        ...     source="negation_keyword"
        ... )
        >>> result.detected, result.value
        (True, False)

        >>> # Not detected
        >>> result = DetectionResult(detected=False)
        >>> result.detected
        False

    Clinical Notes:
        The distinction between "not detected" and "confirmed absent"
        is critical for clinical safety. If fever is not detected,
        the system should ask about fever. If fever is confirmed
        absent (apyrétique), the system can proceed with that information.
    """

    detected: bool = False
    value: Any = None
    confidence: float = 0.0
    matched_term: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_reliable(self) -> bool:
        """
        Check if detection is reliable for clinical use.

        Returns:
            True if confidence >= 0.60 (minimum for clinical decisions)

        Clinical Note:
            Detections below 0.60 confidence should trigger
            clarification questions rather than being used directly.
        """
        return self.detected and self.confidence >= 0.60

    def is_high_confidence(self) -> bool:
        """
        Check if detection has high confidence.

        Returns:
            True if confidence >= 0.85

        Clinical Note:
            High confidence detections can be used without
            clarification for non-critical fields.
        """
        return self.detected and self.confidence >= 0.85

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with all detection attributes

        Example:
            >>> result = DetectionResult(detected=True, value=True, confidence=0.9)
            >>> result.to_dict()
            {'detected': True, 'value': True, 'confidence': 0.9, ...}
        """
        return {
            "detected": self.detected,
            "value": self.value,
            "confidence": self.confidence,
            "matched_term": self.matched_term,
            "source": self.source,
            "metadata": self.metadata
        }


# =============================================================================
# TEXT NORMALIZATION UTILITIES
# =============================================================================

# French accent normalization mapping
ACCENT_MAP = {
    'à': 'a', 'â': 'a', 'ä': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'î': 'i', 'ï': 'i',
    'ô': 'o', 'ö': 'o',
    'ù': 'u', 'û': 'u', 'ü': 'u',
    'ÿ': 'y',
    'ç': 'c',
    'œ': 'oe', 'æ': 'ae'
}


def normalize_text(text: str, preserve_accents: bool = False) -> str:
    """
    Normalize French clinical text for pattern matching.

    This function prepares clinical text for vocabulary matching by:
    1. Converting to lowercase
    2. Optionally removing accents (for robust matching)
    3. Normalizing whitespace
    4. Preserving clinically significant punctuation

    Args:
        text: Raw clinical text in French
        preserve_accents: If True, keep French accents (default False)

    Returns:
        Normalized text suitable for pattern matching

    Example:
        >>> normalize_text("Fièvre à 39°C, SANS céphalée")
        'fievre a 39°c, sans cephalee'

        >>> normalize_text("Céphalée brutale", preserve_accents=True)
        'céphalée brutale'

    Clinical Notes:
        - Accents are removed by default to handle user typos
        - Medical abbreviations are preserved (°C, etc.)
        - Multiple spaces are collapsed to single space
        - Newlines are converted to spaces
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Remove accents if requested (default behavior)
    if not preserve_accents:
        for accented, plain in ACCENT_MAP.items():
            text = text.replace(accented, plain)

    return text


def remove_accents(text: str) -> str:
    """
    Remove all accents from text using Unicode normalization.

    This is a more thorough accent removal than the ACCENT_MAP,
    using Unicode NFD decomposition.

    Args:
        text: Text with accents

    Returns:
        Text without accents

    Example:
        >>> remove_accents("Céphalée fébrile")
        'Cephalee febrile'
    """
    if not text:
        return ""

    # NFD decomposition separates base characters from combining marks
    nfkd = unicodedata.normalize('NFD', text)
    # Remove combining marks (accents)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def extract_numbers(text: str) -> List[float]:
    """
    Extract numeric values from clinical text.

    Handles various French number formats including:
    - Integer: "39"
    - Decimal with comma: "38,5"
    - Decimal with period: "38.5"
    - With units: "39°C", "10/10"

    Args:
        text: Clinical text containing numbers

    Returns:
        List of extracted numeric values

    Example:
        >>> extract_numbers("Température 38,5°C, EVA 8/10")
        [38.5, 8.0, 10.0]

    Clinical Notes:
        - French uses comma as decimal separator
        - Temperature values around 38 suggest fever threshold
        - EVA scores are on 0-10 scale
    """
    if not text:
        return []

    # Replace French comma with period for parsing
    text = text.replace(',', '.')

    # Find all number patterns
    pattern = r'\d+\.?\d*'
    matches = re.findall(pattern, text)

    return [float(m) for m in matches if m]


def clean_medical_text(text: str) -> str:
    """
    Clean clinical text while preserving medical significance.

    Performs cleaning operations that preserve clinical meaning:
    - Normalize whitespace
    - Preserve medical abbreviations
    - Keep numeric values and units
    - Remove extraneous punctuation

    Args:
        text: Raw clinical input

    Returns:
        Cleaned text suitable for NLU processing

    Example:
        >>> clean_medical_text("  Patient, 35 ans,   fièvre...  ")
        'patient, 35 ans, fievre'
    """
    if not text:
        return ""

    # Normalize and lowercase
    text = normalize_text(text, preserve_accents=False)

    # Remove repeated punctuation (except medical notation)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r',{2,}', ',', text)

    # Clean up spacing around punctuation
    text = re.sub(r'\s+([,.])', r'\1', text)
    text = re.sub(r'([,.])\s+', r'\1 ', text)

    return text.strip()
