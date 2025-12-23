"""
Custom exception hierarchy for the Clinical Headache NLU System.

This module defines a comprehensive exception hierarchy designed for:
1. Clinical safety: Clear error categorization for medical decision support
2. Audit trail: All exceptions capture context for regulatory compliance
3. Graceful degradation: Specific exception types enable targeted recovery

Exception Hierarchy:
    ClinicalNLUError (base)
    ├── InvalidInputError      - Malformed or empty input text
    ├── SessionNotFoundError   - Missing dialogue session
    ├── RuleMatchError         - Rule engine failures
    ├── ExtractionError        - NLU extraction failures
    └── ValidationError        - Data validation failures

Clinical Notes:
    In a medical decision support system, error handling is safety-critical.
    All exceptions preserve context information to enable:
    - Root cause analysis for quality improvement
    - Regulatory audit trail compliance
    - Graceful fallback to conservative recommendations

Usage:
    >>> from headache_assistants.core.exceptions import InvalidInputError
    >>>
    >>> def parse_clinical_text(text: str):
    ...     if not text or not text.strip():
    ...         raise InvalidInputError(
    ...             "Empty clinical input",
    ...             input_text=text,
    ...             context={"source": "api"}
    ...         )

See Also:
    - audit/tracer.py: Clinical decision traceability
    - dialogue/session.py: Session management
"""

from typing import Dict, Any, Optional
from datetime import datetime


