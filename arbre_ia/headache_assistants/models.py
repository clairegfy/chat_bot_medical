"""
Modeles de donnees pour le systeme d'aide a la decision medicale.

Ce module definit les modeles Pydantic utilises dans le systeme :
- HeadacheCase : representation d'un cas clinique de cephalee
- ImagingRecommendation : recommandation d'imagerie avec justification
- ChatMessage / ChatResponse : gestion du dialogue

Le systeme vise a reduire les ~30% de prescriptions d'imagerie inappropriees
en guidant le medecin selon les recommandations HAS.

Logique 3 etats pour les champs booleens :
- True : signe present (confirme)
- False : signe absent (confirme)
- None : non evalue (on doit poser la question)

C'est important car "fievre inconnue" != "pas de fievre".
"""

from typing import Optional, Literal, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class HeadacheCase(BaseModel):
    """
    Representation d'un cas clinique de cephalee.

    Contient toutes les infos necessaires pour naviguer dans l'arbre de decision
    et determiner si une imagerie est necessaire. Base sur les guidelines HAS.

    Les champs Optional[bool] utilisent la logique 3 etats :
    - True = signe present
    - False = signe absent
    - None = pas encore evalue (declenchera une question)

    Exemple:
        >>> case = HeadacheCase(age=35, sex="F", onset="thunderclap")
        >>> case.has_red_flags()
        True
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False
    )

    # ==========================================================================
    # DONNEES DEMOGRAPHIQUES
    # ==========================================================================

    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        description="Age du patient en annees. None si pas encore collecte."
    )

    sex: Literal["M", "F", "Other"] = Field(
        default="Other",
        description="Sexe du patient. M=Homme, F=Femme, Other=Non precise."
    )

    # ==========================================================================
    # PROFIL TEMPOREL
    # ==========================================================================

    profile: Literal["acute", "chronic", "subacute", "unknown"] = Field(
        default="unknown",
        description=(
            "Profil temporel de la cephalee. "
            "acute: <7 jours, subacute: 7-90 jours, chronic: >90 jours."
        )
    )

    onset: Literal["thunderclap", "progressive", "chronic", "unknown"] = Field(
        default="unknown",
        description=(
            "Mode d'installation. "
            "thunderclap: intensite max en <1min (URGENCE), "
            "progressive: installation en heures/jours."
        )
    )

    duration_current_episode_hours: Optional[float] = Field(
        default=None,
        ge=0,
        description="Duree de l'episode actuel en heures."
    )

    intensity: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Intensite de la douleur sur l'echelle EVA (0-10)."
    )

    # ==========================================================================
    # RED FLAGS - SIGNES D'ALARME
    # Logique 3 etats : True=present, False=absent, None=non evalue
    # ==========================================================================

    fever: Optional[bool] = Field(
        default=None,
        description=(
            "Presence de fievre (>=38C). "
            "Fievre + cephalee = infection jusqu'a preuve du contraire."
        )
    )

    meningeal_signs: Optional[bool] = Field(
        default=None,
        description=(
            "Signes meninges (Kernig, Brudzinski, raideur de nuque). "
            "Si present = URGENCE."
        )
    )

    neuro_deficit: Optional[bool] = Field(
        default=None,
        description=(
            "Deficit neurologique focal (hemiparesie, aphasie, diplopie...). "
            "Attention: l'aura migraineuse n'est PAS un deficit focal."
        )
    )

    seizure: Optional[bool] = Field(
        default=None,
        description="Crise d'epilepsie. Si oui = rechercher lesion cerebrale."
    )

    htic_pattern: Optional[bool] = Field(
        default=None,
        description=(
            "Signes d'HTIC (hypertension intracranienne). "
            "Signes forts: vomissements en jet, oedeme papillaire. "
            "Signes faibles (seuls insuffisants): cephalee matinale, toux."
        )
    )

    # ==========================================================================
    # CONTEXTES A RISQUE
    # ==========================================================================

    pregnancy_postpartum: Optional[bool] = Field(
        default=None,
        description=(
            "Grossesse ou post-partum (<6 semaines). "
            "Si oui = rechercher TVC (thrombose veineuse cerebrale)."
        )
    )

    pregnancy_trimester: Optional[int] = Field(
        default=None,
        ge=1,
        le=3,
        description="Trimestre de grossesse (1, 2 ou 3). Influence le choix d'imagerie."
    )

    trauma: Optional[bool] = Field(
        default=None,
        description="Traumatisme cranien recent. Si oui = scanner pour eliminer hematome."
    )

    recent_pl_or_peridural: Optional[bool] = Field(
        default=None,
        description=(
            "Ponction lombaire ou peridurale recente (<2 semaines). "
            "Cephalee positionnelle = breche durale."
        )
    )

    immunosuppression: Optional[bool] = Field(
        default=None,
        description=(
            "Immunodepression (VIH, chimio, corticoides au long cours...). "
            "Abaisse le seuil pour rechercher infection SNC."
        )
    )

    recent_pattern_change: Optional[bool] = Field(
        default=None,
        description=(
            "Changement recent du pattern de cephalee chronique. "
            "Nouveaux symptomes sur cephalee connue = red flag."
        )
    )

    # ==========================================================================
    # CONTEXTE ONCOLOGIQUE
    # ==========================================================================

    cancer_history: Optional[bool] = Field(
        default=None,
        description=(
            "Antecedent de cancer (actif ou en remission). "
            "Cephalee + cancer = metastase jusqu'a preuve du contraire."
        )
    )

    # ==========================================================================
    # SYMPTOMES ASSOCIES
    # ==========================================================================

    vertigo: Optional[bool] = Field(
        default=None,
        description="Vertige. Considere comme deficit neurologique si present."
    )

    tinnitus: Optional[bool] = Field(
        default=None,
        description="Acouphenes. A noter sur l'ordonnance si present."
    )

    visual_disturbance_type: Optional[Literal["stroboscopic", "blur", "blindness", "none"]] = Field(
        default=None,
        description=(
            "Type de trouble visuel. "
            "stroboscopic: scintillements (aura - benin), "
            "blur: flou (peut etre HTIC), "
            "blindness: perte de vision (deficit = urgent)."
        )
    )

    joint_pain: Optional[bool] = Field(
        default=None,
        description="Douleurs articulaires. Si age >60 = penser a Horton."
    )

    horton_criteria: Optional[bool] = Field(
        default=None,
        description=(
            "Criteres evocateurs de maladie de Horton. "
            "Claudication machoire, artere temporale anormale, VS/CRP elevees."
        )
    )

    # ==========================================================================
    # ANTECEDENTS
    # ==========================================================================

    first_episode: Optional[bool] = Field(
        default=None,
        description="Premier episode de cephalee. Si oui = plus de suspicion pour cause secondaire."
    )

    previous_workup: Optional[bool] = Field(
        default=None,
        description="Bilan d'imagerie anterieur deja realise."
    )

    chronic_or_episodic: Optional[Literal["chronic_constant", "episodic_attacks", "unknown"]] = Field(
        default=None,
        description=(
            "Pattern de la cephalee chronique. "
            "chronic_constant: tous les jours, "
            "episodic_attacks: crises avec intervalles libres."
        )
    )

    # ==========================================================================
    # LOCALISATION ET ANTECEDENTS PARTICULIERS
    # ==========================================================================

    headache_location: Optional[str] = Field(
        default=None,
        description="Localisation anatomique (frontal, temporal, occipital, diffus...)."
    )

    brain_infection_history: Optional[bool] = Field(
        default=None,
        description="Antecedent d'infection du SNC (meningite, encephalite, abces)."
    )

    congenital_brain_malformation: Optional[bool] = Field(
        default=None,
        description="Malformation cerebrale connue (Chiari, anevrisme familial...)."
    )

    persistent_or_resolving: Optional[Literal["persistent", "resolving", "fluctuating", "unknown"]] = Field(
        default=None,
        description=(
            "Evolution des symptomes. "
            "persistent: stable ou aggravation, "
            "resolving: amelioration."
        )
    )

    # ==========================================================================
    # CHAMPS DE SYNTHESE
    # ==========================================================================

    red_flag_context: List[str] = Field(
        default_factory=list,
        description="Liste des contextes a risque identifies (age>50, cancer, etc.)."
    )

    headache_profile: Literal["migraine_like", "tension_like", "htic_like", "unknown"] = Field(
        default="unknown",
        description=(
            "Classification clinique du type de cephalee. "
            "migraine_like: unilateral, pulsatile, photo/phonophobie. "
            "tension_like: bilateral, en casque, modere."
        )
    )

    # ==========================================================================
    # VALIDATEURS
    # ==========================================================================

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """Verifie que l'age est dans une plage realiste (0-120)."""
        if v is not None and (v < 0 or v > 120):
            raise ValueError("L'âge doit être entre 0 et 120 ans")
        return v

    @field_validator('duration_current_episode_hours')
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        """Verifie que la duree est positive."""
        if v is not None and v < 0:
            raise ValueError("La durée doit être positive")
        return v

    # ==========================================================================
    # METHODES D'AIDE A LA DECISION
    # ==========================================================================

    def has_red_flags(self) -> bool:
        """
        Verifie si le cas presente des signes d'alarme (red flags).

        Red flags evalues :
        - Onset thunderclap (HSA)
        - Fievre, signes meninges
        - Deficit neurologique focal
        - Crise d'epilepsie
        - Signes d'HTIC
        - Age >50 + cephalee aigue
        - Immunodepression, cancer
        - Vertigo, cecite
        - Criteres de Horton

        Returns:
            True si au moins un red flag present
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
        Determine si le cas necessite une prise en charge en urgence immediate.

        Criteres d'urgence vitale :
        - Thunderclap (HSA jusqu'a preuve du contraire)
        - Fievre + signes meninges (meningite)
        - Deficit neurologique aigu (AVC, masse)
        - Crise d'epilepsie aigue
        - HTIC + deficit ou crise (risque d'engagement)

        Returns:
            True si urgence immediate
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
        Identifie les champs critiques non encore evalues.

        Ces champs sont necessaires pour une decision sure.
        S'ils sont None, le dialogue doit poser la question.

        Returns:
            Liste des noms de champs manquants
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
    Recommandation d'imagerie avec justification clinique.

    Contient le resultat de l'arbre de decision : quels examens prescrire,
    avec quel niveau d'urgence, et pourquoi.

    Niveaux d'urgence :
    - immediate : urgence vitale, imagerie dans les minutes
    - urgent : le jour meme
    - delayed : programmable sous quelques jours
    - none : pas d'imagerie necessaire

    Exemple:
        >>> rec = ImagingRecommendation(
        ...     imaging=["scanner_cerebral_sans_injection"],
        ...     urgency="immediate",
        ...     comment="HSA suspectee"
        ... )
        >>> rec.is_emergency()
        True
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    imaging: List[str] = Field(
        default_factory=list,
        description="Liste des examens d'imagerie recommandes."
    )

    urgency: Literal["none", "urgent", "immediate", "delayed"] = Field(
        ...,
        description="Niveau d'urgence pour l'imagerie."
    )

    comment: str = Field(
        ...,
        min_length=1,
        description="Justification clinique de la recommandation."
    )

    applied_rule_id: Optional[str] = Field(
        default=None,
        description="ID de la regle qui a genere cette recommandation (pour tracabilite)."
    )

    @field_validator('imaging')
    @classmethod
    def validate_imaging_list(cls, v: List[str]) -> List[str]:
        """Verifie que les examens sont dans la liste des examens reconnus."""
        valid_imaging = {
            # Formats standards
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
            # Variantes du JSON de regles
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
        """Retourne True si urgence immediate."""
        return self.urgency == "immediate"

    def requires_imaging(self) -> bool:
        """Retourne True si au moins un examen est recommande (hors 'aucun')."""
        return len(self.imaging) > 0 and "aucun" not in self.imaging


class ChatMessage(BaseModel):
    """
    Message dans le dialogue clinique.

    Represente un echange entre le medecin (user) et le systeme (assistant).

    Roles :
    - user : message du medecin (description clinique)
    - assistant : reponse du systeme
    - system : notifications systeme
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Source du message : user, assistant ou system."
    )

    content: str = Field(
        ...,
        min_length=1,
        description="Contenu textuel du message."
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Horodatage du message."
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadonnees additionnelles (scores de confiance, champs extraits...)."
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Verifie que le contenu n'est pas vide."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Le contenu du message ne peut pas être vide")
        return stripped


class ChatResponse(BaseModel):
    """
    Reponse du chatbot d'aide a la decision.

    Encapsule la reponse du systeme avec l'etat actuel du cas clinique
    et les prochaines etapes du dialogue.

    Flux du dialogue :
    1. Initial : requires_more_info=True, next_question defini
    2. Intermediaire : le cas s'enrichit, questions continuent
    3. Final : dialogue_complete=True, imaging_recommendation definie
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Message de reponse a afficher."
    )

    session_id: str = Field(
        ...,
        min_length=1,
        description="Identifiant unique de la session de dialogue."
    )

    next_question: Optional[str] = Field(
        default=None,
        description="Prochaine question a poser (nom du champ)."
    )

    headache_case: Optional[HeadacheCase] = Field(
        default=None,
        description="Etat actuel du cas clinique."
    )

    imaging_recommendation: Optional[ImagingRecommendation] = Field(
        default=None,
        description="Recommandation finale (quand dialogue termine)."
    )

    requires_more_info: bool = Field(
        default=True,
        description="True si des informations supplementaires sont necessaires."
    )

    dialogue_complete: bool = Field(
        default=False,
        description="True si le dialogue est termine."
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de confiance global (0-1)."
    )

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Verifie que le score est entre 0 et 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Le score de confiance doit être entre 0 et 1")
        return v

    def is_emergency_response(self) -> bool:
        """Retourne True si la recommandation indique une urgence immediate."""
        if self.imaging_recommendation:
            return self.imaging_recommendation.is_emergency()
        return False
