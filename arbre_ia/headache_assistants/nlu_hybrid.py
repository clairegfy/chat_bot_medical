"""NLU Hybride : Règles + Embedding pour robustesse maximale.

Architecture:
    Layer 1 (Primaire): NLU v2 basé sur règles (rapide, déterministe)
    Layer 2 (Fallback): Embedding similarity (gère formulations inconnues)

Amélioration v2:
    - Prétraitement pour retirer les durées temporelles avant embedding
    - Corpus atomique sans paramètres temporels inclus
    - Matching plus précis sur les symptômes, pas les durées

Amélioration v3:
    - Détection des négations contextuelles (pas de fièvre, sans déficit, etc.)
    - Les négations sont extraites AVANT l'embedding pour éviter les faux positifs
    - Support des patterns de négation français courants

Amélioration v4:
    - Détection des N-grams (expressions composées à sens médical fort)
    - "pire douleur de ma vie" → thunderclap
    - "vomissements en jet" → HTIC
    - "chien de fusil" → syndrome méningé
    - Priorité sur l'embedding car sens médical spécifique

Pipeline complet:
    1. N-grams (expressions composées)
    2. Négations (pas de, sans, absence de)
    3. Règles NLU v2
    4. Application N-grams + Négations
    5. Embedding (fallback si confiance faible)

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
    "déficit neurologique": "neuro_deficit",
    "déficit moteur": "neuro_deficit",
    "déficit sensitif": "neuro_deficit",
    "paralysie": "neuro_deficit",
    "parésie": "neuro_deficit",
    "faiblesse": "neuro_deficit",
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
) -> Tuple[Dict[str, Any], List[str]]:
    """Applique les négations détectées au cas médical.

    Args:
        case_dict: Dictionnaire du cas (from model_dump())
        negations: Liste des négations détectées
        detected_fields: Liste des champs déjà détectés

    Returns:
        Tuple (case_dict modifié, detected_fields mis à jour)
    """
    for neg in negations:
        # Ne pas écraser si déjà détecté avec une valeur True par les règles
        current_value = case_dict.get(neg.field)
        if current_value is True:
            # Les règles ont détecté True, on ne change pas
            continue

        # Appliquer la négation
        case_dict[neg.field] = False
        if neg.field not in detected_fields:
            detected_fields.append(neg.field)

    return case_dict, detected_fields


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
        "fields": {"onset": "thunderclap", "neuropathic_pattern": True},
        "confidence": 0.85,
        "category": "thunderclap_or_neuralgia"
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
    # -------------------------------------------------------------------------
    "décharge électrique": {
        "fields": {"neuropathic_pattern": True, "facial_pain": True},
        "confidence": 0.90,
        "category": "neuralgia",
        "note": "Névralgie du trijumeau typique"
    },
    "éclair douloureux": {
        "fields": {"neuropathic_pattern": True},
        "confidence": 0.85,
        "category": "neuralgia"
    },
    "douleur fulgurante": {
        "fields": {"neuropathic_pattern": True},
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


def apply_ngrams_to_case(
    case_dict: Dict[str, Any],
    ngram_matches: List[NgramMatch],
    detected_fields: List[str]
) -> Tuple[Dict[str, Any], List[str], List[Dict[str, Any]]]:
    """Applique les n-grams détectés au cas médical.

    Les n-grams ont priorité sur l'embedding mais pas sur les règles
    qui ont déjà détecté une valeur.

    Args:
        case_dict: Dictionnaire du cas
        ngram_matches: Liste des n-grams détectés
        detected_fields: Liste des champs déjà détectés

    Returns:
        Tuple (case_dict modifié, detected_fields mis à jour, détails des applications)
    """
    applied = []

    for match in ngram_matches:
        for field, value in match.fields.items():
            current_value = case_dict.get(field)

            # Appliquer si:
            # - Le champ n'a pas de valeur
            # - Ou la valeur actuelle est "unknown"
            # - Ou le champ n'est pas encore dans detected_fields
            if current_value is None or current_value == "unknown" or field not in detected_fields:
                case_dict[field] = value
                if field not in detected_fields:
                    detected_fields.append(field)

                applied.append({
                    "field": field,
                    "value": value,
                    "pattern": match.pattern,
                    "confidence": match.confidence,
                    "category": match.category,
                    "note": match.note
                })

    return case_dict, detected_fields, applied


@dataclass
class HybridResult:
    """Résultat enrichi du NLU hybride."""
    case: HeadacheCase
    metadata: Dict[str, Any]
    hybrid_enhanced: bool  # True si embedding a été utilisé
    enhancement_details: Optional[Dict[str, Any]] = None


class HybridNLU:
    """NLU Hybride combinant NLU v2 et embedding."""

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        use_embedding: bool = True,
        embedding_model: str = 'all-MiniLM-L6-v2',
        verbose: bool = False
    ):
        """Initialise le NLU hybride.

        Args:
            confidence_threshold: Seuil pour activer embedding (0-1)
            use_embedding: Activer la couche embedding
            embedding_model: Nom du modèle sentence-transformers
            verbose: Afficher messages d'initialisation (défaut: False)
        """
        # Layer 1: Règles 
        self.rule_nlu = NLUv2()
        self.confidence_threshold = confidence_threshold
        self.verbose = verbose

        # Layer 2: Embedding 
        self.use_embedding = use_embedding and EMBEDDING_AVAILABLE
        self.embedder = None
        self.example_embeddings = None
        self.examples = MEDICAL_EXAMPLES

        if self.use_embedding:
            self._initialize_embedding(embedding_model)

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

    def parse_free_text_to_case(self, text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """Analyse un texte médical avec architecture hybride.

        Args:
            text: Texte libre à analyser

        Returns:
            Tuple (HeadacheCase, metadata) compatible avec NLU v2
        """
        hybrid_result = self.parse_hybrid(text)
        return hybrid_result.case, hybrid_result.metadata

    def parse_hybrid(self, text: str) -> HybridResult:
        """Analyse hybride complète avec détails d'enrichissement.

        Pipeline:
            0. Détection des N-grams (expressions composées prioritaires)
            1. Détection des négations
            2. Analyse par règles (NLU v2)
            3. Application des N-grams (haute priorité)
            4. Application des négations
            5. Enrichissement par embedding (si nécessaire)

        Args:
            text: Texte médical libre

        Returns:
            HybridResult avec case, metadata, et détails d'enrichissement
        """
        # ÉTAPE 0: Détection des N-grams (expressions composées)
        # Fait AVANT tout car ces expressions ont un sens médical fort
        ngram_matches = detect_ngrams(text)

        # ÉTAPE 0.5: Détection des négations
        negations, text_without_negations = detect_negations(text)

        # ÉTAPE 1: Analyse par règles (Layer 1)
        case, metadata = self.rule_nlu.parse_free_text_to_case(text)

        # ÉTAPE 1.5: Appliquer les N-grams détectés
        # Les N-grams ont priorité car ils représentent des expressions médicales spécifiques
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

        # ÉTAPE 2: Appliquer les négations détectées
        if negations:
            case_dict = case.model_dump()
            detected_fields = metadata.get("detected_fields", []).copy()

            case_dict, detected_fields = apply_negations_to_case(
                case_dict, negations, detected_fields
            )

            # Reconstruire le cas et mettre à jour metadata
            case = HeadacheCase(**case_dict)
            metadata["detected_fields"] = detected_fields
            metadata["negations_detected"] = [
                {"field": n.field, "matched_text": n.matched_text, "confidence": n.confidence}
                for n in negations
            ]

        # Par défaut, pas d'enrichissement
        hybrid_enhanced = False
        enhancement_details = None

        # ÉTAPE 3: Vérifier si enrichissement embedding nécessaire
        # On utilise le texte SANS négations pour l'embedding
        if self._should_use_embedding(metadata):
            # Enrichir avec embedding (texte sans négations pour éviter faux positifs)
            case, enhancement_details = self._enhance_with_embedding(
                text_without_negations, case, metadata
            )
            hybrid_enhanced = True

            # Mettre à jour métadonnées
            metadata["hybrid_mode"] = "rules+ngrams+embedding"
            metadata["embedding_used"] = True
            metadata["enhancement_details"] = enhancement_details
        else:
            metadata["hybrid_mode"] = "rules+ngrams" if ngram_matches else "rules_only"
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
    """Fonction utilitaire pour analyse hybride rapide.

    Compatible avec l'API NLU v2.

    Args:
        text: Texte médical

    Returns:
        Tuple (HeadacheCase, metadata)
    """
    nlu = HybridNLU()
    return nlu.parse_free_text_to_case(text)
