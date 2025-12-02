#!/usr/bin/env python3
"""
Test de robustesse du système NLU avec différentes formulations.

Ce script teste la capacité du système à comprendre:
- Différents synonymes médicaux
- Acronymes courants
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
        print(f"\n{'='*80}")
        print(f"TEST #{self.total_tests}: {test_name}")
        print(f"{'='*80}")
        print(f"Input: {input_text}")
        print(f"-" * 80)
        
        # Extraction NLU
        extracted_case, metadata = parse_free_text_to_case(input_text)
        
        # Affichage des champs extraits
        print("\n📋 CHAMPS EXTRAITS PAR LE NLU:")
        detected_fields = metadata.get("detected_fields", [])
        if detected_fields:
            for field in detected_fields:
                value = getattr(extracted_case, field, None)
                print(f"  ✓ {field}: {value}")
        else:
            print("  ⚠️  Aucun champ détecté")
        
        # Vérification des champs attendus
        print("\n🔍 VÉRIFICATION DES CHAMPS ATTENDUS:")
        fields_ok = True
        for field_name, expected_value in expected_fields.items():
            actual_value = getattr(extracted_case, field_name, None)
            if actual_value == expected_value:
                print(f"  ✅ {field_name}: {actual_value} (OK)")
            else:
                print(f"  ❌ {field_name}: attendu={expected_value}, obtenu={actual_value}")
                fields_ok = False
        
        # Décision d'imagerie
        try:
            recommendation = decide_imaging(extracted_case)
            
            print("\n🏥 RECOMMANDATION MÉDICALE:")
            print(f"  • Urgence: {recommendation.urgency}")
            print(f"  • Examens: {', '.join(recommendation.imaging)}")
            print(f"  • Commentaire: {recommendation.comment[:100]}...")
            
            # Vérification de l'urgence
            urgency_ok = True
            if expected_urgency:
                if recommendation.urgency == expected_urgency:
                    print(f"  ✅ Urgence correcte: {expected_urgency}")
                else:
                    print(f"  ❌ Urgence incorrecte: attendu={expected_urgency}, obtenu={recommendation.urgency}")
                    urgency_ok = False
            
            # Vérification des examens
            exams_ok = True
            if expected_exam_contains:
                for exam in expected_exam_contains:
                    if any(exam.lower() in img.lower() for img in recommendation.imaging):
                        print(f"  ✅ Examen trouvé: {exam}")
                    else:
                        print(f"  ❌ Examen manquant: {exam}")
                        exams_ok = False
            
            # Résultat global
            test_passed = fields_ok and urgency_ok and exams_ok
            
        except Exception as e:
            print(f"\n❌ ERREUR lors de la décision: {e}")
            test_passed = False
            recommendation = None
        
        # Enregistrement du résultat
        result = {
            "test_name": test_name,
            "input_text": input_text,
            "fields_ok": fields_ok,
            "urgency_ok": urgency_ok if expected_urgency else None,
            "exams_ok": exams_ok if expected_exam_contains else None,
            "passed": test_passed,
            "extracted_case": extracted_case.model_dump() if extracted_case else None,
            "recommendation": {
                "urgency": recommendation.urgency,
                "imaging": recommendation.imaging,
                "comment": recommendation.comment
            } if recommendation else None
        }
        
        self.test_results.append(result)
        
        if test_passed:
            self.passed_tests += 1
            print("\n🎉 TEST RÉUSSI")
        else:
            self.failed_tests += 1
            print("\n💥 TEST ÉCHOUÉ")
        
        return test_passed
    
    def print_summary(self):
        """Affiche un résumé des tests."""
        print("\n" + "="*80)
        print("RÉSUMÉ DES TESTS")
        print("="*80)
        print(f"Total: {self.total_tests}")
        print(f"Réussis: {self.passed_tests} ({100*self.passed_tests/self.total_tests:.1f}%)")
        print(f"Échoués: {self.failed_tests} ({100*self.failed_tests/self.total_tests:.1f}%)")
        
        if self.failed_tests > 0:
            print("\n❌ Tests échoués:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test_name']}")
    
    def save_results(self, filename: str = "test_nlu_results.json"):
        """Sauvegarde les résultats dans un fichier JSON."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total": self.total_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "success_rate": 100 * self.passed_tests / self.total_tests if self.total_tests > 0 else 0
                },
                "tests": self.test_results
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultats sauvegardés dans: {filename}")


