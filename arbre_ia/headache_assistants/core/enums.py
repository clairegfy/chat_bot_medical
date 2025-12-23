"""
Clinical enumeration types for the Headache Assessment NLU System.

This module defines standardized enumeration types that align with
French medical guidelines (HAS - Haute Autorité de Santé) for
headache assessment and imaging recommendations.

Design Principles:
    1. String-based enums for JSON serialization compatibility
    2. Medical terminology aligned with French clinical practice
    3. Clear documentation with clinical context
    4. Explicit "UNKNOWN" values for unassessed states

Clinical Safety Note:
    The distinction between "absent" and "unknown/unassessed" is
    critical in medical decision-making. An unknown fever status
    should not be treated the same as confirmed absence of fever.
    All enums that represent clinical findings include explicit
    handling of the unknown state.

Usage:
    >>> from headache_assistants.core.enums import OnsetType, UrgencyLevel
    >>>
    >>> onset = OnsetType.THUNDERCLAP
    >>> if onset == OnsetType.THUNDERCLAP:
    ...     urgency = UrgencyLevel.IMMEDIATE
    >>>
    >>> # JSON serialization works seamlessly
    >>> import json
    >>> json.dumps({"onset": onset})
    '{"onset": "thunderclap"}'

See Also:
    - models.py: Pydantic models using these enums
    - rules/headache_rules.json: Decision rules using enum values
"""

from enum import Enum


class OnsetType(str, Enum):
    """
    Classification of headache onset patterns.

    The onset type is one of the most critical clinical indicators
    for headache triage. A thunderclap onset, in particular, is a
    red flag requiring immediate investigation for subarachnoid
    hemorrhage (HSA) until proven otherwise.

    Values:
        THUNDERCLAP: Sudden, maximal intensity within seconds
            - Clinical: "Coup de tonnerre", worst headache of life
            - Urgency: IMMEDIATE (HSA suspicion)
            - Typical workup: CT + lumbar puncture if CT negative

        PROGRESSIVE: Gradual onset over hours to days
            - Clinical: Intensity builds over time
            - Urgency: Varies based on other findings
            - Consider: Infection, mass effect, hypertensive crisis

        CHRONIC: Long-standing headache pattern
            - Clinical: Weeks to months/years duration
            - Urgency: Usually LOW unless red flags present
            - Consider: Primary headache, medication overuse

        UNKNOWN: Onset pattern not yet determined
            - Clinical: Patient has not been asked or answer unclear
            - Action: Dialogue system should clarify this field

    Clinical Context (French HAS Guidelines):
        - Thunderclap onset mandates immediate neuroimaging
        - "Céphalée en coup de tonnerre" is a medical emergency
        - 10-25% of thunderclap headaches have serious underlying cause

    Example:
        >>> onset = OnsetType.THUNDERCLAP
        >>> if onset == OnsetType.THUNDERCLAP:
        ...     print("Emergency: Consider HSA")
    """

    THUNDERCLAP = "thunderclap"
    PROGRESSIVE = "progressive"
    CHRONIC = "chronic"
    UNKNOWN = "unknown"

    def is_emergency(self) -> bool:
        """
        Check if this onset type indicates emergency.

        Returns:
            True if onset is thunderclap (emergency indicator)
        """
        return self == OnsetType.THUNDERCLAP


class ProfileType(str, Enum):
    """
    Temporal profile classification for headache duration.

    The temporal profile helps categorize the headache into acute,
    subacute, or chronic presentations, which influences the
    differential diagnosis and urgency of investigation.

    Values:
        ACUTE: Duration < 7 days
            - Recent onset, requires careful evaluation
            - Higher likelihood of secondary cause
            - Consider: HSA, meningitis, first migraine

        SUBACUTE: Duration 7-90 days
            - Intermediate duration
            - Consider: Subdural hematoma, tumor, temporal arteritis
            - Often warrants imaging if no clear diagnosis

        CHRONIC: Duration > 90 days (3 months)
            - Long-standing pattern
            - Usually primary headache (migraine, tension)
            - Imaging if: pattern change, new features, red flags

        UNKNOWN: Duration/profile not yet determined
            - Patient has not provided temporal information
            - Dialogue should clarify duration

    Clinical Context:
        - Acute + thunderclap = highest urgency
        - Chronic + stable = usually benign
        - Chronic + recent change = red flag

    Example:
        >>> profile = ProfileType.ACUTE
        >>> if profile == ProfileType.ACUTE:
        ...     print("Consider secondary causes")
    """

    ACUTE = "acute"
    SUBACUTE = "subacute"
    CHRONIC = "chronic"
    UNKNOWN = "unknown"

    def days_threshold(self) -> tuple:
        """
        Get the day thresholds for this profile.

        Returns:
            Tuple of (min_days, max_days) or (None, None) for unknown
        """
        thresholds = {
            ProfileType.ACUTE: (0, 7),
            ProfileType.SUBACUTE: (7, 90),
            ProfileType.CHRONIC: (90, None),
            ProfileType.UNKNOWN: (None, None),
        }
        return thresholds.get(self, (None, None))


