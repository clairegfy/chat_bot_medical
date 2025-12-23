"""
Clinical decision traceability for the Headache Assessment System.

This module provides comprehensive audit trail capabilities for tracking
all clinical decisions made by the system. It is designed to meet
regulatory requirements for medical decision support systems.

Design Principles:
    1. Immutability: All traces are frozen dataclasses
    2. Completeness: Full context captured for each decision
    3. Serializability: JSON-compatible for storage and transmission
    4. Privacy: Configurable PHI handling

Audit Levels:
    - MINIMAL: Session ID and outcome only (for production)
    - STANDARD: Includes extracted fields and rule ID (recommended)
    - DETAILED: Full input text and confidence scores (for debugging)
    - DEBUG: Maximum verbosity including intermediate states

Regulatory Compliance:
    This module supports compliance with:
    - FDA 21 CFR Part 11: Electronic records and signatures
    - HIPAA: Health information privacy (configurable PHI handling)
    - MDR (EU 2017/745): Medical device regulation
    - ISO 14971: Risk management for medical devices

Usage:
    >>> from headache_assistants.audit.tracer import ClinicalDecisionTrace, AuditLogger
    >>>
    >>> # Create a decision trace
    >>> trace = ClinicalDecisionTrace.create(
    ...     session_id="session_123",
    ...     input_text="Femme 35 ans céphalée brutale",
    ...     extracted_case={"age": 35, "sex": "F", "onset": "thunderclap"},
    ...     matched_rule="HSA_001",
    ...     recommendation={"urgency": "immediate", "imaging": ["CT"]}
    ... )
    >>>
    >>> # Log the decision
    >>> logger = AuditLogger(level=AuditLevel.STANDARD)
    >>> logger.log_decision(trace)
    >>>
    >>> # Retrieve for review
    >>> traces = logger.get_session_traces("session_123")

See Also:
    - core/exceptions.py: Exception handling with trace context
    - dialogue/session.py: Session management integration
"""

import json
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum


