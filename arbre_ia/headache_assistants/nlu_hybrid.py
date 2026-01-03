"""
Module NLU Hybride - Regles + Embeddings pour une extraction robuste.

Ce module combine l'extraction par regles (patterns, vocabulaire medical)
avec les embeddings semantiques pour detecter les concepts cliniques
meme quand le patient utilise des expressions inhabituelles.

Pourquoi une approche hybride ?
-------------------------------
- Les regles sont rapides et precises pour le vocabulaire medical standard
- Mais elles ratent les expressions patients ("j'ai l'impression que ma tete va exploser")
- Les embeddings capturent le sens meme avec des formulations inattendues

Pipeline de traitement (par ordre de priorite)
----------------------------------------------
1. N-grams : expressions composees a fort sens medical
   Ex: "pire douleur de ma vie" -> thunderclap (HSA)

2. Vocabulaire semantique : matching par similarite d'embedding
   Ex: "mal de crane" ~ "cephalee" (similarite > 0.82)

3. Negations : detection des patterns negatifs (PRIORITE MAX)
   Ex: "pas de fievre", "sans deficit" -> valeur = False

4. Regles NLU v2 : extraction structuree (age, duree, profil)

Securite clinique
-----------------
Les negations ont toujours priorite car elles representent une info explicite.
"cephalee brutale sans deficit" -> neuro_deficit = False (meme si "deficit" detecte)

Performance
-----------
- Mode regles seules : ~50ms
- Avec embedding : ~150-200ms
- Premiere execution : ~2s (chargement du modele)
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import re
from dataclasses import dataclass
import warnings

# Import du NLU v2
from .nlu_v2 import NLUv2
from .models import HeadacheCase
from .medical_examples_corpus import MEDICAL_EXAMPLES

# Lazy import de sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    warnings.warn(
        "sentence-transformers non installé. NLU hybride fonctionnera en mode règles uniquement.\n"
        "Pour activer l'embedding: pip install sentence-transformers"
    )

# Import SemanticVocabulary (uses sentence-transformers)
try:
    from .vocabulary.semantic_vocabulary import SemanticVocabulary, SemanticMatch
    SEMANTIC_VOCAB_AVAILABLE = EMBEDDING_AVAILABLE  # Requires embedding
except ImportError:
    SEMANTIC_VOCAB_AVAILABLE = False
    SemanticVocabulary = None
    SemanticMatch = None


def preprocess_for_embedding(text: str) -> str:
    """Prétraite le texte pour un matching embedding plus précis.

    Retire les informations temporelles (durées, dates) qui pourraient
    polluer le matching sémantique. L'objectif est de matcher sur les
    SYMPTÔMES, pas sur les durées.

    Args:
        text: Texte médical brut

    Returns:
        Texte nettoyé des références temporelles

    Examples:
        >>> preprocess_for_embedding("Céphalée progressive depuis 3 semaines")
        "Céphalée progressive"
        >>> preprocess_for_embedding("Mal de tête depuis 1-3 jours qui empire")
        "Mal de tête qui empire"
    """
    # Pattern pour les durées "depuis X temps"
    # Couvre: depuis 3 jours, depuis 1-3 semaines, depuis quelques mois, etc.
    patterns = [
        # "depuis X jours/semaines/mois/ans" avec variantes (incluant minutes)
        r"depuis\s+(?:\d+[\s\-à]*\d*\s*)?(?:quelques?\s+)?(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "depuis environ X temps"
        r"depuis\s+environ\s+\d+[\s\-à]*\d*\s*(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "il y a X temps"
        r"il\s+y\s+a\s+(?:\d+[\s\-à]*\d*\s*)?(?:quelques?\s+)?(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "X jours/semaines/mois" en début ou après virgule
        r"(?:^|,\s*)\d+[\s\-à]*\d*\s*(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "sur plusieurs jours/semaines"
        r"sur\s+(?:plusieurs|quelques)\s+(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "depuis longtemps", "depuis des mois", "depuis des années"
        r"depuis\s+(?:longtemps|des\s+(?:mois|années?|semaines?|jours?))",
        # Durées avec "environ", "à peu près"
        r"(?:environ|à\s+peu\s+près)\s+\d+\s*(?:minutes?|heures?|jours?|semaines?|mois|ans?)",
        # "ce matin", "hier", "avant-hier", "cette nuit", etc.
        r"\b(?:ce\s+matin|hier\s*(?:soir|matin)?|avant[\s\-]hier|cette\s+nuit|aujourd'hui)\b",
        # "depuis" orphelin en fin après suppression (nettoyage)
        r"\bdepuis\s*$",
        r"\bdepuis\s+(?=\s|$)",
    ]

    result = text
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    # Nettoyer les espaces multiples et les virgules orphelines
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"\s*,\s*,\s*", ", ", result)
    result = re.sub(r"^\s*,\s*", "", result)
    result = re.sub(r"\s*,\s*$", "", result)

    return result.strip()


# =============================================================================
# SYSTÈME DE DÉTECTION DES NÉGATIONS
# =============================================================================

# Mapping des termes médicaux vers les champs du modèle
SYMPTOM_TO_FIELD = {
    # Fièvre
    "fièvre": "fever",
    "fébrile": "fever",
    "température": "fever",
    "hyperthermie": "fever",
    "pyrexie": "fever",
    # Signes méningés
    "raideur de nuque": "meningeal_signs",
    "raideur nuque": "meningeal_signs",
    "signes méningés": "meningeal_signs",
    "syndrome méningé": "meningeal_signs",
    "méningé": "meningeal_signs",
    # Déficit neurologique
    "déficit": "neuro_deficit",
    "deficit": "neuro_deficit",  # Sans accent
    "déficit neurologique": "neuro_deficit",
    "deficit neurologique": "neuro_deficit",
    "déficit moteur": "neuro_deficit",
    "deficit moteur": "neuro_deficit",
    "déficit sensitif": "neuro_deficit",
    "deficit sensitif": "neuro_deficit",
    "déficit sensitivo-moteur": "neuro_deficit",
    "deficit sensitivo-moteur": "neuro_deficit",
    "déficit focal": "neuro_deficit",
    "deficit focal": "neuro_deficit",
    "paralysie": "neuro_deficit",
    "parésie": "neuro_deficit",
    "faiblesse": "neuro_deficit",
    "signe de localisation": "neuro_deficit",
    "signes de localisation": "neuro_deficit",
    # Traumatisme
    "traumatisme": "trauma",
    "trauma": "trauma",
    "choc": "trauma",
    "chute": "trauma",
    # Convulsions
    "convulsion": "seizure",
    "convulsions": "seizure",
    "crise": "seizure",
    "épilepsie": "seizure",
    # HTIC
    "vomissements": "htic_pattern",
    "vomissement": "htic_pattern",
    # Nausées (associées mais pas HTIC seul)
    "nausée": None,  # Pas de champ direct
    "nausées": None,
}

# Patterns de négation en français
NEGATION_PATTERNS = [
    # "pas de X", "pas d'X"
    r"pas\s+d[e']?\s*",
    # "sans X"
    r"sans\s+",
    # "absence de X", "absence d'X"
    r"absence\s+d[e']?\s*",
    # "aucun(e) X"
    r"aucune?\s+",
    # "ni X" (dans contexte "ni fièvre ni déficit")
    r"ni\s+",
    # "pas de notion de X"
    r"pas\s+de\s+notion\s+d[e']?\s*",
    # "examen normal" patterns
    r"(?:examen\s+)?(?:neurologique\s+)?(?:strictement\s+)?normal",
    # "négatif" / "négative"
    r"n[ée]gatif(?:ve)?\s*",
]


@dataclass
class NegationResult:
    """Résultat de la détection de négation."""
    field: str  # Nom du champ (fever, meningeal_signs, etc.)
    value: bool  # Toujours False pour une négation
    matched_text: str  # Texte qui a matché
    confidence: float  # Confiance dans la détection


def detect_negations(text: str) -> Tuple[List[NegationResult], str]:
    """Détecte les négations dans le texte médical.

    Identifie les patterns de négation (pas de, sans, absence de, etc.)
    et extrait les champs concernés.

    Args:
        text: Texte médical à analyser

    Returns:
        Tuple contenant:
        - Liste des négations détectées
        - Texte nettoyé (négations retirées pour l'embedding)

    Examples:
        >>> negations, cleaned = detect_negations("Céphalée sans fièvre ni déficit")
        >>> negations[0].field
        'fever'
        >>> negations[1].field
        'neuro_deficit'
    """
    negations = []
    text_lower = text.lower()
    cleaned_text = text

    # Construire les patterns complets pour chaque symptôme
    for symptom, field in SYMPTOM_TO_FIELD.items():
        if field is None:
            continue

        for neg_pattern in NEGATION_PATTERNS:
            # Pattern complet : négation + symptôme
            full_pattern = neg_pattern + r"(" + re.escape(symptom) + r")"

            matches = list(re.finditer(full_pattern, text_lower, re.IGNORECASE))
            for match in matches:
                negations.append(NegationResult(
                    field=field,
                    value=False,
                    matched_text=match.group(0),
                    confidence=0.9
                ))
                # Retirer du texte pour l'embedding
                cleaned_text = re.sub(
                    re.escape(match.group(0)),
                    "",
                    cleaned_text,
                    flags=re.IGNORECASE
                )

    # Patterns spéciaux pour "examen normal"
    exam_patterns = [
        (r"examen\s+neurologique\s+(?:strictement\s+)?normal", "neuro_deficit"),
        (r"nuque\s+souple", "meningeal_signs"),
        (r"apyrétique", "fever"),
        (r"apyrexie", "fever"),
    ]

    for pattern, field in exam_patterns:
        matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
        for match in matches:
            negations.append(NegationResult(
                field=field,
                value=False,
                matched_text=match.group(0),
                confidence=0.95
            ))
            cleaned_text = re.sub(
                re.escape(match.group(0)),
                "",
                cleaned_text,
                flags=re.IGNORECASE
            )

    # Nettoyer les espaces multiples
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    # Dédupliquer les négations (même champ)
    seen_fields = set()
    unique_negations = []
    for neg in negations:
        if neg.field not in seen_fields:
            unique_negations.append(neg)
            seen_fields.add(neg.field)

    return unique_negations, cleaned_text


def apply_negations_to_case(
    case_dict: Dict[str, Any],
    negations: List[NegationResult],
    detected_fields: List[str]
) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
    """Applique les négations détectées au cas médical.

    Les négations ont la PRIORITÉ la plus haute car elles représentent
    une information médicale explicite (ex: "pas de déficit" est clair).
    Elles écrasent les détections des keywords et N-grams.

    Args:
        case_dict: Dictionnaire du cas (from model_dump())
        negations: Liste des négations détectées
        detected_fields: Liste des champs déjà détectés

    Returns:
        Tuple (case_dict modifié, detected_fields mis à jour, détails des négations appliquées)
    """
    applied = []

    for neg in negations:
        current_value = case_dict.get(neg.field)

        # Les négations explicites ont PRIORITÉ sur les keywords/ngrams
        # car "pas de déficit" est plus spécifique que la détection du mot "déficit"
        # On applique toujours la négation sauf si la valeur est déjà False
        if current_value is not False:
            case_dict[neg.field] = False
            if neg.field not in detected_fields:
                detected_fields.append(neg.field)
            applied.append({
                "field": neg.field,
                "value": False,
                "matched_text": neg.matched_text,
                "confidence": neg.confidence,
                "overrode_previous": current_value
            })

    return case_dict, detected_fields, applied


# =============================================================================
# SYSTÈME DE DÉTECTION N-GRAMS (EXPRESSIONS COMPOSÉES)
# =============================================================================

# Expressions composées avec leur signification médicale
# Ces patterns ont un sens spécifique qui dépasse leurs mots individuels
NGRAM_PATTERNS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # ONSET THUNDERCLAP - Expressions critiques pour HSA
    # -------------------------------------------------------------------------
    "pire douleur de ma vie": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.95,
        "category": "thunderclap",
        "note": "Expression pathognomonique HSA"
    },
    "pire mal de tête de ma vie": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.95,
        "category": "thunderclap"
    },
    "coup de tonnerre": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.95,
        "category": "thunderclap"
    },
    "coup de poignard": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.85,
        "category": "thunderclap"
    },
    "comme un coup de marteau": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.90,
        "category": "thunderclap"
    },
    "explosion dans la tête": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.90,
        "category": "thunderclap"
    },
    "maximale d'emblée": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.95,
        "category": "thunderclap"
    },
    "d'emblée maximale": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.95,
        "category": "thunderclap"
    },
    "brutale maximale": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.90,
        "category": "thunderclap"
    },

    # -------------------------------------------------------------------------
    # SYNDROME MÉNINGÉ - Expressions spécifiques
    # -------------------------------------------------------------------------
    "chien de fusil": {
        "fields": {"meningeal_signs": True},
        "confidence": 0.95,
        "category": "meningeal",
        "note": "Position méningée caractéristique"
    },
    "raideur de nuque": {
        "fields": {"meningeal_signs": True},
        "confidence": 0.90,
        "category": "meningeal"
    },
    "nuque raide": {
        "fields": {"meningeal_signs": True},
        "confidence": 0.90,
        "category": "meningeal"
    },

    # -------------------------------------------------------------------------
    # HTIC - Hypertension intracrânienne
    # -------------------------------------------------------------------------
    "vomissements en jet": {
        "fields": {"htic_pattern": True},
        "confidence": 0.95,
        "category": "htic",
        "note": "Signe cardinal HTIC"
    },
    "aggravé par la toux": {
        "fields": {"htic_pattern": True},
        "confidence": 0.85,
        "category": "htic"
    },
    "aggravé par l'effort": {
        "fields": {"htic_pattern": True},
        "confidence": 0.85,
        "category": "htic"
    },
    "pire le matin": {
        "fields": {"htic_pattern": True},
        "confidence": 0.80,
        "category": "htic"
    },
    "pire au réveil": {
        "fields": {"htic_pattern": True},
        "confidence": 0.80,
        "category": "htic"
    },
    "œdème papillaire": {
        "fields": {"htic_pattern": True},
        "confidence": 0.95,
        "category": "htic"
    },

    # -------------------------------------------------------------------------
    # PROFILS CÉPHALÉE
    # -------------------------------------------------------------------------
    "en étau": {
        "fields": {"headache_profile": "tension_like"},
        "confidence": 0.85,
        "category": "profile"
    },
    "comme un bandeau": {
        "fields": {"headache_profile": "tension_like"},
        "confidence": 0.85,
        "category": "profile"
    },
    "bandeau serré": {
        "fields": {"headache_profile": "tension_like"},
        "confidence": 0.85,
        "category": "profile"
    },
    "bat dans la tête": {
        "fields": {"headache_profile": "migraine_like"},
        "confidence": 0.80,
        "category": "profile"
    },
    "pulsatile": {
        "fields": {"headache_profile": "migraine_like"},
        "confidence": 0.75,
        "category": "profile"
    },

    # -------------------------------------------------------------------------
    # NÉVRALGIES - Patterns caractéristiques
    # Note: neuropathic_pattern n'existe pas dans HeadacheCase
    # Ces patterns sont documentés mais ne modifient pas le case
    # -------------------------------------------------------------------------
    "décharge électrique": {
        "fields": {},  # Pas de champ correspondant dans HeadacheCase
        "confidence": 0.90,
        "category": "neuralgia",
        "note": "Névralgie du trijumeau typique - informatif uniquement"
    },
    "éclair douloureux": {
        "fields": {},
        "confidence": 0.85,
        "category": "neuralgia"
    },
    "douleur fulgurante": {
        "fields": {},
        "confidence": 0.85,
        "category": "neuralgia"
    },

    # -------------------------------------------------------------------------
    # CONTEXTES SPÉCIAUX
    # -------------------------------------------------------------------------
    "pendant rapport sexuel": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.85,
        "category": "coital_headache",
        "note": "Céphalée coïtale - SVCR ou HSA"
    },
    "pendant l'orgasme": {
        "fields": {"onset": "thunderclap"},
        "confidence": 0.85,
        "category": "coital_headache"
    },
    "effort physique intense": {
        "fields": {"htic_pattern": True},
        "confidence": 0.75,
        "category": "exertional"
    },

    # -------------------------------------------------------------------------
    # POST-PL / POSITIONNELLE
    # -------------------------------------------------------------------------
    "soulagé allongé": {
        "fields": {"recent_pl_or_peridural": True},
        "confidence": 0.80,
        "category": "positional"
    },
    "pire debout": {
        "fields": {"recent_pl_or_peridural": True},
        "confidence": 0.75,
        "category": "positional"
    },
    "aggravé debout": {
        "fields": {"recent_pl_or_peridural": True},
        "confidence": 0.75,
        "category": "positional"
    },

    # -------------------------------------------------------------------------
    # PATTERNS TEMPORELS PROGRESSIFS
    # -------------------------------------------------------------------------
    "depuis plusieurs semaines": {
        "fields": {"onset": "progressive"},
        "confidence": 0.85,
        "category": "temporal"
    },
    "depuis 3 semaines": {
        "fields": {"onset": "progressive"},
        "confidence": 0.85,
        "category": "temporal"
    },
    "depuis 2 semaines": {
        "fields": {"onset": "progressive"},
        "confidence": 0.80,
        "category": "temporal"
    },
    "depuis 1 mois": {
        "fields": {"onset": "progressive"},
        "confidence": 0.85,
        "category": "temporal"
    },
    "depuis plusieurs mois": {
        "fields": {"onset": "progressive"},
        "confidence": 0.90,
        "category": "temporal"
    },
    "céphalées matinales": {
        "fields": {"htic_pattern": True},
        "confidence": 0.75,
        "category": "htic"
    },

    # -------------------------------------------------------------------------
    # PATTERNS MIGRAINE
    # -------------------------------------------------------------------------
    "bat dans la tête": {
        "fields": {"headache_profile": "migraine_like"},
        "confidence": 0.80,
        "category": "profile"
    },
    "bat dans la tempe": {
        "fields": {"headache_profile": "migraine_like"},
        "confidence": 0.80,
        "category": "profile"
    },
    "douleur qui bat": {
        "fields": {"headache_profile": "migraine_like"},
        "confidence": 0.75,
        "category": "profile"
    },

    # -------------------------------------------------------------------------
    # SIGNES MÉNINGÉS ADDITIONNELS
    # -------------------------------------------------------------------------
    "nuque raide": {
        "fields": {"meningeal_signs": True},
        "confidence": 0.90,
        "category": "meningeal"
    },
    "un peu raide": {
        "fields": {"meningeal_signs": True},
        "confidence": 0.70,
        "category": "meningeal",
        "note": "Signe méningé discret"
    },

    # -------------------------------------------------------------------------
    # NÉVRALGIES ADDITIONNELLES
    # Note: informatif uniquement, pas de champ HeadacheCase correspondant
    # -------------------------------------------------------------------------
    "en décharge électrique": {
        "fields": {},
        "confidence": 0.90,
        "category": "neuralgia"
    },
    "décharges électriques": {
        "fields": {},
        "confidence": 0.90,
        "category": "neuralgia"
    },

    # -------------------------------------------------------------------------
    # PATTERNS CHRONIQUES / PROGRESSIFS
    # Note: Les patterns avec durée longue (>3 mois) indiquent chronic
    # Les patterns "quotidiennes" sont très spécifiques à la chronicité
    # -------------------------------------------------------------------------
    "depuis 6 mois": {
        "fields": {"onset": "chronic"},  # > 3 mois = chronic
        "confidence": 0.75,  # Confiance moyenne car peut être ambigu
        "category": "temporal"
    },
    "depuis plusieurs années": {
        "fields": {"onset": "chronic"},
        "confidence": 0.90,
        "category": "temporal"
    },
    "céphalées quotidiennes": {
        "fields": {"onset": "chronic"},
        "confidence": 0.90,  # Très spécifique à la chronicité
        "category": "temporal"
    },
}


@dataclass
class NgramMatch:
    """Résultat de la détection d'un n-gram."""
    pattern: str  # Le pattern matché
    fields: Dict[str, Any]  # Champs à appliquer
    confidence: float
    category: str
    start: int  # Position début dans le texte
    end: int  # Position fin
    note: Optional[str] = None

    def __hash__(self):
        return hash((self.pattern, self.start, self.end))

    def __eq__(self, other):
        if not isinstance(other, NgramMatch):
            return False
        return self.pattern == other.pattern and self.start == other.start


def detect_ngrams(text: str) -> List[NgramMatch]:
    """Détecte les expressions composées (n-grams) dans le texte.

    Ces expressions ont un sens médical spécifique qui dépasse
    leurs mots individuels.

    Args:
        text: Texte médical à analyser

    Returns:
        Liste des n-grams détectés, triés par position

    Examples:
        >>> matches = detect_ngrams("Pire douleur de ma vie, brutale")
        >>> matches[0].pattern
        'pire douleur de ma vie'
        >>> matches[0].fields
        {'onset': 'thunderclap'}
    """
    matches = []
    text_lower = text.lower()

    for pattern, info in NGRAM_PATTERNS.items():
        # Chercher le pattern dans le texte
        idx = text_lower.find(pattern)
        if idx != -1:
            matches.append(NgramMatch(
                pattern=pattern,
                fields=info["fields"],
                confidence=info["confidence"],
                category=info.get("category", "unknown"),
                start=idx,
                end=idx + len(pattern),
                note=info.get("note")
            ))

    # Trier par position (début)
    matches.sort(key=lambda m: m.start)

    # Dédupliquer les champs (garder la confiance la plus haute)
    field_best_match: Dict[str, NgramMatch] = {}
    for match in matches:
        for field, value in match.fields.items():
            key = f"{field}:{value}"
            if key not in field_best_match or match.confidence > field_best_match[key].confidence:
                field_best_match[key] = match

    # Retourner les matches uniques
    unique_matches = list(set(field_best_match.values()))
    unique_matches.sort(key=lambda m: m.start)

    return unique_matches


# =============================================================================
# SYSTÈME D'INDEX DE MOTS-CLÉS INVERSÉ
# =============================================================================

# Index inversé: mot-clé → liste de champs possibles avec poids
# Permet un lookup O(1) pour les mots simples à forte valeur sémantique
# Note: les N-grams gèrent les expressions composées, ici on gère les mots seuls

KEYWORD_INDEX: Dict[str, List[Dict[str, Any]]] = {
    # -------------------------------------------------------------------------
    # ONSET - Mode de début
    # -------------------------------------------------------------------------
    "brutale": [
        {"field": "onset", "value": "thunderclap", "weight": 0.85, "note": "Céphalée brutale → thunderclap"}
    ],
    "brutal": [
        {"field": "onset", "value": "thunderclap", "weight": 0.85}
    ],
    "soudaine": [
        {"field": "onset", "value": "thunderclap", "weight": 0.80}
    ],
    "soudain": [
        {"field": "onset", "value": "thunderclap", "weight": 0.80}
    ],
    "progressive": [
        {"field": "onset", "value": "progressive", "weight": 0.85}
    ],
    "progressif": [
        {"field": "onset", "value": "progressive", "weight": 0.85}
    ],
    "graduellement": [
        {"field": "onset", "value": "progressive", "weight": 0.75}
    ],
    "insidieuse": [
        {"field": "onset", "value": "progressive", "weight": 0.80}
    ],
    "insidieux": [
        {"field": "onset", "value": "progressive", "weight": 0.80}
    ],
    "subite": [
        {"field": "onset", "value": "thunderclap", "weight": 0.80}
    ],
    "subit": [
        {"field": "onset", "value": "thunderclap", "weight": 0.80}
    ],
    "foudroyante": [
        {"field": "onset", "value": "thunderclap", "weight": 0.90}
    ],
    "explosive": [
        {"field": "onset", "value": "thunderclap", "weight": 0.85}
    ],

    # -------------------------------------------------------------------------
    # FIÈVRE
    # -------------------------------------------------------------------------
    "fébrile": [
        {"field": "fever", "value": True, "weight": 0.90}
    ],
    "fièvre": [
        {"field": "fever", "value": True, "weight": 0.90}
    ],
    "fiévreux": [
        {"field": "fever", "value": True, "weight": 0.85}
    ],
    "fiévreuse": [
        {"field": "fever", "value": True, "weight": 0.85}
    ],
    "hyperthermie": [
        {"field": "fever", "value": True, "weight": 0.95}
    ],
    "pyrexie": [
        {"field": "fever", "value": True, "weight": 0.95}
    ],
    "apyrétique": [
        {"field": "fever", "value": False, "weight": 0.95, "note": "Négation implicite"}
    ],
    "apyrexie": [
        {"field": "fever", "value": False, "weight": 0.95}
    ],

    # -------------------------------------------------------------------------
    # SIGNES MÉNINGÉS
    # -------------------------------------------------------------------------
    "méningé": [
        {"field": "meningeal_signs", "value": True, "weight": 0.90}
    ],
    "méningée": [
        {"field": "meningeal_signs", "value": True, "weight": 0.90}
    ],
    "méningite": [
        {"field": "meningeal_signs", "value": True, "weight": 0.85},
        {"field": "fever", "value": True, "weight": 0.70, "note": "Méningite souvent fébrile"}
    ],
    "photophobie": [
        {"field": "meningeal_signs", "value": True, "weight": 0.75}
    ],
    "phonophobie": [
        {"field": "meningeal_signs", "value": True, "weight": 0.60}  # Aussi migraine
    ],

    # -------------------------------------------------------------------------
    # DÉFICIT NEUROLOGIQUE
    # -------------------------------------------------------------------------
    "déficit": [
        {"field": "neuro_deficit", "value": True, "weight": 0.85}
    ],
    "déficitaire": [
        {"field": "neuro_deficit", "value": True, "weight": 0.90}
    ],
    "paralysie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.95}
    ],
    "parésie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.95}
    ],
    "hémiplégie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.95}
    ],
    "hémiparésie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.95}
    ],
    "aphasie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.95}
    ],
    "dysarthrie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.90}
    ],
    "diplopie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.85}
    ],
    "ataxie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.90}
    ],
    "paresthésies": [
        {"field": "neuro_deficit", "value": True, "weight": 0.70}
    ],
    "paresthésie": [
        {"field": "neuro_deficit", "value": True, "weight": 0.70}
    ],
    "engourdissement": [
        {"field": "neuro_deficit", "value": True, "weight": 0.65}
    ],
    "fourmillements": [
        {"field": "neuro_deficit", "value": True, "weight": 0.60}
    ],

    # -------------------------------------------------------------------------
    # HTIC - Hypertension intracrânienne
    # -------------------------------------------------------------------------
    "vomissements": [
        {"field": "htic_pattern", "value": True, "weight": 0.70}  # Poids augmenté, souvent associé à HTIC
    ],
    "vomissement": [
        {"field": "htic_pattern", "value": True, "weight": 0.70}
    ],
    "nausées": [
        {"field": "htic_pattern", "value": True, "weight": 0.40}  # Faible seul
    ],
    "nausée": [
        {"field": "htic_pattern", "value": True, "weight": 0.40}
    ],
    "papilloedème": [
        {"field": "htic_pattern", "value": True, "weight": 0.95}
    ],
    "matinales": [
        {"field": "htic_pattern", "value": True, "weight": 0.70, "note": "Céphalées matinales évoquent HTIC"}
    ],
    "matinale": [
        {"field": "htic_pattern", "value": True, "weight": 0.70}
    ],

    # -------------------------------------------------------------------------
    # TRAUMATISME
    # -------------------------------------------------------------------------
    "traumatisme": [
        {"field": "trauma", "value": True, "weight": 0.90}
    ],
    "trauma": [
        {"field": "trauma", "value": True, "weight": 0.90}
    ],
    "traumatique": [
        {"field": "trauma", "value": True, "weight": 0.85}
    ],
    "chute": [
        {"field": "trauma", "value": True, "weight": 0.70}
    ],
    "accident": [
        {"field": "trauma", "value": True, "weight": 0.65}
    ],
    "avp": [
        {"field": "trauma", "value": True, "weight": 0.90, "note": "Accident voie publique"}
    ],
    "choc": [
        {"field": "trauma", "value": True, "weight": 0.60}
    ],
    "coup": [
        {"field": "trauma", "value": True, "weight": 0.55}
    ],

    # -------------------------------------------------------------------------
    # CONVULSIONS / ÉPILEPSIE
    # -------------------------------------------------------------------------
    "convulsion": [
        {"field": "seizure", "value": True, "weight": 0.95}
    ],
    "convulsions": [
        {"field": "seizure", "value": True, "weight": 0.95}
    ],
    "convulsif": [
        {"field": "seizure", "value": True, "weight": 0.90}
    ],
    "épilepsie": [
        {"field": "seizure", "value": True, "weight": 0.95}
    ],
    "épileptique": [
        {"field": "seizure", "value": True, "weight": 0.90}
    ],
    "comitial": [
        {"field": "seizure", "value": True, "weight": 0.95}
    ],
    "comitiale": [
        {"field": "seizure", "value": True, "weight": 0.95}
    ],

    # -------------------------------------------------------------------------
    # GROSSESSE / POST-PARTUM
    # -------------------------------------------------------------------------
    "enceinte": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.95}
    ],
    "grossesse": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.95}
    ],
    "parturiente": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.95}
    ],
    "accouchement": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.90}
    ],
    "post-partum": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.95}
    ],
    "postpartum": [
        {"field": "pregnancy_postpartum", "value": True, "weight": 0.95}
    ],
    "péridural": [
        {"field": "recent_pl_or_peridural", "value": True, "weight": 0.90}
    ],
    "péridurale": [
        {"field": "recent_pl_or_peridural", "value": True, "weight": 0.90}
    ],

    # -------------------------------------------------------------------------
    # IMMUNOSUPPRESSION
    # -------------------------------------------------------------------------
    "immunodéprimé": [
        {"field": "immunosuppression", "value": True, "weight": 0.95}
    ],
    "immunodéprimée": [
        {"field": "immunosuppression", "value": True, "weight": 0.95}
    ],
    "immunosuppression": [
        {"field": "immunosuppression", "value": True, "weight": 0.95}
    ],
    "immunosupprimé": [
        {"field": "immunosuppression", "value": True, "weight": 0.95}
    ],
    "vih": [
        {"field": "immunosuppression", "value": True, "weight": 0.90}
    ],
    "sida": [
        {"field": "immunosuppression", "value": True, "weight": 0.90}
    ],
    "chimiothérapie": [
        {"field": "immunosuppression", "value": True, "weight": 0.85}
    ],
    "greffe": [
        {"field": "immunosuppression", "value": True, "weight": 0.80}
    ],
    "greffé": [
        {"field": "immunosuppression", "value": True, "weight": 0.85}
    ],
    "greffée": [
        {"field": "immunosuppression", "value": True, "weight": 0.85}
    ],
    "corticothérapie": [
        {"field": "immunosuppression", "value": True, "weight": 0.70}
    ],

    # -------------------------------------------------------------------------
    # PONCTION LOMBAIRE
    # -------------------------------------------------------------------------
    "ponction": [
        {"field": "recent_pl_or_peridural", "value": True, "weight": 0.80}
    ],
    "lombaire": [
        {"field": "recent_pl_or_peridural", "value": True, "weight": 0.65}
    ],
    "pl": [
        {"field": "recent_pl_or_peridural", "value": True, "weight": 0.85}
    ],

    # -------------------------------------------------------------------------
    # PROFILS CÉPHALÉE (indice sur le type)
    # -------------------------------------------------------------------------
    "pulsatile": [
        {"field": "headache_profile", "value": "migraine_like", "weight": 0.75}
    ],
    "pulsatilité": [
        {"field": "headache_profile", "value": "migraine_like", "weight": 0.75}
    ],
    "lancinante": [
        {"field": "headache_profile", "value": "migraine_like", "weight": 0.70}
    ],
    "lancinant": [
        {"field": "headache_profile", "value": "migraine_like", "weight": 0.70}
    ],
    "oppressif": [
        {"field": "headache_profile", "value": "tension_like", "weight": 0.75}
    ],
    "oppressive": [
        {"field": "headache_profile", "value": "tension_like", "weight": 0.75}
    ],
    "constrictif": [
        {"field": "headache_profile", "value": "tension_like", "weight": 0.75}
    ],
    "constrictive": [
        {"field": "headache_profile", "value": "tension_like", "weight": 0.75}
    ],

    # -------------------------------------------------------------------------
    # NÉVRALGIES / DOULEURS NEUROPATHIQUES
    # -------------------------------------------------------------------------
    "névralgie": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.95},
        {"field": "facial_pain", "value": True, "weight": 0.80}
    ],
    "névralgique": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.90}
    ],
    "trijumeau": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.90},
        {"field": "facial_pain", "value": True, "weight": 0.95}
    ],
    "électrique": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.75}
    ],
    "brûlure": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.70}
    ],
    "brûlante": [
        {"field": "neuropathic_pattern", "value": True, "weight": 0.70}
    ],

    # -------------------------------------------------------------------------
    # ANTICOAGULATION (facteur de risque hémorragique)
    # -------------------------------------------------------------------------
    "anticoagulant": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "anticoagulants": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "anticoagulé": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "anticoagulée": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "coumadine": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "warfarine": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "xarelto": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "eliquis": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "pradaxa": [
        {"field": "anticoagulation", "value": True, "weight": 0.95}
    ],
    "héparine": [
        {"field": "anticoagulation", "value": True, "weight": 0.90}
    ],
    "lovenox": [
        {"field": "anticoagulation", "value": True, "weight": 0.90}
    ],

    # -------------------------------------------------------------------------
    # ÂGE (indication sur urgence)
    # -------------------------------------------------------------------------
    "âgé": [
        {"field": "age_over_50", "value": True, "weight": 0.60}  # Faible sans chiffre
    ],
    "âgée": [
        {"field": "age_over_50", "value": True, "weight": 0.60}
    ],
    "octogénaire": [
        {"field": "age_over_50", "value": True, "weight": 0.95}
    ],
    "septuagénaire": [
        {"field": "age_over_50", "value": True, "weight": 0.95}
    ],
    "sexagénaire": [
        {"field": "age_over_50", "value": True, "weight": 0.95}
    ],
    "quinquagénaire": [
        {"field": "age_over_50", "value": True, "weight": 0.95}
    ],
}


