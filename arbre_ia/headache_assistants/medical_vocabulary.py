"""Dictionnaire médical centralisé pour la détection robuste de termes cliniques.

Ce module fournit un système de normalisation sémantique qui résout les problèmes
de synonymes, acronymes et variations linguistiques dans les textes médicaux.

Architecture:
    1. Dictionnaire central avec ontologie médicale
    2. Normalisation linguistique (lemmatisation, accents)
    3. Scoring de confiance pour chaque détection
    4. Gestion des contextes d'exclusion (anti-patterns)
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import unicodedata


class ConceptCategory(Enum):
    """Catégories de concepts médicaux."""
    ONSET = "onset"
    PROFILE = "profile"
    INTENSITY = "intensity"
    FEVER = "fever"
    MENINGEAL_SIGNS = "meningeal_signs"
    HTIC = "htic_pattern"
    TRAUMA = "trauma"
    NEURO_DEFICIT = "neuro_deficit"
    SEIZURE = "seizure"
    PREGNANCY = "pregnancy_postpartum"
    IMMUNOSUPPRESSION = "immunosuppression"
    HEADACHE_PROFILE = "headache_profile"


@dataclass
class DetectionResult:
    """Résultat d'une détection de concept médical.

    Attributes:
        detected: True si le concept a été détecté
        value: Valeur détectée (ex: True/False pour booléens, "thunderclap" pour onset)
        confidence: Score de confiance 0-1
        matched_term: Terme exact qui a matché
        canonical_form: Forme canonique du concept
        source: Source de la détection (acronym, synonym, canonical, etc.)
    """
    detected: bool
    value: any
    confidence: float
    matched_term: str = ""
    canonical_form: str = ""
    source: str = ""


class MedicalVocabulary:
    """Dictionnaire médical avec normalisation sémantique.

    Ce système central gère tous les synonymes, acronymes et variations
    pour chaque concept médical, avec scoring de confiance.
    """

    def __init__(self):
        """Initialise le dictionnaire médical."""
        self._build_vocabulary()

    def _build_vocabulary(self):
        """Construit le dictionnaire médical complet avec ontologie."""

        # ====================================================================
        # ONSET (type de début)
        # ====================================================================
        self.onset_vocabulary = {
            "thunderclap": {
                "canonical": ["coup de tonnerre", "thunderclap"],
                "acronyms": ["cdt"],
                "synonyms": [
                    "brutale", "brutal", "soudaine", "soudain", "instantanée", "instantané",
                    "d'emblée maximale", "maximale d'emblée", "violence maximale d'emblée",
                    "installation brutale", "d'installation brutale",
                    "début brutal", "début soudain", "ictus céphalalgique",
                    "explosive", "explosif", "foudroyante", "foudroyant"
                ],
                "phrases": [
                    "en quelques secondes", "d'un coup", "d'un seul coup",
                    "tout d'un coup", "commencé d'un coup", "du jour au lendemain",
                    "jamais eu aussi mal", "jamais ressenti",
                    "pire douleur de ma vie", "pire douleur de sa vie",
                    "pire mal de ma vie", "pire mal de sa vie",
                    "pire céphalée de ma vie", "pire céphalée de sa vie"
                ],
                "medical_terms": ["HSA suspectée", "hémorragie sous-arachnoïdienne"],
                "confidence": 0.95  # Haute confiance pour onset critique
            },
            "progressive": {
                "canonical": ["progressive", "progressif"],
                "synonyms": [
                    "progressivement", "qui augmente", "installation progressive",
                    "progressivement installée", "progressivement installé",
                    "en quelques heures", "en quelques jours"  # Ajouté ici
                ],
                "confidence": 0.85
            },
            "chronic": {
                "canonical": ["chronique"],
                "synonyms": [
                    "permanente", "permanent", "quotidienne", "quotidien",
                    "de longue date", "depuis longtemps",
                    "depuis des mois", "depuis des années",  # Ajouté ici
                    "tous les jours", "chaque jour"
                ],
                "medical_terms": ["céphalée chronique quotidienne", "CCQ"],
                "confidence": 0.90
            }
        }

        # ====================================================================
        # FIÈVRE
        # ====================================================================
        self.fever_vocabulary = {
            True: {
                "canonical": ["fièvre", "fébrile"],
                "acronyms": ["féb"],  # "T°" déplacé dans patterns numériques
                "synonyms": ["hyperthermie"],  # Retiré "température" et "temp" (trop génériques)
                "numeric_patterns": [
                    # Patterns avec "T" ou "T°" suivi d'un nombre (ex: T 39, T° 40.5, T=41)
                    r"\b[Tt]°?\s*(?:=\s*)?(\d{2}(?:\.\d+)?)",
                    # Pattern français: 38°5, 39°8, 40°2 (notation décimale avec °)
                    r"\b(\d{2})°(\d)",
                    # Température avec °C ou juste ° (ex: 39°, 40.5°C, 38°C, 41°)
                    r"\b(\d{2}(?:\.\d+)?)\s*°[Cc]?(?:\b|$|\s|,)",
                    # Température en contexte (ex: "température 39", "température à 40")
                    r"temp[ée]rature\s*(?:[àa]\s*)?(\d{2}(?:\.\d+)?)",
                ],
                "phrases": ["avec de la fièvre", "en hyperthermie"],
                "threshold": 38.0,  # Température ≥ 38°C = fièvre
                "confidence": 0.90
            },
            False: {
                "canonical": ["sans fièvre", "sans fievre", "apyrétique", "apyretique"],
                "acronyms": ["apyr"],
                "synonyms": [
                    "pas de fièvre", "pas de fievre",
                    "afébril", "afébrile", "afebril", "afebrile",
                    "absence de fièvre", "absence de fievre",
                    "pas fébrile", "pas febrile",
                    "non fébrile", "non febrile",
                    "aucune fièvre", "aucune fievre",
                    "nie fièvre", "nie fievre", "nie toute fièvre", "nie toute fievre"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # SYNDROME MÉNINGÉ
        # ====================================================================
        self.meningeal_signs_vocabulary = {
            True: {
                "canonical": ["syndrome méningé", "signes méningés"],
                "acronyms": [
                    "sdm", "sdm méningé", "sg méningés", "sgs méningés",
                    "rdn", "rdn+", "rdn++", "RDN", "RDN+", "RDN++"
                ],
                "clinical_signs": [
                    "raideur nuque", "raideur de la nuque", "raideur de nuque",
                    "raideur méningée",
                    "signe de kernig", "kernig positif", "kernig pos", "kernig+",
                    "signe de brudzinski", "brudzinski positif", "brudzinski pos", "brudzinski+",
                    "nuque raide", "chien de fusil"
                ],
                "patient_language": [
                    "ne peut pas bouger le cou", "ne peut pas bouger la nuque",
                    "ne peut pas tourner le cou", "ne peut pas tourner la nuque",
                    "ne peut pas plier le cou", "ne peut pas plier la nuque",
                    "impossible de bouger la tête", "impossible de bouger le cou",
                    "impossible de plier la nuque", "impossible de tourner la tête",
                    "cou bloqué", "cou raide", "nuque douloureuse",
                    "nuque tendue", "nuque bloquée"
                ],
                "confidence": 0.95  # Haute confiance car signe critique
            },
            False: {
                "canonical": [
                    "sans signe méningé", "sans signe meninge",
                    "pas de syndrome méningé", "pas de syndrome meninge"
                ],
                "acronyms": ["rdn-", "rdn nég", "rdn neg", "kernig-", "brudzinski-"],
                "synonyms": [
                    "sans raideur", "pas de raideur", "pas de rdn",
                    "pas de kernig", "pas de brudzinski",
                    "nuque souple", "kernig négatif", "brudzinski négatif",
                    "aucune raideur", "aucune raideur de nuque",
                    "aucun signe méningé", "aucun signe meninge",
                    "pas de raideur de nuque", "pas de raideur nuque",
                    "raideur de nuque absente", "raideur nuque absente"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # HTIC (Hypertension IntraCrânienne)
        # ====================================================================
        self.htic_vocabulary = {
            True: {
                "canonical": ["hypertension intracrânienne", "HTIC"],
                "acronyms": ["htic", "sdm htic", "signes htic", "signes d'htic"],
                "clinical_patterns": [
                    # SIGNES FORTS uniquement - haute spécificité HTIC
                    "vomissements en jet", "vom en jet", "vomissement en jet",
                    # RETIRÉS: "aggravation toux/effort" seuls
                    # → Peuvent être céphalée bénigne de toux (toux chronique, Valsalva)
                    # → HTIC nécessite vomissements en jet OU œdème papillaire OU mention explicite
                ],
                "ophtalmo_signs": [
                    "œdème papillaire", "oedème papillaire", "op++", "op+",
                    "flou visuel", "éclipses visuelles", "éclipse visuelle"
                ],
                # SUPPRIMÉ: temporal_phrases (signes trop faibles)
                # "plus forte le matin", "pire le matin" peuvent être migraine/tension
                # HTIC nécessite signes FORTS: vomissements en jet OU œdème papillaire
                "confidence": 0.90,
                # Anti-patterns: termes qui ressemblent mais ne sont PAS HTIC
                "exclusions": ["scotomes", "scotome", "aura"]  # Aura migraineuse ≠ HTIC
            },
            False: {
                "canonical": ["pas de signes htic", "sans htic"],
                "synonyms": ["htic négatif", "htic absent", "htic écarté"],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # TRAUMATISME CRÂNIEN
        # ====================================================================
        self.trauma_vocabulary = {
            True: {
                "canonical": ["traumatisme crânien", "trauma crânien"],
                "acronyms": [
                    "tcc", "tce", "avp", "pdc",
                    "TCC", "TCE", "AVP", "PDC"
                ],
                "full_terms": [
                    "traumatisme cranio-cérébral", "traumatisme cérébral",
                    "accident de la voie publique", "accident voie publique",
                    "perte de connaissance"
                ],
                "mechanisms": [
                    "chute", "choc à la tête", "choc au crâne",
                    "coup à la tête", "coup au crâne", "coup sur la tête",
                    "coup sur le crâne", "choc sur la tête", "choc sur le crâne"
                ],
                "temporal_context": [
                    "depuis traumatisme", "dep traumatisme",
                    "depuis trauma", "dep trauma",
                    "depuis chute", "dep chute",
                    "après traumatisme", "après trauma", "après chute",
                    "post-traumatique", "post traumatique",
                    "contexte de trauma", "contexte traumatique"
                ],
                "confidence": 0.90
            },
            False: {
                "canonical": ["pas de traumatisme", "sans traumatisme"],
                "synonyms": [
                    "aucun traumatisme", "pas de choc", "sans choc",
                    "nie traumatisme", "nie tout traumatisme",
                    "sans trauma", "nie trauma"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # DÉFICIT NEUROLOGIQUE
        # ====================================================================
        self.neuro_deficit_vocabulary = {
            True: {
                "canonical": ["déficit neurologique", "déficit neurologique focal"],
                "acronyms": [
                    "dsm", "pf", "glasgow", "gcs",
                    "DSM", "PF", "GCS"
                ],
                "motor_deficits": [
                    "hémiparésie", "hémipar d", "hémipar g",
                    "hémiplégie", "parésie", "paralysie",
                    "paralysie faciale",
                    "faiblesse bras", "faiblesse jambe",
                    "faiblesse membre", "faiblesse mb",
                    "faiblesse d'un bras", "faiblesse d'un membre",
                    "faiblesse du bras", "faiblesse de la jambe"  # Ajouté
                ],
                "language_deficits": [
                    "aphasie", "trouble du langage", "troubles du langage",
                    "difficulté à parler", "difficultés à parler",
                    "difficulté pour parler", "difficultés pour parler",
                    "troubles de la parole", "trouble de la parole"
                ],
                "visual_deficits": [
                    "hémianopsie", "diplopie", "vision double",
                    "flou visuel", "vision floue", "vision trouble",
                    "perte de la vision", "perte de vision",
                    "troubles visuels", "trouble visuel"
                ],
                "consciousness": [
                    "confusion", "désorientation", "désorienté",
                    "altération de la conscience", "altération de conscience",
                    "troubles mnésiques", "trouble mnésique"
                ],
                "patient_language": [
                    "ne peut plus bouger", "ne peut pas bouger",
                    "ne peut plus lever le bras", "ne peut plus lever la jambe",
                    "ne peut pas lever le bras", "ne peut pas lever la jambe"
                ],
                "confidence": 0.90,
                # Exclusions: termes qui ne sont PAS des déficits neurologiques
                "exclusions": [
                    # Scotome/aura sont des phénomènes migraineux, pas des déficits
                    # SAUF si accompagnés de vrais déficits moteurs/sensitifs
                ]
            },
            False: {
                "canonical": ["pas de déficit", "sans déficit"],
                "synonyms": [
                    "aucun déficit", "pas de déficit neurologique",
                    "sans déficit neurologique",
                    "pas de trouble neurologique", "sans trouble neurologique",
                    "pas de trouble moteur", "sans trouble moteur",
                    "pas de trouble sensitif", "sans trouble sensitif",
                    "examen neurologique normal"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # CRISES D'ÉPILEPSIE / CONVULSIONS
        # ====================================================================
        self.seizure_vocabulary = {
            True: {
                "canonical": ["crise d'épilepsie", "crise épileptique"],
                "acronyms": ["cgt", "crise tc", "CGT"],
                "medical_terms": [
                    "crise comitiale", "crise convulsive",
                    "crises épileptiques", "crises convulsives",
                    "crise généralisée tonico-clonique",
                    "crise tonico-clonique", "crise tonique", "crise clonique"
                ],
                "generic_terms": [
                    "convulsions", "convulsion", "épilepsie",
                    "a convulsé", "fait une crise", "a fait une crise"
                ],
                "temporal_context": [
                    "crise ce matin", "crise hier", "crise ce soir",
                    "suivie d'une crise", "puis convulsions",
                    "avec convulsions", "accompagnée de convulsions"
                ],
                "clinical_description": [
                    "mouvements anormaux", "secousses",
                    "perte de connaissance avec secousses",
                    "pdc avec secousses"
                ],
                "confidence": 0.90
            },
            False: {
                "canonical": ["pas de crise", "sans crise"],
                "synonyms": [
                    "pas de convulsion", "sans convulsion",
                    "nie toute crise", "nie crise"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # GROSSESSE / POST-PARTUM
        # ====================================================================
        self.pregnancy_vocabulary = {
            True: {
                "canonical": ["enceinte", "grossesse", "post-partum"],
                "medical_terms": [
                    "femme enceinte", "patiente enceinte",
                    "gestante", "en gestation",
                    "femme gestante", "patiente gestante",
                    "patiente en gestation"
                ],
                "acronyms": [
                    "g1p0", "g2p1", "g0p0",  # Grossesse/Parité
                    "sa",  # Semaines d'Aménorrhée (contextualisé)
                    "t1", "t2", "t3"  # Trimestres
                ],
                "temporal_terms": [
                    "1er trimestre", "2ème trimestre", "3ème trimestre",
                    "premier trimestre", "deuxième trimestre", "troisième trimestre"
                ],
                "postpartum": [
                    "post-partum", "postpartum", "post partum",
                    "accouchement", "a accouché", "vient d'accoucher",
                    "suite à accouchement", "suite à un accouchement",
                    "après accouchement", "après l'accouchement",
                    "période du post-partum", "période de post-partum",
                    "jeune mère", "mère"
                ],
                "obstetric_context": ["gravidique"],
                "confidence": 0.95  # Haute confiance car contexte critique
            }
        }

        # ====================================================================
        # IMMUNODÉPRESSION
        # ====================================================================
        self.immunosuppression_vocabulary = {
            True: {
                "canonical": ["immunodéprimé", "immunodéprimée", "immunodépression"],
                "medical_conditions": [
                    "vih", "vih+", "vih positif", "sida",
                    "séropositif", "séropositive"
                ],
                "treatments": [
                    "chimiothérapie", "chimio", "sous chimiothérapie",
                    "corticoïde", "corticothérapie", "cortico",
                    "sous corticothérapie", "corticothérapie au long cours",
                    "immunosuppresseur", "ttt immunosup"
                ],
                "contexts": [
                    "greffe", "greffé", "greffée", "patient greffé"
                ],
                "oncology": [
                    "cancer", "k poumon", "k sein", "k colon",
                    "k prostate", "k ovaire"
                ],
                "bio_markers": ["cd4"],
                "confidence": 0.90
            }
        }

        # ====================================================================
        # CONTEXTE ONCOLOGIQUE (PRIORITÉ 1 - impact décision scanner/IRM)
        # ====================================================================
        self.cancer_history_vocabulary = {
            True: {
                "canonical": [
                    "cancer", "antécédent cancer", "atcd cancer",
                    "histoire de cancer", "antécédent de cancer"
                ],
                "medical_terms": [
                    "néoplasie", "tumeur maligne", "carcinome",
                    "adénocarcinome", "épithélioma", "sarcome"
                ],
                "contexts": [
                    "oncologique", "contexte oncologique", "suivi oncologique",
                    "en rémission", "rémission complète"
                ],
                "treatments": [
                    "chimio", "chimiothérapie", "sous chimiothérapie",
                    "radiothérapie", "radiothérapie", "immunothérapie",
                    "hormonothérapie"
                ],
                "specific_cancers": [
                    "cancer poumon", "cancer du poumon", "k poumon",
                    "cancer sein", "cancer du sein", "k sein",
                    "cancer colon", "cancer colorectal", "k colon",
                    "cancer prostate", "k prostate",
                    "cancer ovaire", "k ovaire",
                    "leucémie", "lymphome", "myélome"
                ],
                "metastasis": [
                    "métastase", "métastases", "métastatique",
                    "métastase cérébrale", "métastases cérébrales",
                    "localisation secondaire", "envahissement"
                ],
                "temporal_context": [
                    "traité pour", "traité il y a", "opéré pour",
                    "sous traitement pour", "en cours de traitement",
                    "antécédent de", "atcd de"
                ],
                "confidence": 0.95  # Haute confiance car contexte critique
            },
            False: {
                "canonical": ["pas de cancer", "sans cancer", "sans atcd cancer"],
                "synonyms": [
                    "aucun cancer", "pas d'antécédent cancer",
                    "sans antécédent oncologique", "nie cancer"
                ],
                "confidence": 0.85
            }
        }

        # ====================================================================
        # VERTIGES (PRIORITÉ 2)
        # ====================================================================
        self.vertigo_vocabulary = {
            True: {
                "canonical": ["vertige", "vertiges"],
                "medical_terms": [
                    "syndrome vestibulaire", "vertige positionnel",
                    "vertige rotatoire", "vertige central", "vertige périphérique"
                ],
                "patient_language": [
                    "tournement", "tournoiement", "tourne",
                    "la pièce qui tourne", "tout tourne", "ça tourne",
                    "impression de tourner", "sensation de tourner"
                ],
                "generic_terms": [
                    "instabilité", "instable", "déséquilibre",
                    "perte d'équilibre", "mal à tenir debout"
                ],
                "confidence": 0.85
            },
            False: {
                "canonical": ["pas de vertige", "sans vertige"],
                "synonyms": ["aucun vertige", "nie vertige", "pas de déséquilibre"],
                "confidence": 0.80
            }
        }

        # ====================================================================
        # ACOUPHÈNES (PRIORITÉ 2)
        # ====================================================================
        self.tinnitus_vocabulary = {
            True: {
                "canonical": ["acouphène", "acouphènes", "tinnitus"],
                "patient_language": [
                    "sifflement", "sifflements", "siffle dans l'oreille",
                    "bourdonnement", "bourdonnements", "bourdonne",
                    "bruit dans l'oreille", "bruit dans les oreilles",
                    "entend des bruits", "entend un bruit",
                    "oreille qui siffle", "oreilles qui sifflent"
                ],
                "medical_terms": [
                    "acouphène pulsatile", "acouphènes bilatéraux",
                    "acouphène unilatéral"
                ],
                "confidence": 0.85
            },
            False: {
                "canonical": ["pas d'acouphène", "sans acouphène"],
                "synonyms": ["aucun acouphène", "nie acouphène", "pas de tinnitus"],
                "confidence": 0.80
            }
        }

        # ====================================================================
        # TROUBLES VISUELS - TYPE (PRIORITÉ 2)
        # ====================================================================
        self.visual_disturbance_vocabulary = {
            "stroboscopic": {
                "canonical": ["scotome scintillant", "aura visuelle"],
                "medical_terms": [
                    "spectre de fortification", "phosphènes",
                    "points lumineux", "éclairs lumineux",
                    "tâches lumineuses", "zigzags lumineux"
                ],
                "patient_language": [
                    "voit des éclairs", "voit des points brillants",
                    "comme des flashs", "lumières qui clignotent",
                    "scintillement", "ça clignote"
                ],
                "confidence": 0.85
            },
            "blur": {
                "canonical": ["vision floue", "flou visuel"],
                "patient_language": [
                    "voit flou", "voit trouble", "vision trouble",
                    "ne voit pas net", "vision pas nette"
                ],
                "confidence": 0.80
            },
            "blindness": {
                "canonical": ["cécité", "perte de vision", "amaurose"],
                "medical_terms": [
                    "cécité monoculaire", "amaurose fugace",
                    "perte de vision brutale"
                ],
                "patient_language": [
                    "ne voit plus", "ne voit rien", "tout noir",
                    "a perdu la vue", "vision disparue"
                ],
                "confidence": 0.90
            },
            "none": {
                "canonical": ["pas de troubles visuels", "sans troubles visuels"],
                "synonyms": ["vision normale", "voit bien", "pas de problème visuel"],
                "confidence": 0.75
            }
        }

        # ====================================================================
        # DOULEURS ARTICULAIRES (PRIORITÉ 2 - lié Horton)
        # ====================================================================
        self.joint_pain_vocabulary = {
            True: {
                "canonical": ["douleurs articulaires", "douleur articulaire"],
                "medical_terms": [
                    "arthralgies", "arthralgie", "polyarthralgies",
                    "rhumatisme", "douleurs rhumatismales"
                ],
                "patient_language": [
                    "mal aux articulations", "articulations douloureuses",
                    "douleurs dans les articulations"
                ],
                "confidence": 0.80
            },
            False: {
                "canonical": ["pas de douleurs articulaires", "sans arthralgies"],
                "synonyms": ["aucune arthralgie", "pas d'arthralgie"],
                "confidence": 0.75
            }
        }

        # ====================================================================
        # CRITÈRES HORTON / ARTÉRITE TEMPORALE (PRIORITÉ 2)
        # ====================================================================
        self.horton_criteria_vocabulary = {
            True: {
                "canonical": ["maladie de Horton", "Horton", "artérite temporale"],
                "clinical_signs": [
                    "claudication mâchoire", "claudication de la mâchoire",
                    "claudication mandibulaire",
                    "douleur à la mastication", "douleur en mâchant",
                    "mal quand il mâche", "mal quand elle mâche"
                ],
                "vascular_signs": [
                    "artère temporale", "artères temporales",
                    "artère temporale indurée", "artère temporale sensible",
                    "artère temporale douloureuse",
                    "pouls temporal aboli", "pouls temporal absent"
                ],
                "systemic_symptoms": [
                    "pseudopolyarthrite rhizomélique", "PPR",
                    "altération état général", "aeg", "amaigrissement",
                    "fièvre prolongée", "sueurs nocturnes"
                ],
                "lab_markers": [
                    "VS élevée", "VS augmentée", "CRP élevée", "CRP augmentée",
                    "syndrome inflammatoire"
                ],
                "confidence": 0.90
            },
            False: {
                "canonical": ["pas de signe Horton", "Horton écarté"],
                "synonyms": ["pas d'artérite temporale", "sans Horton"],
                "confidence": 0.80
            }
        }

        # ====================================================================
        # LOCALISATION CÉPHALÉE (PRIORITÉ 4)
        # ====================================================================
        self.headache_location_vocabulary = {
            "frontal": {
                "canonical": ["frontale", "frontal"],
                "patient_language": ["front", "au front", "sur le front"],
                "confidence": 0.80
            },
            "temporal": {
                "canonical": ["temporale", "temporal"],
                "patient_language": ["tempe", "tempes", "sur la tempe", "aux tempes"],
                "confidence": 0.80
            },
            "occipital": {
                "canonical": ["occipitale", "occipital"],
                "patient_language": [
                    "arrière", "derrière", "nuque",
                    "arrière de la tête", "derrière la tête"
                ],
                "confidence": 0.80
            },
            "unilateral": {
                "canonical": ["unilatérale", "unilatéral", "hémicrânie"],
                "patient_language": [
                    "d'un côté", "d'un seul côté",
                    "côté droit", "côté gauche", "à droite", "à gauche",
                    "moitié droite", "moitié gauche"
                ],
                "confidence": 0.85
            },
            "diffuse": {
                "canonical": ["diffuse", "diffus", "généralisée"],
                "patient_language": [
                    "partout", "toute la tête", "toute la tête",
                    "dans toute la tête"
                ],
                "confidence": 0.75
            }
        }

        # ====================================================================
        # CHANGEMENT RÉCENT DE PATTERN (pour céphalées chroniques)
        # ====================================================================
        self.pattern_change_vocabulary = {
            True: {
                "canonical": [
                    "changement récent", "modification récente",
                    "aggravation récente", "aggravé récemment",
                    "ont changé", "a changé", "ont change", "a change",
                    "changé récemment", "change recemment"
                ],
                "temporal_markers": [
                    "pire depuis", "pire dep", "aggravé depuis",
                    "aggravée depuis", "plus forte depuis",
                    "changé depuis", "différent depuis",
                    "nouveau depuis", "nouvel épisode",
                    "jamais eu ça avant", "inhabituel",
                    "jamais comme ça", "pas comme d'habitude",
                    "pas comme avant", "différent d'habitude"
                ],
                "intensity_change": [
                    "beaucoup plus forte", "beaucoup plus intense",
                    "intensité augmentée", "intensité croissante",
                    "douleur accrue", "s'aggrave", "empire",
                    "devient de pire en pire",
                    "plus fréquentes", "plus frequentes",
                    "plus intenses", "plus intense",
                    "durent plus longtemps"
                ],
                "new_symptoms": [
                    "nouveaux symptômes", "nouveau symptôme",
                    "maintenant avec", "accompagné maintenant de",
                    "en plus maintenant", "apparition de"
                ],
                "temporal_windows": [
                    "depuis 1 semaine", "depuis une semaine",
                    "depuis quelques jours", "depuis qqs jours",
                    "depuis 2 semaines", "depuis 1 mois",
                    "depuis 2 mois", "depuis quelques mois"
                ],
                "confidence": 0.85
            },
            False: {
                "canonical": [
                    "non", "aucun changement", "stable", "pareil", "comme d'habitude",
                    "pas de changement", "toujours pareil",
                    "habituelle", "habituel", "connue"
                ],
                "synonyms": [
                    "aucune modification", "inchangé", "inchangée",
                    "identique", "même chose", "pas vraiment", "pas spécialement"
                ],
                "confidence": 0.80
            }
        }

        # ====================================================================
        # CARACTÉRISTIQUES DE CÉPHALÉE (Profil clinique)
        # ====================================================================
        self.headache_characteristics_vocabulary = {
            "migraine_like": {
                "canonical": ["migraine", "migraineuse", "migraineux"],
                "location": [
                    "unilatérale", "unilatéral", "hémicrânienne", "hémicrânien",
                    "d'un côté", "d'un seul côté", "côté droit", "côté gauche",
                    "temporale", "temporal"
                ],
                "quality": [
                    "pulsatile", "battante", "battant", "lancinante", "lancinant",
                    "qui bat", "qui pulse", "en battements"
                ],
                "associated_symptoms": [
                    "photophobie", "phonophobie",
                    "photo+", "phono+",  # Notation médicale
                    "gêné par la lumière", "gêné par le bruit",
                    "gêne à la lumière", "gêne au bruit",
                    "intolérance à la lumière", "intolérance au bruit",
                    "nausées", "nausée", "vomissements", "vomissement",
                    "n/v", "nv"  # Notation médicale
                ],
                "aggravation": [
                    "aggravée par l'activité", "aggravée par l'effort physique",
                    "aggravation à l'effort", "pire à l'effort"
                ],
                "confidence": 0.85
            },
            "tension_like": {
                "canonical": ["céphalée de tension", "tension"],
                "location": [
                    "bilatérale", "bilatéral", "des deux côtés",
                    "en casque", "casque", "comme un casque"
                ],
                "quality": [
                    "en pression", "pression", "en étau", "étau",
                    "serrement", "comme un bandeau", "en bandeau",
                    "constrictive", "constrictif"
                ],
                "associated_symptoms": [
                    "sans nausées", "sans vomissements", "pas de n/v",
                    "ø n/v", "ø photo", "ø phono",  # Notation médicale absence
                    "pas de photophobie", "pas de phonophobie"
                ],
                "confidence": 0.80
            },
            "cluster_like": {
                "canonical": ["algie vasculaire de la face", "AVF", "cluster"],
                "location": [
                    "périorbitaire", "orbitaire", "autour de l'œil",
                    "autour de l'oeil", "derrière l'œil", "derrière l'oeil"
                ],
                "quality": [
                    "en salves", "par salves", "en crises",
                    "très intense", "atroce", "insupportable"
                ],
                "associated_symptoms": [
                    "larmoiement", "œil qui pleure", "oeil qui pleure",
                    "injection conjonctivale", "œil rouge", "oeil rouge",
                    "rhinorrhée", "nez qui coule",
                    "ptosis", "myosis"
                ],
                "temporal_pattern": [
                    "même heure", "à heure fixe", "horaire fixe",
                    "plusieurs fois par jour", "quotidien"
                ],
                "confidence": 0.85
            }
        }

    def normalize_text(self, text: str) -> str:
        """Normalise le texte pour améliorer la détection.

        Transformations appliquées:
        - Conversion en minuscules
        - Suppression accents (é → e)
        - Normalisation espaces multiples
        - Préservation de la ponctuation médicale (+, -, °)

        Args:
            text: Texte brut

        Returns:
            Texte normalisé
        """
        # Minuscules
        text = text.lower()

        # Supprimer les accents (é → e, è → e, ê → e, ë → e)
        text = ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

        # Normaliser espaces multiples
        text = re.sub(r'\s+', ' ', text)

        # Nettoyer espaces autour de la ponctuation médicale
        text = re.sub(r'\s*([+\-°])\s*', r'\1', text)

        return text.strip()

    def has_exception_marker(self, text: str, negation_term: str) -> bool:
        """Détecte si une négation est invalidée par un marqueur d'exception.

        Exemples:
            - "sans déficit MAIS hémiparésie" → True (exception détectée)
            - "sans fièvre CEPENDANT fébrile" → True (exception détectée)
            - "sans déficit" → False (pas d'exception)

        Args:
            text: Texte médical normalisé
            negation_term: Terme de négation trouvé

        Returns:
            True si un marqueur d'exception suit la négation
        """
        text_norm = self.normalize_text(text)
        negation_norm = self.normalize_text(negation_term)

        # Marqueurs d'exception
        exception_markers = ["mais", "cependant", "toutefois", "sauf", "excepte"]

        # Trouver la position de la négation
        negation_pos = text_norm.find(negation_norm)
        if negation_pos == -1:
            return False

        # Extraire le texte après la négation
        text_after_negation = text_norm[negation_pos + len(negation_norm):]

        # Chercher un marqueur d'exception dans les 100 premiers caractères suivants
        # (limite raisonnable pour considérer que l'exception suit la négation)
        search_window = text_after_negation[:100]

        for marker in exception_markers:
            if marker in search_window:
                return True

        return False

    def extract_temporal_priority(self, text: str) -> Dict[str, int]:
        """Extrait les marqueurs temporels et leur priorité.

        Marqueurs récents (priorité haute) doivent primer sur marqueurs anciens.

        Exemples:
            - "hier" → priorité 1
            - "ce matin" → priorité 10
            - "actuellement" → priorité 15

        Args:
            text: Texte médical normalisé

        Returns:
            Dict avec marqueurs et leur position/priorité
        """
        text_norm = self.normalize_text(text)

        # Marqueurs temporels avec leur priorité (plus le score est élevé, plus récent)
        temporal_markers = {
            # Passé ancien (faible priorité)
            "hier": 1,
            "avant-hier": 1,
            "il y a plusieurs jours": 1,
            "il y a quelques jours": 1,
            "la semaine derniere": 1,
            "le mois dernier": 1,

            # Passé récent (priorité moyenne)
            "ce matin": 10,
            "cet apres-midi": 10,
            "aujourd'hui": 10,
            "depuis ce matin": 10,

            # Présent/actuel (priorité haute)
            "actuellement": 15,
            "en ce moment": 15,
            "maintenant": 15,
            "a present": 15,
            "a l'heure actuelle": 15
        }

        found_markers = {}
        for marker, priority in temporal_markers.items():
            marker_norm = self.normalize_text(marker)
            if marker_norm in text_norm:
                # Enregistrer position et priorité
                position = text_norm.find(marker_norm)
                found_markers[marker] = {
                    "priority": priority,
                    "position": position
                }

        return found_markers

    def _get_temporal_priority_at_position(
        self,
        text_norm: str,
        position: int,
        temporal_markers: Dict[str, Dict]
    ) -> int:
        """Obtient la priorité temporelle d'une détection à une position donnée.

        Args:
            text_norm: Texte normalisé
            position: Position de la détection dans le texte
            temporal_markers: Marqueurs temporels trouvés

        Returns:
            Priorité temporelle (0 par défaut, plus élevé = plus récent)
        """
        if not temporal_markers:
            return 0

        # Trouver le marqueur temporel le plus proche AVANT cette position
        best_priority = 0
        best_distance = float('inf')

        for marker, info in temporal_markers.items():
            marker_pos = info["position"]
            # Le marqueur doit être avant ou proche de la détection
            if marker_pos <= position:
                distance = position - marker_pos
                if distance < best_distance:
                    best_distance = distance
                    best_priority = info["priority"]

        return best_priority

    def detect_onset(self, text: str) -> DetectionResult:
        """Détecte le type de début de la céphalée.

        Args:
            text: Texte médical à analyser

        Returns:
            DetectionResult avec onset détecté
        """
        text_norm = self.normalize_text(text)

        # Vérifier chaque type d'onset par ordre de priorité
        for onset_type, vocab in self.onset_vocabulary.items():
            # 1. Termes canoniques
            for term in vocab.get("canonical", []):
                if self.normalize_text(term) in text_norm:
                    return DetectionResult(
                        detected=True,
                        value=onset_type,
                        confidence=vocab["confidence"],
                        matched_term=term,
                        canonical_form=vocab["canonical"][0],
                        source="canonical"
                    )

            # 2. Acronymes
            for acronym in vocab.get("acronyms", []):
                pattern = r'\b' + re.escape(self.normalize_text(acronym)) + r'\b'
                if re.search(pattern, text_norm):
                    return DetectionResult(
                        detected=True,
                        value=onset_type,
                        confidence=vocab["confidence"] * 0.95,  # Légère réduction pour acronyme
                        matched_term=acronym,
                        canonical_form=vocab["canonical"][0],
                        source="acronym"
                    )

            # 3. Synonymes
            for synonym in vocab.get("synonyms", []):
                if self.normalize_text(synonym) in text_norm:
                    return DetectionResult(
                        detected=True,
                        value=onset_type,
                        confidence=vocab["confidence"] * 0.90,
                        matched_term=synonym,
                        canonical_form=vocab["canonical"][0],
                        source="synonym"
                    )

            # 4. Phrases
            for phrase in vocab.get("phrases", []):
                if self.normalize_text(phrase) in text_norm:
                    return DetectionResult(
                        detected=True,
                        value=onset_type,
                        confidence=vocab["confidence"],
                        matched_term=phrase,
                        canonical_form=vocab["canonical"][0],
                        source="phrase"
                    )

            # 5. Termes médicaux
            for med_term in vocab.get("medical_terms", []):
                if self.normalize_text(med_term) in text_norm:
                    return DetectionResult(
                        detected=True,
                        value=onset_type,
                        confidence=vocab["confidence"] * 0.98,
                        matched_term=med_term,
                        canonical_form=vocab["canonical"][0],
                        source="medical_term"
                    )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_fever(self, text: str) -> DetectionResult:
        """Détecte la présence ou absence de fièvre.

        Gère les patterns numériques (T°=39) et valide le seuil ≥38°C.
        Gère également l'évolution temporelle (état actuel > état passé).

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec fever True/False/None
        """
        text_norm = self.normalize_text(text)

        # Détecter marqueurs temporels pour gérer l'évolution
        temporal_markers = self.extract_temporal_priority(text)
        has_temporal_evolution = len(temporal_markers) > 0

        # Vérifier si présence de marqueur d'exception (mais)
        has_exception_marker_in_text = any(
            marker in text_norm for marker in ["mais", "cependant", "toutefois"]
        )

        # Si évolution temporelle détectée, chercher toutes les occurrences
        # et prioriser la plus récente
        if has_temporal_evolution or has_exception_marker_in_text:
            # Chercher négations avec leur position
            vocab_false = self.fever_vocabulary[False]
            negation_detections = []
            for term in vocab_false.get("canonical", []) + vocab_false.get("acronyms", []) + vocab_false.get("synonyms", []):
                if self.normalize_text(term) in text_norm:
                    pos = text_norm.find(self.normalize_text(term))
                    negation_detections.append({
                        "result": DetectionResult(
                            detected=True,
                            value=False,
                            confidence=vocab_false["confidence"],
                            matched_term=term,
                            canonical_form="sans fièvre",
                            source="negation"
                        ),
                        "position": pos,
                        "temporal_priority": self._get_temporal_priority_at_position(
                            text_norm, pos, temporal_markers
                        )
                    })

            # Chercher occurrences positives
            vocab_true = self.fever_vocabulary[True]
            positive_detections = []

            # Termes textuels
            for term in vocab_true.get("canonical", []) + vocab_true.get("acronyms", []) + vocab_true.get("synonyms", []):
                term_norm = self.normalize_text(term)
                if term_norm in text_norm:
                    # Vérifier qu'il n'est pas précédé par une négation
                    negation_pattern = r'(?:pas de |sans |aucun[e]? |absence de |non )' + re.escape(term_norm)
                    if re.search(negation_pattern, text_norm):
                        # C'est une négation, ne pas ajouter comme positif
                        continue
                    pattern = r'(?<![a-z])' + re.escape(term_norm)
                    if re.search(pattern, text_norm):
                        pos = text_norm.find(term_norm)
                        positive_detections.append({
                            "result": DetectionResult(
                                detected=True,
                                value=True,
                                confidence=vocab_true["confidence"],
                                matched_term=term,
                                canonical_form="fièvre",
                                source="canonical"
                            ),
                            "position": pos,
                            "temporal_priority": self._get_temporal_priority_at_position(
                                text_norm, pos, temporal_markers
                            )
                        })

            # Patterns numériques
            for pattern in vocab_true.get("numeric_patterns", []):
                matches = re.finditer(pattern, text_norm)
                for match in matches:
                    try:
                        if match.lastindex >= 1:
                            temp_str = match.group(1)
                            if '°' in match.group(0) and match.lastindex >= 2:
                                temp = float(f"{match.group(1)}.{match.group(2)}")
                            else:
                                temp = float(temp_str)

                            if temp >= vocab_true["threshold"]:
                                positive_detections.append({
                                    "result": DetectionResult(
                                        detected=True,
                                        value=True,
                                        confidence=0.95,
                                        matched_term=match.group(0),
                                        canonical_form="fièvre",
                                        source="numeric"
                                    ),
                                    "position": match.start(),
                                    "temporal_priority": self._get_temporal_priority_at_position(
                                        text_norm, match.start(), temporal_markers
                                    )
                                })
                            elif 35.0 <= temp < 38.0:
                                negation_detections.append({
                                    "result": DetectionResult(
                                        detected=True,
                                        value=False,
                                        confidence=0.90,
                                        matched_term=match.group(0),
                                        canonical_form="sans fièvre",
                                        source="numeric_normal"
                                    ),
                                    "position": match.start(),
                                    "temporal_priority": self._get_temporal_priority_at_position(
                                        text_norm, match.start(), temporal_markers
                                    )
                                })
                    except (ValueError, IndexError):
                        continue

            # Combiner et prioriser: priorité temporelle > position dans le texte
            all_detections = negation_detections + positive_detections
            if all_detections:
                # Trier par priorité temporelle décroissante, puis par position décroissante
                all_detections.sort(
                    key=lambda x: (x["temporal_priority"], x["position"]),
                    reverse=True
                )
                return all_detections[0]["result"]

        # Sinon, comportement standard (pas d'évolution temporelle)
        vocab_false = self.fever_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("acronyms", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans fièvre",
                    source="negation"
                )

        # Puis chercher patterns numériques
        vocab_true = self.fever_vocabulary[True]

        # Termes canoniques, acronyms et synonymes D'ABORD
        for term in vocab_true.get("canonical", []) + vocab_true.get("acronyms", []) + vocab_true.get("synonyms", []):
            # Éviter faux positifs: "féb" isolé mais pas dans "afébrile"
            term_norm = self.normalize_text(term)
            if term_norm in text_norm:
                # Vérifier qu'il n'est pas précédé par une négation
                # Patterns de negation: "pas de X", "sans X", "aucun X", "absence de X"
                negation_pattern = r'(?:pas de |sans |aucun[e]? |absence de |non )' + re.escape(term_norm)
                if re.search(negation_pattern, text_norm):
                    # C'est une négation, ne pas matcher comme positif
                    continue
                # Vérifier qu'il n'est pas précédé de "a" (pour afébrile)
                pattern = r'(?<![a-z])' + re.escape(term_norm)
                if re.search(pattern, text_norm):
                    return DetectionResult(
                        detected=True,
                        value=True,
                        confidence=vocab_true["confidence"],
                        matched_term=term,
                        canonical_form="fièvre",
                        source="canonical"
                    )

        # Patterns numériques EN DERNIER (après termes textuels)
        for pattern in vocab_true.get("numeric_patterns", []):
            matches = re.finditer(pattern, text_norm)
            for match in matches:
                try:
                    # Extraire température
                    if match.lastindex >= 1:
                        temp_str = match.group(1)
                        if '°' in match.group(0) and match.lastindex >= 2:
                            # Format 38°5 → 38.5
                            temp = float(f"{match.group(1)}.{match.group(2)}")
                        else:
                            temp = float(temp_str)

                        # Validation médicale: fièvre ≥ 38.0°C
                        if temp >= vocab_true["threshold"]:
                            return DetectionResult(
                                detected=True,
                                value=True,
                                confidence=0.95,  # Haute confiance pour valeur numérique
                                matched_term=match.group(0),
                                canonical_form="fièvre",
                                source="numeric"
                            )
                        elif 35.0 <= temp < 38.0:
                            # Température normale explicite
                            return DetectionResult(
                                detected=True,
                                value=False,
                                confidence=0.90,
                                matched_term=match.group(0),
                                canonical_form="sans fièvre",
                                source="numeric_normal"
                            )
                except (ValueError, IndexError):
                    continue

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_meningeal_signs(self, text: str) -> DetectionResult:
        """Détecte les signes méningés.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec meningeal_signs True/False/None
        """
        text_norm = self.normalize_text(text)

        # D'abord chercher les négations
        vocab_false = self.meningeal_signs_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("acronyms", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans syndrome méningé",
                    source="negation"
                )

        # Puis chercher affirmations
        vocab_true = self.meningeal_signs_vocabulary[True]

        # Acronymes (haute priorité) - mais vérifier patterns simples aussi
        for acronym in vocab_true.get("acronyms", []):
            # D'abord chercher patterns simples (sans word boundary pour les + -)
            if self.normalize_text(acronym) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=acronym,
                    canonical_form="syndrome méningé",
                    source="acronym"
                )

        # Signes cliniques
        for sign in vocab_true.get("clinical_signs", []):
            sign_norm = self.normalize_text(sign)
            if sign_norm in text_norm:
                # Vérifier qu'il n'est pas précédé par une négation
                negation_pattern = r'(?:pas de |sans |aucun[e]? |absence de |non )' + re.escape(sign_norm)
                if re.search(negation_pattern, text_norm):
                    # C'est une négation, ne pas matcher comme positif
                    continue
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=sign,
                    canonical_form="syndrome méningé",
                    source="clinical_sign"
                )

        # Langage patient
        for phrase in vocab_true.get("patient_language", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.85,  # Légère réduction
                    matched_term=phrase,
                    canonical_form="syndrome méningé",
                    source="patient_language"
                )

        # Termes canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="syndrome méningé",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_htic(self, text: str) -> DetectionResult:
        """Détecte le pattern HTIC en excluant les faux positifs (aura).

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec htic_pattern True/False/None
        """
        text_norm = self.normalize_text(text)

        # Vérifier exclusions d'abord (scotome/aura ≠ HTIC)
        vocab_true = self.htic_vocabulary[True]
        for exclusion in vocab_true.get("exclusions", []):
            if self.normalize_text(exclusion) in text_norm:
                # Présence d'un anti-pattern, ne pas détecter HTIC
                # (scotome = aura migraineuse, pas HTIC)
                return DetectionResult(detected=False, value=None, confidence=0.0)

        # Chercher négations
        vocab_false = self.htic_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="pas de signes htic",
                    source="negation"
                )

        # Acronymes
        for acronym in vocab_true.get("acronyms", []):
            if self.normalize_text(acronym) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=acronym,
                    canonical_form="HTIC",
                    source="acronym"
                )

        # Patterns cliniques - SEULEMENT signes FORTS (vomissements en jet, aggravation toux/effort)
        # Les signes faibles (céphalée matutinale, pire le matin) ont été retirés du vocabulaire
        for pattern in vocab_true.get("clinical_patterns", []):
            if self.normalize_text(pattern) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=pattern,
                    canonical_form="HTIC",
                    source="clinical_pattern"
                )

        # Signes ophtalmologiques
        for sign in vocab_true.get("ophtalmo_signs", []):
            if self.normalize_text(sign) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=sign,
                    canonical_form="HTIC",
                    source="ophtalmo_sign"
                )

        # Phrases temporelles - SUPPRIMÉES DE LA DÉTECTION
        # "pire le matin" seul n'est PAS HTIC (peut être migraine, céphalée tension)
        # HTIC nécessite: vomissements en jet OU œdème papillaire OU mention explicite "HTIC"
        # Les phrases temporelles seules NE DOIVENT PAS détecter HTIC
        # (Cette section est intentionnellement vide pour éviter faux positifs)

        # Termes canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="HTIC",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_trauma(self, text: str) -> DetectionResult:
        """Détecte le traumatisme crânien."""
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.trauma_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans traumatisme",
                    source="negation"
                )

        vocab_true = self.trauma_vocabulary[True]

        # Acronymes (haute confiance)
        for acronym in vocab_true.get("acronyms", []):
            pattern = r'\b' + re.escape(self.normalize_text(acronym)) + r'\b'
            if re.search(pattern, text_norm):
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=acronym,
                    canonical_form="traumatisme crânien",
                    source="acronym"
                )

        # Termes complets
        for term in vocab_true.get("full_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="traumatisme crânien",
                    source="full_term"
                )

        # Mécanismes
        for mechanism in vocab_true.get("mechanisms", []):
            if self.normalize_text(mechanism) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=mechanism,
                    canonical_form="traumatisme crânien",
                    source="mechanism"
                )

        # Contexte temporel
        for context in vocab_true.get("temporal_context", []):
            if self.normalize_text(context) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=context,
                    canonical_form="traumatisme crânien",
                    source="temporal_context"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="traumatisme crânien",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_neuro_deficit(self, text: str) -> DetectionResult:
        """Détecte le déficit neurologique."""
        text_norm = self.normalize_text(text)

        # Négations (mais vérifier qu'il n'y a pas d'exception type "sans... mais...")
        vocab_false = self.neuro_deficit_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                # Vérifier si négation invalidée par marqueur d'exception
                if self.has_exception_marker(text, term):
                    # Ne pas retourner la négation, continuer à chercher termes positifs
                    continue

                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans déficit",
                    source="negation"
                )

        vocab_true = self.neuro_deficit_vocabulary[True]

        # Acronymes
        for acronym in vocab_true.get("acronyms", []):
            pattern = r'\b' + re.escape(self.normalize_text(acronym)) + r'\b'
            if re.search(pattern, text_norm):
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=acronym,
                    canonical_form="déficit neurologique",
                    source="acronym"
                )

        # Déficits moteurs
        for deficit in vocab_true.get("motor_deficits", []):
            if self.normalize_text(deficit) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=deficit,
                    canonical_form="déficit neurologique",
                    source="motor"
                )

        # Troubles du langage
        for deficit in vocab_true.get("language_deficits", []):
            if self.normalize_text(deficit) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=deficit,
                    canonical_form="déficit neurologique",
                    source="language"
                )

        # Troubles visuels
        for deficit in vocab_true.get("visual_deficits", []):
            if self.normalize_text(deficit) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=deficit,
                    canonical_form="déficit neurologique",
                    source="visual"
                )

        # Troubles de la conscience
        for symptom in vocab_true.get("consciousness", []):
            if self.normalize_text(symptom) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=symptom,
                    canonical_form="déficit neurologique",
                    source="consciousness"
                )

        # Langage patient
        for phrase in vocab_true.get("patient_language", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.85,
                    matched_term=phrase,
                    canonical_form="déficit neurologique",
                    source="patient_language"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="déficit neurologique",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_seizure(self, text: str) -> DetectionResult:
        """Détecte les crises d'épilepsie/convulsions."""
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.seizure_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans crise",
                    source="negation"
                )

        vocab_true = self.seizure_vocabulary[True]

        # Acronymes
        for acronym in vocab_true.get("acronyms", []):
            pattern = r'\b' + re.escape(self.normalize_text(acronym)) + r'\b'
            if re.search(pattern, text_norm):
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=acronym,
                    canonical_form="crise d'épilepsie",
                    source="acronym"
                )

        # Termes médicaux
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="crise d'épilepsie",
                    source="medical_term"
                )

        # Contexte temporel
        for context in vocab_true.get("temporal_context", []):
            if self.normalize_text(context) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=context,
                    canonical_form="crise d'épilepsie",
                    source="temporal"
                )

        # Description clinique
        for desc in vocab_true.get("clinical_description", []):
            if self.normalize_text(desc) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=desc,
                    canonical_form="crise d'épilepsie",
                    source="clinical_desc"
                )

        # Termes génériques (dernière priorité)
        for term in vocab_true.get("generic_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.85,
                    matched_term=term,
                    canonical_form="crise d'épilepsie",
                    source="generic"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_pregnancy_postpartum(self, text: str) -> DetectionResult:
        """Détecte le contexte grossesse/post-partum."""
        text_norm = self.normalize_text(text)
        vocab_true = self.pregnancy_vocabulary[True]

        # Acronymes obstétricaux (haute confiance)
        for acronym in vocab_true.get("acronyms", []):
            # Pattern spécial pour G#P# (g1p0, g2p1, etc.)
            if acronym.startswith("g") and "p" in acronym:
                pattern = r'\bg\d+p\d+\b'
                if re.search(pattern, text_norm):
                    return DetectionResult(
                        detected=True,
                        value=True,
                        confidence=0.98,
                        matched_term=acronym,
                        canonical_form="grossesse",
                        source="obstetric_acronym"
                    )
            # SA (Semaines d'Aménorrhée) - contextualisé
            elif acronym == "sa":
                # Chercher pattern "XX sa" ou "XX SA"
                pattern = r'\b\d{1,2}\s*sa\b'
                if re.search(pattern, text_norm):
                    return DetectionResult(
                        detected=True,
                        value=True,
                        confidence=0.95,
                        matched_term="semaines d'aménorrhée",
                        canonical_form="grossesse",
                        source="gestational_age"
                    )
            # Trimestres
            elif acronym in ["t1", "t2", "t3"]:
                pattern = r'\b' + re.escape(acronym) + r'\b'
                if re.search(pattern, text_norm):
                    return DetectionResult(
                        detected=True,
                        value=True,
                        confidence=0.90,
                        matched_term=acronym,
                        canonical_form="grossesse",
                        source="trimester"
                    )

        # Post-partum
        for term in vocab_true.get("postpartum", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="post-partum",
                    source="postpartum"
                )

        # Termes médicaux
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="grossesse",
                    source="medical_term"
                )

        # Termes temporels
        for term in vocab_true.get("temporal_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=term,
                    canonical_form="grossesse",
                    source="temporal"
                )

        # Contexte obstétrique
        for term in vocab_true.get("obstetric_context", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="grossesse",
                    source="obstetric"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="grossesse",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_immunosuppression(self, text: str) -> DetectionResult:
        """Détecte l'immunodépression."""
        text_norm = self.normalize_text(text)
        vocab_true = self.immunosuppression_vocabulary[True]

        # Conditions médicales
        for condition in vocab_true.get("medical_conditions", []):
            if self.normalize_text(condition) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=condition,
                    canonical_form="immunodépression",
                    source="medical_condition"
                )

        # Traitements immunosuppresseurs
        for treatment in vocab_true.get("treatments", []):
            if self.normalize_text(treatment) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=treatment,
                    canonical_form="immunodépression",
                    source="treatment"
                )

        # Contextes (greffe, etc.)
        for context in vocab_true.get("contexts", []):
            if self.normalize_text(context) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=context,
                    canonical_form="immunodépression",
                    source="context"
                )

        # Oncologie
        for term in vocab_true.get("oncology", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=term,
                    canonical_form="immunodépression",
                    source="oncology"
                )

        # Marqueurs biologiques
        for marker in vocab_true.get("bio_markers", []):
            if self.normalize_text(marker) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=marker,
                    canonical_form="immunodépression",
                    source="bio_marker"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="immunodépression",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_pattern_change(self, text: str) -> DetectionResult:
        """Détecte un changement récent dans le pattern d'une céphalée chronique.

        Utile pour différencier:
        - Céphalée chronique STABLE (pas d'urgence)
        - Céphalée chronique AGGRAVÉE (nécessite évaluation urgente)

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec recent_pattern_change True/False/None
        """
        text_norm = self.normalize_text(text)

        # Chercher négations/stabilité d'abord
        vocab_false = self.pattern_change_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="stable",
                    source="stability"
                )

        vocab_true = self.pattern_change_vocabulary[True]

        # Termes canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="changement récent",
                    source="canonical"
                )

        # Marqueurs temporels (pire depuis, etc.)
        for marker in vocab_true.get("temporal_markers", []):
            if self.normalize_text(marker) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=marker,
                    canonical_form="changement récent",
                    source="temporal_marker"
                )

        # Changement d'intensité
        for phrase in vocab_true.get("intensity_change", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=phrase,
                    canonical_form="changement récent",
                    source="intensity_change"
                )

        # Nouveaux symptômes
        for phrase in vocab_true.get("new_symptoms", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=phrase,
                    canonical_form="changement récent",
                    source="new_symptoms"
                )

        # Fenêtres temporelles ("depuis 1 semaine")
        for window in vocab_true.get("temporal_windows", []):
            if self.normalize_text(window) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=window,
                    canonical_form="changement récent",
                    source="temporal_window"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_headache_characteristics(self, text: str) -> DetectionResult:
        """Détecte le profil clinique de la céphalée (migraine, tension, cluster).

        Compte les matches pour chaque profil et retourne celui avec le plus de points.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec profil détecté (migraine_like, tension_like, cluster_like)
        """
        text_norm = self.normalize_text(text)

        # Compter les matches pour chaque profil
        profile_scores = {}

        for profile_type, vocab in self.headache_characteristics_vocabulary.items():
            score = 0
            matched_terms = []

            # Vérifier chaque catégorie de termes
            for category in ["canonical", "location", "quality", "associated_symptoms", "aggravation", "temporal_pattern"]:
                terms = vocab.get(category, [])
                for term in terms:
                    if self.normalize_text(term) in text_norm:
                        score += 1
                        matched_terms.append(term)

            if score > 0:
                profile_scores[profile_type] = {
                    "score": score,
                    "matched_terms": matched_terms,
                    "confidence": vocab["confidence"]
                }

        # Retourner le profil avec le score le plus élevé
        if profile_scores:
            best_profile = max(profile_scores.items(), key=lambda x: x[1]["score"])
            profile_name = best_profile[0]
            profile_data = best_profile[1]

            return DetectionResult(
                detected=True,
                value=profile_name,
                confidence=profile_data["confidence"],
                matched_term=", ".join(profile_data["matched_terms"][:3]),  # Max 3 termes
                canonical_form=profile_name.replace("_", " "),
                source="headache_characteristics"
            )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_cancer_history(self, text: str) -> DetectionResult:
        """Détecte le contexte oncologique (cancer actuel ou antécédent).

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec cancer_history True/False/None
        """
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.cancer_history_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans cancer",
                    source="negation"
                )

        vocab_true = self.cancer_history_vocabulary[True]

        # Métastases (haute priorité - contexte critique)
        for term in vocab_true.get("metastasis", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="cancer",
                    source="metastasis"
                )

        # Cancers spécifiques (haute confiance)
        for cancer in vocab_true.get("specific_cancers", []):
            if self.normalize_text(cancer) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=cancer,
                    canonical_form="cancer",
                    source="specific_cancer"
                )

        # Traitements oncologiques (chimio, radio, etc.)
        for treatment in vocab_true.get("treatments", []):
            if self.normalize_text(treatment) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=treatment,
                    canonical_form="cancer",
                    source="oncology_treatment"
                )

        # Contextes oncologiques
        for context in vocab_true.get("contexts", []):
            if self.normalize_text(context) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=context,
                    canonical_form="cancer",
                    source="oncology_context"
                )

        # Termes médicaux
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=term,
                    canonical_form="cancer",
                    source="medical_term"
                )

        # Contexte temporel combiné avec d'autres termes
        for context in vocab_true.get("temporal_context", []):
            if self.normalize_text(context) in text_norm:
                # Rechercher si accompagné de "cancer" ou termes liés
                if any(self.normalize_text(t) in text_norm
                       for t in ["cancer", "tumeur", "chimio", "oncologique"]):
                    return DetectionResult(
                        detected=True,
                        value=True,
                        confidence=vocab_true["confidence"],
                        matched_term=context,
                        canonical_form="cancer",
                        source="temporal_context"
                    )

        # Termes canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="cancer",
                    source="canonical"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_vertigo(self, text: str) -> DetectionResult:
        """Détecte les vertiges.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec vertigo True/False/None
        """
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.vertigo_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans vertige",
                    source="negation"
                )

        vocab_true = self.vertigo_vocabulary[True]

        # Termes médicaux (haute confiance)
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="vertige",
                    source="medical_term"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="vertige",
                    source="canonical"
                )

        # Langage patient
        for phrase in vocab_true.get("patient_language", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=phrase,
                    canonical_form="vertige",
                    source="patient_language"
                )

        # Termes génériques (plus faible confiance)
        for term in vocab_true.get("generic_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.75,
                    matched_term=term,
                    canonical_form="vertige",
                    source="generic"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_tinnitus(self, text: str) -> DetectionResult:
        """Détecte les acouphènes.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec tinnitus True/False/None
        """
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.tinnitus_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans acouphène",
                    source="negation"
                )

        vocab_true = self.tinnitus_vocabulary[True]

        # Termes médicaux
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="acouphène",
                    source="medical_term"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="acouphène",
                    source="canonical"
                )

        # Langage patient
        for phrase in vocab_true.get("patient_language", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.90,
                    matched_term=phrase,
                    canonical_form="acouphène",
                    source="patient_language"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_visual_disturbance_type(self, text: str) -> DetectionResult:
        """Détecte le type de troubles visuels.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec visual_disturbance_type (stroboscopic/blur/blindness/none)
        """
        text_norm = self.normalize_text(text)

        # Compter les matches pour chaque type
        type_scores = {}

        for disturbance_type, vocab in self.visual_disturbance_vocabulary.items():
            score = 0
            matched_terms = []

            # Vérifier chaque catégorie de termes
            for category in ["canonical", "medical_terms", "patient_language", "synonyms"]:
                terms = vocab.get(category, [])
                for term in terms:
                    if self.normalize_text(term) in text_norm:
                        score += 1
                        matched_terms.append(term)

            if score > 0:
                type_scores[disturbance_type] = {
                    "score": score,
                    "matched_terms": matched_terms,
                    "confidence": vocab["confidence"]
                }

        # Retourner le type avec le score le plus élevé
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1]["score"])
            type_name = best_type[0]
            type_data = best_type[1]

            return DetectionResult(
                detected=True,
                value=type_name,
                confidence=type_data["confidence"],
                matched_term=type_data["matched_terms"][0] if type_data["matched_terms"] else "",
                canonical_form=type_name,
                source="visual_disturbance"
            )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_joint_pain(self, text: str) -> DetectionResult:
        """Détecte les douleurs articulaires.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec joint_pain True/False/None
        """
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.joint_pain_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="sans douleurs articulaires",
                    source="negation"
                )

        vocab_true = self.joint_pain_vocabulary[True]

        # Termes médicaux
        for term in vocab_true.get("medical_terms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="douleurs articulaires",
                    source="medical_term"
                )

        # Canoniques
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="douleurs articulaires",
                    source="canonical"
                )

        # Langage patient
        for phrase in vocab_true.get("patient_language", []):
            if self.normalize_text(phrase) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.85,
                    matched_term=phrase,
                    canonical_form="douleurs articulaires",
                    source="patient_language"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_horton_criteria(self, text: str) -> DetectionResult:
        """Détecte les critères de maladie de Horton / artérite temporale.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec horton_criteria True/False/None
        """
        text_norm = self.normalize_text(text)

        # Négations
        vocab_false = self.horton_criteria_vocabulary[False]
        for term in vocab_false.get("canonical", []) + vocab_false.get("synonyms", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=False,
                    confidence=vocab_false["confidence"],
                    matched_term=term,
                    canonical_form="pas de Horton",
                    source="negation"
                )

        vocab_true = self.horton_criteria_vocabulary[True]

        # Canoniques (diagnostic posé)
        for term in vocab_true.get("canonical", []):
            if self.normalize_text(term) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=term,
                    canonical_form="Horton",
                    source="canonical"
                )

        # Signes cliniques (claudication mâchoire - très évocateur)
        for sign in vocab_true.get("clinical_signs", []):
            if self.normalize_text(sign) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"],
                    matched_term=sign,
                    canonical_form="Horton",
                    source="clinical_sign"
                )

        # Signes vasculaires
        for sign in vocab_true.get("vascular_signs", []):
            if self.normalize_text(sign) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.95,
                    matched_term=sign,
                    canonical_form="Horton",
                    source="vascular_sign"
                )

        # Symptômes systémiques (plus faible confiance seuls)
        for symptom in vocab_true.get("systemic_symptoms", []):
            if self.normalize_text(symptom) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.75,
                    matched_term=symptom,
                    canonical_form="Horton",
                    source="systemic"
                )

        # Marqueurs biologiques (plus faible confiance seuls)
        for marker in vocab_true.get("lab_markers", []):
            if self.normalize_text(marker) in text_norm:
                return DetectionResult(
                    detected=True,
                    value=True,
                    confidence=vocab_true["confidence"] * 0.70,
                    matched_term=marker,
                    canonical_form="Horton",
                    source="lab_marker"
                )

        return DetectionResult(detected=False, value=None, confidence=0.0)

    def detect_headache_location(self, text: str) -> DetectionResult:
        """Détecte la localisation de la céphalée.

        Args:
            text: Texte médical

        Returns:
            DetectionResult avec localisation (frontal/temporal/occipital/unilateral/diffuse)
        """
        text_norm = self.normalize_text(text)

        # Compter les matches pour chaque localisation
        location_scores = {}

        for location_type, vocab in self.headache_location_vocabulary.items():
            score = 0
            matched_terms = []

            # Vérifier chaque catégorie de termes
            for category in ["canonical", "patient_language"]:
                terms = vocab.get(category, [])
                for term in terms:
                    if self.normalize_text(term) in text_norm:
                        score += 1
                        matched_terms.append(term)

            if score > 0:
                location_scores[location_type] = {
                    "score": score,
                    "matched_terms": matched_terms,
                    "confidence": vocab["confidence"]
                }

        # Retourner la localisation avec le score le plus élevé
        if location_scores:
            best_location = max(location_scores.items(), key=lambda x: x[1]["score"])
            location_name = best_location[0]
            location_data = best_location[1]

            return DetectionResult(
                detected=True,
                value=location_name,
                confidence=location_data["confidence"],
                matched_term=location_data["matched_terms"][0] if location_data["matched_terms"] else "",
                canonical_form=location_name,
                source="headache_location"
            )

        return DetectionResult(detected=False, value=None, confidence=0.0)
