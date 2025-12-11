"""Gestionnaire de dialogue conversationnel pour le chatbot médical des céphalées.

Ce module orchestre la conversation avec le patient en:
1. Extrayant les informations via NLU (parse_free_text_to_case)
2. Identifiant les champs manquants critiques selon headache_rules.txt
3. Posant des questions ciblées pour compléter le cas
4. Appliquant le moteur de décision (decide_imaging) quand les infos sont suffisantes

Le dialogue suit une stratégie de questions progressives basée sur les red flags
et les conditions nécessaires pour matcher les règles médicales.
"""

import uuid
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from .models import ChatMessage, ChatResponse, HeadacheCase, ImagingRecommendation
from .nlu_hybrid import HybridNLU
from .nlu_base import (
    suggest_clarification_questions,
    get_missing_critical_fields
)
from .rules_engine import decide_imaging, load_rules
from .logging_config import get_logger, log_nlu_parsing, log_error_with_context


def get_critical_fields_for_rules() -> Dict[str, List[str]]:
    return {
        "emergency_red_flags": [
            "onset",  # thunderclap = HSA/SVCR
            "fever",  # + meningeal_signs = méningite
            "meningeal_signs",  # + fever = méningite
            "intensity",  # HSA nécessite intensity >= 7
        ],
        "htic_signs": [
            "htic_pattern",  # Céphalée matutinale, vomissements en jet
            "neuro_deficit",  # Déficit focal
            "seizure",  # Crise d'épilepsie
        ],
        "temporal_profile": [
            "profile",  # acute/subacute/chronic
            "onset",  # thunderclap/progressive/chronic
        ],
        "risk_contexts": [
            "pregnancy_postpartum",  # TVC
            "trauma",  # Hématome
            "immunosuppression",  # Infections opportunistes
        ],
        "headache_classification": [
            "headache_profile",  # migraine_like/tension_like/htic_like
        ]
    }


def prioritize_missing_fields(missing_fields: List[str], case: HeadacheCase) -> List[str]:
    """Priorise les champs manquants selon leur importance médicale.
    
    Les red flags d'urgence vitale sont prioritaires, suivis des signes HTIC,
    puis du profil temporel, et enfin de la classification.
    
    Args:
        missing_fields: Liste des champs manquants
        case: Cas actuel (peut influencer la priorité)
        
    Returns:
        Liste triée des champs par priorité décroissante
    """
    priority_order = {
        # Urgence vitale (à poser EN PREMIER)
        "onset": 100,  # Coup de tonnerre = urgence absolue
        "fever": 95,
        "meningeal_signs": 95,
        "intensity": 90,
        
        # Signes HTIC et neurologiques
        "htic_pattern": 85,
        "neuro_deficit": 85,
        "seizure": 80,
        
        # Profil temporel (aide au diagnostic)
        "profile": 70,

        # Changement de pattern (CRITIQUE pour chronique)
        "recent_pattern_change": 65,  # Si chronique, demander changement avant autres red flags

        # Contextes à risque
        "pregnancy_postpartum": 60,
        "trauma": 55,
        "recent_pl_or_peridural": 52,  # Céphalée post-PL = diagnostic spécifique
        "immunosuppression": 50,
        
        # Classification (moins urgent)
        "headache_profile": 30,
        "duration_current_episode_hours": 20,
    }
    
    # Trier par priorité décroissante
    sorted_fields = sorted(
        missing_fields,
        key=lambda f: priority_order.get(f, 0),
        reverse=True
    )
    
    return sorted_fields


