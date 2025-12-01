"""Module de compréhension du langage naturel (NLU) pour l'analyse des céphalées.

Ce module extrait les informations médicales pertinentes depuis du texte libre
pour créer un cas HeadacheCase structuré. Il utilise actuellement des règles simples
basées sur des patterns et mots-clés, avec des points d'accroche pour intégrer
un LLM dans le futur.
"""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .models import HeadacheCase


# ============================================================================
# DICTIONNAIRES DE PATTERNS - Basés sur headache_rules.txt
# ============================================================================

# Patterns pour l'onset (type de début)
ONSET_PATTERNS = {
    "thunderclap": [
        r"coup de tonnerre",
        r"brutale?",
        r"soudaine?",
        r"instantanée?",
        r"thunderclap",
        r"en quelques secondes",
        r"d'emblée maximale?",
        r"violence maximale d'emblée"
    ],
    "progressive": [
        r"progressive?",
        r"progressivement",
        r"qui augmente",
        r"en quelques heures",
        r"en quelques jours",
        r"installation progressive",
        r"progressivement installée?"
    ],
    "chronic": [
        r"chronique",
        r"depuis des mois",
        r"depuis des années",
        r"permanente?",
        r"quotidienne?",
        r"tous les jours"
    ]
}

# Patterns pour le profil temporel
PROFILE_PATTERNS = {
    "acute": [
        r"aigu[eë]?",
        r"depuis (?:quelques )?heures?",
        r"depuis \d+\s*heures?",  # "depuis 2 heures", "depuis 12h"
        r"depuis (?:quelques )?jours?",
        r"depuis [1-6]\s*jours?",
        r"récente?",
        r"soudaine?"
    ],
    "subacute": [
        r"subaigu[eë]?",
        r"depuis (?:quelques )?semaines?",
        r"depuis [1-2]\s*mois",
        r"depuis [7-9]\d?\s*jours"
    ],
    "chronic": [
        r"chronique",
        r"depuis (?:plusieurs|des) (?:mois|années?)",
        r"permanente?",
        r"céphalée chronique quotidienne",
        r"depuis (?:\d+|de nombreux) mois",
        r"depuis (?:\d+|de nombreuses) années?"
    ]
}

# Patterns pour l'intensité
INTENSITY_PATTERNS = {
    "severe": [
        r"intense",
        r"sévère",
        r"atroce",
        r"insupportable",
        r"maximale?",
        r"(?:9|10)/10",
        r"pire (?:douleur|céphalée) de (?:ma|sa) vie"
    ],
    "moderate": [
        r"modérée?",
        r"moyenne",
        r"gênante?",
        r"[5-8]/10"
    ],
    "mild": [
        r"légère?",
        r"faible",
        r"peu intense",
        r"[1-4]/10"
    ]
}

# Patterns pour la fièvre
FEVER_PATTERNS = {
    True: [
        r"fièvre",
        r"fébrile",
        r"température",
        r"(?:38|39|40)°?C",
        r"hyperthermie",
        r"avec de la fièvre"
    ],
    False: [
        r"sans fièvre",
        r"apyrétique",
        r"pas de fièvre",
        r"afébril"
    ]
}

# Patterns pour le syndrome méningé
MENINGEAL_SIGNS_PATTERNS = {
    True: [
        r"syndrome méningé",
        r"raideur (?:de la )?nuque",
        r"raideur méningée",
        r"signe de Kernig",
        r"signe de Brudzinski",
        r"chien de fusil",
        r"nuque raide",
        r"méningé"
    ],
    False: [
        r"sans (?:signe )?méningé",
        r"pas de raideur",
        r"nuque souple"
    ]
}

# Patterns pour le pattern HTIC
HTIC_PATTERNS = {
    True: [
        r"hypertension intracrânienne",
        r"HTIC",
        r"céphalée matutinale",
        r"vomissement(?:s)? en jet",
        r"aggrav(?:ée?|ation) (?:par la )?toux",
        r"aggrav(?:ée?|ation) (?:par (?:l'|les ))?effort",
        r"œdème papillaire",
        r"flou visuel",
        r"éclipses? visuelles?"
    ]
}