@dataclass
class KeywordMatch:
    """Résultat de la détection d'un mot-clé."""
    keyword: str
    field: str
    value: Any
    weight: float
    position: int  # Position dans le texte
    note: Optional[str] = None

    def __hash__(self):
        return hash((self.keyword, self.field, self.position))

    def __eq__(self, other):
        if not isinstance(other, KeywordMatch):
            return False
        return self.keyword == other.keyword and self.field == other.field and self.position == other.position


def detect_keywords(text: str) -> List[KeywordMatch]:
    """Détecte les mots-clés médicaux dans le texte via index inversé.

    Lookup O(1) pour chaque mot du texte contre l'index de mots-clés.
    Retourne les matches triés par poids décroissant.

    Args:
        text: Texte médical à analyser

    Returns:
        Liste des mots-clés détectés avec leurs mappings

    Examples:
        >>> matches = detect_keywords("Céphalée brutale fébrile")
        >>> matches[0].field
        'onset'
        >>> matches[0].value
        'thunderclap'
    """
    matches = []
    text_lower = text.lower()

    # Tokeniser le texte (mots simples)
    # On garde aussi les mots composés courants avec tiret
    words = re.findall(r'\b[\w-]+\b', text_lower)

    # Lookup dans l'index pour chaque mot
    for i, word in enumerate(words):
        if word in KEYWORD_INDEX:
            for mapping in KEYWORD_INDEX[word]:
                # Trouver la position réelle dans le texte
                pattern = r'\b' + re.escape(word) + r'\b'
                match = re.search(pattern, text_lower)
                position = match.start() if match else i

                matches.append(KeywordMatch(
                    keyword=word,
                    field=mapping["field"],
                    value=mapping["value"],
                    weight=mapping["weight"],
                    position=position,
                    note=mapping.get("note")
                ))

    # Trier par poids décroissant
    matches.sort(key=lambda m: m.weight, reverse=True)

    # Dédupliquer: garder le match avec le plus haut poids pour chaque champ
    seen_fields: Dict[str, KeywordMatch] = {}
    unique_matches = []

    for match in matches:
        key = match.field
        if key not in seen_fields or match.weight > seen_fields[key].weight:
            seen_fields[key] = match

    unique_matches = list(seen_fields.values())
    unique_matches.sort(key=lambda m: m.weight, reverse=True)

    return unique_matches


