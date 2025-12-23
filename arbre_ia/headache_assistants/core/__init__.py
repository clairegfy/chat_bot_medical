"""
Core module for the Headache Assessment Clinical NLU System.

This module provides the foundational components for the clinical decision
support system, including:

- Custom exceptions for clinical error handling
- Clinical enums for standardized medical terminology
- Re-exports of core model classes

Architecture:
    The core module serves as the foundation layer of the application.
    All other modules depend on these core components, but the core
    module has no internal dependencies to prevent circular imports.

Usage:
    >>> from headache_assistants.core import ClinicalNLUError, OnsetType
    >>> from headache_assistants.core import UrgencyLevel

Clinical Context:
    This system is designed for clinical use in headache assessment.
    All enums and exceptions are designed to align with French medical
    guidelines (HAS - Haute Autorité de Santé) for headache management.

See Also:
    - exceptions.py: Custom exception hierarchy
    - enums.py: Clinical enumeration types
"""

from .exceptions import (
    ClinicalNLUError,
    InvalidInputError,
    SessionNotFoundError,
    RuleMatchError,
    ExtractionError,
    ValidationError,
)

from .enums import (
    OnsetType,
    ProfileType,
    UrgencyLevel,
    HeadacheProfile,
    ExtractionConfidence,
)

__all__ = [
    # Exceptions
    "ClinicalNLUError",
    "InvalidInputError",
    "SessionNotFoundError",
    "RuleMatchError",
    "ExtractionError",
    "ValidationError",
    # Enums
    "OnsetType",
    "ProfileType",
    "UrgencyLevel",
    "HeadacheProfile",
    "ExtractionConfidence",
]