# Patterns pour déficit neurologique
NEURO_DEFICIT_PATTERNS = {
    False: [
        r"pas de déficit",
        r"sans déficit",
        r"aucun déficit",
        r"pas de trouble (?:neurologique|moteur|sensitif)",
        r"sans trouble (?:neurologique|moteur|sensitif)",
        r"examen neurologique normal"
    ],
    True: [
        r"déficit",
        r"hémiparésie",
        r"hémiplégie",
        r"aphasie",
        r"trouble du langage",
        r"hémianopsie",
        r"parésie",
        r"faiblesse (?:d')?un (?:bras|membre)",
        r"ne peut plus bouger"
    ]
}

# Patterns pour crises d'épilepsie
SEIZURE_PATTERNS = {
    True: [
        r"crise(?:s)? (?:d')?épilep(?:sie|tique)",
        r"convulsion",
        r"crise convulsive",
        r"perte de connaissance avec secousses",
        r"mouvement(?:s)? anormaux"
    ]
}

# Patterns pour contextes à risque
PREGNANCY_POSTPARTUM_PATTERNS = {
    True: [
        r"enceinte",
        r"grossesse",
        r"post[- ]partum",
        r"accouchement",
        r"a accouché",
        r"vient d'accoucher"
    ]
}

TRAUMA_PATTERNS = {
    False: [
        r"pas de traumatisme",
        r"sans traumatisme",
        r"aucun traumatisme",
        r"pas de choc",
        r"sans choc",
        r"nie (?:tout )?traumatisme"
    ],
    True: [
        r"traumatisme",
        r"choc (?:à|sur) la tête",
        r"coup (?:à|sur) la tête",
        r"chute",
        r"accident"
    ]
}

IMMUNOSUPPRESSION_PATTERNS = {
    True: [
        r"immunodéprim(?:é|ée?|és)",
        r"VIH",
        r"SIDA",
        r"chimiothérapie",
        r"corticoïde",
        r"immunosuppresseur",
        r"greffe"
    ]
}

# Patterns pour profil clinique de la céphalée
HEADACHE_PROFILE_PATTERNS = {
    "migraine_like": [
        r"migraine",
        r"unilatéral",
        r"hémicrân(?:ie|ien)",
        r"pulsatile",
        r"battante?",
        r"photophobie",
        r"phonophobie",
        r"nausées?",
        r"vomissement(?:s)?",
        r"aura",
        r"scotome"
    ],
    "tension_like": [
        r"céphalée de tension",
        r"tension",
        r"pression",
        r"pesanteur",
        r"en casque",
        r"bilatérale?",
        r"serrement",
        r"étau"
    ],
    "htic_like": [
        r"HTIC",
        r"hypertension intracrânienne",
        r"en casque",
        r"matutinale?",
        r"vomissements? en jet"
    ]
}


# ============================================================================
# FONCTIONS D'EXTRACTION PAR RÈGLES
# ============================================================================

def detect_pattern(text: str, patterns: Dict[Any, list], check_negation: bool = True) -> Optional[Any]:
    """Détecte la première valeur matchant dans un dictionnaire de patterns.
    
    Pour les patterns booléens (True/False), vérifie d'abord les négations (False)
    avant les affirmations (True) pour éviter les faux positifs.
    
    Args:
        text: Texte à analyser (converti en minuscules)
        patterns: Dictionnaire {valeur: [liste de regex]}
        check_negation: Si True, vérifie les False avant les True pour booléens
        
    Returns:
        La clé correspondante ou None
    """
    text_lower = text.lower()
    
    # Pour les patterns booléens, vérifier False en premier
    if check_negation and False in patterns and True in patterns:
        # Vérifier négations d'abord
        for pattern in patterns[False]:
            if re.search(pattern, text_lower):
                return False
        # Puis affirmations
        for pattern in patterns[True]:
            if re.search(pattern, text_lower):
                return True
        return None
    
    # Pour les autres patterns, ordre normal
    for value, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                return value
    
    return None