def apply_keywords_to_case(
    case_dict: Dict[str, Any],
    keyword_matches: List[KeywordMatch],
    detected_fields: List[str],
    weight_threshold: float = 0.65
) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
    """Applique les mots-clés détectés au cas médical.

    Les mots-clés ont priorité moyenne: après les N-grams mais avant l'embedding.
    Seuls les matches avec un poids >= threshold sont appliqués.

    Args:
        case_dict: Dictionnaire du cas
        keyword_matches: Liste des mots-clés détectés
        detected_fields: Liste des champs déjà détectés
        weight_threshold: Seuil de poids minimum pour appliquer (défaut: 0.65)

    Returns:
        Tuple (case_dict modifié, detected_fields mis à jour, détails des applications)
    """
    applied = []

    for match in keyword_matches:
        # Ne pas appliquer si poids trop faible
        if match.weight < weight_threshold:
            continue

        current_value = case_dict.get(match.field)

        # Appliquer si:
        # - Le champ n'a pas de valeur
        # - La valeur actuelle est "unknown"
        # - Le champ n'est pas encore dans detected_fields
        if current_value is None or current_value == "unknown" or match.field not in detected_fields:
            case_dict[match.field] = match.value
            if match.field not in detected_fields:
                detected_fields.append(match.field)

            applied.append({
                "field": match.field,
                "value": match.value,
                "keyword": match.keyword,
                "weight": match.weight,
                "note": match.note
            })

    return case_dict, detected_fields, applied


