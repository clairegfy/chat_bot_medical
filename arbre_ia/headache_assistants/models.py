"""Modèles de données pour le chatbot médical des céphalées.

Ce module définit les structures de données Pydantic utilisées pour représenter:
- Les cas cliniques de céphalées (HeadacheCase)
- Les recommandations d'imagerie (ImagingRecommendation)
- Les messages de chat et réponses (ChatMessage, ChatResponse)

Tous les modèles sont basés sur les règles médicales définies dans headache_rules.txt
et permettent une validation stricte des données.
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class HeadacheCase(BaseModel):
    """Représente un cas clinique de céphalée avec tous les critères décisionnels.
    
    Ce modèle capture les informations essentielles pour naviguer dans l'arbre
    de décision médical et déterminer les examens d'imagerie appropriés.
    
    Attributes:
        age: Âge du patient en années
        sex: Sexe du patient
        profile: Profil temporel de la céphalée (aiguë, chronique, subaiguë)
        onset: Type de début de la céphalée
        duration_current_episode_hours: Durée de l'épisode actuel en heures
        fever: Présence de fièvre
        meningeal_signs: Présence de signes méningés (raideur nuque, Kernig, Brudzinski)
        neuro_deficit: Présence de déficit neurologique focal
        seizure: Survenue de crise d'épilepsie
        htic_pattern: Pattern évocateur d'hypertension intracrânienne
        pregnancy_postpartum: Contexte de grossesse ou post-partum
        trauma: Notion de traumatisme crânien
        recent_pl_or_peridural: Ponction lombaire ou péridurale récente
        immunosuppression: Patient immunodéprimé
        red_flag_context: Liste des contextes à risque détectés
        headache_profile: Profil clinique de la céphalée
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False
    )
    
    # Données démographiques
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        description="Âge du patient en années (None si non renseigné)"
    )
    sex: Literal["M", "F", "Other"] = Field(
        default="Other",
        description="Sexe du patient"
    )
    
    # Profil temporel
    profile: Literal["acute", "chronic", "subacute", "unknown"] = Field(
        default="unknown",
        description="Profil temporel de la céphalée: aiguë (<7j), subaiguë (7j-3mois), chronique (>3mois)"
    )
    onset: Literal["thunderclap", "progressive", "chronic", "unknown"] = Field(
        default="unknown",
        description="Type de début: coup de tonnerre (<1min), progressif (heures/jours), chronique"
    )
    duration_current_episode_hours: Optional[float] = Field(
        default=None,
        ge=0,
        description="Durée de l'épisode actuel en heures"
    )
    intensity: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Intensité de la douleur sur échelle 0-10 (0=aucune, 10=maximale)"
    )
    
    # Signes cliniques majeurs (red flags)
    fever: Optional[bool] = Field(
        default=None,
        description="Présence de fièvre (température >38°C)"
    )
    meningeal_signs: Optional[bool] = Field(
        default=None,
        description="Signes méningés: raideur nuque, signe de Kernig, signe de Brudzinski"
    )
    neuro_deficit: Optional[bool] = Field(
        default=None,
        description="Déficit neurologique focal: hémiparésie, aphasie, hémianopsie, etc."
    )
    seizure: Optional[bool] = Field(
        default=None,
        description="Crise d'épilepsie (focale ou généralisée)"
    )
    htic_pattern: Optional[bool] = Field(
        default=None,
        description="Pattern d'HTIC: céphalée matutinale, vomissements en jet, aggravation toux/effort"
    )
    
    # Contextes à risque
    pregnancy_postpartum: Optional[bool] = Field(
        default=None,
        description="Grossesse en cours ou post-partum (<6 semaines)"
    )
    pregnancy_trimester: Optional[int] = Field(
        default=None,
        ge=1,
        le=3,
        description="Trimestre de grossesse si enceinte (1=<14 sem, 2=14-28 sem, 3=>28 sem)"
    )
    trauma: Optional[bool] = Field(
        default=None,
        description="Traumatisme crânien récent"
    )
    recent_pl_or_peridural: Optional[bool] = Field(
        default=None,
        description="Ponction lombaire ou péridurale récente (<2 semaines)"
    )
    immunosuppression: Optional[bool] = Field(
        default=None,
        description="Immunodépression (VIH, chimiothérapie, corticoïdes au long cours)"
    )
    recent_pattern_change: Optional[bool] = Field(
        default=None,
        description="Changement récent du pattern d'une céphalée chronique connue (aggravation, nouveaux symptômes)"
    )

    # PRIORITÉ 1 - Contexte oncologique
    cancer_history: Optional[bool] = Field(
        default=None,
        description="Antécédents oncologiques (cancer actif ou en rémission)"
    )

    # PRIORITÉ 2 - Questions complémentaires selon client
    vertigo: Optional[bool] = Field(
        default=None,
        description="Présence de vertiges (à considérer comme déficit moteur si présent)"
    )
    tinnitus: Optional[bool] = Field(
        default=None,
        description="Présence d'acouphènes (à préciser sur ordonnance)"
    )
    visual_disturbance_type: Optional[Literal["stroboscopic", "blur", "blindness", "none"]] = Field(
        default=None,
        description="Type de troubles visuels: stroboscopique (aura), flou, cécité (=déficit moteur), aucun"
    )
    joint_pain: Optional[bool] = Field(
        default=None,
        description="Douleurs articulaires (si oui + âge>60, évaluer Horton)"
    )
    horton_criteria: Optional[bool] = Field(
        default=None,
        description="Arguments pour maladie de Horton (claudication mâchoire, artères temporales, ESR/CRP élevée)"
    )

    # PRIORITÉ 3 - Historique patient
    first_episode: Optional[bool] = Field(
        default=None,
        description="Premier épisode de céphalée vs céphalées récurrentes connues"
    )
    previous_workup: Optional[bool] = Field(
        default=None,
        description="Bilan déjà réalisé (imagerie antérieure)"
    )
    chronic_or_episodic: Optional[Literal["chronic_constant", "episodic_attacks", "unknown"]] = Field(
        default=None,
        description="Céphalées constantes chroniques vs par crises épisodiques"
    )

    # PRIORITÉ 4 - Localisation et ATCD
    headache_location: Optional[str] = Field(
        default=None,
        description="Localisation de la céphalée (frontale, temporale, occipitale, diffuse, unilatérale, etc.)"
    )
    brain_infection_history: Optional[bool] = Field(
        default=None,
        description="Antécédents d'infections cérébrales (méningite, encéphalite, abcès)"
    )
    congenital_brain_malformation: Optional[bool] = Field(
        default=None,
        description="Malformation congénitale cérébrale connue (Chiari, anévrisme familial, etc.)"
    )
    persistent_or_resolving: Optional[Literal["persistent", "resolving", "fluctuating", "unknown"]] = Field(
        default=None,
        description="Céphalée persistante, résolutive, ou fluctuante"
    )

    # Synthèse des red flags
    red_flag_context: list[str] = Field(
        default_factory=list,
        description="Liste des contextes à risque identifiés (âge>50, cancer, etc.)"
    )
    
    # Profil clinique de la céphalée
    headache_profile: Literal["migraine_like", "tension_like", "htic_like", "unknown"] = Field(
        default="unknown",
        description="Profil clinique: migraineux, tension, HTIC, ou indéterminé"
    )
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        """Valide que l'âge est dans une plage réaliste."""
        if v is not None and (v < 0 or v > 120):
            raise ValueError("L'âge doit être entre 0 et 120 ans")
        return v
    
    @field_validator('duration_current_episode_hours')
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        """Valide que la durée est positive."""
        if v is not None and v < 0:
            raise ValueError("La durée doit être positive")
        return v
    
    def has_red_flags(self) -> bool:
        """Vérifie si le cas présente des signes d'alarme (red flags).

        Returns:
            True si au moins un red flag est présent
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
            self.cancer_history is True,  # Contexte oncologique
            self.vertigo is True,  # Vertiges = déficit neurologique
            self.visual_disturbance_type == "blindness",  # Cécité = déficit
            self.horton_criteria is True,  # Suspicion Horton
            len(self.red_flag_context) > 0
        ]
        return any(red_flags)
    
    def is_emergency(self) -> bool:
        """Détermine si le cas nécessite une prise en charge urgente immédiate.
        
        Returns:
            True si urgence vitale (HSA, méningite, HTIC sévère)
        """
        emergency_criteria = [
            self.onset == "thunderclap",
            self.fever is True and self.meningeal_signs is True,
            self.neuro_deficit is True and self.profile == "acute",
            self.seizure is True and self.profile == "acute",
            self.htic_pattern is True and (self.neuro_deficit is True or self.seizure is True)
        ]
        return any(emergency_criteria)


class ImagingRecommendation(BaseModel):
    """Recommandation d'examens d'imagerie médicale.
    
    Ce modèle encapsule la décision concernant les examens à réaliser,
    leur urgence, et la justification médicale.
    
    Attributes:
        imaging: Liste des examens recommandés (scanner, IRM, ponction lombaire, etc.)
        urgency: Niveau d'urgence de la réalisation des examens
        comment: Justification médicale et contexte de la recommandation
        applied_rule_id: Identifiant de la règle de décision appliquée
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    imaging: list[str] = Field(
        default_factory=list,
        description="Liste des examens d'imagerie recommandés"
    )
    urgency: Literal["none", "urgent", "immediate", "delayed"] = Field(
        ...,
        description=(
            "Urgence: none (pas d'imagerie), delayed (consultation programmée), "
            "urgent (dans les heures), immediate (urgence vitale)"
        )
    )
    comment: str = Field(
        ...,
        min_length=1,
        description="Justification médicale de la recommandation"
    )
    applied_rule_id: Optional[str] = Field(
        default=None,
        description="ID de la règle de décision qui a généré cette recommandation"
    )
    
    @field_validator('imaging')
    @classmethod
    def validate_imaging_list(cls, v: list[str]) -> list[str]:
        """Valide la liste des examens d'imagerie."""
        valid_imaging = {
            # Format snake_case
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
            # Variantes du JSON (headache_rules.json)
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
        """Vérifie si la recommandation concerne une urgence.
        
        Returns:
            True si urgence immédiate
        """
        return self.urgency == "immediate"
    
    def requires_imaging(self) -> bool:
        """Vérifie si une imagerie est nécessaire.
        
        Returns:
            True si au moins un examen est recommandé
        """
        return len(self.imaging) > 0 and "aucun" not in self.imaging


class ChatMessage(BaseModel):
    """Message dans une conversation de chat.
    
    Représente un message envoyé par l'utilisateur (patient) ou le système (assistant).
    
    Attributes:
        role: Rôle de l'émetteur du message (user ou assistant)
        content: Contenu textuel du message
        timestamp: Horodatage du message
        metadata: Métadonnées optionnelles (confiance NLU, champs extraits, etc.)
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Rôle de l'émetteur: user (patient), assistant (IA), system (info système)"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Contenu textuel du message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Horodatage du message"
    )
    metadata: dict[str, str | float | bool | None] = Field(
        default_factory=dict,
        description="Métadonnées optionnelles (confiance, entités extraites, etc.)"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Valide que le contenu n'est pas vide après nettoyage."""
        if not v.strip():
            raise ValueError("Le contenu du message ne peut pas être vide")
        return v.strip()


class ChatResponse(BaseModel):
    """Réponse du chatbot à un message utilisateur.
    
    Encapsule la réponse de l'assistant avec les informations contextuelles
    nécessaires pour continuer le dialogue.
    
    Attributes:
        message: Message de réponse à afficher à l'utilisateur
        session_id: Identifiant de session du dialogue
        next_question: Prochaine question à poser (si dialogue en cours)
        headache_case: État actuel du cas clinique
        imaging_recommendation: Recommandation d'imagerie (si disponible)
        requires_more_info: Indique si plus d'informations sont nécessaires
        dialogue_complete: Indique si le dialogue est terminé
        confidence_score: Score de confiance de l'évaluation (0-1)
    """
    
    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    message: str = Field(
        ...,
        min_length=1,
        description="Message de réponse de l'assistant"
    )
    session_id: str = Field(
        ...,
        min_length=1,
        description="Identifiant unique de la session de dialogue"
    )
    next_question: Optional[str] = Field(
        default=None,
        description="Prochaine question à poser au patient (si dialogue en cours)"
    )
    headache_case: Optional[HeadacheCase] = Field(
        default=None,
        description="État actuel du cas clinique collecté"
    )
    imaging_recommendation: Optional[ImagingRecommendation] = Field(
        default=None,
        description="Recommandation d'imagerie (si évaluation complète)"
    )
    requires_more_info: bool = Field(
        default=True,
        description="Indique si plus d'informations sont nécessaires"
    )
    dialogue_complete: bool = Field(
        default=False,
        description="Indique si le dialogue est terminé et une recommandation peut être faite"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de confiance de l'évaluation actuelle (0-1)"
    )
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Valide que le score de confiance est entre 0 et 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Le score de confiance doit être entre 0 et 1")
        return v
    
    def is_emergency_response(self) -> bool:
        """Vérifie si la réponse indique une urgence médicale.
        
        Returns:
            True si urgence détectée
        """
        if self.imaging_recommendation:
            return self.imaging_recommendation.is_emergency()
        return False