def extract_age(text: str) -> Optional[int]:
    """Extrait l'âge depuis le texte.
    
    Cherche des patterns comme:
    - "45 ans"
    - "âgé de 30 ans"
    - "patient de 55 ans"
    
    Args:
        text: Texte à analyser
        
    Returns:
        L'âge détecté ou None
    """
    # Pattern: nombre suivi de "ans"
    match = re.search(r'(\d{1,3})\s*ans?', text, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 0 <= age <= 120:
            return age
    
    # Pattern: "âgé(e) de X ans"
    match = re.search(r'âgée? de (\d{1,3})', text, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 0 <= age <= 120:
            return age
    
    return None


def extract_sex(text: str) -> Optional[str]:
    """Extrait le sexe depuis le texte.
    
    Args:
        text: Texte à analyser
        
    Returns:
        "M", "F", ou None
    """
    text_lower = text.lower()
    
    # Recherche de marqueurs féminins
    if re.search(r'\b(?:femme|patiente|elle|madame|mme)\b', text_lower):
        return "F"
    
    # Recherche de marqueurs masculins
    if re.search(r'\b(?:homme|patient|il|monsieur|mr?\.)\b', text_lower):
        return "M"
    
    return None


def extract_intensity_score(text: str) -> Optional[int]:
    """Extrait un score d'intensité numérique (0-10).
    
    Args:
        text: Texte à analyser
        
    Returns:
        Score 0-10 ou None
    """
    # Pattern: "X/10"
    match = re.search(r'(\d{1,2})\s*/\s*10', text)
    if match:
        score = int(match.group(1))
        if 0 <= score <= 10:
            return score
    
    # Mapping qualitatif vers numérique
    intensity_level = detect_pattern(text, INTENSITY_PATTERNS)
    if intensity_level == "severe":
        return 9
    elif intensity_level == "moderate":
        return 6
    elif intensity_level == "mild":
        return 3
    
    return None


def extract_duration_hours(text: str) -> Optional[float]:
    """Extrait la durée de l'épisode actuel en heures.
    
    Args:
        text: Texte à analyser
        
    Returns:
        Durée en heures ou None
    """
    # Pattern: "X heures"
    match = re.search(r'depuis (\d+(?:\.\d+)?)\s*heures?', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Pattern: "X jours" -> convertir en heures
    match = re.search(r'depuis (\d+)\s*jours?', text, re.IGNORECASE)
    if match:
        return float(match.group(1)) * 24
    
    return None


# ============================================================================
# FONCTION PRINCIPALE NLU
# ============================================================================

def parse_free_text_to_case(text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
    """Analyse un texte libre et extrait un cas de céphalée structuré.
    
    Cette fonction utilise actuellement des règles simples basées sur des patterns
    et mots-clés. Elle peut être enrichie avec un LLM pour améliorer la précision
    et gérer des formulations plus complexes.
    
    Architecture:
        1. Extraction par règles (patterns regex)
        2. [FUTUR] Enrichissement par LLM
        3. Construction du HeadacheCase
        4. Métadonnées sur la confiance d'extraction
    
    Args:
        text: Description en texte libre du cas clinique
        
    Returns:
        Tuple contenant:
        - HeadacheCase: Le cas structuré
        - dict: Métadonnées d'extraction (confiance, champs détectés, etc.)
        
    Example:
        >>> text = "Femme de 45 ans, céphalée en coup de tonnerre depuis 2h, fièvre à 39°C"
        >>> case, metadata = parse_free_text_to_case(text)
        >>> case.age
        45
        >>> case.onset
        'thunderclap'
        >>> case.fever
        True
        
    Points d'accroche LLM:
        - TODO_LLM_1: Appel LLM pour extraction structurée complète
        - TODO_LLM_2: Validation et enrichissement des champs détectés
        - TODO_LLM_3: Détection de contradictions ou ambiguïtés
        - TODO_LLM_4: Extraction de contexte narratif additionnel
    """
    
    # ========================================================================
    # ÉTAPE 1: Extraction par règles
    # ========================================================================
    
    extracted_data = {}
    detected_fields = []
    confidence_scores = {}
    
    # Données démographiques (OBLIGATOIRES)
    age = extract_age(text)
    sex = extract_sex(text)
    
    if age is not None:
        extracted_data["age"] = age
        detected_fields.append("age")
        confidence_scores["age"] = 0.9  # Haute confiance pour pattern numérique
    else:
        # Valeur par défaut si non détecté
        extracted_data["age"] = 50  # Âge moyen par défaut
        confidence_scores["age"] = 0.1  # Très faible confiance
    
    if sex is not None:
        extracted_data["sex"] = sex
        detected_fields.append("sex")
        confidence_scores["sex"] = 0.8
    else:
        # Valeur par défaut
        extracted_data["sex"] = "Other"
        confidence_scores["sex"] = 0.0
    
    # TODO_LLM_1: Point d'accroche pour extraction démographique par LLM
    # -----------------------------------------------------------------------
    # Un LLM pourrait mieux gérer des formulations comme:
    # - "quinquagénaire" -> 50-59 ans
    # - "jeune patiente" -> femme, 20-35 ans
    # - "monsieur âgé" -> homme, >65 ans
    #
    # Exemple d'intégration:
    # ```python
    # if llm_enabled:
    #     llm_demographics = llm_extract_demographics(text)
    #     if llm_demographics["confidence"] > 0.7:
    #         extracted_data.update(llm_demographics["data"])
    #         confidence_scores.update(llm_demographics["scores"])
    # ```
    # -----------------------------------------------------------------------
    
    # Profil temporel
    onset = detect_pattern(text, ONSET_PATTERNS)
    if onset:
        extracted_data["onset"] = onset
        detected_fields.append("onset")
        confidence_scores["onset"] = 0.85
    else:
        extracted_data["onset"] = "unknown"
    
    profile = detect_pattern(text, PROFILE_PATTERNS)
    if profile:
        extracted_data["profile"] = profile
        detected_fields.append("profile")
        confidence_scores["profile"] = 0.8
    else:
        extracted_data["profile"] = "unknown"
    
    # Durée et intensité
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
    
    # TODO_LLM_2: Point d'accroche pour extraction temporelle enrichie par LLM
    # -----------------------------------------------------------------------
    # Un LLM pourrait mieux interpréter:
    # - "depuis ce matin" -> calculer durée en heures
    # - "cela fait 3 semaines que..." -> subacute, ~504h
    # - "douleur qui empire depuis hier soir" -> onset progressive, ~12-18h
    #
    # Exemple:
    # ```python
    # if llm_enabled:
    #     temporal_info = llm_extract_temporal_context(text)
    #     extracted_data.update(temporal_info["structured_data"])
    # ```
    # -----------------------------------------------------------------------
    
    # Signes cliniques majeurs (RED FLAGS)
    
    # 1. Fièvre
    fever = detect_pattern(text, FEVER_PATTERNS)
    if fever is not None:
        extracted_data["fever"] = fever
        detected_fields.append("fever")
        confidence_scores["fever"] = 0.9
    
    # 2. Syndrome méningé (CRITIQUE)
    meningeal_signs = detect_pattern(text, MENINGEAL_SIGNS_PATTERNS)
    if meningeal_signs is not None:
        extracted_data["meningeal_signs"] = meningeal_signs
        detected_fields.append("meningeal_signs")
        confidence_scores["meningeal_signs"] = 0.95  # Haute confiance car critique
    
    # 3. Pattern HTIC
    htic = detect_pattern(text, HTIC_PATTERNS)
    if htic is True:
        extracted_data["htic_pattern"] = True
        detected_fields.append("htic_pattern")
        confidence_scores["htic_pattern"] = 0.85
    
    # 4. Déficit neurologique
    neuro_deficit = detect_pattern(text, NEURO_DEFICIT_PATTERNS)
    if neuro_deficit is True:
        extracted_data["neuro_deficit"] = True
        detected_fields.append("neuro_deficit")
        confidence_scores["neuro_deficit"] = 0.9
    
    # 5. Crises d'épilepsie
    seizure = detect_pattern(text, SEIZURE_PATTERNS)
    if seizure is True:
        extracted_data["seizure"] = True
        detected_fields.append("seizure")
        confidence_scores["seizure"] = 0.9
    
    # TODO_LLM_3: Point d'accroche pour détection de red flags par LLM
    # -----------------------------------------------------------------------
    # Un LLM pourrait détecter des formulations complexes:
    # - "nuque un peu raide mais pas sûr" -> meningeal_signs=uncertain
    # - "troubles visuels brefs au réveil" -> htic_pattern avec nuance
    # - "parle bizarrement" -> possible aphasie -> neuro_deficit
    # - Détection de CONTRADICTIONS: "fièvre mais apyrétique"
    #
    # Exemple:
    # ```python
    # if llm_enabled:
    #     red_flags = llm_detect_red_flags(text)
    #     # LLM peut aussi détecter des incertitudes
    #     extracted_data.update(red_flags["definite"])
    #     uncertain_flags = red_flags["uncertain"]  # À clarifier avec l'utilisateur
    # ```
    # -----------------------------------------------------------------------
    
    # Contextes à risque
    
    pregnancy_postpartum = detect_pattern(text, PREGNANCY_POSTPARTUM_PATTERNS)
    if pregnancy_postpartum is not None:
        extracted_data["pregnancy_postpartum"] = pregnancy_postpartum
        detected_fields.append("pregnancy_postpartum")
        confidence_scores["pregnancy_postpartum"] = 0.9
    
    trauma = detect_pattern(text, TRAUMA_PATTERNS)
    if trauma is not None:
        extracted_data["trauma"] = trauma
        detected_fields.append("trauma")
        confidence_scores["trauma"] = 0.85
    
    immunosuppression = detect_pattern(text, IMMUNOSUPPRESSION_PATTERNS)
    if immunosuppression is not None:
        extracted_data["immunosuppression"] = immunosuppression
        detected_fields.append("immunosuppression")
        confidence_scores["immunosuppression"] = 0.9
    
    # Profil clinique de la céphalée
    headache_profile = detect_pattern(text, HEADACHE_PROFILE_PATTERNS)
    if headache_profile:
        extracted_data["headache_profile"] = headache_profile
        detected_fields.append("headache_profile")
        confidence_scores["headache_profile"] = 0.75
    else:
        extracted_data["headache_profile"] = "unknown"
    
    # TODO_LLM_4: Point d'accroche pour classification par LLM
    # -----------------------------------------------------------------------
    # Un LLM pourrait classifier le profil de céphalée en analysant:
    # - Ensemble des symptômes (unilatéral + pulsatile + photophobie = migraine)
    # - Description narrative: "douleur comme si on me serrait la tête dans un étau"
    # - Critères diagnostiques complexes (IHS/ICHD-3)
    #
    # Exemple:
    # ```python
    # if llm_enabled:
    #     classification = llm_classify_headache_type(
    #         text=text,
    #         extracted_symptoms=extracted_data
    #     )
    #     if classification["confidence"] > 0.8:
    #         extracted_data["headache_profile"] = classification["type"]
    #         extracted_data["diagnostic_criteria_met"] = classification["criteria"]
    # ```
    # -----------------------------------------------------------------------
    
    # ========================================================================
    # ÉTAPE 2: Construction du HeadacheCase
    # ========================================================================
    
    try:
        case = HeadacheCase(**extracted_data)
    except Exception as e:
        # En cas d'erreur de validation, créer un cas minimal valide
        case = HeadacheCase(
            age=extracted_data.get("age", 50),
            sex=extracted_data.get("sex", "Other")
        )
        confidence_scores["validation_error"] = str(e)
    
    # ========================================================================
    # ÉTAPE 3: Métadonnées d'extraction
    # ========================================================================
    
    metadata = {
        "detected_fields": detected_fields,
        "confidence_scores": confidence_scores,
        "overall_confidence": sum(confidence_scores.values()) / max(len(confidence_scores), 1),
        "extraction_method": "rule_based",
        "timestamp": datetime.now().isoformat(),
        "original_text": text,
        
        # TODO_LLM_5: Métadonnées additionnelles avec LLM
        # -------------------------------------------------------------------
        # Ajouter:
        # - "llm_used": True/False
        # - "llm_model": "gpt-4" / "claude-3" / etc.
        # - "clarification_needed": [list of ambiguous points]
        # - "suggested_questions": ["Depuis combien de temps?", ...]
        # -------------------------------------------------------------------
    }
    
    return case, metadata


# ============================================================================
# FONCTIONS UTILITAIRES POUR DIALOGUE
# ============================================================================

def suggest_clarification_questions(case: HeadacheCase, metadata: Dict[str, Any]) -> list[str]:
    """Génère des questions de clarification basées sur les champs manquants.
    
    Analyse le cas et les métadonnées pour identifier les informations critiques
    manquantes et propose des questions ciblées.
    
    Args:
        case: Le cas HeadacheCase extrait
        metadata: Métadonnées d'extraction
        
    Returns:
        Liste de questions de clarification
        
    TODO_LLM_6: Génération de questions par LLM
    --------------------------------------------
    Un LLM pourrait générer des questions plus naturelles et contextuelles:
    - Tenir compte du contexte narratif déjà donné
    - Adapter le ton (urgence vs chronique)
    - Prioriser les questions selon l'arbre décisionnel
    
    Exemple:
    ```python
    if llm_enabled:
        questions = llm_generate_questions(
            case=case,
            metadata=metadata,
            priority="red_flags_first"
        )
        return questions
    ```
    """
    questions = []
    
    # Champs critiques pour le diagnostic
    if case.onset == "unknown":
        questions.append("Comment la douleur a-t-elle débuté ? (brutalement, progressivement, depuis longtemps)")
    
    if case.profile == "unknown":
        questions.append("Depuis combien de temps avez-vous cette douleur ?")
    
    # Red flags critiques
    if case.fever is None:
        questions.append("Avez-vous de la fièvre ?")
    
    if case.meningeal_signs is None:
        questions.append("Avez-vous une raideur de la nuque ?")
    
    if case.htic_pattern is None:
        questions.append("La douleur est-elle pire le matin ? Y a-t-il des vomissements en jet ?")
    
    if case.neuro_deficit is None:
        questions.append("Avez-vous des faiblesses, troubles de la parole ou de la vision ?")
    
    if case.intensity is None:
        questions.append("Sur une échelle de 0 à 10, comment évalueriez-vous l'intensité de la douleur ?")
    
    return questions


def get_missing_critical_fields(case: HeadacheCase) -> list[str]:
    """Identifie les champs critiques manquants pour l'arbre décisionnel.
    
    Args:
        case: Le cas HeadacheCase
        
    Returns:
        Liste des noms de champs critiques non renseignés
    """
    critical_fields = []
    
    # Champs utilisés par les règles HSA/méningite/HTIC
    if case.onset == "unknown":
        critical_fields.append("onset")
    
    if case.fever is None:
        critical_fields.append("fever")
    
    if case.meningeal_signs is None:
        critical_fields.append("meningeal_signs")
    
    if case.intensity is None:
        critical_fields.append("intensity")
    
    if case.htic_pattern is None:
        critical_fields.append("htic_pattern")
    
    return critical_fields