def generate_question_for_field(field_name: str, case: HeadacheCase) -> str:
    """Génère une question naturelle pour un champ manquant.
    
    Adapte la formulation selon le contexte déjà connu du cas.
    
    Args:
        field_name: Nom du champ à questionner
        case: Cas actuel avec contexte
        
    Returns:
        Question formulée de manière naturelle
        
    """
    questions_map = {
        "onset": (
            "Comment la douleur a-t-elle débuté ? "
            "Soudainement comme un coup de tonnerre, progressivement, "
            "ou s'agit-il d'une douleur chronique ?)"
        ),
        "profile": (
            "Depuis combien de temps le patient a-t-il cette céphalée ? "
            "Quelques heures/jours, plusieurs semaines, ou des mois/années ?"
        ),
        "intensity": (
            "Sur une échelle de 0 à 10, quelle est l'intensité de la douleur ? "
        ),
        "fever": (
            "Le patient a-t-il de la fièvre ?"
        ),
        "meningeal_signs": (
            "Le patient présente-t-il une raideur de la nuque ? "
            "Difficulté ou douleur à plier la tête vers l'avant"
        ),
        "htic_pattern": (
            "La douleur est-elle pire le matin au réveil ? "
            "Y a-t-il des vomissements en jet ou une aggravation lors de la toux ou lors d'un effort ?"
        ),
        "neuro_deficit": (
            "Le patient présente-t-il des faiblesses musculaires, des troubles de la parole, "
            "ou des troubles visuels ?"
        ),
        "seizure": (
            "Le patient a-t-il eu une crise d'épilepsie ou des convulsions ?"
        ),
        "pregnancy_postpartum": (
            "La patiente est-elle enceinte ou a-t-elle accouché récemment ? "
            "(moins de 6 semaines)"
        ),
        "trauma": (
            "Le patient a-t-il eu un traumatisme crânien récent ? "
        ),
        "recent_pl_or_peridural": (
            "Le patient a-t-il eu une ponction lombaire ou péridurale récemment ? "
        ),
        "immunosuppression": (
            "Le patient est-il immunodéprimé ? "
            "(VIH, chimiothérapie, traitement immunosuppresseur, greffe)"
        ),
        "recent_pattern_change": (
            "Y a-t-il eu un changement récent dans les céphalées du patient ? "
            "(aggravation, nouveaux symptômes)"
        ),
        "headache_profile": (
            "Pouvez-vous décrire la douleur du patient ? "
            "(unilatérale ou des deux côtés, pulsatile/battante, en pression/étau, "
            "avec nausées/vomissements, photophobie ?)"
        ),
        "duration_current_episode_hours": (
            "Depuis combien de temps exactement le patient a-t-il cette douleur ? "
            "(en heures ou jours)"
        ),
    }
    
    return questions_map.get(
        field_name,
        f"Pouvez-vous me donner plus d'informations sur: {field_name} ?"
    )


def merge_cases(current_case: HeadacheCase, new_info: HeadacheCase) -> HeadacheCase:
    """Fusionne un cas existant avec des nouvelles informations.
    
    Les nouvelles informations écrasent les anciennes (sauf si None ou "unknown").
    
    Args:
        current_case: Cas actuel avec informations déjà collectées
        new_info: Nouvelles informations extraites du dernier message
        
    Returns:
        Cas fusionné
    """
    # Convertir en dict
    current_dict = current_case.model_dump(exclude_none=True)
    new_dict = new_info.model_dump(exclude_none=True)
    
    # Ne pas écraser les valeurs connues avec "unknown"
    # Pour onset, profile, headache_profile qui ont "unknown" comme valeur par défaut
    for field in ['onset', 'profile', 'headache_profile']:
        if field in new_dict and new_dict[field] == "unknown":
            # Si l'ancienne valeur existe et n'est pas "unknown", la garder
            if field in current_dict and current_dict[field] != "unknown":
                new_dict.pop(field)  # Retirer la nouvelle valeur "unknown"
    
    # Fusionner
    merged = {**current_dict, **new_dict}
    
    # Créer nouveau cas
    merged_case = HeadacheCase(**merged)
    
    # Inférer le profile depuis onset si onset est connu mais profile n'est pas
    if merged_case.onset and merged_case.profile == "unknown":
        merged_case = _infer_profile_from_onset(merged_case)
    
    return merged_case

