"""
Clinical data models for the Headache Assessment Decision Support System.

This module defines the core Pydantic models used throughout the clinical
decision support system for headache evaluation and imaging recommendations.

Module Overview:
    The models in this module represent the domain entities for clinical
    headache assessment following French HAS (Haute Autorité de Santé)
    guidelines. They are designed for:

    1. Clinical Safety: Explicit handling of unknown/unassessed states
    2. Regulatory Compliance: Full traceability and audit support
    3. Interoperability: JSON-serializable for API and storage
    4. Validation: Strict data validation with clinical constraints

Models:
    - HeadacheCase: Comprehensive clinical case representation
    - ImagingRecommendation: Imaging decision with justification
    - ChatMessage: Dialogue message with metadata
    - ChatResponse: System response with clinical context

Clinical Context:
    This system aims to reduce inappropriate imaging for headaches.
    Studies show approximately 30% of brain imaging prescriptions for
    headaches are either excessive or insufficient. These models capture
    all decision-relevant clinical information.

Three-State Logic (Critical for Medical Safety):
    All Optional[bool] clinical fields use three-state logic:
    - True: Clinical finding confirmed PRESENT
    - False: Clinical finding confirmed ABSENT
    - None: Finding NOT YET ASSESSED (unknown)

    This distinction is critical because:
    - "Unknown fever" should prompt a question, not assume absent
    - "Absent fever" actively rules out certain diagnoses
    - Treating unknown as absent could miss serious conditions

Usage:
    >>> from headache_assistants.models import HeadacheCase, ImagingRecommendation
    >>>
    >>> # Create a clinical case
    >>> case = HeadacheCase(
    ...     age=35,
    ...     sex="F",
    ...     onset="thunderclap",
    ...     profile="acute",
    ...     intensity=10
    ... )
    >>>
    >>> # Check for red flags
    >>> if case.has_red_flags():
    ...     print("Red flags detected - urgent evaluation needed")
    >>>
    >>> # Check for emergency
    >>> if case.is_emergency():
    ...     print("Emergency - immediate imaging required")

Dependencies:
    - pydantic>=2.5.0: Data validation and serialization
    - typing: Type hints for clinical fields

See Also:
    - core/enums.py: Clinical enumeration types
    - core/exceptions.py: Custom exception hierarchy
    - rules/headache_rules.json: Medical decision rules
    - French HAS Guidelines: https://www.has-sante.fr/

Author: Clinical Informatics Team
Version: 2.0.0 (Refactored with clinical-grade documentation)
"""