# =============================================================================
# SYSTÈME DE FUZZY MATCHING / CORRECTION ORTHOGRAPHIQUE
# =============================================================================

# Dictionnaire des termes médicaux critiques avec leurs variantes/fautes courantes
# Format: terme_correct → liste de variantes acceptées (fautes courantes)
MEDICAL_TERMS_DICTIONARY: Dict[str, str] = {
    # Termes corrects (clés de KEYWORD_INDEX) - le système ajoutera automatiquement
    # les variantes fuzzy basées sur la distance de Levenshtein
}

# Liste des termes médicaux critiques pour le fuzzy matching
# Ces termes seront utilisés comme référence pour corriger les fautes
CRITICAL_MEDICAL_TERMS: List[str] = [
    # Onset / Mode de début
    "brutale", "brutal", "soudaine", "soudain", "progressive", "progressif",
    "foudroyante", "explosive", "subite", "insidieuse",
    # Fièvre
    "fièvre", "fébrile", "fiévreux", "fiévreuse", "hyperthermie", "pyrexie",
    "apyrétique", "apyrexie",
    # Signes méningés
    "méningé", "méningée", "méningite", "photophobie", "phonophobie",
    # Déficit neurologique
    "déficit", "déficitaire", "paralysie", "parésie", "hémiplégie",
    "hémiparésie", "aphasie", "dysarthrie", "diplopie", "ataxie",
    "paresthésies", "paresthésie", "engourdissement", "fourmillements",
    # HTIC
    "vomissements", "vomissement", "nausées", "nausée", "papilloedème",
    # Traumatisme
    "traumatisme", "trauma", "traumatique", "chute", "accident",
    # Convulsions
    "convulsion", "convulsions", "convulsif", "épilepsie", "épileptique",
    "comitial", "comitiale",
    # Grossesse
    "enceinte", "grossesse", "parturiente", "accouchement", "post-partum",
    "postpartum", "péridural", "péridurale",
    # Immunosuppression
    "immunodéprimé", "immunodéprimée", "immunosuppression", "immunosupprimé",
    "chimiothérapie", "greffe", "greffé", "greffée", "corticothérapie",
    # Anticoagulation
    "anticoagulant", "anticoagulants", "anticoagulé", "anticoagulée",
    "coumadine", "warfarine", "héparine",
    # Profils céphalée
    "pulsatile", "pulsatilité", "lancinante", "lancinant",
    "oppressif", "oppressive", "constrictif", "constrictive",
    # Névralgies
    "névralgie", "névralgique", "trijumeau", "électrique", "brûlure", "brûlante",
    # Termes généraux céphalées
    "céphalée", "céphalées", "migraine", "migraineux", "migraineuse",
    # Âge
    "octogénaire", "septuagénaire", "sexagénaire", "quinquagénaire",
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calcule la distance de Levenshtein entre deux chaînes.

    La distance de Levenshtein est le nombre minimum d'éditions
    (insertions, suppressions, substitutions) pour transformer s1 en s2.

    Args:
        s1: Première chaîne
        s2: Deuxième chaîne

    Returns:
        Distance de Levenshtein (entier >= 0)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Coût: 0 si caractères identiques, 1 sinon
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calcule un ratio de similarité entre deux chaînes (0.0 à 1.0).

    Basé sur la distance de Levenshtein normalisée.

    Args:
        s1: Première chaîne
        s2: Deuxième chaîne

    Returns:
        Ratio de similarité (1.0 = identique, 0.0 = totalement différent)
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    distance = levenshtein_distance(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))

    return 1.0 - (distance / max_len)


