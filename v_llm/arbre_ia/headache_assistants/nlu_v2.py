"""Module NLU v2 avec détection robuste basée sur le vocabulaire médical centralisé.

Ce module remplace les patterns regex par un système sémantique basé sur:
- Dictionnaire médical avec synonymes/acronymes (medical_vocabulary.py)
- Détection contextuelle avec scoring de confiance
- Gestion des anti-patterns (évite faux positifs)
- Traçabilité complète des détections

Migration depuis nlu.py:
    - Même interface (parse_free_text_to_case)
    - Détection plus robuste et maintenable
    - Métadonnées enrichies (confiance, termes matchés)
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .models import HeadacheCase
from .medical_vocabulary import MedicalVocabulary, DetectionResult
from .nlu import (
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
    """Module NLU v2 avec vocabulaire médical centralisé.

    Utilise MedicalVocabulary pour une détection robuste et traçable
    des concepts médicaux.
    """

    def __init__(self):
        """Initialise le module NLU avec le vocabulaire médical."""
        self.vocab = MedicalVocabulary()

    def parse_free_text_to_case(self, text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """Analyse un texte libre et extrait un cas de céphalée structuré.

        Version améliorée avec détection robuste basée sur vocabulaire médical.

        Args:
            text: Description en texte libre du cas clinique

        Returns:
            Tuple contenant:
            - HeadacheCase: Le cas structuré
            - dict: Métadonnées d'extraction enrichies

        Améliorations vs nlu.py:
            - Détection d'acronymes robuste (TCC, AVP, RDN, etc.)
            - Gestion des synonymes multiples
            - Anti-patterns pour éviter faux positifs
            - Scores de confiance par champ
            - Traçabilité (terme matché, source)
        """
        extracted_data = {}
        detected_fields = []
        confidence_scores = {}
        detection_trace = {}  # Nouveau: traçabilité des détections

        # ====================================================================
        # ÉTAPE 1: Extraction démographique (réutilise nlu.py)
        # ====================================================================
        age = extract_age(text)
        sex = extract_sex(text)

        if age is not None and 1 <= age <= 120:
            extracted_data["age"] = age
            detected_fields.append("age")
            confidence_scores["age"] = 0.9
        else:
            extracted_data["age"] = 50
            confidence_scores["age"] = 0.1

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
            case = HeadacheCase(
                age=extracted_data.get("age", 50),
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

        metadata = {
            "detected_fields": detected_fields,
            "confidence_scores": confidence_scores,
            "overall_confidence": sum(confidence_scores.values()) / max(len(confidence_scores), 1),
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
    """Wrapper pour compatibilité avec l'interface nlu.py.

    Utilise le nouveau système basé sur vocabulaire médical.

    Args:
        text: Description en texte libre

    Returns:
        Tuple (HeadacheCase, metadata) compatible avec nlu.py
    """
    nlu = NLUv2()
    return nlu.parse_free_text_to_case(text)
