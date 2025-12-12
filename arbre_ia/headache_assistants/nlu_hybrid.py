"""NLU Hybride : Règles + Embedding pour robustesse maximale.

Architecture:
    Layer 1 (Primaire): NLU v2 basé sur règles (rapide, déterministe)
    Layer 2 (Fallback): Embedding similarity (gère formulations inconnues)

"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
from dataclasses import dataclass
import warnings

# Import du NLU v2 
from headache_assistants.nlu_v2 import NLUv2
from headache_assistants.models import HeadacheCase
from headache_assistants.medical_examples_corpus import MEDICAL_EXAMPLES

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
        """Initialise le modèle d'embedding et pré-calcule les embeddings."""
        try:
            if self.verbose:
                print(f"[INIT] Chargement du modèle embedding '{model_name}'...")
            self.embedder = SentenceTransformer(model_name)

            # Pré-calculer les embeddings du corpus
            if self.verbose:
                print(f"[INIT] Pré-calcul des embeddings pour {len(self.examples)} exemples...")
            texts = [ex["text"] for ex in self.examples]
            self.example_embeddings = self.embedder.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            if self.verbose:
                print(f"[OK] Modèle embedding initialisé ({self.example_embeddings.shape})")

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

        Args:
            text: Texte médical libre

        Returns:
            HybridResult avec case, metadata, et détails d'enrichissement
        """
        # ÉTAPE 1: Analyse par règles (Layer 1)
        case, metadata = self.rule_nlu.parse_free_text_to_case(text)

        # Par défaut, pas d'enrichissement
        hybrid_enhanced = False
        enhancement_details = None

        # ÉTAPE 2: Vérifier si enrichissement embedding nécessaire
        if self._should_use_embedding(metadata):
            # Enrichir avec embedding
            case, enhancement_details = self._enhance_with_embedding(text, case, metadata)
            hybrid_enhanced = True

            # Mettre à jour métadonnées
            metadata["hybrid_mode"] = "rules+embedding"
            metadata["embedding_used"] = True
            metadata["enhancement_details"] = enhancement_details
        else:
            metadata["hybrid_mode"] = "rules_only"
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

        Args:
            text: Texte original
            case: Cas parsé par règles
            metadata: Métadonnées de l'analyse

        Returns:
            Tuple (case enrichi, détails enrichissement)
        """
        # Encoder le texte requête
        query_embedding = self.embedder.encode([text], convert_to_numpy=True)[0]

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