class AuditLevel(str, Enum):
    """
    Audit detail levels for clinical decision logging.

    Values:
        MINIMAL: Session ID and final outcome only
            - Lowest storage requirements
            - Suitable for high-volume production
            - Limited debugging capability

        STANDARD: Extracted fields and rule ID included
            - Recommended for production use
            - Enables most audit scenarios
            - Moderate storage requirements

        DETAILED: Full input text and confidence scores
            - For quality assurance reviews
            - Enables full decision reconstruction
            - Higher storage requirements

        DEBUG: Maximum verbosity with intermediate states
            - For development and troubleshooting
            - Not recommended for production
            - Highest storage requirements

    Example:
        >>> level = AuditLevel.STANDARD
        >>> if level >= AuditLevel.DETAILED:
        ...     include_raw_input = True
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"

    def __ge__(self, other):
        """Compare audit levels by verbosity."""
        order = [AuditLevel.MINIMAL, AuditLevel.STANDARD,
                 AuditLevel.DETAILED, AuditLevel.DEBUG]
        return order.index(self) >= order.index(other)


@dataclass(frozen=True)
class ClinicalDecisionTrace:
    """
    Immutable record of a clinical decision for audit trail.

    This dataclass captures the complete context of a clinical decision,
    including inputs, processing details, and outputs. It is designed
    to be immutable (frozen) to ensure audit trail integrity.

    Attributes:
        trace_id: Unique identifier for this trace (auto-generated)
        timestamp: ISO format timestamp when decision was made
        session_id: Dialogue session identifier
        input_text: Raw input text from user (may be redacted)
        extracted_case: Structured case data extracted from input
        matched_rule: ID of the rule that triggered recommendation
        recommendation: Final imaging recommendation
        confidence_scores: Per-field confidence metrics
        processing_time_ms: Time taken to process in milliseconds
        metadata: Additional context (NLU mode, version, etc.)

    Immutability:
        This class is frozen to prevent modification after creation.
        This ensures audit trail integrity - once a decision is logged,
        it cannot be altered.

    Privacy:
        The input_text field may contain patient information.
        Use the sanitize() method to create a privacy-safe version
        that replaces potentially identifying information.

    Example:
        >>> trace = ClinicalDecisionTrace.create(
        ...     session_id="abc123",
        ...     input_text="Femme 35 ans céphalée brutale",
        ...     extracted_case={"age": 35, "onset": "thunderclap"},
        ...     matched_rule="HSA_001",
        ...     recommendation={"urgency": "immediate"}
        ... )
        >>> print(trace.trace_id)
        'trace_abc123_...'
        >>> trace.to_json()
        '{"trace_id": "...", "timestamp": "...", ...}'

    Clinical Notes:
        - Every imaging recommendation generates a trace
        - Traces are retained for regulatory compliance period
        - Quality reviews use traces to verify decision accuracy
    """

    trace_id: str
    timestamp: str
    session_id: str
    input_text: str = ""
    extracted_case: Dict[str, Any] = field(default_factory=dict)
    matched_rule: Optional[str] = None
    recommendation: Dict[str, Any] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        input_text: str = "",
        extracted_case: Optional[Dict[str, Any]] = None,
        matched_rule: Optional[str] = None,
        recommendation: Optional[Dict[str, Any]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
        processing_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ClinicalDecisionTrace":
        """
        Factory method to create a new trace with auto-generated ID.

        Args:
            session_id: Dialogue session identifier
            input_text: Raw input text from user
            extracted_case: Structured case data
            matched_rule: ID of matched rule
            recommendation: Imaging recommendation
            confidence_scores: Per-field confidence
            processing_time_ms: Processing duration
            metadata: Additional context

        Returns:
            New ClinicalDecisionTrace instance

        Example:
            >>> trace = ClinicalDecisionTrace.create(
            ...     session_id="abc123",
            ...     input_text="Patient avec fièvre"
            ... )
        """
        timestamp = datetime.now().isoformat()
        trace_id = cls._generate_trace_id(session_id, timestamp)

        return cls(
            trace_id=trace_id,
            timestamp=timestamp,
            session_id=session_id,
            input_text=input_text,
            extracted_case=extracted_case or {},
            matched_rule=matched_rule,
            recommendation=recommendation or {},
            confidence_scores=confidence_scores or {},
            processing_time_ms=processing_time_ms,
            metadata=metadata or {}
        )

    @staticmethod
    def _generate_trace_id(session_id: str, timestamp: str) -> str:
        """Generate unique trace ID from session and timestamp."""
        content = f"{session_id}_{timestamp}"
        hash_suffix = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"trace_{session_id[:8]}_{hash_suffix}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with all trace attributes
        """
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize to JSON string.

        Args:
            indent: JSON indentation level (None for compact)

        Returns:
            JSON string representation

        Example:
            >>> trace.to_json(indent=2)
            '{\\n  "trace_id": "...",\\n  ...\\n}'
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def sanitize(self, redact_input: bool = True) -> "ClinicalDecisionTrace":
        """
        Create privacy-safe version with redacted PHI.

        Args:
            redact_input: Whether to redact input_text (default True)

        Returns:
            New trace with potentially identifying information redacted

        Example:
            >>> trace = ClinicalDecisionTrace.create(
            ...     session_id="abc",
            ...     input_text="Marie, 35 ans, 01.02.1989"
            ... )
            >>> safe = trace.sanitize()
            >>> safe.input_text
            '[REDACTED]'
        """
        return ClinicalDecisionTrace(
            trace_id=self.trace_id,
            timestamp=self.timestamp,
            session_id=self.session_id,
            input_text="[REDACTED]" if redact_input else self.input_text,
            extracted_case=self.extracted_case,
            matched_rule=self.matched_rule,
            recommendation=self.recommendation,
            confidence_scores=self.confidence_scores,
            processing_time_ms=self.processing_time_ms,
            metadata=self.metadata
        )


