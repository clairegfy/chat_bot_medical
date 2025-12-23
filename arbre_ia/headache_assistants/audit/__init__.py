"""
Clinical audit trail module for regulatory compliance.

This module provides infrastructure for tracking all clinical decisions
made by the headache assessment system, ensuring:

1. Traceability: Every decision can be traced back to its inputs
2. Accountability: Clear record of what information was used
3. Reproducibility: Decisions can be reviewed and verified
4. Compliance: Meets medical device regulatory requirements

Components:
    - ClinicalDecisionTrace: Immutable record of each decision
    - AuditLogger: Structured logging for clinical audit trail

Regulatory Context:
    Medical decision support systems are subject to regulatory
    oversight (FDA, CE marking). This audit module supports:
    - ISO 13485: Medical device quality management
    - IEC 62304: Medical device software lifecycle
    - GDPR: Data protection and patient privacy

Usage:
    >>> from headache_assistants.audit import ClinicalDecisionTrace, AuditLogger
    >>>
    >>> trace = ClinicalDecisionTrace(
    ...     session_id="abc123",
    ...     input_text="Femme 35 ans céphalée brutale",
    ...     extracted_case={"onset": "thunderclap"},
    ...     matched_rule="HSA_001",
    ...     recommendation={"urgency": "immediate"}
    ... )
    >>>
    >>> logger = AuditLogger()
    >>> logger.log_decision(trace)

See Also:
    - dialogue/session.py: Session management with audit integration
    - rules_engine.py: Rule matching with trace logging
"""

from .tracer import (
    ClinicalDecisionTrace,
    AuditLogger,
    AuditLevel,
)

__all__ = [
    "ClinicalDecisionTrace",
    "AuditLogger",
    "AuditLevel",
]