class UrgencyLevel(str, Enum):
    """
    Clinical urgency level for imaging recommendations.

    This enum defines the urgency with which imaging should be
    performed, aligned with French emergency medicine protocols.

    Values:
        IMMEDIATE: Imaging within minutes (< 1 hour)
            - Clinical: Life-threatening conditions suspected
            - Examples: HSA, acute stroke, meningitis
            - Action: Direct to emergency imaging

        URGENT: Imaging within hours (< 24 hours)
            - Clinical: Serious condition requiring prompt workup
            - Examples: Temporal arteritis, brain abscess
            - Action: Same-day imaging arranged

        DELAYED: Imaging within days to weeks
            - Clinical: Non-emergent but warrants investigation
            - Examples: New chronic headache in older adult
            - Action: Outpatient imaging scheduled

        NONE: No imaging indicated
            - Clinical: Primary headache diagnosis confident
            - Examples: Typical migraine, tension headache
            - Action: Reassurance and symptomatic treatment

    Clinical Context:
        - IMMEDIATE: Patient should not leave until imaged
        - URGENT: Imaging before discharge or same-day outpatient
        - DELAYED: Can be scheduled within reasonable timeframe
        - NONE: Imaging would not change management

    Example:
        >>> urgency = UrgencyLevel.IMMEDIATE
        >>> if urgency == UrgencyLevel.IMMEDIATE:
        ...     print("Alert radiology for emergency scan")
    """

    IMMEDIATE = "immediate"
    URGENT = "urgent"
    DELAYED = "delayed"
    NONE = "none"

    def requires_imaging(self) -> bool:
        """
        Check if this urgency level requires imaging.

        Returns:
            True if imaging is indicated (immediate, urgent, or delayed)
        """
        return self != UrgencyLevel.NONE

    def is_emergency(self) -> bool:
        """
        Check if this is an emergency urgency level.

        Returns:
            True if immediate imaging is required
        """
        return self == UrgencyLevel.IMMEDIATE


class HeadacheProfile(str, Enum):
    """
    Clinical headache profile classification.

    This enum classifies the clinical presentation of the headache
    based on associated symptoms and characteristics, helping to
    identify the likely headache type.

    Values:
        MIGRAINE_LIKE: Features suggesting migraine
            - Unilateral, pulsatile, photophobia, phonophobia
            - Nausea/vomiting, aura
            - Moderate to severe intensity

        TENSION_LIKE: Features suggesting tension-type headache
            - Bilateral, pressing/tightening quality
            - Mild to moderate intensity
            - No nausea, minimal photo/phonophobia

        HTIC_LIKE: Features suggesting raised intracranial pressure
            - Worse in morning, with vomiting
            - Papilledema, visual obscurations
            - Worsened by coughing/straining

        CLUSTER_LIKE: Features suggesting cluster headache
            - Unilateral, orbital/periorbital
            - Autonomic features (lacrimation, rhinorrhea)
            - Severe intensity, short duration (15-180 min)

        UNKNOWN: Profile not yet determined
            - Insufficient information for classification
            - Dialogue should gather more symptom details

    Clinical Context:
        - Migraine-like: Usually primary headache
        - Tension-like: Usually benign
        - HTIC-like: Red flag, requires imaging
        - Cluster-like: Primary but may need imaging to exclude

    Example:
        >>> profile = HeadacheProfile.HTIC_LIKE
        >>> if profile == HeadacheProfile.HTIC_LIKE:
        ...     print("Consider imaging for mass/hydrocephalus")
    """

    MIGRAINE_LIKE = "migraine_like"
    TENSION_LIKE = "tension_like"
    HTIC_LIKE = "htic_like"
    CLUSTER_LIKE = "cluster_like"
    UNKNOWN = "unknown"

    def is_red_flag(self) -> bool:
        """
        Check if this profile is a red flag.

        Returns:
            True if profile suggests secondary headache (HTIC-like)
        """
        return self == HeadacheProfile.HTIC_LIKE


class ExtractionConfidence(str, Enum):
    """
    Confidence levels for NLU extraction results.

    This enum categorizes the reliability of extracted clinical
    information, helping to identify when clarification is needed.

    Values:
        HIGH: Confidence >= 0.85
            - Extraction is reliable
            - No clarification needed
            - Example: Direct pattern match "fièvre 39°C"

        MEDIUM: Confidence 0.60-0.84
            - Extraction is likely correct but uncertain
            - May benefit from confirmation
            - Example: Fuzzy match or embedding-based detection

        LOW: Confidence 0.40-0.59
            - Extraction is uncertain
            - Clarification recommended
            - Example: Weak pattern match, ambiguous phrasing

        VERY_LOW: Confidence < 0.40
            - Extraction is unreliable
            - Should be treated as unknown
            - Example: Guessed value, no supporting evidence

    Clinical Context:
        - HIGH: Can be used for clinical decisions
        - MEDIUM: Acceptable but validate if critical
        - LOW: Ask clarifying question
        - VERY_LOW: Treat as unknown

    Example:
        >>> confidence = ExtractionConfidence.from_score(0.75)
        >>> if confidence == ExtractionConfidence.MEDIUM:
        ...     print("Consider asking for confirmation")
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"

    @classmethod
    def from_score(cls, score: float) -> "ExtractionConfidence":
        """
        Convert a numeric confidence score to ExtractionConfidence enum.

        Args:
            score: Confidence score between 0.0 and 1.0

        Returns:
            Corresponding ExtractionConfidence level

        Example:
            >>> ExtractionConfidence.from_score(0.92)
            <ExtractionConfidence.HIGH: 'high'>
            >>> ExtractionConfidence.from_score(0.35)
            <ExtractionConfidence.VERY_LOW: 'very_low'>
        """
        if score >= 0.85:
            return cls.HIGH
        elif score >= 0.60:
            return cls.MEDIUM
        elif score >= 0.40:
            return cls.LOW
        else:
            return cls.VERY_LOW

    def is_reliable(self) -> bool:
        """
        Check if this confidence level is reliable for clinical use.

        Returns:
            True if HIGH or MEDIUM confidence
        """
        return self in (ExtractionConfidence.HIGH, ExtractionConfidence.MEDIUM)