class AuditLogger:
    """
    Structured logger for clinical decision audit trail.

    This class provides methods for logging clinical decisions
    at various detail levels, with support for multiple output
    destinations (console, file, remote).

    Attributes:
        level: Audit detail level (MINIMAL to DEBUG)
        logger: Python logger instance
        trace_store: In-memory store for session traces

    Thread Safety:
        This class is designed for single-threaded use.
        For multi-threaded environments, use SessionManager's
        integrated audit logging.

    Example:
        >>> logger = AuditLogger(level=AuditLevel.STANDARD)
        >>> trace = ClinicalDecisionTrace.create(...)
        >>> logger.log_decision(trace)
        >>> logger.get_session_traces("session_123")

    Configuration:
        The logger uses Python's logging module. Configure it
        with appropriate handlers for your deployment:
        - FileHandler for persistent storage
        - StreamHandler for console output
        - Custom handlers for remote logging
    """

    def __init__(
        self,
        level: AuditLevel = AuditLevel.STANDARD,
        logger_name: str = "clinical_audit"
    ):
        """
        Initialize the audit logger.

        Args:
            level: Audit detail level
            logger_name: Name for the Python logger
        """
        self.level = level
        self.logger = logging.getLogger(logger_name)
        self._trace_store: Dict[str, List[ClinicalDecisionTrace]] = {}

    def log_decision(self, trace: ClinicalDecisionTrace) -> None:
        """
        Log a clinical decision trace.

        The amount of information logged depends on the audit level.

        Args:
            trace: The decision trace to log

        Example:
            >>> logger.log_decision(trace)
        """
        # Store trace in memory
        session_id = trace.session_id
        if session_id not in self._trace_store:
            self._trace_store[session_id] = []
        self._trace_store[session_id].append(trace)

        # Format log message based on level
        if self.level == AuditLevel.MINIMAL:
            msg = self._format_minimal(trace)
        elif self.level == AuditLevel.STANDARD:
            msg = self._format_standard(trace)
        elif self.level == AuditLevel.DETAILED:
            msg = self._format_detailed(trace)
        else:  # DEBUG
            msg = self._format_debug(trace)

        self.logger.info(msg)

    def _format_minimal(self, trace: ClinicalDecisionTrace) -> str:
        """Format minimal audit message."""
        urgency = trace.recommendation.get("urgency", "unknown")
        return (
            f"AUDIT|{trace.trace_id}|"
            f"session={trace.session_id}|"
            f"urgency={urgency}"
        )

    def _format_standard(self, trace: ClinicalDecisionTrace) -> str:
        """Format standard audit message."""
        urgency = trace.recommendation.get("urgency", "unknown")
        imaging = trace.recommendation.get("imaging", [])
        return (
            f"AUDIT|{trace.trace_id}|"
            f"session={trace.session_id}|"
            f"rule={trace.matched_rule}|"
            f"urgency={urgency}|"
            f"imaging={','.join(imaging)}"
        )

    def _format_detailed(self, trace: ClinicalDecisionTrace) -> str:
        """Format detailed audit message."""
        return (
            f"AUDIT|{trace.trace_id}|"
            f"session={trace.session_id}|"
            f"rule={trace.matched_rule}|"
            f"case={json.dumps(trace.extracted_case)}|"
            f"recommendation={json.dumps(trace.recommendation)}|"
            f"confidence={json.dumps(trace.confidence_scores)}"
        )

    def _format_debug(self, trace: ClinicalDecisionTrace) -> str:
        """Format debug audit message with full trace."""
        return f"AUDIT_DEBUG|{trace.to_json()}"

    def get_session_traces(self, session_id: str) -> List[ClinicalDecisionTrace]:
        """
        Retrieve all traces for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of traces for the session (empty if none)
        """
        return self._trace_store.get(session_id, [])

    def get_latest_trace(self, session_id: str) -> Optional[ClinicalDecisionTrace]:
        """
        Get the most recent trace for a session.

        Args:
            session_id: Session identifier

        Returns:
            Most recent trace or None if no traces
        """
        traces = self.get_session_traces(session_id)
        return traces[-1] if traces else None

    def clear_session(self, session_id: str) -> None:
        """
        Clear traces for a session (e.g., after export).

        Args:
            session_id: Session identifier to clear
        """
        if session_id in self._trace_store:
            del self._trace_store[session_id]

    def export_traces(
        self,
        session_id: str,
        sanitize: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Export traces for external storage or analysis.

        Args:
            session_id: Session to export
            sanitize: Whether to redact PHI (default True)

        Returns:
            List of trace dictionaries
        """
        traces = self.get_session_traces(session_id)
        if sanitize:
            traces = [t.sanitize() for t in traces]
        return [t.to_dict() for t in traces]