@dataclass
class FuzzyMatch:
    """Résultat d'une correction fuzzy."""
    original: str  # Mot original (potentiellement mal orthographié)
    corrected: str  # Mot corrigé
    similarity: float  # Score de similarité (0.0-1.0)
    position: int  # Position dans le texte

    def __hash__(self):
        return hash((self.original, self.corrected, self.position))

    def __eq__(self, other):
        if not isinstance(other, FuzzyMatch):
            return False
        return (self.original == other.original and
                self.corrected == other.corrected and
                self.position == other.position)


def fuzzy_correct_text(
    text: str,
    min_similarity: float = 0.75,
    min_word_length: int = 4
) -> Tuple[str, List[FuzzyMatch]]:
    """Corrige les fautes d'orthographe dans le texte médical.

    Utilise le fuzzy matching pour identifier et corriger les mots
    mal orthographiés qui ressemblent à des termes médicaux critiques.

    Args:
        text: Texte à corriger
        min_similarity: Seuil minimum de similarité (défaut: 0.80)
        min_word_length: Longueur minimum des mots à corriger (défaut: 4)

    Returns:
        Tuple (texte corrigé, liste des corrections effectuées)

    Examples:
        >>> corrected, matches = fuzzy_correct_text("Patient avec fievre et cephalé")
        >>> corrected
        'Patient avec fièvre et céphalée'
        >>> matches[0].original
        'fievre'
        >>> matches[0].corrected
        'fièvre'
    """
    corrections = []
    text_lower = text.lower()
    words = re.findall(r'\b[\w-]+\b', text_lower)

    # Pour chaque mot du texte
    for word in words:
        # Ignorer les mots trop courts
        if len(word) < min_word_length:
            continue

        # Ignorer si le mot est déjà dans le dictionnaire
        if word in KEYWORD_INDEX or word in CRITICAL_MEDICAL_TERMS:
            continue

        # Chercher le meilleur match dans les termes médicaux
        best_match = None
        best_similarity = 0.0

        for term in CRITICAL_MEDICAL_TERMS:
            # Optimisation: ignorer si la différence de longueur est trop grande
            if abs(len(word) - len(term)) > 3:
                continue

            sim = similarity_ratio(word, term)

            if sim >= min_similarity and sim > best_similarity:
                best_similarity = sim
                best_match = term

        # Si on a trouvé une correction valide
        if best_match and best_match != word:
            # Trouver la position dans le texte original
            pattern = r'\b' + re.escape(word) + r'\b'
            match = re.search(pattern, text_lower)
            position = match.start() if match else 0

            corrections.append(FuzzyMatch(
                original=word,
                corrected=best_match,
                similarity=best_similarity,
                position=position
            ))

    # Appliquer les corrections au texte
    corrected_text = text
    # Trier par position décroissante pour éviter les décalages d'index
    corrections.sort(key=lambda c: c.position, reverse=True)

    for correction in corrections:
        # Remplacer en préservant la casse du premier caractère si possible
        pattern = r'\b' + re.escape(correction.original) + r'\b'

        def replace_preserve_case(match):
            original = match.group(0)
            replacement = correction.corrected
            if original[0].isupper():
                return replacement.capitalize()
            return replacement

        corrected_text = re.sub(pattern, replace_preserve_case, corrected_text, flags=re.IGNORECASE)

    # Re-trier par position croissante pour le retour
    corrections.sort(key=lambda c: c.position)

    return corrected_text, corrections


