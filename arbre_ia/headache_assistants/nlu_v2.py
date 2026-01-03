"""
Module NLU v2 - Extraction basee sur le vocabulaire medical.

Ce module fournit un systeme NLU ameliore qui utilise un vocabulaire medical
centralise pour une extraction plus robuste et maintenable.

Differences avec nlu_base.py (v1)
---------------------------------
- v1 : Patterns regex codes en dur dans des dictionnaires
- v2 : Vocabulaire medical centralise avec groupes semantiques

Avantages de v2 :
- Gestion des synonymes : "fievre", "febrile", "hyperthermie" -> meme concept
- Expansion des acronymes : "RDN" -> "raideur de nuque" -> meningeal_signs
- Anti-patterns : "scotomes" bloque la detection HTIC (aura migraineuse)
- Meilleure tracabilite : terme matche, forme canonique, source dans les metadata

Fonctionnalites cliniques etendues
----------------------------------
1. Antecedent de cancer (cancer_history)
   - Critique pour le risque de metastases

2. Criteres de Horton (horton_criteria)
   - Indicateurs d'arterite a cellules geantes
   - Age >50 + sensibilite artere temporale

3. Localisation cephalee (headache_location)
   - Unilateral vs bilateral
   - Regions temporale, occipitale, frontale

4. Symptomes vestibulaires/auditifs
   - Detection vertiges, acouphenes
   - Peut indiquer pathologie fosse posterieure

Pipeline de detection
---------------------
1. Extraction demographiques (age, sexe)
2. Detection onset via MedicalVocabulary.detect_onset()
3. Classification profil (aigu/subaigu/chronique)
4. Red flags via vocabulaire (fievre, meninges, HTIC, deficit)
5. Contextes a risque (grossesse, immunosuppression, trauma)
6. Fonctionnalites etendues (cancer, Horton, visuel, vestibulaire)
7. Inference profil depuis onset/duree si necessaire

Exemple
-------
>>> from headache_assistants.nlu_v2 import NLUv2
>>> nlu = NLUv2()
>>> case, metadata = nlu.parse_free_text_to_case(
...     "Homme 65 ans, cephalee temporale, claudication machoire, VS elevee"
... )
>>> case.horton_criteria
True

Migration Guide
---------------
Replace nlu_base imports:
    # Before
    from headache_assistants.nlu_base import parse_free_text_to_case

    # After
    from headache_assistants.nlu_v2 import parse_free_text_to_case_v2

API Compatibility:
    - Same return type: Tuple[HeadacheCase, Dict[str, Any]]
    - Enriched metadata with detection_trace

Author: Medical NLU Team
Version: 2.0 (Vocabulary-based refactoring)
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .models import HeadacheCase


# =============================================================================
# CALCUL DE CONFIANCE AMÉLIORÉ
# =============================================================================

# Poids des champs par importance clinique (pour le calcul de confiance)
FIELD_WEIGHTS = {
    # Champs critiques (red flags) - poids élevé
    "onset": 2.0,           # Mode de début très important pour urgence
    "fever": 1.5,           # Fièvre = infection possible
    "meningeal_signs": 2.0, # Méningite = urgence
    "neuro_deficit": 2.0,   # Déficit = AVC/processus expansif
    "seizure": 1.5,         # Crise = pathologie grave
    "htic_pattern": 1.8,    # HTIC = urgence
    # Champs importants
    "trauma": 1.3,
    "pregnancy_postpartum": 1.3,
    "immunosuppression": 1.3,
    "age": 1.0,
    "profile": 1.0,
    "duration_current_episode_hours": 0.8,
    "intensity": 0.7,
    # Champs secondaires
    "sex": 0.3,
    "headache_profile": 0.5,
    "headache_location": 0.4,
    "cancer_history": 0.8,
    "horton_criteria": 0.8,
    "vertigo": 0.4,
    "tinnitus": 0.3,
}

# Champs essentiels à détecter pour un cas complet
ESSENTIAL_FIELDS = ["onset", "age", "profile"]
CRITICAL_RED_FLAGS = ["fever", "meningeal_signs", "neuro_deficit", "seizure", "htic_pattern"]


def calculate_overall_confidence(
    confidence_scores: Dict[str, float],
    detected_fields: List[str],
    text_length: int
) -> float:
    """
    Calcule une confiance globale améliorée basée sur plusieurs facteurs.

    Formule:
        overall = (weighted_avg * 0.5) + (coverage_score * 0.3) + (completeness_bonus * 0.2)

    Où:
        - weighted_avg: Moyenne pondérée des confiances par importance clinique
        - coverage_score: Proportion de champs essentiels détectés
        - completeness_bonus: Bonus si beaucoup de champs détectés vs longueur du texte

    Args:
        confidence_scores: Dict des scores de confiance par champ
        detected_fields: Liste des champs détectés
        text_length: Longueur du texte original (en caractères)

    Returns:
        Score de confiance globale entre 0.0 et 1.0
    """
    if not confidence_scores:
        return 0.0

    # 1. Moyenne pondérée des confiances par importance clinique
    weighted_sum = 0.0
    weight_total = 0.0

    for field, confidence in confidence_scores.items():
        weight = FIELD_WEIGHTS.get(field, 0.5)  # Poids par défaut = 0.5
        weighted_sum += confidence * weight
        weight_total += weight

    weighted_avg = weighted_sum / weight_total if weight_total > 0 else 0.0

    # 2. Score de couverture des champs essentiels
    essential_detected = sum(1 for f in ESSENTIAL_FIELDS if f in detected_fields)
    coverage_score = essential_detected / len(ESSENTIAL_FIELDS)

    # 3. Bonus de complétude (plus de champs = meilleure extraction)
    # Normaliser par la longueur du texte (un texte court ne peut pas avoir beaucoup de champs)
    expected_fields = min(3 + text_length // 50, 10)  # Entre 3 et 10 champs attendus
    actual_meaningful_fields = len([f for f in detected_fields if f not in ["sex"]])
    completeness_ratio = min(actual_meaningful_fields / expected_fields, 1.0)

    # 4. Bonus si des red flags sont explicitement détectés (positifs OU négatifs)
    red_flag_clarity = sum(1 for f in CRITICAL_RED_FLAGS if f in detected_fields) / len(CRITICAL_RED_FLAGS)

    # Formule finale avec pondération
    overall = (
        weighted_avg * 0.45 +           # Qualité des détections
        coverage_score * 0.25 +          # Couverture des essentiels
        completeness_ratio * 0.15 +      # Richesse de l'extraction
        red_flag_clarity * 0.15          # Clarté sur les red flags
    )

    # Clamp entre 0 et 1
    return max(0.0, min(1.0, overall))


from .medical_vocabulary import MedicalVocabulary, DetectionResult
from .pregnancy_utils import extract_pregnancy_trimester
from .nlu_base import (
    extract_age,
    extract_sex,
    extract_intensity_score,
    extract_duration_hours,
    detect_pattern,
    PROFILE_PATTERNS,
    RECENT_PL_OR_PERIDURAL_PATTERNS,
    HEADACHE_PROFILE_PATTERNS
)


class NLUv2:
    """
    Vocabulary-Based NLU for Clinical Headache Assessment.

    This class provides enhanced clinical text understanding using a centralized
    MedicalVocabulary that supports synonyms, abbreviations, and anti-patterns.

    Design Philosophy:
        - Centralized vocabulary for maintainability
        - Semantic grouping of related terms
        - Full traceability of detection decisions
        - Confidence scoring for clinical validation

    Attributes:
        vocab (MedicalVocabulary): The medical vocabulary instance used for
                                   all clinical term detection.

    Clinical Advantages:
        - Handles French medical abbreviations (RDN, HTIC, AVP, etc.)
        - Supports patient vernacular expressions
        - Anti-pattern awareness (scotomes ≠ HTIC)
        - Extended clinical features (Horton, cancer history, etc.)

    Example:
        >>> nlu = NLUv2()
        >>> case, meta = nlu.parse_free_text_to_case("Céphalée brutale fébrile")
        >>> print(case.onset, case.fever)
        thunderclap True
        >>> print(meta["detection_trace"]["fever"]["matched_term"])
        fébrile
    """

    def __init__(self):
        """
        Initialize NLU v2 with the centralized medical vocabulary.

        The MedicalVocabulary instance is created once and reused for all
        parsing operations, ensuring consistent terminology handling.
        """
        self.vocab = MedicalVocabulary()

    def parse_free_text_to_case(self, text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """
        Parse free-text clinical description into a structured HeadacheCase.

        This method provides enhanced detection using the centralized medical
        vocabulary, with full traceability of which terms triggered which
        clinical features.

        Detection Pipeline:
            1. **Demographics**: Age, sex extraction (reuses nlu_base)
            2. **Onset**: MedicalVocabulary.detect_onset() with synonyms
            3. **Profile**: Temporal classification (acute/subacute/chronic)
            4. **Red Flags**:
               - Fever via vocab.detect_fever()
               - Meningeal signs via vocab.detect_meningeal_signs()
               - HTIC via vocab.detect_htic() (with 0.70 confidence threshold)
               - Neurological deficit via vocab.detect_neuro_deficit()
               - Seizures via vocab.detect_seizure()
            5. **Risk Contexts**:
               - Pregnancy/postpartum via vocab.detect_pregnancy_postpartum()
               - Trauma via vocab.detect_trauma()
               - Immunosuppression via vocab.detect_immunosuppression()
            6. **Extended Features** (v2 enhancements):
               - Cancer history for metastases risk
               - Horton criteria for giant cell arteritis
               - Visual disturbance type
               - Vertigo and tinnitus
               - Headache location
            7. **Profile Inference**: Auto-classify if onset detected but profile unknown

        Args:
            text: Free-text clinical description in French.
                  Supports medical notation and patient expressions.

        Returns:
            Tuple[HeadacheCase, Dict[str, Any]]:
                - HeadacheCase: Validated model with all detected fields
                - metadata: Enhanced extraction details including:
                    - detected_fields: List of extracted field names
                    - confidence_scores: Per-field confidence values
                    - detection_trace: Detailed traceability with:
                        - matched_term: Exact text that matched
                        - canonical: Standard form of the concept
                        - source: Origin of the detection
                    - overall_confidence: Weighted average
                    - contradictions: Detected inconsistencies

        Clinical Safety Notes:
            - HTIC requires confidence ≥ 0.70 to avoid false positives
            - Red flags have no threshold (sensitivity prioritized)
            - Age remains None if not detected (triggers dialogue)

        See Also:
            - parse_free_text_to_case_v2: Wrapper function for compatibility
            - HybridNLU: Combines rules + embedding for best coverage
        """
        extracted_data = {}
        detected_fields = []
        confidence_scores = {}
        detection_trace = {}  # Nouveau: traçabilité des détections

        # ====================================================================
        # ÉTAPE 1: Extraction démographique 
        # ====================================================================
        age = extract_age(text)
        sex = extract_sex(text)

        if age is not None and 1 <= age <= 120:
            extracted_data["age"] = age
            detected_fields.append("age")
            confidence_scores["age"] = 0.9
        # Si âge non détecté, on ne met pas de valeur par défaut - reste None

        if sex is not None:
            extracted_data["sex"] = sex
            detected_fields.append("sex")
            confidence_scores["sex"] = 0.8
        else:
            extracted_data["sex"] = "Other"
            confidence_scores["sex"] = 0.0

        # ====================================================================
        # ÉTAPE 2: Détection ONSET avec vocabulaire médical
        # ====================================================================
        onset_result = self.vocab.detect_onset(text)
        if onset_result.detected:
            extracted_data["onset"] = onset_result.value
            detected_fields.append("onset")
            confidence_scores["onset"] = onset_result.confidence
            detection_trace["onset"] = {
                "matched_term": onset_result.matched_term,
                "canonical": onset_result.canonical_form,
                "source": onset_result.source
            }
        else:
            extracted_data["onset"] = "unknown"

        # ====================================================================
        # ÉTAPE 3: Détection PROFILE (réutilise nlu.py pour l'instant)
        # ====================================================================
        profile = detect_pattern(text, PROFILE_PATTERNS)
        if profile:
            extracted_data["profile"] = profile
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.8
        else:
            extracted_data["profile"] = "unknown"

        # ====================================================================
        # ÉTAPE 4: Durée et intensité (réutilise nlu.py)
        # ====================================================================
        duration = extract_duration_hours(text)
        if duration is not None:
            extracted_data["duration_current_episode_hours"] = duration
            detected_fields.append("duration_current_episode_hours")
            confidence_scores["duration_current_episode_hours"] = 0.9

        intensity = extract_intensity_score(text)
        if intensity is not None:
            extracted_data["intensity"] = intensity
            detected_fields.append("intensity")
            confidence_scores["intensity"] = 0.85

        # ====================================================================
        # ÉTAPE 5: RED FLAGS - Vocabulaire médical
        # ====================================================================

        # 5.1 FIÈVRE
        fever_result = self.vocab.detect_fever(text)
        if fever_result.detected:
            extracted_data["fever"] = fever_result.value
            detected_fields.append("fever")
            confidence_scores["fever"] = fever_result.confidence
            detection_trace["fever"] = {
                "matched_term": fever_result.matched_term,
                "canonical": fever_result.canonical_form,
                "source": fever_result.source
            }

        # 5.2 SYNDROME MÉNINGÉ
        meningeal_result = self.vocab.detect_meningeal_signs(text)
        if meningeal_result.detected:
            extracted_data["meningeal_signs"] = meningeal_result.value
            detected_fields.append("meningeal_signs")
            confidence_scores["meningeal_signs"] = meningeal_result.confidence
            detection_trace["meningeal_signs"] = {
                "matched_term": meningeal_result.matched_term,
                "canonical": meningeal_result.canonical_form,
                "source": meningeal_result.source
            }

        # 5.3 HTIC - SEUIL DE CONFIANCE pour éviter faux positifs
        # "pire le matin" seul (confiance 0.45) ne devrait PAS déclencher HTIC
        # HTIC nécessite: vomissements en jet OU œdème papillaire OU céphalée matutinale + autre signe
        HTIC_CONFIDENCE_THRESHOLD = 0.70  # Seuil pour valider HTIC
        htic_result = self.vocab.detect_htic(text)
        if htic_result.detected and htic_result.value is True:
            # Appliquer seuil de confiance
            if htic_result.confidence >= HTIC_CONFIDENCE_THRESHOLD:
                extracted_data["htic_pattern"] = True
                detected_fields.append("htic_pattern")
                confidence_scores["htic_pattern"] = htic_result.confidence
                detection_trace["htic_pattern"] = {
                    "matched_term": htic_result.matched_term,
                    "canonical": htic_result.canonical_form,
                    "source": htic_result.source
                }
            # Si confiance < seuil, ne pas détecter HTIC (éviter faux positifs)
            # Tracer quand même pour debugging
            elif htic_result.confidence > 0:
                detection_trace["htic_pattern_low_confidence"] = {
                    "matched_term": htic_result.matched_term,
                    "confidence": htic_result.confidence,
                    "reason": "below_threshold"
                }

        # 5.4 DÉFICIT NEUROLOGIQUE
        neuro_result = self.vocab.detect_neuro_deficit(text)
        if neuro_result.detected and neuro_result.value is True:
            extracted_data["neuro_deficit"] = True
            detected_fields.append("neuro_deficit")
            confidence_scores["neuro_deficit"] = neuro_result.confidence
            detection_trace["neuro_deficit"] = {
                "matched_term": neuro_result.matched_term,
                "canonical": neuro_result.canonical_form,
                "source": neuro_result.source
            }

        # 5.5 CRISES D'ÉPILEPSIE
        seizure_result = self.vocab.detect_seizure(text)
        if seizure_result.detected and seizure_result.value is True:
            extracted_data["seizure"] = True
            detected_fields.append("seizure")
            confidence_scores["seizure"] = seizure_result.confidence
            detection_trace["seizure"] = {
                "matched_term": seizure_result.matched_term,
                "canonical": seizure_result.canonical_form,
                "source": seizure_result.source
            }

        # ====================================================================
        # ÉTAPE 6: CONTEXTES À RISQUE - Vocabulaire médical
        # ====================================================================

        # 6.1 GROSSESSE / POST-PARTUM
        pregnancy_result = self.vocab.detect_pregnancy_postpartum(text)
        if pregnancy_result.detected:
            extracted_data["pregnancy_postpartum"] = pregnancy_result.value
            detected_fields.append("pregnancy_postpartum")
            confidence_scores["pregnancy_postpartum"] = pregnancy_result.confidence
            detection_trace["pregnancy_postpartum"] = {
                "matched_term": pregnancy_result.matched_term,
                "canonical": pregnancy_result.canonical_form,
                "source": pregnancy_result.source
            }

            # 6.1.1 TRIMESTRE DE GROSSESSE (si enceinte)
            # Extraction robuste: semaines, mois, jours, SA, trimestre explicite
            if pregnancy_result.value is True:  # Si enceinte (pas post-partum)
                trimester = extract_pregnancy_trimester(text)
                if trimester is not None:
                    extracted_data["pregnancy_trimester"] = trimester
                    detected_fields.append("pregnancy_trimester")
                    confidence_scores["pregnancy_trimester"] = 0.85
                    detection_trace["pregnancy_trimester"] = {
                        "trimester": trimester,
                        "source": "robust_extraction"
                    }

        # 6.2 TRAUMATISME
        trauma_result = self.vocab.detect_trauma(text)
        if trauma_result.detected:
            extracted_data["trauma"] = trauma_result.value
            detected_fields.append("trauma")
            confidence_scores["trauma"] = trauma_result.confidence
            detection_trace["trauma"] = {
                "matched_term": trauma_result.matched_term,
                "canonical": trauma_result.canonical_form,
                "source": trauma_result.source
            }

        # 6.3 PL / PÉRIDURALE récente (réutilise nlu.py)
        recent_pl = detect_pattern(text, RECENT_PL_OR_PERIDURAL_PATTERNS)
        if recent_pl is not None:
            extracted_data["recent_pl_or_peridural"] = recent_pl
            detected_fields.append("recent_pl_or_peridural")
            confidence_scores["recent_pl_or_peridural"] = 0.9

        # 6.4 IMMUNODÉPRESSION
        immunosup_result = self.vocab.detect_immunosuppression(text)
        if immunosup_result.detected:
            extracted_data["immunosuppression"] = immunosup_result.value
            detected_fields.append("immunosuppression")
            confidence_scores["immunosuppression"] = immunosup_result.confidence
            detection_trace["immunosuppression"] = {
                "matched_term": immunosup_result.matched_term,
                "canonical": immunosup_result.canonical_form,
                "source": immunosup_result.source
            }

        # 6.5 CHANGEMENT RÉCENT DE PATTERN (céphalées chroniques)
        pattern_change_result = self.vocab.detect_pattern_change(text)
        if pattern_change_result.detected:
            extracted_data["recent_pattern_change"] = pattern_change_result.value
            detected_fields.append("recent_pattern_change")
            confidence_scores["recent_pattern_change"] = pattern_change_result.confidence
            detection_trace["recent_pattern_change"] = {
                "matched_term": pattern_change_result.matched_term,
                "canonical": pattern_change_result.canonical_form,
                "source": pattern_change_result.source
            }

        # 6.6 CONTEXTE ONCOLOGIQUE (PRIORITÉ 1 - impact décision scanner/IRM)
        cancer_result = self.vocab.detect_cancer_history(text)
        if cancer_result.detected:
            extracted_data["cancer_history"] = cancer_result.value
            detected_fields.append("cancer_history")
            confidence_scores["cancer_history"] = cancer_result.confidence
            detection_trace["cancer_history"] = {
                "matched_term": cancer_result.matched_term,
                "canonical": cancer_result.canonical_form,
                "source": cancer_result.source
            }

        # 6.7 VERTIGES (PRIORITÉ 2)
        vertigo_result = self.vocab.detect_vertigo(text)
        if vertigo_result.detected:
            extracted_data["vertigo"] = vertigo_result.value
            detected_fields.append("vertigo")
            confidence_scores["vertigo"] = vertigo_result.confidence
            detection_trace["vertigo"] = {
                "matched_term": vertigo_result.matched_term,
                "canonical": vertigo_result.canonical_form,
                "source": vertigo_result.source
            }

        # 6.8 ACOUPHÈNES (PRIORITÉ 2)
        tinnitus_result = self.vocab.detect_tinnitus(text)
        if tinnitus_result.detected:
            extracted_data["tinnitus"] = tinnitus_result.value
            detected_fields.append("tinnitus")
            confidence_scores["tinnitus"] = tinnitus_result.confidence
            detection_trace["tinnitus"] = {
                "matched_term": tinnitus_result.matched_term,
                "canonical": tinnitus_result.canonical_form,
                "source": tinnitus_result.source
            }

        # 6.9 TROUBLES VISUELS - TYPE (PRIORITÉ 2)
        visual_result = self.vocab.detect_visual_disturbance_type(text)
        if visual_result.detected:
            extracted_data["visual_disturbance_type"] = visual_result.value
            detected_fields.append("visual_disturbance_type")
            confidence_scores["visual_disturbance_type"] = visual_result.confidence
            detection_trace["visual_disturbance_type"] = {
                "matched_term": visual_result.matched_term,
                "canonical": visual_result.canonical_form,
                "source": visual_result.source
            }

        # 6.10 DOULEURS ARTICULAIRES (PRIORITÉ 2 - lié Horton)
        joint_pain_result = self.vocab.detect_joint_pain(text)
        if joint_pain_result.detected:
            extracted_data["joint_pain"] = joint_pain_result.value
            detected_fields.append("joint_pain")
            confidence_scores["joint_pain"] = joint_pain_result.confidence
            detection_trace["joint_pain"] = {
                "matched_term": joint_pain_result.matched_term,
                "canonical": joint_pain_result.canonical_form,
                "source": joint_pain_result.source
            }

        # 6.11 CRITÈRES HORTON (PRIORITÉ 2)
        horton_result = self.vocab.detect_horton_criteria(text)
        if horton_result.detected:
            extracted_data["horton_criteria"] = horton_result.value
            detected_fields.append("horton_criteria")
            confidence_scores["horton_criteria"] = horton_result.confidence
            detection_trace["horton_criteria"] = {
                "matched_term": horton_result.matched_term,
                "canonical": horton_result.canonical_form,
                "source": horton_result.source
            }

        # 6.12 LOCALISATION CÉPHALÉE (PRIORITÉ 4)
        location_result = self.vocab.detect_headache_location(text)
        if location_result.detected:
            extracted_data["headache_location"] = location_result.value
            detected_fields.append("headache_location")
            confidence_scores["headache_location"] = location_result.confidence
            detection_trace["headache_location"] = {
                "matched_term": location_result.matched_term,
                "canonical": location_result.canonical_form,
                "source": location_result.source
            }

        # ====================================================================
        # ÉTAPE 7: PROFIL CLINIQUE CÉPHALÉE (réutilise nlu.py)
        # ====================================================================
        import re
        headache_profile_scores = {}
        text_lower = text.lower()

        for profile_type, pattern_list in HEADACHE_PROFILE_PATTERNS.items():
            score = 0
            for pattern in pattern_list:
                if re.search(pattern, text_lower):
                    score += 1
            if score > 0:
                headache_profile_scores[profile_type] = score

        # Bonus tension_like si absence explicite signes migraineux
        if any(re.search(pattern, text_lower) for pattern in [r"Ø\s*(?:n/?v|photo|phono)", r"sans\s+n/?v", r"pas\s+de\s+n/?v", r"aucun s associé"]):
            headache_profile_scores["tension_like"] = headache_profile_scores.get("tension_like", 0) + 3

        if headache_profile_scores:
            headache_profile = max(headache_profile_scores, key=headache_profile_scores.get)
            extracted_data["headache_profile"] = headache_profile
            detected_fields.append("headache_profile")
            confidence_scores["headache_profile"] = 0.75
        else:
            extracted_data["headache_profile"] = "unknown"

        # ====================================================================
        # ÉTAPE 8: Construction HeadacheCase
        # ====================================================================
        try:
            case = HeadacheCase(**extracted_data)
        except Exception as e:
            # On ne met plus de valeur par défaut pour l'âge - il reste None
            case = HeadacheCase(
                age=extracted_data.get("age"),  # None si non détecté
                sex=extracted_data.get("sex", "Other")
            )
            confidence_scores["validation_error"] = str(e)

        # ====================================================================
        # ÉTAPE 9: Inférence automatique profile depuis onset/durée
        # ====================================================================
        if case.onset != "unknown" and case.profile == "unknown":
            if case.onset == "thunderclap":
                case = case.model_copy(update={"profile": "acute"})
                detected_fields.append("profile")
                confidence_scores["profile"] = 0.95
            elif case.onset == "progressive":
                if case.duration_current_episode_hours:
                    if case.duration_current_episode_hours < 168:
                        case = case.model_copy(update={"profile": "acute"})
                    elif case.duration_current_episode_hours < 2160:
                        case = case.model_copy(update={"profile": "subacute"})
                    else:
                        case = case.model_copy(update={"profile": "chronic"})
                    detected_fields.append("profile")
                    confidence_scores["profile"] = 0.9
                else:
                    if 'semaine' in text.lower():
                        case = case.model_copy(update={"profile": "subacute"})
                        confidence_scores["profile"] = 0.75
                    else:
                        case = case.model_copy(update={"profile": "acute"})
                        confidence_scores["profile"] = 0.6
                    detected_fields.append("profile")
            elif case.onset == "chronic":
                case = case.model_copy(update={"profile": "chronic"})
                detected_fields.append("profile")
                confidence_scores["profile"] = 0.9

        # Inférence depuis durée seule si profile toujours unknown
        if case.profile == "unknown" and case.duration_current_episode_hours is not None:
            if case.duration_current_episode_hours < 168:
                case = case.model_copy(update={"profile": "acute"})
            elif case.duration_current_episode_hours < 2160:
                case = case.model_copy(update={"profile": "subacute"})
            else:
                case = case.model_copy(update={"profile": "chronic"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.85

        # ====================================================================
        # ÉTAPE 10: Métadonnées enrichies
        # ====================================================================
        text_norm = text.lower()
        contradictions = []

        # Détection contradictions
        if case.onset in ['thunderclap', 'progressive']:
            if 'progressive' in text_norm and ('brutal' in text_norm or 'thunderclap' in text_norm):
                contradictions.append('onset_conflicting')

        if case.fever is True and any(word in text_norm for word in ['apyretique', 'apyr', 'sans fievre']):
            contradictions.append('fever_conflicting')

        if case.duration_current_episode_hours and case.profile != "unknown":
            if case.duration_current_episode_hours < 168 and case.profile == "chronic":
                contradictions.append('duration_profile_mismatch')
            elif case.duration_current_episode_hours >= 2160 and case.profile == "acute":
                contradictions.append('duration_profile_mismatch')

        # Calcul de confiance amélioré
        overall_conf = calculate_overall_confidence(
            confidence_scores=confidence_scores,
            detected_fields=detected_fields,
            text_length=len(text)
        )

        metadata = {
            "detected_fields": detected_fields,
            "confidence_scores": confidence_scores,
            "overall_confidence": overall_conf,
            "extraction_method": "vocabulary_based_v2",
            "timestamp": datetime.now().isoformat(),
            "original_text": text,
            "contradictions": contradictions,
            "detection_trace": detection_trace  # Nouveau: traçabilité complète
        }

        return case, metadata


# ============================================================================
# FONCTION WRAPPER POUR COMPATIBILITÉ AVEC NLU.PY
# ============================================================================

def parse_free_text_to_case_v2(text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
    """
    Convenience function for vocabulary-based NLU parsing.

    This function provides a simple interface compatible with nlu_base.py,
    creating a fresh NLUv2 instance for each call.

    For repeated parsing (e.g., batch processing), consider creating
    a single NLUv2 instance and reusing it:

        nlu = NLUv2()
        for text in texts:
            case, meta = nlu.parse_free_text_to_case(text)

    Args:
        text: Free-text clinical description in French.

    Returns:
        Tuple[HeadacheCase, Dict[str, Any]]:
            - HeadacheCase: Validated model with extracted fields
            - metadata: Enhanced extraction details with detection_trace

    Example:
        >>> case, meta = parse_free_text_to_case_v2("H 45a, céphalée brutale")
        >>> print(case.onset)
        thunderclap

    See Also:
        - NLUv2: The underlying class with vocabulary-based detection
        - parse_free_text_to_case_hybrid: For rules + embedding
    """
    nlu = NLUv2()
    return nlu.parse_free_text_to_case(text)
