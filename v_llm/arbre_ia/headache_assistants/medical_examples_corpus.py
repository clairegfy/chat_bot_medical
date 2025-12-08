"""Corpus d'exemples médicaux annotés pour le NLU hybride.

Ce corpus sert de base de connaissances pour le système d'embedding,
permettant de gérer les formulations non couvertes par les règles.

Organisation:
    - Exemples réels anonymisés
    - Patterns validés par médecins
    - Formulations variées (technique/patient)
"""

from typing import List, Dict, Any

# Corpus d'exemples médicaux annotés
MEDICAL_EXAMPLES: List[Dict[str, Any]] = [
    # ========================================================================
    # ONSET - Début de la céphalée
    # ========================================================================
    {
        "text": "Céphalée brutale pire douleur de ma vie",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "HSA classique",
            "keywords": ["brutale", "pire douleur"]
        }
    },
    {
        "text": "Mal de tête soudain très violent comme un coup de marteau",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["soudain", "violent", "coup de marteau"]
        }
    },
    {
        "text": "Douleur crânienne installation progressive sur plusieurs jours",
        "onset": "progressive",
        "profile": "acute",
        "annotations": {
            "source": "Formulation médicale",
            "keywords": ["progressive", "plusieurs jours"]
        }
    },
    {
        "text": "Céphalée qui s'aggrave petit à petit depuis une semaine",
        "onset": "progressive",
        "profile": "subacute",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["aggrave petit à petit", "depuis une semaine"]
        }
    },
    {
        "text": "Mal de tête tous les jours depuis des mois",
        "onset": "chronic",
        "profile": "chronic",
        "annotations": {
            "source": "Céphalée chronique",
            "keywords": ["tous les jours", "depuis des mois"]
        }
    },
    {
        "text": "Douleur permanente au niveau du crâne depuis longtemps",
        "onset": "chronic",
        "profile": "chronic",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["permanente", "depuis longtemps"]
        }
    },

    # ========================================================================
    # FIÈVRE
    # ========================================================================
    {
        "text": "Patient fébrile à 39 degrés",
        "fever": True,
        "annotations": {
            "source": "Formulation médicale classique",
            "keywords": ["fébrile", "39"]
        }
    },
    {
        "text": "Il a chaud et transpire beaucoup",
        "fever": True,
        "annotations": {
            "source": "Langage patient - signes indirects",
            "keywords": ["chaud", "transpire"]
        }
    },
    {
        "text": "Température normale, pas de fièvre",
        "fever": False,
        "annotations": {
            "source": "Négation explicite",
            "keywords": ["normale", "pas de fièvre"]
        }
    },
    {
        "text": "Apyrétique depuis consultation",
        "fever": False,
        "annotations": {
            "source": "Terme médical",
            "keywords": ["apyrétique"]
        }
    },

    # ========================================================================
    # SYNDROME MÉNINGÉ
    # ========================================================================
    {
        "text": "Raideur de nuque importante avec impossibilité de fléchir",
        "meningeal_signs": True,
        "annotations": {
            "source": "Signe méningé classique",
            "keywords": ["raideur nuque", "impossibilité fléchir"]
        }
    },
    {
        "text": "Le patient ne peut plus bouger le cou tellement c'est raide",
        "meningeal_signs": True,
        "annotations": {
            "source": "Langage patient",
            "keywords": ["ne peut plus bouger cou", "raide"]
        }
    },
    {
        "text": "Kernig et Brudzinski positifs",
        "meningeal_signs": True,
        "annotations": {
            "source": "Signes cliniques",
            "keywords": ["Kernig", "Brudzinski"]
        }
    },
    {
        "text": "Position en chien de fusil au lit",
        "meningeal_signs": True,
        "annotations": {
            "source": "Posture méningée",
            "keywords": ["chien de fusil"]
        }
    },
    {
        "text": "Nuque souple, pas de signes méningés",
        "meningeal_signs": False,
        "annotations": {
            "source": "Examen négatif",
            "keywords": ["nuque souple", "pas de signes"]
        }
    },

    # ========================================================================
    # HTIC - Hypertension IntraCrânienne
    # ========================================================================
    {
        "text": "Céphalée pire le matin au réveil avec vomissements",
        "htic_pattern": True,
        "annotations": {
            "source": "HTIC classique",
            "keywords": ["pire le matin", "vomissements"]
        }
    },
    {
        "text": "Douleur qui empire quand il tousse ou fait un effort",
        "htic_pattern": True,
        "annotations": {
            "source": "Déclencheurs HTIC",
            "keywords": ["empire", "tousse", "effort"]
        }
    },
    {
        "text": "Céphalée matutinale avec œdème papillaire au fond d'œil",
        "htic_pattern": True,
        "annotations": {
            "source": "HTIC avec signe ophtalmo",
            "keywords": ["matutinale", "œdème papillaire"]
        }
    },

    # ========================================================================
    # DÉFICIT NEUROLOGIQUE
    # ========================================================================
    {
        "text": "Faiblesse du bras droit avec difficulté à lever",
        "neuro_deficit": True,
        "annotations": {
            "source": "Déficit moteur",
            "keywords": ["faiblesse bras", "difficulté lever"]
        }
    },
    {
        "text": "Le patient n'arrive plus à parler correctement",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble langage",
            "keywords": ["n'arrive plus parler"]
        }
    },
    {
        "text": "Vision double depuis ce matin",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble visuel",
            "keywords": ["vision double"]
        }
    },
    {
        "text": "Patient confus, désorienté dans le temps",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble conscience",
            "keywords": ["confus", "désorienté"]
        }
    },
    {
        "text": "Examen neurologique strictement normal",
        "neuro_deficit": False,
        "annotations": {
            "source": "Examen négatif",
            "keywords": ["normal"]
        }
    },

    # ========================================================================
    # TRAUMATISME
    # ========================================================================
    {
        "text": "Chute avec choc à la tête hier",
        "trauma": True,
        "annotations": {
            "source": "Traumatisme récent",
            "keywords": ["chute", "choc tête"]
        }
    },
    {
        "text": "Accident de voiture il y a 2 jours",
        "trauma": True,
        "annotations": {
            "source": "AVP",
            "keywords": ["accident voiture"]
        }
    },
    {
        "text": "Pas de notion de traumatisme crânien",
        "trauma": False,
        "annotations": {
            "source": "Négation explicite",
            "keywords": ["pas de traumatisme"]
        }
    },

    # ========================================================================
    # CRISES / CONVULSIONS
    # ========================================================================
    {
        "text": "Épisode de convulsions ce matin",
        "seizure": True,
        "annotations": {
            "source": "Crise convulsive",
            "keywords": ["convulsions"]
        }
    },
    {
        "text": "Perte de connaissance avec mouvements anormaux",
        "seizure": True,
        "annotations": {
            "source": "Description patient",
            "keywords": ["perte connaissance", "mouvements anormaux"]
        }
    },

    # ========================================================================
    # GROSSESSE / POST-PARTUM
    # ========================================================================
    {
        "text": "Patiente enceinte de 7 mois",
        "pregnancy_postpartum": True,
        "annotations": {
            "source": "Grossesse en cours",
            "keywords": ["enceinte"]
        }
    },
    {
        "text": "Accouchement il y a 2 semaines",
        "pregnancy_postpartum": True,
        "annotations": {
            "source": "Post-partum",
            "keywords": ["accouchement", "2 semaines"]
        }
    },

    # ========================================================================
    # IMMUNODÉPRESSION
    # ========================================================================
    {
        "text": "Patient VIH positif sous traitement",
        "immunosuppression": True,
        "annotations": {
            "source": "VIH",
            "keywords": ["VIH positif"]
        }
    },
    {
        "text": "Antécédent de chimiothérapie pour cancer du sein",
        "immunosuppression": True,
        "annotations": {
            "source": "Traitement immunosuppresseur",
            "keywords": ["chimiothérapie"]
        }
    },

    # ========================================================================
    # PROFILS CLINIQUES - Caractéristiques céphalée
    # ========================================================================
    {
        "text": "Douleur d'un seul côté qui bat avec gêne à la lumière",
        "headache_profile": "migraine_like",
        "annotations": {
            "source": "Migraine classique",
            "keywords": ["un seul côté", "bat", "gêne lumière"]
        }
    },
    {
        "text": "Céphalée pulsatile temporale gauche avec nausées",
        "headache_profile": "migraine_like",
        "annotations": {
            "source": "Migraine médicale",
            "keywords": ["pulsatile", "temporale", "nausées"]
        }
    },
    {
        "text": "Mal de tête des deux côtés comme un bandeau serré",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Céphalée tension",
            "keywords": ["deux côtés", "bandeau serré"]
        }
    },
    {
        "text": "Douleur en étau bilatérale sans nausées",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Tension type",
            "keywords": ["étau", "bilatérale"]
        }
    },
    {
        "text": "Douleur atroce derrière l'œil gauche avec larmoiement",
        "headache_profile": "cluster_like",
        "annotations": {
            "source": "Algie vasculaire face",
            "keywords": ["derrière œil", "larmoiement"]
        }
    },

    # ========================================================================
    # CAS COMPLEXES - Formulations inhabituelles
    # ========================================================================
    {
        "text": "Sensation d'explosion dans la tête en plein effort",
        "onset": "thunderclap",
        "htic_pattern": True,
        "annotations": {
            "source": "HSA à l'effort",
            "keywords": ["explosion", "plein effort"]
        }
    },
    {
        "text": "Douleur crânienne maximale d'emblée pendant rapport sexuel",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Céphalée coïtale",
            "keywords": ["maximale d'emblée", "rapport sexuel"]
        }
    },
    {
        "text": "Tête qui serre fort quand je travaille devant l'ordinateur",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Céphalée tension contexte",
            "keywords": ["serre fort", "travaille ordinateur"]
        }
    },
]