def apply_fuzzy_corrections(
    text: str,
    min_similarity: float = 0.75
) -> Tuple[str, List[Dict[str, Any]]]:
    """Applique les corrections fuzzy et retourne les métadonnées.

    Wrapper autour de fuzzy_correct_text pour intégration dans le pipeline.

    Args:
        text: Texte à corriger
        min_similarity: Seuil de similarité (défaut: 0.80)

    Returns:
        Tuple (texte corrigé, liste des corrections avec détails)
    """
    corrected_text, corrections = fuzzy_correct_text(text, min_similarity)

    corrections_metadata = [
        {
            "original": c.original,
            "corrected": c.corrected,
            "similarity": round(c.similarity, 3),
            "position": c.position
        }
        for c in corrections
    ]

    return corrected_text, corrections_metadata


def apply_ngrams_to_case(
    case_dict: Dict[str, Any],
    ngram_matches: List[NgramMatch],
    detected_fields: List[str]
) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
    """Applique les n-grams détectés au cas médical.

    Les n-grams sont des expressions composées à fort sens médical spécifique.
    Ils peuvent OVERRIDER les détections des règles pour certains champs
    car ils sont plus précis (ex: "en étau" est spécifique à tension_like).

    Champs où les N-grams peuvent overrider les règles:
    - headache_profile: les N-grams comme "en étau" sont plus spécifiques
    - onset: les expressions comme "coup de tonnerre" sont pathognomoniques

    Args:
        case_dict: Dictionnaire du cas
        ngram_matches: Liste des n-grams détectés
        detected_fields: Liste des champs déjà détectés

    Returns:
        Tuple (case_dict modifié, detected_fields mis à jour, détails des applications)
    """
    applied = []

    # Champs où les N-grams à haute confiance peuvent overrider
    NGRAM_OVERRIDE_FIELDS = {"headache_profile", "onset"}

    for match in ngram_matches:
        for field, value in match.fields.items():
            current_value = case_dict.get(field)

            # Appliquer si:
            # - Le champ n'a pas de valeur
            # - La valeur actuelle est "unknown"
            # - Le champ n'est pas encore dans detected_fields
            # - OU (le champ est dans NGRAM_OVERRIDE_FIELDS ET confiance >= 0.80)
            should_apply = (
                current_value is None or
                current_value == "unknown" or
                field not in detected_fields or
                (field in NGRAM_OVERRIDE_FIELDS and match.confidence >= 0.80)
            )

            if should_apply:
                old_value = current_value
                case_dict[field] = value
                if field not in detected_fields:
                    detected_fields.append(field)

                applied.append({
                    "field": field,
                    "value": value,
                    "pattern": match.pattern,
                    "confidence": match.confidence,
                    "category": match.category,
                    "note": match.note,
                    "overrode_previous": old_value if old_value != value else None
                })

    return case_dict, detected_fields, applied


@dataclass
class HybridResult:
    """
    Resultat du NLU hybride.

    Contient le cas clinique extrait + les metadonnees de traitement.

    Attributs:
        case: HeadacheCase avec tous les champs detectes
        metadata: Details de l'extraction (champs detectes, scores...)
        hybrid_enhanced: True si l'embedding a ete utilise
        enhancement_details: Details des enrichissements par embedding (si utilise)
    """
    case: HeadacheCase
    metadata: Dict[str, Any]
    hybrid_enhanced: bool
    enhancement_details: Optional[Dict[str, Any]] = None