def main():
    """Lance les tests de robustesse du NLU."""
    tester = NLUTester()
    
    print("""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                  TEST DE ROBUSTESSE DU SYSTÈME NLU                         ║
    ║                                                                            ║
    ║  Ce script teste la capacité du système à comprendre différentes          ║
    ║  formulations, synonymes, acronymes et niveaux de langage.                 ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ========================================================================
    # CATÉGORIE 1: HÉMORRAGIE SOUS-ARACHNOÏDIENNE (HSA)
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 1: HÉMORRAGIE SOUS-ARACHNOÏDIENNE (HSA)")
    print("█"*80)
    
    # Test 1.1: Formulation classique
    tester.test_case(
        test_name="HSA - Formulation classique",
        input_text="Homme 55 ans, céphalée en coup de tonnerre, intensité 10/10",
        expected_fields={
            "age": 55,
            "sex": "M",
            "onset": "thunderclap",
            "intensity": 10,
            "profile": "acute"
        },
        expected_urgency="immediate",
        expected_exam_contains=["scanner", "ponction"]
    )
    
    # Test 1.2: Synonymes de "coup de tonnerre"
    tester.test_case(
        test_name="HSA - Synonymes onset",
        input_text="Patient de 60 ans, douleur brutale et soudaine, pire douleur de sa vie",
        expected_fields={
            "age": 60,
            "onset": "thunderclap",
            "profile": "acute"
        },
        expected_urgency="immediate"
    )
    
    # Test 1.3: Langage familier
    tester.test_case(
        test_name="HSA - Langage familier",
        input_text="Monsieur de 50 ans, mal de tête horrible qui a commencé d'un coup, jamais eu aussi mal",
        expected_fields={
            "age": 50,
            "sex": "M",
            "onset": "thunderclap"
        },
        expected_urgency="immediate"
    )
    
    # Test 1.4: Avec intensité écrite en lettres
    tester.test_case(
        test_name="HSA - Intensité en lettres",
        input_text="Femme 45 ans, céphalée brutale, douleur maximale insupportable",
        expected_fields={
            "age": 45,
            "sex": "F",
            "onset": "thunderclap",
            "intensity": 10  # "maximale" devrait être détecté comme 10
        },
        expected_urgency="immediate"
    )
    
    # ========================================================================
    # CATÉGORIE 2: MÉNINGITE
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 2: MÉNINGITE")
    print("█"*80)
    
    # Test 2.1: Formulation médicale
    tester.test_case(
        test_name="Méningite - Formulation médicale",
        input_text="Patiente 30 ans, céphalée fébrile, température 39°C, raideur de la nuque",
        expected_fields={
            "age": 30,
            "sex": "F",
            "fever": True,
            "meningeal_signs": True
        },
        expected_urgency="immediate",
        expected_exam_contains=["ponction_lombaire"]
    )
    
    # Test 2.2: Synonymes de fièvre
    tester.test_case(
        test_name="Méningite - Synonymes fièvre",
        input_text="Homme 25 ans, mal de tête avec hyperthermie, nuque raide",
        expected_fields={
            "age": 25,
            "sex": "M",
            "fever": True,
            "meningeal_signs": True
        },
        expected_urgency="immediate"
    )
    
    # Test 2.3: Langage familier
    tester.test_case(
        test_name="Méningite - Langage familier",
        input_text="Jeune femme de 28 ans, grosse fièvre, mal de tête, ne peut pas bouger le cou",
        expected_fields={
            "age": 28,
            "sex": "F",
            "fever": True,
            "meningeal_signs": True
        },
        expected_urgency="immediate"
    )
    
    # Test 2.4: Avec signes de Kernig/Brudzinski
    tester.test_case(
        test_name="Méningite - Signes cliniques spécifiques",
        input_text="Patient 35 ans, céphalée, fièvre à 38.5°C, signe de Kernig positif",
        expected_fields={
            "age": 35,
            "fever": True,
            "meningeal_signs": True
        },
        expected_urgency="immediate"
    )
    
    # ========================================================================
    # CATÉGORIE 3: PROFIL TEMPOREL (ONSET ET PROFILE)
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 3: PROFIL TEMPOREL")
    print("█"*80)
    
    # Test 3.1: Aigu - Formulations variées
    tester.test_case(
        test_name="Profil aigu - Heures",
        input_text="Femme 40 ans, céphalée depuis 6 heures",
        expected_fields={
            "age": 40,
            "sex": "F",
            "profile": "acute",
            "onset": "progressive"
        }
    )
    
    tester.test_case(
        test_name="Profil aigu - Jours",
        input_text="Homme 50 ans, mal de tête depuis 3 jours qui augmente",
        expected_fields={
            "age": 50,
            "sex": "M",
            "profile": "acute",
            "onset": "progressive"
        }
    )
    
    # Test 3.2: Subaigu
    tester.test_case(
        test_name="Profil subaigu",
        input_text="Patiente 35 ans, céphalées progressives depuis 2 semaines",
        expected_fields={
            "age": 35,
            "sex": "F",
            "profile": "subacute",
            "onset": "progressive"
        }
    )
    
    # Test 3.3: Chronique - Variantes
    tester.test_case(
        test_name="Profil chronique - Mois",
        input_text="Homme 60 ans, céphalées quotidiennes depuis 6 mois",
        expected_fields={
            "age": 60,
            "sex": "M",
            "profile": "chronic",
            "onset": "chronic"
        }
    )
    
    tester.test_case(
        test_name="Profil chronique - Années",
        input_text="Patiente de 45 ans, maux de tête permanents depuis des années",
        expected_fields={
            "age": 45,
            "sex": "F",
            "profile": "chronic",
            "onset": "chronic"
        }
    )
    
    # ========================================================================
    # CATÉGORIE 4: GROSSESSE ET CONTEXTES À RISQUE
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 4: GROSSESSE ET CONTEXTES À RISQUE")
    print("█"*80)
    
    # Test 4.1: Grossesse - Formulations variées
    tester.test_case(
        test_name="Grossesse - Enceinte",
        input_text="Femme enceinte de 28 ans, céphalée brutale",
        expected_fields={
            "age": 28,
            "sex": "F",
            "pregnancy_postpartum": True,
            "onset": "thunderclap"
        },
        expected_exam_contains=["irm"]  # Pas de scanner!
    )
    
    tester.test_case(
        test_name="Grossesse - Post-partum",
        input_text="Jeune mère de 32 ans, accouchement il y a 2 semaines, forte céphalée",
        expected_fields={
            "age": 32,
            "sex": "F",
            "pregnancy_postpartum": True
        }
    )
    
    tester.test_case(
        test_name="Grossesse - Terme médical",
        input_text="Patiente en période du post-partum, 30 ans, céphalée progressive",
        expected_fields={
            "age": 30,
            "sex": "F",
            "pregnancy_postpartum": True,
            "onset": "progressive"
        }
    )
    
    # Test 4.2: Traumatisme - Variantes
    tester.test_case(
        test_name="Traumatisme - TCE",
        input_text="Homme 55 ans, TCE il y a 3 jours, céphalées depuis",
        expected_fields={
            "age": 55,
            "sex": "M",
            "trauma": True
        },
        expected_urgency="urgent"
    )
    
    tester.test_case(
        test_name="Traumatisme - Chute",
        input_text="Patiente 70 ans, chute avec choc à la tête hier, mal de tête aujourd'hui",
        expected_fields={
            "age": 70,
            "sex": "F",
            "trauma": True
        }
    )
    
    # Test 4.3: Immunosuppression - Variantes
    tester.test_case(
        test_name="Immunosuppression - VIH",
        input_text="Patient VIH+ de 40 ans, céphalées progressives",
        expected_fields={
            "age": 40,
            "immunosuppression": True,
            "onset": "progressive"
        }
    )
    
    tester.test_case(
        test_name="Immunosuppression - Chimiothérapie",
        input_text="Femme 55 ans sous chimiothérapie, nouvelles céphalées",
        expected_fields={
            "age": 55,
            "sex": "F",
            "immunosuppression": True
        }
    )
    
    # ========================================================================
    # CATÉGORIE 5: SIGNES NEUROLOGIQUES
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 5: SIGNES NEUROLOGIQUES")
    print("█"*80)
    
    # Test 5.1: Déficit neurologique - Variantes
    tester.test_case(
        test_name="Déficit neuro - Hémiparésie",
        input_text="Homme 65 ans, céphalée avec faiblesse du bras droit",
        expected_fields={
            "age": 65,
            "sex": "M",
            "neuro_deficit": True
        },
        expected_urgency="immediate"
    )
    
    tester.test_case(
        test_name="Déficit neuro - Aphasie",
        input_text="Patiente 70 ans, mal de tête, difficultés à parler",
        expected_fields={
            "age": 70,
            "sex": "F",
            "neuro_deficit": True
        }
    )
    
    tester.test_case(
        test_name="Déficit neuro - Troubles visuels",
        input_text="Homme 58 ans, céphalée, vision floue d'un œil",
        expected_fields={
            "age": 58,
            "sex": "M",
            "neuro_deficit": True
        }
    )
    
    # Test 5.2: Crises d'épilepsie - Variantes
    tester.test_case(
        test_name="Épilepsie - Crise",
        input_text="Femme 35 ans, céphalée après une crise convulsive",
        expected_fields={
            "age": 35,
            "sex": "F",
            "seizure": True
        }
    )
    
    tester.test_case(
        test_name="Épilepsie - Convulsions",
        input_text="Patient 42 ans, convulsions ce matin, puis mal de tête persistant",
        expected_fields={
            "age": 42,
            "seizure": True
        }
    )
    
    # Test 5.3: HTIC - Variantes
    tester.test_case(
        test_name="HTIC - Matinale",
        input_text="Homme 50 ans, céphalée plus forte le matin au réveil, vomissements",
        expected_fields={
            "age": 50,
            "sex": "M",
            "htic_pattern": True
        }
    )
    
    tester.test_case(
        test_name="HTIC - Vomissements en jet",
        input_text="Patiente 38 ans, mal de tête avec vomissements en jet",
        expected_fields={
            "age": 38,
            "sex": "F",
            "htic_pattern": True
        }
    )
    
    # ========================================================================
    # CATÉGORIE 6: EXTRACTION D'ÂGE ET SEXE - VARIANTES
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 6: EXTRACTION ÂGE ET SEXE")
    print("█"*80)
    
    # Test 6.1: Formats d'âge variés
    tester.test_case(
        test_name="Âge - Format standard",
        input_text="Patient de 55 ans, céphalée",
        expected_fields={"age": 55}
    )
    
    tester.test_case(
        test_name="Âge - Sans 'de'",
        input_text="Homme 62 ans, mal de tête",
        expected_fields={"age": 62, "sex": "M"}
    )
    
    tester.test_case(
        test_name="Âge - 'Âgé de'",
        input_text="Patiente âgée de 78 ans, céphalées",
        expected_fields={"age": 78, "sex": "F"}
    )
    
    # Test 6.2: Détection du sexe
    tester.test_case(
        test_name="Sexe - Homme",
        input_text="Homme de 45 ans",
        expected_fields={"sex": "M", "age": 45}
    )
    
    tester.test_case(
        test_name="Sexe - Monsieur",
        input_text="Monsieur de 50 ans",
        expected_fields={"sex": "M", "age": 50}
    )
    
    tester.test_case(
        test_name="Sexe - Femme",
        input_text="Femme de 35 ans",
        expected_fields={"sex": "F", "age": 35}
    )
    
    tester.test_case(
        test_name="Sexe - Patiente",
        input_text="Patiente de 40 ans",
        expected_fields={"sex": "F", "age": 40}
    )
    
    # ========================================================================
    # CATÉGORIE 7: CAS COMPLEXES MULTI-CRITÈRES
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 7: CAS COMPLEXES")
    print("█"*80)
    
    # Test 7.1: HSA + grossesse
    tester.test_case(
        test_name="Complexe - HSA + grossesse",
        input_text="Femme enceinte de 30 ans, céphalée en coup de tonnerre, intensité maximale",
        expected_fields={
            "age": 30,
            "sex": "F",
            "onset": "thunderclap",
            "pregnancy_postpartum": True,
            "intensity": 10
        },
        expected_urgency="immediate",
        expected_exam_contains=["irm"]  # IRM car grossesse
    )
    
    # Test 7.2: Méningite + immunosuppression
    tester.test_case(
        test_name="Complexe - Méningite + immunosuppression",
        input_text="Patient VIH+ de 38 ans, fièvre 39°C, raideur nuque, céphalée",
        expected_fields={
            "age": 38,
            "fever": True,
            "meningeal_signs": True,
            "immunosuppression": True
        },
        expected_urgency="immediate"
    )
    
    # Test 7.3: Trauma + déficit neuro
    tester.test_case(
        test_name="Complexe - Trauma + déficit neuro",
        input_text="Homme 65 ans, chute il y a 2 jours, céphalée, faiblesse bras gauche",
        expected_fields={
            "age": 65,
            "sex": "M",
            "trauma": True,
            "neuro_deficit": True
        },
        expected_urgency="immediate"
    )
    
    # Test 7.4: Cas bénin chronique
    tester.test_case(
        test_name="Complexe - Céphalée bénigne",
        input_text="Femme 35 ans, céphalées de tension quotidiennes depuis 1 an, sans autre signe",
        expected_fields={
            "age": 35,
            "sex": "F",
            "profile": "chronic",
            "onset": "chronic"
        },
        expected_urgency="none"
    )
    
    # ========================================================================
    # CATÉGORIE 8: TESTS DE ROBUSTESSE - FORMULATIONS AMBIGUËS
    # ========================================================================
    
    print("\n" + "█"*80)
    print("CATÉGORIE 8: FORMULATIONS AMBIGUËS")
    print("█"*80)
    
    # Test 8.1: Intensité implicite
    tester.test_case(
        test_name="Ambiguë - Intensité implicite",
        input_text="Patient 50 ans, céphalée atroce, insupportable",
        expected_fields={
            "age": 50,
            "intensity": 10  # "atroce" et "insupportable" → intensité max
        }
    )
    
    # Test 8.2: Négation de fièvre
    tester.test_case(
        test_name="Ambiguë - Négation",
        input_text="Femme 40 ans, céphalée sans fièvre, pas de raideur de nuque",
        expected_fields={
            "age": 40,
            "sex": "F",
            "fever": False,
            "meningeal_signs": False
        }
    )
    
    # Test 8.3: Formulation très familière
    tester.test_case(
        test_name="Ambiguë - Très familier",
        input_text="Madame de 55 ans qui a super mal à la tête depuis ce matin",
        expected_fields={
            "age": 55,
            "sex": "F",
            "profile": "acute"
        }
    )
    
    # Affichage du résumé
    tester.print_summary()
    
    # Sauvegarde des résultats
    tester.save_results()
    
    print("\n" + "="*80)
    print("FIN DES TESTS")
    print("="*80)


if __name__ == "__main__":
    main()