class ClinicalNLUError(Exception):
    """
    Base exception for all clinical NLU system errors.

    This is the root exception class for the headache assessment system.
    All custom exceptions inherit from this class to enable unified
    error handling and audit trail capture.

    Attributes:
        message: Human-readable error description
        timestamp: ISO format timestamp when error occurred
        context: Additional contextual information for debugging
        original_exception: Underlying exception if this wraps another error

    Clinical Safety:
        This exception class is designed for medical applications where
        error handling must be:
        - Traceable: Full context capture for audit
        - Informative: Clear messages for clinical staff
        - Safe: Conservative fallback recommendations when errors occur

    Example:
        >>> try:
        ...     process_clinical_case(text)
        ... except ClinicalNLUError as e:
        ...     log_clinical_error(e)
        ...     return conservative_recommendation()
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize a ClinicalNLUError.

        Args:
            message: Human-readable error description
            context: Additional contextual information (optional)
            original_exception: Wrapped exception if applicable (optional)
        """
        super().__init__(message)
        self.message = message
        self.timestamp = datetime.now().isoformat()
        self.context = context or {}
        self.original_exception = original_exception

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize exception to dictionary for logging/audit.

        Returns:
            Dict containing all exception attributes for JSON serialization.

        Example:
            >>> error = ClinicalNLUError("Test error", context={"field": "fever"})
            >>> error.to_dict()
            {'type': 'ClinicalNLUError', 'message': 'Test error', ...}
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "timestamp": self.timestamp,
            "context": self.context,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class InvalidInputError(ClinicalNLUError):
    """
    Raised when clinical input text is invalid or malformed.

    This exception is raised when the input text cannot be processed
    due to format issues, empty content, or unexpected characters.

    Attributes:
        input_text: The original input that caused the error
        All attributes from ClinicalNLUError

    Clinical Context:
        Invalid input detection is critical for clinical safety.
        Empty or malformed inputs must not produce recommendations
        as this could lead to missed diagnoses or inappropriate imaging.

    Common Causes:
        - Empty or whitespace-only input
        - Encoding errors (non-UTF8 characters)
        - Input exceeding maximum length
        - Binary or non-text content

    Example:
        >>> def parse(text: str):
        ...     if not text.strip():
        ...         raise InvalidInputError(
        ...             "Empty clinical description",
        ...             input_text=text,
        ...             context={"endpoint": "/chat"}
        ...         )
    """

    def __init__(
        self,
        message: str,
        input_text: str = "",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize an InvalidInputError.

        Args:
            message: Description of the input validation failure
            input_text: The invalid input text (may be truncated for logging)
            context: Additional context (endpoint, user session, etc.)
            original_exception: Underlying exception if applicable
        """
        super().__init__(message, context, original_exception)
        # Truncate very long inputs to prevent log bloat
        self.input_text = input_text[:500] if input_text else ""
        self.context["input_length"] = len(input_text) if input_text else 0


class SessionNotFoundError(ClinicalNLUError):
    """
    Raised when a dialogue session cannot be found.

    This exception is raised when operations require an existing session
    but the session ID is not found in the session store.

    Attributes:
        session_id: The session ID that was not found
        All attributes from ClinicalNLUError

    Clinical Context:
        Session continuity is important for multi-turn dialogue.
        Lost sessions may result in incomplete case information
        and suboptimal recommendations. The system should gracefully
        handle this by starting a new session when appropriate.

    Common Causes:
        - Session expired due to timeout
        - Session ID typo or corruption
        - Server restart cleared session store
        - Concurrent access race condition

    Example:
        >>> def get_session(session_id: str):
        ...     session = session_store.get(session_id)
        ...     if not session:
        ...         raise SessionNotFoundError(
        ...             f"Session not found: {session_id}",
        ...             session_id=session_id
        ...         )
        ...     return session
    """

    def __init__(
        self,
        message: str,
        session_id: str = "",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize a SessionNotFoundError.

        Args:
            message: Description of the session lookup failure
            session_id: The session ID that was not found
            context: Additional context (request info, etc.)
            original_exception: Underlying exception if applicable
        """
        super().__init__(message, context, original_exception)
        self.session_id = session_id
        self.context["session_id"] = session_id


class RuleMatchError(ClinicalNLUError):
    """
    Raised when the rules engine encounters an error.

    This exception is raised when rule matching or evaluation fails,
    including JSON parsing errors, invalid rule conditions, or
    unexpected rule structure.

    Attributes:
        rule_id: ID of the problematic rule (if known)
        rule_data: The rule data that caused the error
        All attributes from ClinicalNLUError

    Clinical Context:
        Rule matching is the core decision-making component.
        Rule errors are safety-critical and must trigger fallback
        to conservative recommendations. All rule errors should be
        logged for immediate review by clinical informatics team.

    Common Causes:
        - Malformed rule JSON
        - Invalid condition operators
        - Missing required rule fields
        - Type mismatches in rule conditions

    Example:
        >>> def match_rule(case, rule):
        ...     try:
        ...         return evaluate_conditions(case, rule["conditions"])
        ...     except KeyError as e:
        ...         raise RuleMatchError(
        ...             f"Missing condition in rule",
        ...             rule_id=rule.get("id"),
        ...             rule_data=rule,
        ...             original_exception=e
        ...         )
    """

    def __init__(
        self,
        message: str,
        rule_id: Optional[str] = None,
        rule_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize a RuleMatchError.

        Args:
            message: Description of the rule matching failure
            rule_id: ID of the problematic rule
            rule_data: The rule data that caused the error
            context: Additional context
            original_exception: Underlying exception if applicable
        """
        super().__init__(message, context, original_exception)
        self.rule_id = rule_id
        self.rule_data = rule_data
        self.context["rule_id"] = rule_id


class ExtractionError(ClinicalNLUError):
    """
    Raised when NLU extraction encounters an error.

    This exception is raised when the NLU pipeline fails to extract
    clinical information from text, including pattern matching errors,
    embedding failures, or vocabulary lookup issues.

    Attributes:
        field: The clinical field being extracted when error occurred
        extraction_phase: The NLU phase where extraction failed
        All attributes from ClinicalNLUError

    Clinical Context:
        Extraction errors may result in missing clinical data.
        The system should continue processing other fields and
        explicitly mark failed fields as "unknown" rather than
        silently ignoring them. This ensures dialogue will ask
        clarifying questions for missing information.

    Common Causes:
        - Regex pattern exceptions
        - Embedding model unavailable
        - Vocabulary lookup failures
        - Character encoding issues

    Example:
        >>> def extract_fever(text: str):
        ...     try:
        ...         return fever_patterns.search(text)
        ...     except re.error as e:
        ...         raise ExtractionError(
        ...             "Fever pattern matching failed",
        ...             field="fever",
        ...             extraction_phase="pattern_matching",
        ...             original_exception=e
        ...         )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        extraction_phase: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize an ExtractionError.

        Args:
            message: Description of the extraction failure
            field: Clinical field being extracted (e.g., "fever", "onset")
            extraction_phase: NLU phase (e.g., "keywords", "embedding", "patterns")
            context: Additional context
            original_exception: Underlying exception if applicable
        """
        super().__init__(message, context, original_exception)
        self.field = field
        self.extraction_phase = extraction_phase
        self.context["field"] = field
        self.context["extraction_phase"] = extraction_phase


class ValidationError(ClinicalNLUError):
    """
    Raised when data validation fails.

    This exception is raised when extracted or provided data fails
    validation checks, such as out-of-range values, type mismatches,
    or constraint violations.

    Attributes:
        field: The field that failed validation
        value: The invalid value
        expected: Description of expected value/format
        All attributes from ClinicalNLUError

    Clinical Context:
        Validation is critical for clinical data integrity.
        Invalid values (e.g., age=200, intensity=15) could lead
        to incorrect rule matching. Validation errors should
        result in the field being treated as "unknown" and
        triggering clarification questions.

    Common Causes:
        - Age outside valid range (0-120)
        - Intensity outside 0-10 scale
        - Invalid enumeration values
        - Null values for required fields

    Example:
        >>> def validate_age(age: int):
        ...     if not 0 <= age <= 120:
        ...         raise ValidationError(
        ...             f"Age {age} outside valid range",
        ...             field="age",
        ...             value=age,
        ...             expected="0-120"
        ...         )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        expected: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize a ValidationError.

        Args:
            message: Description of the validation failure
            field: Field that failed validation
            value: The invalid value
            expected: Description of what was expected
            context: Additional context
            original_exception: Underlying exception if applicable
        """
        super().__init__(message, context, original_exception)
        self.field = field
        self.value = value
        self.expected = expected
        self.context["field"] = field
        self.context["value"] = str(value)[:100]  # Truncate long values
        self.context["expected"] = expected