# détecte oui/non dans l'input utilisateur lors du dialogue
def _interpret_yes_no_response(text: str, field_name: str, current_case: HeadacheCase) -> HeadacheCase:
    import re
    
    text_lower = text.lower().strip()
    
    # Détecter oui/non avec correspondance de mots entiers
    is_yes = bool(re.search(r'\b(oui|yes|o)\b', text_lower))
    is_no = bool(re.search(r'\b(non|no|n|aucun|aucune|pas)\b', text_lower))
    
    # Si c'est un champ booléen
    boolean_fields = [
        'fever', 'meningeal_signs', 'neuro_deficit', 'seizure', 
        'htic_pattern', 'pregnancy_postpartum', 'trauma', 
        'recent_pl_or_peridural', 'immunosuppression'
    ]
    
    if field_name in boolean_fields:
        # Prioriser "non" car plus spécifique que "oui" ex: pas de fièvre
        if is_no:
            return current_case.model_copy(update={field_name: False})
        elif is_yes:
            return current_case.model_copy(update={field_name: True})
    
    # Si c'est une intensité, extraire la valeure
    if field_name == 'intensity':
        numbers = re.findall(r'\d+', text)
        if numbers:
            intensity_val = int(numbers[0])
            if 0 <= intensity_val <= 10:
                return current_case.model_copy(update={'intensity': intensity_val})
    
    # Sinon, retourner le cas inchangé
    return current_case    # Inférer le profile depuis onset si onset est connu mais profile n'est pas
    if merged_case.onset and merged_case.profile == "unknown":
        merged_case = _infer_profile_from_onset(merged_case)
    
    return merged_case


def _infer_profile_from_onset(case: HeadacheCase) -> HeadacheCase:
    """Infère le profil temporel depuis le mode de début.
    
    Logique d'inférence:
    - thunderclap → TOUJOURS aigue (urgence vitale)
    - progressive + durée connue → aigue/sous aigue/chronique selon durée
    - progressive sans durée → aigue par défaut (principe de précaution)
    - chronic → chronique
    
    Args:
        case: Cas avec onset défini
        
    Returns:
        Cas avec profile mis à jour
    """
    new_profile = case.profile
    
    if case.onset == "thunderclap":
        # Coup de tonnerre = toujours aigu (HSA, urgence vitale)
        new_profile = "acute"
    elif case.onset == "progressive":
        # Progressif peut être aigu ou subaigu selon durée
        if case.duration_current_episode_hours:
            if case.duration_current_episode_hours < 168:  # < 7 jours
                new_profile = "acute"
            elif case.duration_current_episode_hours < 2160:  # < 3 mois (90 jours)
                new_profile = "subacute"
            else:
                new_profile = "chronic"
        else:
            # Sans durée précise, on considère aigu par précaution
            # (meilleur sensibilité pour urgences)
            new_profile = "acute"
    elif case.onset == "chronic":
        # Onset chronique = profil chronique
        new_profile = "chronic"
    
    # Retourner une copie avec le profile mis à jour
    return case.model_copy(update={"profile": new_profile})