from typing import Optional, Literal, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class HeadacheCase(BaseModel):
    """
    Comprehensive clinical representation of a headache case.

    This model captures all clinically relevant information required for
    navigating the medical decision tree and determining appropriate
    imaging recommendations. It is designed to align with French HAS
    guidelines for headache management.

    The model uses a three-state logic for all Optional[bool] fields:
    - True: Finding confirmed PRESENT
    - False: Finding confirmed ABSENT
    - None: Finding NOT YET ASSESSED (requires clarification)

    Attributes:
        Demographics:
            age: Patient age in years (0-120). None if not yet collected.
            sex: Patient sex ("M", "F", "Other")

        Temporal Profile:
            profile: Duration category (acute <7d, subacute 7-90d, chronic >90d)
            onset: Onset pattern (thunderclap, progressive, chronic)
            duration_current_episode_hours: Current episode duration in hours
            intensity: Pain intensity on 0-10 scale (EVA)

        Red Flags (Critical Clinical Signs):
            fever: Temperature ≥38°C (requires immediate evaluation if with meningeal signs)
            meningeal_signs: Kernig, Brudzinski, neck stiffness (meningitis indicator)
            neuro_deficit: Focal neurological deficit (stroke, mass effect indicator)
            seizure: Epileptic seizure occurrence
            htic_pattern: Signs of raised intracranial pressure

        Risk Contexts:
            pregnancy_postpartum: Pregnancy or <6 weeks postpartum
            pregnancy_trimester: Trimester if pregnant (affects imaging choice)
            trauma: Recent head trauma
            recent_pl_or_peridural: Recent lumbar puncture or epidural
            immunosuppression: Immunocompromised state
            recent_pattern_change: New symptoms in known chronic headache

        Priority 1 - Oncological Context:
            cancer_history: Active or remission cancer (high imaging priority)

        Priority 2 - Associated Symptoms:
            vertigo: Vertigo (considered neurological deficit)
            tinnitus: Tinnitus (note on prescription)
            visual_disturbance_type: Type of visual symptoms
            joint_pain: Joint pain (Horton's disease if age >60)
            horton_criteria: Giant cell arteritis indicators

        Priority 3 - Patient History:
            first_episode: First ever vs recurrent headache
            previous_workup: Prior imaging performed
            chronic_or_episodic: Pattern of chronic headache

        Priority 4 - Location and Special History:
            headache_location: Anatomical location
            brain_infection_history: Prior CNS infection
            congenital_brain_malformation: Known malformation
            persistent_or_resolving: Symptom trajectory

        Synthesis:
            red_flag_context: List of identified risk contexts
            headache_profile: Clinical headache type classification

    Clinical Notes:
        - Age >50 with acute headache is itself a red flag
        - Thunderclap onset mandates HSA workup until excluded
        - Fever + meningeal signs = meningitis until proven otherwise
        - Post-partum headache requires TVC exclusion

    Example:
        >>> case = HeadacheCase(
        ...     age=65,
        ...     sex="M",
        ...     onset="thunderclap",
        ...     profile="acute",
        ...     intensity=10,
        ...     fever=False,
        ...     meningeal_signs=True
        ... )
        >>> case.has_red_flags()
        True
        >>> case.is_emergency()
        True

    See Also:
        - rules/headache_rules.json: Decision rules using these fields
        - French HAS: "Céphalées de l'adulte" recommendations
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False
    )

    # =========================================================================
    # DEMOGRAPHICS
    # =========================================================================

    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        description=(
            "Patient age in years. None if not yet collected. "
            "Clinical Note: Age >50 with new acute headache is a red flag."
        )
    )

    sex: Literal["M", "F", "Other"] = Field(
        default="Other",
        description=(
            "Patient sex. 'M'=Male, 'F'=Female, 'Other'=Unknown/Other. "
            "Clinical Note: Female + postpartum context requires TVC screening."
        )
    )

    # =========================================================================
    # TEMPORAL PROFILE
    # =========================================================================

    profile: Literal["acute", "chronic", "subacute", "unknown"] = Field(
        default="unknown",
        description=(
            "Temporal profile of headache. "
            "'acute': <7 days duration - requires careful evaluation. "
            "'subacute': 7-90 days - consider tumor, subdural. "
            "'chronic': >90 days - usually primary headache. "
            "'unknown': Not yet determined - dialogue should clarify."
        )
    )

    onset: Literal["thunderclap", "progressive", "chronic", "unknown"] = Field(
        default="unknown",
        description=(
            "Onset pattern of headache. "
            "'thunderclap': Maximal intensity in <1 minute - EMERGENCY (HSA). "
            "'progressive': Builds over hours/days. "
            "'chronic': Long-standing pattern. "
            "'unknown': Not yet determined."
        )
    )

    duration_current_episode_hours: Optional[float] = Field(
        default=None,
        ge=0,
        description=(
            "Duration of current episode in hours. "
            "Used to categorize profile and assess urgency. "
            "Clinical Note: <6h with thunderclap = highest HSA risk."
        )
    )

    intensity: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description=(
            "Pain intensity on EVA (Visual Analog Scale) 0-10. "
            "0=no pain, 10=worst imaginable pain. "
            "Clinical Note: 10/10 with thunderclap = 'worst headache of life' (HSA)."
        )
    )

    # =========================================================================
    # RED FLAGS - CRITICAL CLINICAL SIGNS
    # Three-state logic: True=present, False=absent, None=unknown
    # =========================================================================

    fever: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of fever (temperature ≥38°C). "
            "True=fever confirmed, False=afebrile, None=not assessed. "
            "Clinical Note: Fever + headache = infection until proven otherwise. "
            "Fever + meningeal signs = IMMEDIATE meningitis workup."
        )
    )

    meningeal_signs: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of meningeal signs (Kernig, Brudzinski, neck stiffness). "
            "True=present, False=absent (nuque souple), None=not assessed. "
            "Clinical Note: Any meningeal sign = EMERGENCY. "
            "Kernig+: pain on leg extension with hip flexed. "
            "Brudzinski+: neck flexion causes hip/knee flexion."
        )
    )

    neuro_deficit: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of focal neurological deficit. "
            "True=present, False=absent, None=not assessed. "
            "Includes: hemiparesis, aphasia, hemianopia, diplopia, ataxia. "
            "Clinical Note: Acute deficit + headache = stroke/mass until excluded. "
            "Note: Migraine aura (scotoma) is NOT a focal deficit."
        )
    )

    seizure: Optional[bool] = Field(
        default=None,
        description=(
            "Occurrence of epileptic seizure. "
            "True=occurred, False=no seizure, None=not assessed. "
            "Clinical Note: New seizure + headache = brain lesion until excluded. "
            "Includes: generalized tonic-clonic, focal with impaired awareness."
        )
    )

    htic_pattern: Optional[bool] = Field(
        default=None,
        description=(
            "Signs suggestive of raised intracranial pressure (HTIC). "
            "True=present, False=absent, None=not assessed. "
            "STRONG indicators: projectile vomiting, papilledema. "
            "WEAK indicators (alone insufficient): morning headache, cough worsening. "
            "Clinical Note: HTIC requires CT/MRI to exclude mass/hydrocephalus."
        )
    )

    # =========================================================================
    # RISK CONTEXTS
    # =========================================================================

    pregnancy_postpartum: Optional[bool] = Field(
        default=None,
        description=(
            "Pregnancy or postpartum period (<6 weeks after delivery). "
            "True=pregnant/postpartum, False=not, None=not assessed. "
            "Clinical Note: Postpartum + headache = exclude CVT (venous thrombosis). "
            "Pregnancy affects imaging choice (MRI preferred over CT in T1)."
        )
    )

    pregnancy_trimester: Optional[int] = Field(
        default=None,
        ge=1,
        le=3,
        description=(
            "Trimester of pregnancy if pregnant. "
            "1=<14 weeks (contraindicated for MRI gadolinium). "
            "2=14-28 weeks. "
            "3=>28 weeks. "
            "Clinical Note: T1 = avoid MRI contrast; CT only if vital emergency."
        )
    )

    trauma: Optional[bool] = Field(
        default=None,
        description=(
            "Recent head trauma. "
            "True=trauma occurred, False=no trauma, None=not assessed. "
            "Clinical Note: Post-traumatic headache may indicate subdural hematoma. "
            "Consider CT if <24h since trauma or neurological signs."
        )
    )

    recent_pl_or_peridural: Optional[bool] = Field(
        default=None,
        description=(
            "Recent lumbar puncture or epidural (<2 weeks). "
            "True=recent procedure, False=no procedure, None=not assessed. "
            "Clinical Note: Postural headache after LP = post-dural puncture headache. "
            "Improved by lying down, worsened by standing."
        )
    )

    immunosuppression: Optional[bool] = Field(
        default=None,
        description=(
            "Immunocompromised state. "
            "True=immunosuppressed, False=immunocompetent, None=not assessed. "
            "Includes: HIV, chemotherapy, chronic steroids, transplant. "
            "Clinical Note: Lowers threshold for CNS infection workup."
        )
    )

    recent_pattern_change: Optional[bool] = Field(
        default=None,
        description=(
            "Recent change in chronic headache pattern. "
            "True=changed, False=stable, None=not assessed. "
            "Clinical Note: New symptoms in known chronic headache = red flag. "
            "May indicate secondary cause superimposed on primary."
        )
    )

    # =========================================================================
    # PRIORITY 1 - ONCOLOGICAL CONTEXT (High imaging priority)
    # =========================================================================

    cancer_history: Optional[bool] = Field(
        default=None,
        description=(
            "History of cancer (active or in remission). "
            "True=cancer history, False=no cancer, None=not assessed. "
            "Clinical Note: Headache + cancer = brain metastasis until excluded. "
            "Priority imaging with contrast."
        )
    )

    # =========================================================================
    # PRIORITY 2 - ASSOCIATED SYMPTOMS (Client requirements)
    # =========================================================================

    vertigo: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of vertigo. "
            "True=vertigo present, False=absent, None=not assessed. "
            "Clinical Note: Considered as neurological deficit if present. "
            "May indicate cerebellar lesion or vestibular pathology."
        )
    )

    tinnitus: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of tinnitus (ringing in ears). "
            "True=present, False=absent, None=not assessed. "
            "Clinical Note: Should be noted on prescription if present."
        )
    )

    visual_disturbance_type: Optional[Literal["stroboscopic", "blur", "blindness", "none"]] = Field(
        default=None,
        description=(
            "Type of visual disturbance. "
            "'stroboscopic': Flickering (migraine aura - benign). "
            "'blur': Blurred vision (may be HTIC). "
            "'blindness': Vision loss (neurological deficit - urgent). "
            "'none': No visual symptoms. "
            "None: Not assessed. "
            "Clinical Note: blindness = deficit, requires urgent imaging."
        )
    )

    joint_pain: Optional[bool] = Field(
        default=None,
        description=(
            "Presence of joint pain. "
            "True=present, False=absent, None=not assessed. "
            "Clinical Note: Joint pain + age >60 = evaluate for Giant Cell Arteritis."
        )
    )

    horton_criteria: Optional[bool] = Field(
        default=None,
        description=(
            "Criteria suggestive of Giant Cell Arteritis (Horton's disease). "
            "True=criteria present, False=absent, None=not assessed. "
            "Includes: jaw claudication, temporal artery abnormality, elevated ESR/CRP. "
            "Clinical Note: If positive, urgent ESR/CRP and temporal artery biopsy."
        )
    )

    # =========================================================================
    # PRIORITY 3 - PATIENT HISTORY
    # =========================================================================

    first_episode: Optional[bool] = Field(
        default=None,
        description=(
            "First ever headache episode. "
            "True=first episode, False=recurrent pattern, None=not assessed. "
            "Clinical Note: First severe headache in adult = higher suspicion for secondary cause."
        )
    )

    previous_workup: Optional[bool] = Field(
        default=None,
        description=(
            "Prior imaging workup performed. "
            "True=prior imaging exists, False=never imaged, None=not assessed. "
            "Clinical Note: Prior normal imaging may reduce need for repeat if stable."
        )
    )

    chronic_or_episodic: Optional[Literal["chronic_constant", "episodic_attacks", "unknown"]] = Field(
        default=None,
        description=(
            "Pattern of chronic headache. "
            "'chronic_constant': Continuous daily headache. "
            "'episodic_attacks': Discrete attacks with pain-free intervals. "
            "'unknown': Pattern not characterized. "
            "Clinical Note: Constant = consider medication overuse or secondary."
        )
    )

    # =========================================================================
    # PRIORITY 4 - LOCATION AND SPECIAL HISTORY
    # =========================================================================

    headache_location: Optional[str] = Field(
        default=None,
        description=(
            "Anatomical location of headache. "
            "Examples: 'frontal', 'temporal', 'occipital', 'diffuse', 'unilateral'. "
            "Clinical Note: Unilateral temporal in elderly = consider GCA."
        )
    )

    brain_infection_history: Optional[bool] = Field(
        default=None,
        description=(
            "History of CNS infection. "
            "True=prior infection, False=no history, None=not assessed. "
            "Includes: meningitis, encephalitis, brain abscess. "
            "Clinical Note: Increases risk of recurrent CNS infection."
        )
    )

    congenital_brain_malformation: Optional[bool] = Field(
        default=None,
        description=(
            "Known congenital brain malformation. "
            "True=malformation known, False=none known, None=not assessed. "
            "Includes: Chiari malformation, familial aneurysm. "
            "Clinical Note: May require specialized imaging protocols."
        )
    )

    persistent_or_resolving: Optional[Literal["persistent", "resolving", "fluctuating", "unknown"]] = Field(
        default=None,
        description=(
            "Trajectory of headache symptoms. "
            "'persistent': Constant or worsening. "
            "'resolving': Improving over time. "
            "'fluctuating': Variable intensity. "
            "'unknown': Trajectory unclear. "
            "Clinical Note: Persistent or worsening = higher concern."
        )
    )

    # =========================================================================
    # SYNTHESIS FIELDS
    # =========================================================================

    red_flag_context: List[str] = Field(
        default_factory=list,
        description=(
            "List of identified red flag contexts. "
            "Examples: 'age>50', 'cancer_history', 'immunosuppression'. "
            "Clinical Note: Each context lowers threshold for imaging."
        )
    )

    headache_profile: Literal["migraine_like", "tension_like", "htic_like", "unknown"] = Field(
        default="unknown",
        description=(
            "Clinical headache type classification. "
            "'migraine_like': Unilateral, pulsatile, photo/phonophobia, nausea. "
            "'tension_like': Bilateral, pressing, mild-moderate. "
            "'htic_like': Morning headache, vomiting, papilledema. "
            "'unknown': Cannot classify from available information."
        )
    )

    # =========================================================================
    # VALIDATORS
    # =========================================================================

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate age is within realistic clinical range.

        Args:
            v: Age value to validate

        Returns:
            Validated age or None

        Raises:
            ValueError: If age outside 0-120 range

        Clinical Note:
            Age validation is important as extreme values could indicate
            data entry errors. Age >50 with new acute headache is
            clinically significant (red flag for GCA, mass lesions).
        """
        if v is not None and (v < 0 or v > 120):
            raise ValueError("L'âge doit être entre 0 et 120 ans")
        return v

    @field_validator('duration_current_episode_hours')
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate duration is non-negative.

        Args:
            v: Duration value to validate

        Returns:
            Validated duration or None

        Raises:
            ValueError: If duration is negative

        Clinical Note:
            Duration is used to categorize temporal profile:
            - <168h (7 days): Acute
            - 168-2160h (7-90 days): Subacute
            - >2160h (90 days): Chronic
        """
        if v is not None and v < 0:
            raise ValueError("La durée doit être positive")
        return v

    # =========================================================================
    # CLINICAL DECISION SUPPORT METHODS
    # =========================================================================

    def has_red_flags(self) -> bool:
        """
        Check if the case presents any red flag indicators.

        Red flags are clinical findings that increase suspicion for
        serious secondary headache causes requiring urgent investigation.

        Red Flag Criteria Evaluated:
            1. Thunderclap onset - HSA until proven otherwise
            2. Fever - Infection (meningitis, abscess)
            3. Meningeal signs - Meningitis, SAH
            4. Focal neurological deficit - Stroke, mass, abscess
            5. Seizure - Epileptogenic lesion
            6. HTIC pattern - Mass, hydrocephalus, venous thrombosis
            7. Age >50 + acute - GCA, mass, vascular malformation
            8. Immunosuppression - Opportunistic CNS infection
            9. Cancer history - Brain metastasis
            10. Vertigo - Cerebellar/brainstem lesion
            11. Blindness - Acute visual deficit
            12. Horton's criteria - Giant cell arteritis

        Returns:
            True if at least one red flag is present

        Example:
            >>> case = HeadacheCase(onset="thunderclap")
            >>> case.has_red_flags()
            True

            >>> case = HeadacheCase(fever=True, meningeal_signs=True)
            >>> case.has_red_flags()
            True

        Clinical Note:
            The presence of ANY red flag should prompt urgent evaluation
            and consideration for imaging, even in young patients with
            otherwise benign presentation.
        """
        red_flags = [
            self.onset == "thunderclap",
            self.fever is True,
            self.meningeal_signs is True,
            self.neuro_deficit is True,
            self.seizure is True,
            self.htic_pattern is True,
            self.age is not None and self.age > 50 and self.profile == "acute",
            self.immunosuppression is True,
            self.cancer_history is True,
            self.vertigo is True,
            self.visual_disturbance_type == "blindness",
            self.horton_criteria is True,
            len(self.red_flag_context) > 0
        ]
        return any(red_flags)

    def is_emergency(self) -> bool:
        """
        Determine if the case requires immediate emergency evaluation.

        Emergency criteria represent life-threatening conditions where
        delay in diagnosis and treatment could result in death or
        permanent neurological damage.

        Emergency Criteria:
            1. Thunderclap onset: HSA until proven otherwise
               - Mortality 50% if untreated, 25% with treatment
               - CT within 6h detects 95% of SAH

            2. Fever + meningeal signs: Bacterial meningitis
               - Mortality 20-30% even with treatment
               - Every hour of delay increases mortality

            3. Acute neurological deficit: Stroke or mass effect
               - Stroke thrombolysis window <4.5h
               - Herniation can occur rapidly

            4. Acute seizure: Epileptogenic brain lesion
               - May indicate tumor, abscess, hemorrhage
               - Status epilepticus risk

            5. HTIC + deficit/seizure: Imminent herniation risk
               - Mass effect with deterioration
               - Requires immediate neurosurgical evaluation

        Returns:
            True if immediate emergency response required

        Clinical Note:
            Emergency cases should NOT leave the facility until
            appropriate imaging is obtained and serious conditions
            are excluded. Direct communication with radiology is
            recommended.

        Example:
            >>> case = HeadacheCase(onset="thunderclap", profile="acute")
            >>> case.is_emergency()
            True

            >>> case = HeadacheCase(fever=True, meningeal_signs=True)
            >>> case.is_emergency()
            True
        """
        emergency_criteria = [
            self.onset == "thunderclap",
            self.fever is True and self.meningeal_signs is True,
            self.neuro_deficit is True and self.profile == "acute",
            self.seizure is True and self.profile == "acute",
            self.htic_pattern is True and (self.neuro_deficit is True or self.seizure is True)
        ]
        return any(emergency_criteria)

    def get_missing_critical_fields(self) -> List[str]:
        """
        Identify critical clinical fields that have not been assessed.

        Critical fields are those required for safe clinical decision-making.
        Their absence (None value) should trigger clarification questions
        in the dialogue system.

        Priority Order (by clinical importance):
            1. onset - Determines emergency vs non-emergency pathway
            2. fever - Infection screening
            3. meningeal_signs - Meningitis detection
            4. neuro_deficit - Stroke/mass detection
            5. htic_pattern - Raised pressure detection
            6. seizure - Epileptogenic lesion

        Returns:
            List of field names that are None but clinically required

        Example:
            >>> case = HeadacheCase(age=35, onset="thunderclap")
            >>> missing = case.get_missing_critical_fields()
            >>> 'fever' in missing
            True
        """
        critical_fields = []

        if self.onset == "unknown":
            critical_fields.append("onset")
        if self.fever is None:
            critical_fields.append("fever")
        if self.meningeal_signs is None:
            critical_fields.append("meningeal_signs")
        if self.neuro_deficit is None:
            critical_fields.append("neuro_deficit")
        if self.htic_pattern is None:
            critical_fields.append("htic_pattern")
        if self.seizure is None:
            critical_fields.append("seizure")

        return critical_fields


class ImagingRecommendation(BaseModel):
    """
    Medical imaging recommendation with clinical justification.

    This model encapsulates the decision output from the clinical
    decision tree, including which imaging studies to perform,
    their urgency, and the medical rationale.

    Attributes:
        imaging: List of recommended imaging studies
        urgency: Urgency level for performing the imaging
        comment: Clinical justification for the recommendation
        applied_rule_id: ID of the decision rule that generated this recommendation

    Urgency Levels:
        - 'immediate': Life-threatening - imaging within minutes
          Examples: HSA, meningitis, acute stroke
        - 'urgent': Serious - imaging within hours (same day)
          Examples: GCA, brain abscess, subacute stroke
        - 'delayed': Non-emergent - imaging within days/weeks
          Examples: Chronic headache workup, follow-up studies
        - 'none': No imaging indicated
          Examples: Typical migraine, tension-type headache

    Valid Imaging Studies:
        CT Studies:
            - scanner_cerebral_sans_injection: Non-contrast CT
              Best for: acute hemorrhage, bone lesions
            - scanner_cerebral_avec_injection: Contrast CT
              Best for: tumor, abscess, enhancement patterns
            - angioscanner_cerebral: CT angiography
              Best for: vascular malformation, dissection

        MRI Studies:
            - IRM_cerebrale: Non-contrast MRI
              Best for: posterior fossa, white matter disease
            - IRM_cerebrale_avec_gadolinium: Contrast MRI
              Best for: tumor, infection, inflammation
            - ARM_cerebrale: MR angiography
              Best for: aneurysm, vascular malformation
            - venographie_IRM: MR venography
              Best for: cerebral venous thrombosis

        Other:
            - ponction_lombaire: Lumbar puncture
              Required for: meningitis, HSA with negative CT
            - fond_oeil: Fundoscopy
              Screening for: papilledema (HTIC)

    Clinical Notes:
        - CT is faster and preferred for emergency (hemorrhage detection)
        - MRI has better soft tissue resolution (tumors, posterior fossa)
        - Avoid gadolinium in pregnancy T1 and renal failure (eGFR <30)
        - LP contraindicated if HTIC suspected without prior imaging

    Example:
        >>> recommendation = ImagingRecommendation(
        ...     imaging=["scanner_cerebral_sans_injection", "ponction_lombaire"],
        ...     urgency="immediate",
        ...     comment="HSA suspected - CT to detect blood, LP if CT negative"
        ... )
        >>> recommendation.is_emergency()
        True
        >>> recommendation.requires_imaging()
        True

    See Also:
        - rules/headache_rules.json: Decision rules generating recommendations
        - French HAS imaging guidelines for headache
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    imaging: List[str] = Field(
        default_factory=list,
        description=(
            "List of recommended imaging studies. "
            "See class docstring for valid options and their indications."
        )
    )

    urgency: Literal["none", "urgent", "immediate", "delayed"] = Field(
        ...,
        description=(
            "Urgency level for imaging: "
            "'immediate' = life-threatening, within minutes; "
            "'urgent' = same day; "
            "'delayed' = can be scheduled; "
            "'none' = no imaging indicated"
        )
    )

    comment: str = Field(
        ...,
        min_length=1,
        description=(
            "Clinical justification for the recommendation. "
            "Should explain the clinical reasoning and suspected diagnosis."
        )
    )

    applied_rule_id: Optional[str] = Field(
        default=None,
        description=(
            "ID of the decision rule that generated this recommendation. "
            "Used for audit trail and quality assurance."
        )
    )

    @field_validator('imaging')
    @classmethod
    def validate_imaging_list(cls, v: List[str]) -> List[str]:
        """
        Validate that all imaging studies are recognized.

        Args:
            v: List of imaging study names

        Returns:
            Validated list of imaging studies

        Raises:
            ValueError: If unrecognized imaging study is included

        Clinical Note:
            This validation ensures only clinically valid imaging
            studies are recommended, preventing prescription errors.
        """
        valid_imaging = {
            # Standard format (snake_case)
            "scanner_cerebral_sans_injection",
            "scanner_cerebral_avec_injection",
            "angioscanner_cerebral",
            "angioscanner_TSA",
            "IRM_cerebrale",
            "IRM_cerebrale_avec_gadolinium",
            "ARM_cerebrale",
            "venographie_IRM",
            "ponction_lombaire",
            "fond_oeil",
            "doppler_TSA",
            "aucun",
            # Variant formats from rules JSON
            "irm_cerebrale",
            "angio_irm",
            "angio_irm_veineuse",
            "echographie_arteres_temporales",
            "biopsie_artere_temporale",
            "irm_rachis",
            "angioscanner"
        }

        for exam in v:
            if exam not in valid_imaging:
                raise ValueError(
                    f"Examen '{exam}' non reconnu. Examens valides: {valid_imaging}"
                )
        return v

    def is_emergency(self) -> bool:
        """
        Check if this recommendation indicates emergency.

        Returns:
            True if urgency is 'immediate'

        Clinical Note:
            Immediate urgency means the patient should not leave
            the facility until imaging is performed and interpreted.
        """
        return self.urgency == "immediate"

    def requires_imaging(self) -> bool:
        """
        Check if imaging is recommended.

        Returns:
            True if at least one imaging study is recommended
            (excluding 'aucun' which means no imaging)

        Example:
            >>> rec = ImagingRecommendation(imaging=["aucun"], urgency="none", comment="Normal exam")
            >>> rec.requires_imaging()
            False
        """
        return len(self.imaging) > 0 and "aucun" not in self.imaging