def get_examples_by_field(field: str, value: Any = True) -> List[Dict[str, Any]]:
    """Récupère tous les exemples annotés pour un champ donné.

    Args:
        field: Nom du champ (fever, onset, meningeal_signs, etc.)
        value: Valeur recherchée (par défaut True)

    Returns:
        Liste d'exemples correspondants
    """
    return [ex for ex in MEDICAL_EXAMPLES if ex.get(field) == value]


def get_all_texts() -> List[str]:
    """Retourne tous les textes du corpus."""
    return [ex["text"] for ex in MEDICAL_EXAMPLES]


def get_corpus_statistics() -> Dict[str, int]:
    """Statistiques du corpus."""
    stats = {
        "total_examples": len(MEDICAL_EXAMPLES),
        "with_onset": len([ex for ex in MEDICAL_EXAMPLES if "onset" in ex]),
        "with_fever": len([ex for ex in MEDICAL_EXAMPLES if "fever" in ex]),
        "with_meningeal": len([ex for ex in MEDICAL_EXAMPLES if "meningeal_signs" in ex]),
        "with_htic": len([ex for ex in MEDICAL_EXAMPLES if "htic_pattern" in ex]),
        "with_neuro_deficit": len([ex for ex in MEDICAL_EXAMPLES if "neuro_deficit" in ex]),
        "with_trauma": len([ex for ex in MEDICAL_EXAMPLES if "trauma" in ex]),
        "with_profile": len([ex for ex in MEDICAL_EXAMPLES if "headache_profile" in ex]),
    }
    return stats


if __name__ == "__main__":
    # Afficher statistiques du corpus
    stats = get_corpus_statistics()
    print("=" * 60)
    print("CORPUS MÉDICAL - Statistiques")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key:25s}: {value:3d}")
    print("=" * 60)

    # Exemples par catégorie
    print("\nExemples ONSET thunderclap:")
    for ex in get_examples_by_field("onset", "thunderclap")[:3]:
        print(f"  • {ex['text']}")

    print("\nExemples FIÈVRE (positifs):")
    for ex in get_examples_by_field("fever", True)[:3]:
        print(f"  • {ex['text']}")