def should_end_dialogue(case: HeadacheCase, missing_fields: List[str]) -> Tuple[bool, str]:
    """Détermine si le dialogue peut se terminer et une décision être prise.
    
    Critères:
    1. Aucun champ critique manquant
    2. OU urgence détectée nécessitant décision immédiate
    3. OU profil chronique sans red flags VÉRIFIÉS (tous doivent être explicitement False)
    4. OU timeout conversationnel (trop de tours sans progrès)
    
    Args:
        case: Cas actuel
        missing_fields: Champs critiques manquants
        
    Returns:
        Tuple (can_end: bool, reason: str)
    """
    # Cas 1: Tous les champs critiques sont renseignés
    if len(missing_fields) == 0:
        return True, "complete"
    
    # Cas 2: Urgence détectée (onset thunderclap, fever+meningeal, etc.)
    if case.onset == "thunderclap":
        return True, "emergency_thunderclap"
    
    if case.fever is True and case.meningeal_signs is True:
        return True, "emergency_meningitis"
    
    if case.htic_pattern is True and case.neuro_deficit is True:
        return True, "emergency_htic"
    
    # Cas 3: Profil chronic - Logique différenciée si il y a eu un changement récemment ou non
    if case.profile == "chronic" or case.onset == "chronic":
        # Cas 3A: Chronic STABLE (pas de changement récent) -> Pas d'urgence
        if case.recent_pattern_change is False:
            # Céphalée chronique stable connue sans changement = PAS D'URGENCE
            # Pas besoin de vérifier tous les red flags
            return True, "chronic_stable_no_urgency"

        # Cas 3B: Chronic AGGRAVÉ (changement récent détecté) -> Vérifier red flags
        if case.recent_pattern_change is True:
            # Changement récent = nécessite évaluation des red flags
            # Ne pas terminer tant que les red flags ne sont pas vérifiés
            red_flag_fields = [
                case.fever, case.meningeal_signs, case.neuro_deficit,
                case.seizure, case.htic_pattern, case.trauma
            ]
            all_verified = all(flag is not None for flag in red_flag_fields)
            any_positive = any(flag is True for flag in red_flag_fields)

            # Si aggravé + red flag positif = urgence
            if any_positive:
                return True, "chronic_with_new_red_flags"

            # Si tous vérifiés et négatifs = peut terminer
            if all_verified:
                return True, "chronic_aggravated_no_red_flags"

        # Cas 3C: Chronic mais changement non encore demandé (None)
        # Si recent_pattern_change est None, demander d'abord ce champ
        if case.recent_pattern_change is None:
            # Ne pas terminer, il faut poser la question du changement
            return False, "needs_pattern_change_assessment"

        # Cas 3D: Legacy - tous red flags vérifiés négatifs (ancien comportement)
        red_flag_fields = [
            case.fever, case.meningeal_signs, case.neuro_deficit,
            case.seizure, case.htic_pattern, case.trauma
        ]
        all_verified = all(flag is not None for flag in red_flag_fields)
        any_positive = any(flag is True for flag in red_flag_fields)

        if all_verified and not any_positive:
            return True, "chronic_no_red_flags"
    
    # Sinon, continuer le dialogue
    return False, "needs_more_info"


# management de session
# Stockage en mémoire des sessions actives
_active_sessions: Dict[str, Dict[str, Any]] = {}

# Instance globale de HybridNLU (éviter de recharger l'embedding à chaque appel)
_hybrid_nlu: Optional[HybridNLU] = None

def _get_hybrid_nlu() -> HybridNLU:
    """Récupère l'instance globale de HybridNLU (singleton).

    Returns:
        Instance de HybridNLU initialisée

    Raises:
        RuntimeError: Si l'initialisation du NLU échoue
    """
    global _hybrid_nlu
    logger = get_logger()

    if _hybrid_nlu is None:
        try:
            logger.debug("Initialisation du NLU hybride...")
            _hybrid_nlu = HybridNLU()
            logger.info("NLU hybride initialisé avec succès")
        except Exception as e:
            log_error_with_context(e, "initialisation NLU hybride")
            raise RuntimeError(f"Impossible d'initialiser le NLU: {e}") from e

    return _hybrid_nlu