class ChatMessage(BaseModel):
    """
    Message in a clinical dialogue conversation.

    Represents a single message in the multi-turn dialogue between
    the healthcare provider and the clinical decision support system.

    Attributes:
        role: Source of the message (user, assistant, or system)
        content: Text content of the message
        timestamp: When the message was created
        metadata: Additional context (NLU confidence, extracted fields, etc.)

    Roles:
        - 'user': Message from healthcare provider (clinical input)
        - 'assistant': Response from the AI system
        - 'system': System notifications or context

    Metadata Examples:
        - confidence_score: NLU extraction confidence (0-1)
        - detected_fields: List of fields extracted from this message
        - extraction_method: How fields were extracted (rules, embedding, etc.)

    Example:
        >>> message = ChatMessage(
        ...     role="user",
        ...     content="Femme 35 ans, céphalée brutale depuis 2h"
        ... )
        >>> print(message.role, message.content)
        user Femme 35 ans, céphalée brutale depuis 2h
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Source of message: 'user' (provider), 'assistant' (AI), 'system'"
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Text content of the message"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when message was created"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (confidence scores, extracted entities, etc.)"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """
        Validate message content is not empty.

        Args:
            v: Message content

        Returns:
            Stripped message content

        Raises:
            ValueError: If content is empty after stripping
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Le contenu du message ne peut pas être vide")
        return stripped