class HybridNLU:
    """
    NLU hybride combinant regles et embeddings.

    Cette classe implemente un pipeline multi-couches pour extraire les
    informations cliniques du texte libre, meme avec des formulations
    inhabituelles.

    Architecture:
        - Couche 1 : N-grams, mots-cles, negations (deterministe, rapide)
        - Couche 2 : Regles NLU v2 (vocabulaire medical complet)
        - Couche 3 : Similarite embedding (fallback pour expressions inconnues)

    Attributs:
        rule_nlu: Moteur NLU base sur les regles
        confidence_threshold: Seuil en dessous duquel l'embedding est active
        use_embedding: True si l'embedding est active
        embedder: Modele SentenceTransformer (si embedding active)
        example_embeddings: Embeddings pre-calcules du corpus

    Exemple:
        >>> nlu = HybridNLU(confidence_threshold=0.7)
        >>> result = nlu.parse_hybrid("J'ai l'impression que ma tete va exploser")
        >>> print(result.case.onset)
        thunderclap
        >>> print(result.hybrid_enhanced)
        True  # "tete va exploser" matche par embedding

    Performance:
        - Mode regles seules : ~50ms
        - Avec embedding : ~200ms
        - Initialisation : ~2s (chargement du modele)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        use_embedding: bool = True,
        embedding_model: str = 'all-MiniLM-L6-v2',
        verbose: bool = False
    ):
        """
        Initialise le NLU hybride.

        Args:
            confidence_threshold: Seuil de confiance minimum avant d'activer
                                 l'embedding (0.0-1.0). Defaut: 0.7
            use_embedding: Active la couche embedding. Mettre a False pour
                          un traitement plus rapide. Defaut: True
            embedding_model: Nom du modele sentence-transformers.
                            Defaut: 'all-MiniLM-L6-v2'
            verbose: Affiche les messages d'initialisation. Defaut: False

        Note:
            La premiere initialisation prend ~2s (chargement du modele).
            Les appels suivants reutilisent le modele en cache.
        """
        # Layer 1: Rules (NLU v2)
        self.rule_nlu = NLUv2()
        self.confidence_threshold = confidence_threshold
        self.verbose = verbose

        # Layer 2: Semantic Vocabulary (replaces keyword matching)
        # Only use if embedding is enabled (semantic vocab uses embedding internally)
        self.use_semantic = SEMANTIC_VOCAB_AVAILABLE and use_embedding
        self.semantic_vocab = None
        if self.use_semantic:
            self._initialize_semantic_vocabulary(embedding_model)

        # Layer 3: Corpus Embedding (fallback for low confidence)
        self.use_embedding = use_embedding and EMBEDDING_AVAILABLE
        self.embedder = None
        self.example_embeddings = None
        self.examples = MEDICAL_EXAMPLES

        if self.use_embedding and not self.use_semantic:
            # Only initialize corpus embeddings if semantic vocab failed
            self._initialize_embedding(embedding_model)
        elif self.use_embedding and self.use_semantic:
            # Reuse embedder from semantic vocab for corpus
            self._initialize_corpus_from_semantic()

    def _initialize_embedding(self, model_name: str):
        """Initialise le modèle d'embedding et pré-calcule les embeddings.

        Les textes du corpus sont prétraités pour retirer les durées temporelles
        avant le calcul des embeddings, permettant un matching plus précis sur
        les symptômes.
        """
        try:
            if self.verbose:
                print(f"[INIT] Chargement du modèle embedding '{model_name}'...")
            self.embedder = SentenceTransformer(model_name)

            # Pré-calculer les embeddings du corpus AVEC prétraitement
            if self.verbose:
                print(f"[INIT] Pré-calcul des embeddings pour {len(self.examples)} exemples...")

            # Prétraiter les textes pour retirer les durées temporelles
            texts_raw = [ex["text"] for ex in self.examples]
            texts_preprocessed = [preprocess_for_embedding(t) for t in texts_raw]

            # Stocker les textes prétraités pour debug
            self.example_texts_preprocessed = texts_preprocessed

            self.example_embeddings = self.embedder.encode(
                texts_preprocessed,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            if self.verbose:
                print(f"[OK] Modèle embedding initialisé ({self.example_embeddings.shape})")
                print(f"[OK] Textes prétraités pour matching symptomatique pur")

        except Exception as e:
            warnings.warn(f"Erreur initialisation embedding: {e}. Mode règles uniquement.")
            self.use_embedding = False

    def _initialize_semantic_vocabulary(self, model_name: str):
        """Initialize the semantic vocabulary with pre-computed embeddings.

        The semantic vocabulary provides embedding-based matching of medical
        terms, replacing the previous keyword index approach.
        """
        try:
            if self.verbose:
                print(f"[INIT] Initializing SemanticVocabulary with '{model_name}'...")

            self.semantic_vocab = SemanticVocabulary(
                similarity_threshold=0.82,  # Higher threshold to avoid false positives (e.g., "crise" → seizure)
                embedding_model=model_name,
                verbose=self.verbose,
                min_token_length=3  # Avoid matching short words like "en"
            )

            if self.verbose:
                stats = self.semantic_vocab.get_vocabulary_stats()
                print(f"[OK] SemanticVocabulary ready: {stats['total_terms']} terms")

        except Exception as e:
            warnings.warn(f"Erreur initialisation SemanticVocabulary: {e}. Fallback to keywords.")
            self.use_semantic = False
            self.semantic_vocab = None

    def _initialize_corpus_from_semantic(self):
        """Initialize corpus embeddings reusing the semantic vocab embedder.

        This avoids loading the model twice when both semantic vocab and
        corpus embedding are enabled.
        """
        try:
            if self.verbose:
                print(f"[INIT] Pré-calcul des embeddings corpus (réutilisation embedder)...")

            # Reuse the embedder from semantic vocabulary
            self.embedder = self.semantic_vocab.embedder

            # Prétraiter les textes pour retirer les durées temporelles
            texts_raw = [ex["text"] for ex in self.examples]
            texts_preprocessed = [preprocess_for_embedding(t) for t in texts_raw]
            self.example_texts_preprocessed = texts_preprocessed

            self.example_embeddings = self.embedder.encode(
                texts_preprocessed,
                convert_to_numpy=True,
                show_progress_bar=False
            )

            if self.verbose:
                print(f"[OK] Corpus embeddings ready ({self.example_embeddings.shape})")

        except Exception as e:
            warnings.warn(f"Erreur initialisation corpus: {e}")
            self.use_embedding = False

    # Mapping for intensity string values to EVA scores
    INTENSITY_MAP = {
        "maximum": 10,
        "severe": 8,
        "moderate": 5,
        "mild": 3
    }

    def _apply_semantic_matches(
        self,
        case_dict: Dict[str, Any],
        semantic_matches: List[SemanticMatch],
        detected_fields: List[str],
        confidence_threshold: float = 0.55
    ) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
        """Apply semantic vocabulary matches to the case.

        Similar to apply_keywords_to_case but uses SemanticMatch objects
        with their embedding-based confidence scores.

        Args:
            case_dict: Dictionary representation of HeadacheCase
            semantic_matches: List of SemanticMatch from vocabulary matching
            detected_fields: List of already detected field names
            confidence_threshold: Minimum final_confidence to apply (default 0.55)

        Returns:
            Tuple of (updated case_dict, updated detected_fields, applied details)
        """
        applied = []

        # Fields that are informational only (not in HeadacheCase model)
        SKIP_FIELDS = {"headache_type", "vertigo"}

        for match in semantic_matches:
            # Skip if confidence too low
            if match.final_confidence < confidence_threshold:
                continue

            # Skip informational fields that aren't in HeadacheCase
            if match.field in SKIP_FIELDS:
                continue

            # Skip fields that don't exist in HeadacheCase
            if match.field not in case_dict:
                continue

            # Special handling for intensity (needs int, not string)
            value_to_apply = match.value
            if match.field == "intensity" and isinstance(match.value, str):
                value_to_apply = self.INTENSITY_MAP.get(match.value)
                if value_to_apply is None:
                    continue  # Unknown intensity value, skip

            current_value = case_dict.get(match.field)

            # Apply if:
            # - Field not yet set (None)
            # - Field is "unknown"
            # - Field not in detected_fields
            should_apply = (
                current_value is None or
                current_value == "unknown" or
                match.field not in detected_fields
            )

            if should_apply:
                case_dict[match.field] = value_to_apply
                if match.field not in detected_fields:
                    detected_fields.append(match.field)

                applied.append({
                    "field": match.field,
                    "value": value_to_apply,
                    "original_value": match.value if value_to_apply != match.value else None,
                    "term": match.term,
                    "input_token": match.input_token,
                    "similarity": round(match.similarity, 3),
                    "confidence": round(match.final_confidence, 3),
                    "category": match.category
                })

        return case_dict, detected_fields, applied

    def parse_free_text_to_case(self, text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """
        Parse un texte clinique en texte libre.

        Interface compatible avec NLU v2 mais avec le traitement hybride.

        Args:
            text: Description clinique en texte libre

        Returns:
            Tuple (HeadacheCase, metadata)

        Exemple:
            >>> nlu = HybridNLU()
            >>> case, meta = nlu.parse_free_text_to_case("Cephalee brutale")
            >>> print(meta["hybrid_mode"])
            rules+ngrams+keywords
        """
        hybrid_result = self.parse_hybrid(text)
        return hybrid_result.case, hybrid_result.metadata

    def parse_hybrid(self, text: str) -> HybridResult:
        """
        Analyse hybride complete avec infos de traitement detaillees.

        Pipeline de traitement (dans l'ordre) :
            0. Correction orthographique (fuzzy matching)
            1. Detection N-grams (expressions composees)
            2. Detection mots-cles ou vocabulaire semantique
            3. Detection des negations
            4. Analyse par regles (NLU v2)
            5. Application N-grams (priorite haute)
            6. Application mots-cles (priorite moyenne)
            7. Application negations (PRIORITE MAX)
            8. Enrichissement embedding (si confiance < seuil)

        Priorite (de la plus haute a la plus basse) :
            1. Negations - "pas de deficit" override toujours "deficit"
            2. N-grams - expressions pathognomoniques
            3. Mots-cles - termes medicaux simples
            4. Regles - extraction structuree
            5. Embedding - fallback pour expressions inconnues

        Args:
            text: Description clinique en texte libre

        Returns:
            HybridResult avec le cas extrait et les metadonnees

        Performance:
            - Sans embedding : ~50ms
            - Avec embedding : ~200ms
        """
        # ÉTAPE 0: Correction orthographique (fuzzy matching)
        # Corrige les fautes de frappe AVANT toute autre analyse
        corrected_text, fuzzy_corrections = apply_fuzzy_corrections(text)

        # Utiliser le texte corrigé pour toutes les étapes suivantes
        working_text = corrected_text if fuzzy_corrections else text

        # ÉTAPE 1: Détection des N-grams (expressions composées)
        # Fait AVANT tout car ces expressions ont un sens médical fort
        ngram_matches = detect_ngrams(working_text)

        # ÉTAPE 2: Semantic vocabulary matching (replaces keyword index)
        # Uses embedding similarity to find medical terms including synonyms
        semantic_matches = []
        if self.use_semantic and self.semantic_vocab:
            semantic_matches = self.semantic_vocab.match_text(working_text)

        # Fallback to keyword matching if semantic vocab not available
        keyword_matches = []
        if not self.use_semantic:
            keyword_matches = detect_keywords(working_text)

        # ÉTAPE 3: Détection des négations
        negations, text_without_negations = detect_negations(working_text)

        # ÉTAPE 4: Analyse par règles (Layer 1)
        # On passe le texte corrigé pour que les règles bénéficient des corrections
        case, metadata = self.rule_nlu.parse_free_text_to_case(working_text)

        # Ajouter les métadonnées de correction orthographique
        if fuzzy_corrections:
            metadata["fuzzy_corrections"] = fuzzy_corrections
            metadata["original_text"] = text
            metadata["corrected_text"] = corrected_text

        # ÉTAPE 5: Appliquer les N-grams détectés
        # Les N-grams ont la priorité la plus haute (expressions médicales spécifiques)
        if ngram_matches:
            case_dict = case.model_dump()
            detected_fields = metadata.get("detected_fields", []).copy()

            case_dict, detected_fields, ngram_applied = apply_ngrams_to_case(
                case_dict, ngram_matches, detected_fields
            )

            # Reconstruire le cas et mettre à jour metadata
            case = HeadacheCase(**case_dict)
            metadata["detected_fields"] = detected_fields
            metadata["ngrams_detected"] = [
                {"pattern": m.pattern, "category": m.category, "confidence": m.confidence}
                for m in ngram_matches
            ]
            if ngram_applied:
                metadata["ngrams_applied"] = ngram_applied

        # ÉTAPE 6: Appliquer les semantic matches ou keywords
        # Semantic matching a priorité moyenne (après N-grams, avant negations)
        if semantic_matches:
            case_dict = case.model_dump()
            detected_fields = metadata.get("detected_fields", []).copy()

            # Apply semantic matches
            case_dict, detected_fields, semantic_applied = self._apply_semantic_matches(
                case_dict, semantic_matches, detected_fields
            )

            # Reconstruire le cas et mettre à jour metadata
            case = HeadacheCase(**case_dict)
            metadata["detected_fields"] = detected_fields
            metadata["semantic_detected"] = [
                {
                    "term": m.term,
                    "input_token": m.input_token,
                    "field": m.field,
                    "similarity": round(m.similarity, 3),
                    "confidence": round(m.final_confidence, 3)
                }
                for m in semantic_matches
            ]
            if semantic_applied:
                metadata["semantic_applied"] = semantic_applied

        elif keyword_matches:
            # Fallback to keyword matching if semantic not available
            case_dict = case.model_dump()
            detected_fields = metadata.get("detected_fields", []).copy()

            case_dict, detected_fields, keywords_applied = apply_keywords_to_case(
                case_dict, keyword_matches, detected_fields
            )

            # Reconstruire le cas et mettre à jour metadata
            case = HeadacheCase(**case_dict)
            metadata["detected_fields"] = detected_fields
            metadata["keywords_detected"] = [
                {"keyword": m.keyword, "field": m.field, "weight": m.weight}
                for m in keyword_matches
            ]
            if keywords_applied:
                metadata["keywords_applied"] = keywords_applied

        # ÉTAPE 7: Appliquer les négations détectées
        # Les négations ont PRIORITÉ sur les keywords car elles sont explicites
        if negations:
            case_dict = case.model_dump()
            detected_fields = metadata.get("detected_fields", []).copy()

            case_dict, detected_fields, negations_applied = apply_negations_to_case(
                case_dict, negations, detected_fields
            )

            # Reconstruire le cas et mettre à jour metadata
            case = HeadacheCase(**case_dict)
            metadata["detected_fields"] = detected_fields
            metadata["negations_detected"] = [
                {"field": n.field, "matched_text": n.matched_text, "confidence": n.confidence}
                for n in negations
            ]
            if negations_applied:
                metadata["negations_applied"] = negations_applied

        # Par défaut, pas d'enrichissement embedding
        hybrid_enhanced = False
        enhancement_details = None

        # ÉTAPE 8: Vérifier si enrichissement embedding nécessaire
        # On utilise le texte SANS négations pour l'embedding
        if self._should_use_embedding(metadata):
            # Enrichir avec embedding (texte sans négations pour éviter faux positifs)
            case, enhancement_details = self._enhance_with_embedding(
                text_without_negations, case, metadata
            )
            hybrid_enhanced = True

            # Mettre à jour métadonnées
            metadata["hybrid_mode"] = "fuzzy+rules+ngrams+keywords+embedding"
            metadata["embedding_used"] = True
            metadata["enhancement_details"] = enhancement_details
        else:
            # Déterminer le mode utilisé
            modes = []
            if fuzzy_corrections:
                modes.append("fuzzy")
            modes.append("rules")
            if ngram_matches:
                modes.append("ngrams")
            if semantic_matches:
                modes.append("semantic")
            elif keyword_matches:
                modes.append("keywords")
            metadata["hybrid_mode"] = "+".join(modes)
            metadata["embedding_used"] = False

        return HybridResult(
            case=case,
            metadata=metadata,
            hybrid_enhanced=hybrid_enhanced,
            enhancement_details=enhancement_details
        )

    def _should_use_embedding(self, metadata: Dict[str, Any]) -> bool:
        """Détermine si l'embedding doit être utilisé.

        Critères:
            - Embedding disponible
            - Confiance globale < seuil
            - OU champs critiques manquants

        Args:
            metadata: Métadonnées de l'analyse par règles

        Returns:
            True si embedding doit être utilisé
        """
        if not self.use_embedding:
            return False

        # Critère 1: Confiance faible
        overall_confidence = metadata.get("overall_confidence", 1.0)
        if overall_confidence < self.confidence_threshold:
            return True

        # Critère 2: Champs critiques manquants
        detected_fields = metadata.get("detected_fields", [])
        critical_fields = ["onset", "fever", "meningeal_signs"]

        missing_critical = len([f for f in critical_fields if f not in detected_fields])
        if missing_critical >= 2:  # Au moins 2 champs critiques manquants
            return True

        return False

    def _enhance_with_embedding(
        self,
        text: str,
        case: HeadacheCase,
        metadata: Dict[str, Any]
    ) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """Enrichit le cas avec similarity embedding.

        Le texte est prétraité pour retirer les durées temporelles avant
        le calcul de similarité, permettant un matching sur les symptômes
        uniquement (pas sur les durées qui sont extraites par les règles).

        Args:
            text: Texte original
            case: Cas parsé par règles
            metadata: Métadonnées de l'analyse

        Returns:
            Tuple (case enrichi, détails enrichissement)
        """
        # Prétraiter le texte pour retirer les durées temporelles
        text_preprocessed = preprocess_for_embedding(text)

        # Encoder le texte requête prétraité
        query_embedding = self.embedder.encode([text_preprocessed], convert_to_numpy=True)[0]

        # Calculer similarités avec tous les exemples
        similarities = np.dot(self.example_embeddings, query_embedding)

        # Trouver top-5 exemples les plus similaires
        top_k = 5
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        top_similarities = similarities[top_indices]
        top_examples = [self.examples[i] for i in top_indices]

        enhancement_details = {
            "top_matches": [
                {
                    "text": ex["text"],
                    "similarity": float(sim),
                    "annotations": ex.get("annotations", {})
                }
                for ex, sim in zip(top_examples, top_similarities)
            ],
            "enriched_fields": []
        }

        # Enrichir les champs manquants avec vote majoritaire
        case_dict = case.model_dump()
        detected_fields = metadata.get("detected_fields", [])

        # Champs à potentiellement enrichir
        fields_to_enrich = [
            "onset", "fever", "meningeal_signs", "htic_pattern",
            "neuro_deficit", "trauma", "seizure",
            "pregnancy_postpartum", "immunosuppression",
            "headache_profile"
        ]

        for field in fields_to_enrich:
            # Enrichir seulement si:
            # 1. Champ pas détecté par règles
            # 2. Champ est None ou "unknown"
            # 3. Au moins 3 exemples similaires ont ce champ
            current_value = case_dict.get(field)

            if (field not in detected_fields or
                current_value is None or
                current_value == "unknown"):

                # Collecter valeurs des exemples similaires (seuil > 0.6)
                candidate_values = [
                    ex.get(field)
                    for ex, sim in zip(top_examples, top_similarities)
                    if ex.get(field) is not None and sim > 0.6
                ]

                if len(candidate_values) >= 2:  # Au moins 2 exemples supportent
                    # Vote majoritaire
                    from collections import Counter
                    vote = Counter(candidate_values).most_common(1)[0]
                    enriched_value = vote[0]
                    confidence = vote[1] / len(candidate_values)

                    if confidence >= 0.5:  # Majorité > 50%
                        case_dict[field] = enriched_value
                        enhancement_details["enriched_fields"].append({
                            "field": field,
                            "value": enriched_value,
                            "confidence": confidence,
                            "support_examples": vote[1]
                        })

        # Détecter patterns spéciaux dans les annotations (névralgies, CCQ, etc.)
        # Ces patterns ne sont pas dans le modèle HeadacheCase mais doivent être signalés
        special_patterns = []
        for ex, sim in zip(top_examples, top_similarities):
            if sim > 0.65:  # Seuil de similarité élevé
                annotations = ex.get("annotations", {})
                source = annotations.get("source", "")

                # Détecter névralgies
                if any(keyword in source.lower() for keyword in ["névralgie", "neuropathie"]):
                    special_patterns.append({
                        "type": "neuralgia",
                        "description": source,
                        "similarity": float(sim),
                        "imaging_recommendation": annotations.get("imaging", "irm_cerebrale"),
                        "matched_text": ex["text"]
                    })

                # Détecter CCQ
                if "ccq" in source.lower() or "chronique quotidienne" in source.lower():
                    special_patterns.append({
                        "type": "chronic_daily_headache",
                        "description": source,
                        "similarity": float(sim),
                        "imaging_recommendation": "irm_cerebrale",
                        "note": annotations.get("note", ""),
                        "matched_text": ex["text"]
                    })

        if special_patterns:
            enhancement_details["special_patterns_detected"] = special_patterns

        # Reconstruire le cas
        case = HeadacheCase(**case_dict)

        return case, enhancement_details


def parse_free_text_to_case_hybrid(text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
    """
    Fonction raccourci pour le parsing hybride.

    Cree une instance HybridNLU a chaque appel. Pour du traitement en lot,
    preferer creer une seule instance et la reutiliser.

    Fonctionnalites :
        - Correction orthographique (fuzzy matching)
        - Detection N-grams (expressions pathognomoniques)
        - Index mots-cles medicaux
        - Gestion des negations (priorite max)
        - Extraction par regles (NLU v2)
        - Fallback embedding pour expressions inconnues

    Args:
        text: Description clinique en texte libre

    Returns:
        Tuple (HeadacheCase, metadata)

    Exemple:
        >>> case, meta = parse_free_text_to_case_hybrid(
        ...     "Pire mal de tete de ma vie, sans fievre"
        ... )
        >>> print(case.onset, case.fever)
        thunderclap False

    Note:
        Premier appel ~2s (chargement modele), ensuite ~200ms.
        Pour du batch, instancier HybridNLU une seule fois.
    """
    nlu = HybridNLU()
    return nlu.parse_free_text_to_case(text)
