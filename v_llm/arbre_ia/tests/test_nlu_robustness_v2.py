#!/usr/bin/env python3
"""
Test de robustesse du système NLU avec différentes formulations - Version 2.

Ce script teste la capacité du système à comprendre:
- Différents synonymes médicaux
- Acronymes courants (minuscules et majuscules)
- Formulations variées
- Langage familier vs technique

Pour chaque test, on vérifie:
1. Les champs extraits par le NLU
2. La recommandation finale
3. La cohérence médicale
"""

from headache_assistants.models import HeadacheCase
from headache_assistants.nlu import parse_free_text_to_case
from headache_assistants.rules_engine import decide_imaging
from typing import Dict, Any, List
import json


class NLUTester:
    """Testeur de robustesse du NLU."""
    
    def __init__(self):
        self.tests = [
            # === CATÉGORIE 1: HSA (Hémorragie sous-arachnoïdienne) - Variations de synonymes ===
            {
                "name": "HSA - Coup de tonnerre",
                "text": "Femme 45 ans, céphalée en coup de tonnerre ce matin, intensité 10/10",
                "expected_fields": {
                    "age": 45,
                    "sex": "F",
                    "onset": "thunderclap",
                    "profile": "acute",
                    "intensity": 10
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HSA - Brutale explosive",
                "text": "Patiente de 52 ans, douleur brutale explosive, pire mal de tête de sa vie",
                "expected_fields": {
                    "age": 52,
                    "sex": "F",
                    "onset": "thunderclap",
                    "intensity": 10
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HSA - D'un coup",
                "text": "Elle a 48 ans, mal de tête d'un coup, jamais eu aussi mal",
                "expected_fields": {
                    "age": 48,
                    "sex": "F",
                    "onset": "thunderclap",
                    "intensity": 10
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HSA - Tout d'un coup",
                "text": "Homme 55 ans, céphalée atroce tout d'un coup, insupportable",
                "expected_fields": {
                    "age": 55,
                    "sex": "M",
                    "onset": "thunderclap",
                    "intensity": 10
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HSA - Soudaine subite",
                "text": "Patiente 60 ans, douleur soudaine et subite, intensité maximale",
                "expected_fields": {
                    "age": 60,
                    "sex": "F",
                    "onset": "thunderclap",
                    "intensity": 10
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HSA - Commencé brutalement",
                "text": "Homme de 58 ans, céphalée qui a commencé brutalement hier",
                "expected_fields": {
                    "age": 58,
                    "sex": "M",
                    "onset": "thunderclap",
                    "profile": "acute"
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            
            # === CATÉGORIE 2: MÉNINGITE - Variations terminologiques ===
            {
                "name": "Méningite - Fièvre + raideur nuque",
                "text": "Homme 28 ans, céphalée avec fièvre 39°C et raideur de nuque",
                "expected_fields": {
                    "age": 28,
                    "sex": "M",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Méningite - Température + nuque raide",
                "text": "Patient 35 ans, mal de tête, température élevée 38.5, nuque raide",
                "expected_fields": {
                    "age": 35,
                    "sex": "M",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Méningite - Fébrile + cou bloqué",
                "text": "Jeune femme 22 ans, céphalée fébrile, cou bloqué",
                "expected_fields": {
                    "age": 22,
                    "sex": "F",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Méningite - Hyperthermie + raideur",
                "text": "Homme de 30 ans, céphalée avec hyperthermie et raideur méningée",
                "expected_fields": {
                    "age": 30,
                    "sex": "M",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Méningite - Kernig positif",
                "text": "Patient 26 ans, céphalée fébrile, signe de Kernig positif",
                "expected_fields": {
                    "age": 26,
                    "sex": "M",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Méningite - Brudzinski positif",
                "text": "Femme 24 ans, mal de tête avec fièvre, Brudzinski positif",
                "expected_fields": {
                    "age": 24,
                    "sex": "F",
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            
            # === CATÉGORIE 3: PROFILS TEMPORELS - Synonymes de durée ===
            {
                "name": "Aigu - Ce matin",
                "text": "Patient 40 ans, céphalée depuis ce matin",
                "expected_fields": {
                    "age": 40,
                    "sex": "M",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Aigu - Aujourd'hui",
                "text": "Femme 50 ans, mal de tête depuis aujourd'hui",
                "expected_fields": {
                    "age": 50,
                    "sex": "F",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Aigu - Cette nuit",
                "text": "Homme 38 ans, céphalée commencée cette nuit",
                "expected_fields": {
                    "age": 38,
                    "sex": "M",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Aigu - Depuis X heures",
                "text": "Patiente 42 ans, céphalée depuis 12 heures",
                "expected_fields": {
                    "age": 42,
                    "sex": "F",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Subaigu - Depuis X semaines",
                "text": "Homme 60 ans, céphalée progressive depuis 2 semaines",
                "expected_fields": {
                    "age": 60,
                    "sex": "M",
                    "onset": "progressive",
                    "profile": "subacute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Subaigu - Quelques semaines",
                "text": "Femme 55 ans, mal de tête depuis quelques semaines",
                "expected_fields": {
                    "age": 55,
                    "sex": "F",
                    "profile": "subacute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Chronique - Depuis X mois",
                "text": "Patiente 35 ans, céphalées quotidiennes depuis 3 mois",
                "expected_fields": {
                    "age": 35,
                    "sex": "F",
                    "profile": "chronic"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Chronique - Plusieurs années",
                "text": "Patient 45 ans, migraines depuis plusieurs années",
                "expected_fields": {
                    "age": 45,
                    "sex": "M",
                    "profile": "chronic"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Chronique - Longue date",
                "text": "Homme 52 ans, céphalées de longue date",
                "expected_fields": {
                    "age": 52,
                    "sex": "M",
                    "profile": "chronic"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            
            # === CATÉGORIE 4: GROSSESSE - Variations terminologiques ===
            {
                "name": "Grossesse - Enceinte",
                "text": "Femme enceinte 32 ans, céphalée sévère",
                "expected_fields": {
                    "age": 32,
                    "sex": "F",
                    "pregnancy_postpartum": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["IRM"]
            },
            {
                "name": "Grossesse - Gestation",
                "text": "Patiente en gestation 28 ans, mal de tête",
                "expected_fields": {
                    "age": 28,
                    "sex": "F",
                    "pregnancy_postpartum": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["IRM"]
            },
            {
                "name": "Grossesse - Gestante",
                "text": "Femme gestante 35 ans, céphalée brutale",
                "expected_fields": {
                    "age": 35,
                    "sex": "F",
                    "pregnancy_postpartum": True,
                    "onset": "thunderclap"
                },
                "expected_urgency": None,
                "expected_exam_contains": ["IRM"]
            },
            {
                "name": "Post-partum - Accouchement il y a",
                "text": "Jeune mère 28 ans, accouchement il y a 2 semaines, céphalée",
                "expected_fields": {
                    "age": 28,
                    "sex": "F",
                    "pregnancy_postpartum": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Post-partum - Suite accouchement",
                "text": "Femme 30 ans, suite à accouchement récent, mal de tête",
                "expected_fields": {
                    "age": 30,
                    "sex": "F",
                    "pregnancy_postpartum": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            
            # === CATÉGORIE 5: TRAUMATISME - Acronymes et synonymes ===
            {
                "name": "Trauma - TCE (minuscule)",
                "text": "Homme 50 ans, tce hier, céphalée ce matin",
                "expected_fields": {
                    "age": 50,
                    "sex": "M",
                    "trauma": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Trauma - TCC",
                "text": "Patient 45 ans, tcc il y a 24h, maintenant céphalée",
                "expected_fields": {
                    "age": 45,
                    "sex": "M",
                    "trauma": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Trauma - Chute",
                "text": "Patiente 70 ans, chute avec coup à la tête il y a 2 jours",
                "expected_fields": {
                    "age": 70,
                    "sex": "F",
                    "trauma": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Trauma - Traumatisme crânien",
                "text": "Homme 55 ans, traumatisme crânien récent, céphalée",
                "expected_fields": {
                    "age": 55,
                    "sex": "M",
                    "trauma": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Trauma - Coup sur la tête",
                "text": "Femme 62 ans, coup sur la tête hier, mal de tête depuis",
                "expected_fields": {
                    "age": 62,
                    "sex": "F",
                    "trauma": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            
            # === CATÉGORIE 6: IMMUNOSUPPRESSION - Acronymes et variations ===
            {
                "name": "Immunosuppression - VIH+ (minuscule)",
                "text": "Patient vih+ 42 ans, céphalée fébrile progressive",
                "expected_fields": {
                    "age": 42,
                    "sex": "M",
                    "immunosuppression": True,
                    "fever": True,
                    "onset": "progressive"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Immunosuppression - VIH positif",
                "text": "Homme vih positif 38 ans, mal de tête avec fièvre",
                "expected_fields": {
                    "age": 38,
                    "sex": "M",
                    "immunosuppression": True,
                    "fever": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Immunosuppression - SIDA",
                "text": "Patient sida 45 ans, céphalée progressive",
                "expected_fields": {
                    "age": 45,
                    "sex": "M",
                    "immunosuppression": True,
                    "onset": "progressive"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Immunosuppression - Chimiothérapie",
                "text": "Femme 55 ans sous chimio, céphalée avec fièvre",
                "expected_fields": {
                    "age": 55,
                    "sex": "F",
                    "immunosuppression": True,
                    "fever": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Immunosuppression - Immunodéprimé",
                "text": "Homme immunodéprimé 60 ans, céphalée fébrile",
                "expected_fields": {
                    "age": 60,
                    "sex": "M",
                    "immunosuppression": True,
                    "fever": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Immunosuppression - Corticothérapie",
                "text": "Patiente 50 ans sous corticothérapie au long cours, céphalée",
                "expected_fields": {
                    "age": 50,
                    "sex": "F",
                    "immunosuppression": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            
            # === CATÉGORIE 7: SIGNES NEUROLOGIQUES - Variations symptômes ===
            {
                "name": "Neuro - Faiblesse bras droit",
                "text": "Homme 65 ans, céphalée avec faiblesse bras droit",
                "expected_fields": {
                    "age": 65,
                    "sex": "M",
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Hémiparésie",
                "text": "Patiente 58 ans, mal de tête, hémiparésie gauche",
                "expected_fields": {
                    "age": 58,
                    "sex": "F",
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Difficultés à parler",
                "text": "Homme 62 ans, céphalée, difficultés à parler",
                "expected_fields": {
                    "age": 62,
                    "sex": "M",
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Aphasie",
                "text": "Femme 55 ans, céphalée avec aphasie",
                "expected_fields": {
                    "age": 55,
                    "sex": "F",
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Troubles de la parole",
                "text": "Patient 60 ans, mal de tête, troubles de la parole",
                "expected_fields": {
                    "age": 60,
                    "sex": "M",
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Vision floue",
                "text": "Homme 62 ans, céphalée, vision floue",
                "expected_fields": {
                    "age": 62,
                    "sex": "M",
                    "neuro_deficit": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Neuro - Troubles visuels",
                "text": "Femme 48 ans, mal de tête avec troubles visuels",
                "expected_fields": {
                    "age": 48,
                    "sex": "F",
                    "neuro_deficit": True
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Neuro - Crise convulsive",
                "text": "Femme 40 ans, céphalée suivie d'une crise convulsive",
                "expected_fields": {
                    "age": 40,
                    "sex": "F",
                    "seizure": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Neuro - Convulsions",
                "text": "Patient 35 ans, mal de tête puis convulsions",
                "expected_fields": {
                    "age": 35,
                    "sex": "M",
                    "seizure": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HTIC - Acronyme minuscule",
                "text": "Patient 50 ans, céphalée avec signes d'htic",
                "expected_fields": {
                    "age": 50,
                    "sex": "M",
                    "htic_pattern": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HTIC - Hypertension intracrânienne",
                "text": "Homme 55 ans, céphalée avec hypertension intracrânienne",
                "expected_fields": {
                    "age": 55,
                    "sex": "M",
                    "htic_pattern": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "HTIC - Pire le matin",
                "text": "Femme 45 ans, céphalée plus forte le matin",
                "expected_fields": {
                    "age": 45,
                    "sex": "F",
                    "htic_pattern": True
                },
                "expected_urgency": None,
                "expected_exam_contains": ["scanner"]
            },
            
            # === CATÉGORIE 8: INTENSITÉ - Synonymes et variations ===
            {
                "name": "Intensité - 10/10",
                "text": "Homme 50 ans, céphalée intensité 10/10",
                "expected_fields": {
                    "age": 50,
                    "sex": "M",
                    "intensity": 10
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Intensité - Atroce et insupportable",
                "text": "Femme 45 ans, céphalée atroce et insupportable",
                "expected_fields": {
                    "age": 45,
                    "sex": "F",
                    "intensity": 10
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Intensité - Intensité maximale",
                "text": "Patient 55 ans, céphalée d'intensité maximale",
                "expected_fields": {
                    "age": 55,
                    "sex": "M",
                    "intensity": 10
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Intensité - Sévère",
                "text": "Homme 60 ans, céphalée sévère",
                "expected_fields": {
                    "age": 60,
                    "sex": "M",
                    "intensity": 9
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Intensité - Modérée",
                "text": "Femme 40 ans, céphalée modérée",
                "expected_fields": {
                    "age": 40,
                    "sex": "F",
                    "intensity": 6
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Intensité - Légère",
                "text": "Patient 35 ans, céphalée légère",
                "expected_fields": {
                    "age": 35,
                    "sex": "M",
                    "intensity": 3
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            
            # === CATÉGORIE 9: CAS COMPLEXES ===
            {
                "name": "Complexe - HSA + grossesse",
                "text": "Femme enceinte 30 ans, céphalée en coup de tonnerre",
                "expected_fields": {
                    "age": 30,
                    "sex": "F",
                    "pregnancy_postpartum": True,
                    "onset": "thunderclap",
                    "profile": "acute"
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["IRM"]
            },
            {
                "name": "Complexe - Méningite + VIH",
                "text": "Patient vih positif 38 ans, fièvre 39°C, raideur nuque, céphalée",
                "expected_fields": {
                    "age": 38,
                    "sex": "M",
                    "immunosuppression": True,
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            {
                "name": "Complexe - TCE + déficit neuro",
                "text": "Homme 55 ans, tce hier, aujourd'hui céphalée et faiblesse jambe gauche",
                "expected_fields": {
                    "age": 55,
                    "sex": "M",
                    "trauma": True,
                    "neuro_deficit": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner"]
            },
            {
                "name": "Complexe - Post-partum + fièvre + signes méningés",
                "text": "Jeune mère 26 ans, accouchement il y a 10 jours, céphalée fébrile, nuque raide",
                "expected_fields": {
                    "age": 26,
                    "sex": "F",
                    "pregnancy_postpartum": True,
                    "fever": True,
                    "meningeal_signs": True
                },
                "expected_urgency": "immediate",
                "expected_exam_contains": ["scanner", "ponction"]
            },
            
            # === CATÉGORIE 10: FORMULATIONS FAMILIÈRES ===
            {
                "name": "Familier - Mal de crâne",
                "text": "Elle a 42 ans, terrible mal de crâne depuis hier soir",
                "expected_fields": {
                    "age": 42,
                    "sex": "F",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Familier - Tête qui éclate",
                "text": "Homme 50 ans, j'ai la tête qui éclate depuis ce matin",
                "expected_fields": {
                    "age": 50,
                    "sex": "M",
                    "profile": "acute"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            },
            {
                "name": "Familier - Mal partout dans la tête",
                "text": "Femme 35 ans, j'ai mal partout dans la tête",
                "expected_fields": {
                    "age": 35,
                    "sex": "F"
                },
                "expected_urgency": None,
                "expected_exam_contains": None
            }
        ]
        
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def test_case(
        self,
        test_name: str,
        input_text: str,
        expected_fields: Dict[str, Any],
        expected_urgency: str = None,
        expected_exam_contains: List[str] = None
    ):
        """
        Teste un cas avec vérification des champs extraits et de la recommandation.
        
        Args:
            test_name: Nom du test
            input_text: Texte libre à analyser
            expected_fields: Champs attendus {field_name: expected_value}
            expected_urgency: Niveau d'urgence attendu (immediate/urgent/delayed/none)
            expected_exam_contains: Liste d'examens attendus dans la recommandation
        """
        self.total_tests += 1
        
        # Parse le cas (retourne un tuple: case, metadata)
        case, metadata = parse_free_text_to_case(input_text)
        
        # Génère la recommandation
        recommendation = decide_imaging(case)
        
        # Vérifie les champs extraits
        fields_ok = True
        field_errors = []
        
        for field_name, expected_value in expected_fields.items():
            actual_value = getattr(case, field_name, None)
            
            if actual_value != expected_value:
                fields_ok = False
                field_errors.append(
                    f"  - {field_name}: attendu={expected_value}, obtenu={actual_value}"
                )
        
        # Vérifie l'urgence
        urgency_ok = True
        if expected_urgency is not None:
            if recommendation.urgency != expected_urgency:
                urgency_ok = False
        
        # Vérifie les examens
        exam_ok = True
        exam_errors = []
        if expected_exam_contains is not None:
            # Vérifie dans la liste imaging et dans le commentaire
            imaging_lower = [exam.lower() for exam in recommendation.imaging]
            comment_lower = recommendation.comment.lower()
            
            for exam in expected_exam_contains:
                exam_lower = exam.lower()
                found = False
                
                # Cherche dans la liste des examens
                for img in imaging_lower:
                    if exam_lower in img:
                        found = True
                        break
                
                # Cherche dans le commentaire si pas trouvé
                if not found and exam_lower in comment_lower:
                    found = True
                
                if not found:
                    exam_ok = False
                    exam_errors.append(f"  - '{exam}' manquant dans la recommandation")
        
        # Résultat global
        passed = fields_ok and urgency_ok and exam_ok
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        # Enregistre le résultat
        result = {
            "name": test_name,
            "input": input_text,
            "passed": passed,
            "fields_ok": fields_ok,
            "urgency_ok": urgency_ok,
            "exam_ok": exam_ok,
            "field_errors": field_errors,
            "exam_errors": exam_errors,
            "extracted_case": case.model_dump(),
            "recommendation": {
                "urgency": recommendation.urgency,
                "imaging": recommendation.imaging,
                "comment": recommendation.comment
            }
        }
        
        self.test_results.append(result)
        
        return passed
    
    def run_all_tests(self):
        """Exécute tous les tests définis."""
        print("=" * 80)
        print("TESTS DE ROBUSTESSE DU SYSTÈME NLU")
        print("=" * 80)
        print()
        
        for test in self.tests:
            passed = self.test_case(
                test["name"],
                test["text"],
                test["expected_fields"],
                test.get("expected_urgency"),
                test.get("expected_exam_contains")
            )
            
            # Affiche le résultat en temps réel
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {test['name']}")
        
        print()
        self.print_summary()
    
    def print_summary(self):
        """Affiche un résumé des tests."""
        print("=" * 80)
        print("RÉSUMÉ DES TESTS")
        print("=" * 80)
        print(f"Total: {self.total_tests}")
        print(f"Réussis: {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)")
        print(f"Échoués: {self.failed_tests} ({self.failed_tests/self.total_tests*100:.1f}%)")
        
        if self.failed_tests > 0:
            print()
            print("Tests échoués:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['name']}")
                    if result["field_errors"]:
                        print("    Erreurs de champs:")
                        for error in result["field_errors"]:
                            print(f"    {error}")
                    if not result["urgency_ok"]:
                        print(f"    Urgence incorrecte")
                    if result["exam_errors"]:
                        print("    Erreurs d'examens:")
                        for error in result["exam_errors"]:
                            print(f"    {error}")
        
        print("=" * 80)
    
    def save_results(self, filename: str = "test_nlu_results_v2.json"):
        """Sauvegarde les résultats dans un fichier JSON."""
        output = {
            "total": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "success_rate": f"{self.passed_tests/self.total_tests*100:.1f}%",
            "tests": self.test_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\nRésultats sauvegardés dans: {filename}")


if __name__ == "__main__":
    tester = NLUTester()
    tester.run_all_tests()
    tester.save_results()