def get_or_create_session(session_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """Récupère ou crée une session de dialogue.
    
    Args:
        session_id: ID de session existant (None pour créer nouvelle session)
        
    Returns:
        Tuple (session_id, session_data)
    """
    if session_id and session_id in _active_sessions:
        return session_id, _active_sessions[session_id]
    
    # Créer nouvelle session
    new_session_id = session_id or str(uuid.uuid4())
    _active_sessions[new_session_id] = {
        "created_at": datetime.now(),
        "current_case": None,
        "message_count": 0,
        "extraction_metadata": {},
        "asked_fields": [],  # Champs déjà questionnés 
        "last_asked_field": None,  # Dernier champ questionné pour interpréter oui/non
        "accumulated_special_patterns": [],  # Patterns spéciaux détectés durant toute la session
    }
    
    return new_session_id, _active_sessions[new_session_id]

# fonction principale de dialogue
def handle_user_message(
    history: List[ChatMessage],
    new_message: ChatMessage,
    session_id: Optional[str] = None
) -> ChatResponse:
    """Gère un nouveau message utilisateur et retourne la réponse du système.
    
    Workflow:
    1. Récupérer/créer la session
    2. Extraire informations via NLU depuis le nouveau message
    3. Fusionner avec le cas en cours
    4. Identifier champs manquants critiques
    5. Décider:
       - Si complet ou urgence → appliquer decide_imaging()
       - Sinon → poser question ciblée pour champ prioritaire
    
    Args:
        history: Historique des messages de la conversation
        new_message: Nouveau message de l'utilisateur
        session_id: ID de session (optionnel)
        
    Returns:
        ChatResponse avec message, état du cas, et recommandation si applicable
        
    """
    
    # 1 gestion de id de session
    session_id, session_data = get_or_create_session(session_id)
    session_data["message_count"] += 1
    
   
    # 2 extraction via la NLU
    user_text = new_message.content
    
    # Initialiser extracted_case 
    extracted_case = None
    extraction_metadata = {}
    
    # Si le dernier message était une question, interpréter la réponse en contexte
    last_asked = session_data.get("last_asked_field")
    if last_asked and session_data["current_case"] is not None:
        # Tenter d'interpréter la réponse oui/non/nombre
        current_case_before = session_data["current_case"]
        current_case = _interpret_yes_no_response(user_text, last_asked, current_case_before)
        
        # Si l'interprétation a fonctionné (le cas a changé), utiliser ce cas
        if current_case != current_case_before:
            session_data["current_case"] = current_case
            session_data["last_asked_field"] = None  # Réinitialiser
            # Créer un extracted_case vide pour la cohérence
            extracted_case = current_case_before
        else:
            # Sinon, parser normalement avec HybridNLU (utilise embedding si nécessaire)
            hybrid_nlu = _get_hybrid_nlu()
            try:
                extracted_case, extraction_metadata = hybrid_nlu.parse_free_text_to_case(user_text)
            except Exception as e:
                log_error_with_context(e, "parsing NLU", {"text_length": len(user_text)})
                # Fallback: créer un cas vide plutôt que crasher
                extracted_case = HeadacheCase()
                extraction_metadata = {"error": str(e), "overall_confidence": 0.0}

            session_data["extraction_metadata"] = extraction_metadata

            # Logger le parsing NLU
            log_nlu_parsing(
                text=user_text,
                detected_fields=extraction_metadata.get("detected_fields", []),
                confidence=extraction_metadata.get("overall_confidence", 0.0),
                method=extraction_metadata.get("method", "hybrid")
            )

            # Accumuler les patterns spéciaux détectés
            new_patterns = extraction_metadata.get("enhancement_details", {}).get("special_patterns_detected", [])
            if new_patterns:
                session_data["accumulated_special_patterns"].extend(new_patterns)

            current_case = merge_cases(session_data["current_case"], extracted_case)
            session_data["current_case"] = current_case
    else:
        # Analyser le texte normalement avec HybridNLU (utilise embedding si nécessaire)
        hybrid_nlu = _get_hybrid_nlu()
        try:
            extracted_case, extraction_metadata = hybrid_nlu.parse_free_text_to_case(user_text)
        except Exception as e:
            log_error_with_context(e, "parsing NLU", {"text_length": len(user_text)})
            # Fallback: créer un cas vide plutôt que crasher
            extracted_case = HeadacheCase()
            extraction_metadata = {"error": str(e), "overall_confidence": 0.0}

        session_data["extraction_metadata"] = extraction_metadata

        # Logger le parsing NLU
        log_nlu_parsing(
            text=user_text,
            detected_fields=extraction_metadata.get("detected_fields", []),
            confidence=extraction_metadata.get("overall_confidence", 0.0),
            method=extraction_metadata.get("method", "hybrid")
        )

        # Accumuler les patterns spéciaux détectés
        new_patterns = extraction_metadata.get("enhancement_details", {}).get("special_patterns_detected", [])
        if new_patterns:
            session_data["accumulated_special_patterns"].extend(new_patterns)

        # ÉTAPE 3: Fusionner avec le cas en cours
        if session_data["current_case"] is None:
            # Premier message: c'est le cas initial
            if extracted_case.onset and extracted_case.profile == "unknown":
                current_case = _infer_profile_from_onset(extracted_case)
            else:
                current_case = extracted_case
        else:
            current_case = merge_cases(session_data["current_case"], extracted_case)

        session_data["current_case"] = current_case
    
    # 4 identification des cas manquants
    
    missing_critical = get_missing_critical_fields(current_case)
    
    # Prioriser les champs manquants
    prioritized_missing = prioritize_missing_fields(missing_critical, current_case)
    
    # Filtrer les champs déjà demandés récemment 
    # On garde les champs critiques même si déjà demandés (max 1 fois)
    available_to_ask = [
        field for field in prioritized_missing
        if session_data["asked_fields"].count(field) < 1
    ]
    
    # 5 prendre la décision : continuer le dialogue ou le terminer 
    
    can_end, end_reason = should_end_dialogue(current_case, missing_critical)
    
    if can_end or len(available_to_ask) == 0:
        # DIALOGUE TERMINÉ: Générer recommandation
        
        try:
            recommendation = decide_imaging(current_case)
        except Exception as e:
            # Fallback en cas d'erreur
            from .rules_engine import _get_fallback_recommendation
            recommendation = _get_fallback_recommendation(current_case)
            recommendation.comment += f" (Évaluation de secours activée: {str(e)})"
        
        # Construire message de réponse (inclure patterns spéciaux accumulés durant la session)
        special_patterns = session_data.get("accumulated_special_patterns", [])
        response_message = _build_final_response_message(
            current_case,
            recommendation,
            end_reason,
            special_patterns
        )
        
        return ChatResponse(
            message=response_message,
            session_id=session_id,
            next_question=None,
            headache_case=current_case,
            imaging_recommendation=recommendation,
            requires_more_info=False,
            dialogue_complete=True,
            confidence_score=session_data.get("extraction_metadata", {}).get("overall_confidence", 0.5)
        )
    
    else:
        # DIALOGUE EN COURS: Poser question pour le champ le plus prioritaire
        
        next_field = available_to_ask[0]
        session_data["asked_fields"].append(next_field)
        session_data["last_asked_field"] = next_field  # Sauvegarder pour interpréter la prochaine réponse
        
        next_question = generate_question_for_field(next_field, current_case)
        
        # Construire message de réponse
        response_message = _build_clarification_message(
            extracted_case,
            extraction_metadata,
            next_question
        )
        
        return ChatResponse(
            message=response_message,
            session_id=session_id,
            next_question=next_question,
            headache_case=current_case,
            imaging_recommendation=None,
            requires_more_info=True,
            dialogue_complete=False,
            confidence_score=extraction_metadata.get("overall_confidence", 0.3)
        )


# fonctions utilitaires pour le formatage 
def _build_clarification_message(
    extracted_case: HeadacheCase,
    metadata: Dict[str, Any],
    next_question: str
) -> str:
    """Construit un message de clarification naturel.
    
    Args:
        extracted_case: Cas extrait du dernier message
        metadata: Métadonnées d'extraction NLU
        next_question: Prochaine question à poser
        
    Returns:
        Message formaté
    """
    detected_fields = metadata.get("detected_fields", [])
    
    if len(detected_fields) > 0:
        # Accuser réception des infos reçues
        acknowledgment = "D'accord, j'ai bien noté. "
    else:
        acknowledgment = ""
    
    return f"{acknowledgment}{next_question}"


def _build_final_response_message(
    case: HeadacheCase,
    recommendation: ImagingRecommendation,
    end_reason: str,
    special_patterns: List[Dict[str, Any]] = None
) -> str:
    """Construit le message final avec recommandation.

    Args:
        case: Cas clinique complet
        recommendation: Recommandation d'imagerie
        end_reason: Raison de fin de dialogue
        special_patterns: Patterns spéciaux détectés par embedding (névralgies, etc.)

    Returns:
        Message formaté avec recommandation
    """
    special_patterns = special_patterns or []
    # En-tête selon urgence
    if recommendation.urgency == "immediate":
        header = "URGENCE MÉDICALE DÉTECTÉE\n\n"
    elif recommendation.urgency == "urgent":
        header = "Consultation urgente recommandée\n\n"
    elif recommendation.urgency == "delayed":
        header = "Évaluation médicale recommandée\n\n"
    else:
        header = "Évaluation complétée\n\n"
    
    # Corps du message
    body = f"{recommendation.comment}\n\n"

    # Patterns spéciaux détectés grâce à l'embedding 
    if special_patterns:
        body += "Diagnostic différentiel suggéré (via analyse sémantique):\n"
        for pattern in special_patterns:
            pattern_type = pattern.get("type", "unknown")
            description = pattern.get("description", "")
            similarity = pattern.get("similarity", 0.0)
            imaging = pattern.get("imaging_recommendation", "")

            if pattern_type == "neuralgia":
                body += f"  - {description} (similarité: {similarity:.2f})\n"
                if imaging:
                    body += f"    → IRM recommandée: {imaging.replace('_', ' ')}\n"
            elif pattern_type == "chronic_daily_headache":
                body += f"  - {description} (similarité: {similarity:.2f})\n"
                note = pattern.get("note", "")
                if note:
                    body += f"    → {note}\n"
        body += "\n"

    # Examens recommandés
    if len(recommendation.imaging) > 0 and "aucun" not in recommendation.imaging:
        body += "Examens recommandés:\n"
        for exam in recommendation.imaging:
            body += f"  - {exam.replace('_', ' ').title()}\n"
        body += "\n"
    else:
        body += "Aucun examen d'imagerie n'est nécessaire.\n\n"
    
    # Urgence
    urgency_messages = {
        "immediate": "Adresser le patient aux urgences immédiatement.",
        "urgent": "Consultation médicale dans les plus brefs délais (< 24h).",
        "delayed": "Prévoir consultation avec médecin traitant.",
        "none": "Surveillance clinique. Consulter si aggravation."
    }
    
    footer = urgency_messages.get(recommendation.urgency, "")
    
    # Disclaimer médical
    disclaimer = (
        "\n\n---\n"
        "Outil d'aide à la décision. Évaluation clinique du médecin primordiale. "
        "En cas de doute, avis spécialisé recommandé."
    )
    
    return header + body + footer + disclaimer


# fonction pour réinitialiser la session
def reset_session(session_id: str) -> bool:
    """Réinitialise une session de dialogue.
    
    Args:
        session_id: ID de la session à réinitialiser
        
    Returns:
        True si session réinitialisée, False si session introuvable
    """
    if session_id in _active_sessions:
        del _active_sessions[session_id]
        return True
    return False


def get_session_info(session_id: str) -> Optional[Dict[str, Any]]:
    """Récupère les informations d'une session.
    
    Args:
        session_id: ID de la session
        
    Returns:
        Données de session ou None si introuvable
    """
    return _active_sessions.get(session_id)