class ChatResponse(BaseModel):
    """
    Response from the clinical decision support chatbot.

    Encapsulates the system's response including the message to display,
    current clinical state, and next steps in the dialogue.

    Attributes:
        message: Response text to display to the user
        session_id: Unique identifier for this dialogue session
        next_question: Follow-up question if more information needed
        headache_case: Current accumulated clinical case
        imaging_recommendation: Final recommendation (if dialogue complete)
        requires_more_info: Whether additional information is needed
        dialogue_complete: Whether dialogue has concluded
        confidence_score: Overall confidence in the assessment (0-1)

    Dialogue Flow:
        1. Initial: requires_more_info=True, next_question set
        2. Intermediate: Case accumulates, questions continue
        3. Complete: dialogue_complete=True, imaging_recommendation set

    Confidence Score Interpretation:
        - 0.0-0.4: Low confidence, many fields missing
        - 0.4-0.7: Medium confidence, critical fields may be missing
        - 0.7-0.9: Good confidence, minor fields may be missing
        - 0.9-1.0: High confidence, complete assessment

    Example:
        >>> response = ChatResponse(
        ...     message="J'ai bien compris. Le patient a-t-il de la fièvre?",
        ...     session_id="abc123",
        ...     next_question="fever",
        ...     requires_more_info=True,
        ...     confidence_score=0.65
        ... )
        >>> response.is_emergency_response()
        False
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Response message to display to user"
    )

    session_id: str = Field(
        ...,
        min_length=1,
        description="Unique session identifier for dialogue continuity"
    )

    next_question: Optional[str] = Field(
        default=None,
        description="Next question to ask if dialogue ongoing (field name)"
    )

    headache_case: Optional[HeadacheCase] = Field(
        default=None,
        description="Current accumulated clinical case state"
    )

    imaging_recommendation: Optional[ImagingRecommendation] = Field(
        default=None,
        description="Final imaging recommendation (when dialogue complete)"
    )

    requires_more_info: bool = Field(
        default=True,
        description="Whether additional clinical information is needed"
    )

    dialogue_complete: bool = Field(
        default=False,
        description="Whether dialogue has concluded with recommendation"
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in current assessment (0-1)"
    )

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """
        Validate confidence score is in valid range.

        Args:
            v: Confidence score

        Returns:
            Validated confidence score

        Raises:
            ValueError: If score outside [0, 1] range
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError("Le score de confiance doit être entre 0 et 1")
        return v

    def is_emergency_response(self) -> bool:
        """
        Check if response indicates emergency.

        Returns:
            True if imaging recommendation indicates immediate urgency

        Clinical Note:
            Emergency responses should be clearly communicated to
            the healthcare provider with immediate action items.
        """
        if self.imaging_recommendation:
            return self.imaging_recommendation.is_emergency()
        return False
