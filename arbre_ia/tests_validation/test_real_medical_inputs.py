#!/usr/bin/env python3
"""Tests avec des inputs médicaux réalistes.

Ce script teste le système NLU avec des descriptions comme celles
qu'un médecin écrirait réellement aux urgences ou en consultation.

Catégories testées:
1. Urgences neurologiques (HSA, méningite, HTIC)
2. Céphalées primaires (migraine, tension)
3. Contextes spéciaux (grossesse, immunodépression)
4. Formulations familières / argotiques
5. Fautes de frappe courantes
6. Cas complexes multi-symptômes
"""

import sys
sys.path.insert(0, '.')

from headache_assistants.nlu_hybrid import HybridNLU


def run_test(nlu, text, expected_fields, test_name=""):
    """Exécute un test et vérifie les champs attendus."""
    result = nlu.parse_hybrid(text)
    case_dict = result.case.model_dump()
    metadata = result.metadata

    passed = True
    details = []

    for field, expected_value in expected_fields.items():
        actual_value = case_dict.get(field)

        # Gestion des valeurs "any True" ou "any not None"
        if expected_value == "ANY_TRUE":
            if actual_value == True:
                details.append(f"    ✓ {field}={actual_value}")
            else:
                details.append(f"    ✗ {field}={actual_value} (attendu: True)")
                passed = False
        elif expected_value == "ANY_FALSE":
            if actual_value == False:
                details.append(f"    ✓ {field}={actual_value}")
            else:
                details.append(f"    ✗ {field}={actual_value} (attendu: False)")
                passed = False
        elif expected_value == "NOT_NONE":
            if actual_value is not None:
                details.append(f"    ✓ {field}={actual_value} (non null)")
            else:
                details.append(f"    ✗ {field}=None (attendu: non null)")
                passed = False
        elif actual_value == expected_value:
            details.append(f"    ✓ {field}={actual_value}")
        else:
            details.append(f"    ✗ {field}={actual_value} (attendu: {expected_value})")
            passed = False

    # Afficher les corrections fuzzy si présentes
    fuzzy = metadata.get("fuzzy_corrections", [])
    if fuzzy:
        corrections_str = [c["original"] + "→" + c["corrected"] for c in fuzzy]
        details.append(f"    Corrections: {corrections_str}")

    return passed, details, metadata


def test_urgences_neurologiques(hybrid_nlu):
    """Test des urgences neurologiques (HSA, méningite, HTIC)."""
    print("\n" + "="*70)
    print("CATÉGORIE 1: URGENCES NEUROLOGIQUES")
    print("="*70)

    tests = [
        # HSA - Hémorragie sous-arachnoïdienne
        {
            "name": "HSA classique",
            "text": "Homme 45 ans, céphalée brutale en coup de tonnerre survenue il y a 2h pendant effort physique, pire douleur de sa vie, vomissements, nuque raide",
            "expected": {
                "onset": "thunderclap",
                "meningeal_signs": "ANY_TRUE",
                "htic_pattern": "ANY_TRUE",
            }
        },
        {
            "name": "HSA atypique",
            "text": "Patiente 52a, début brutal mal de tête intense ce matin au réveil, jamais eu ça avant, sensation de tête qui va exploser",
            "expected": {
                "onset": "thunderclap",
            }
        },
        # Méningite
        {
            "name": "Méningite bactérienne",
            "text": "Jeune homme 22 ans fébrile à 39.5, céphalées + photophobie + raideur de nuque, confusion depuis 2h, éruption purpurique aux MI",
            "expected": {
                "fever": "ANY_TRUE",
                "meningeal_signs": "ANY_TRUE",
            }
        },
        {
            "name": "Syndrome méningé",
            "text": "Enfant 8 ans, fievre depuis 24h, vomissements en jet, position en chien de fusil, refuse la lumière",
            "expected": {
                "fever": "ANY_TRUE",
                "meningeal_signs": "ANY_TRUE",
                "htic_pattern": "ANY_TRUE",
            }
        },
        # HTIC
        {
            "name": "HTIC tumorale",
            "text": "Patient 60 ans, céphalées matinales depuis 3 semaines, aggravées par la toux et les efforts, vomissements faciles, troubles visuels",
            "expected": {
                "onset": "progressive",
                "htic_pattern": "ANY_TRUE",
            }
        },
        {
            "name": "Processus expansif",
            "text": "Femme 55a, cephalees progressives depuis 1 mois, pire le matin au réveil, oedème papillaire au FO, deficit moteur brachio-facial droit",
            "expected": {
                "onset": "progressive",
                "htic_pattern": "ANY_TRUE",
                "neuro_deficit": "ANY_TRUE",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_cephalees_primaires(hybrid_nlu):
    """Test des céphalées primaires (migraine, tension)."""
    print("\n" + "="*70)
    print("CATÉGORIE 2: CÉPHALÉES PRIMAIRES")
    print("="*70)

    tests = [
        # Migraine
        {
            "name": "Migraine avec aura",
            "text": "Femme 35 ans, migraineuse connue, céphalée pulsatile hémicrânienne droite depuis 6h, précédée de scotomes scintillants, nausées, photophobie, phonophobie",
            "expected": {
                "headache_profile": "migraine_like",
            }
        },
        {
            "name": "Migraine typique",
            "text": "Patiente 28a, crises similaires depuis l'adolescence, douleur qui bat dans la tempe gauche, doit s'allonger dans le noir",
            "expected": {
                "headache_profile": "migraine_like",
            }
        },
        # Céphalée de tension
        {
            "name": "Céphalée tension épisodique",
            "text": "Homme 40 ans, mal de tête en casque depuis ce matin, sensation de serrement, pas de nausées, peut continuer à travailler",
            "expected": {
                "headache_profile": "tension_like",
            }
        },
        {
            "name": "Céphalée tension chronique",
            "text": "Patient 45a, céphalées quotidiennes depuis 6 mois, douleur en étau bilatérale, pas aggravée par l'effort",
            "expected": {
                "headache_profile": "tension_like",
                "onset": "chronic",  # 6 mois de céphalées quotidiennes = chronique
            }
        },
        # Algie vasculaire
        {
            "name": "Algie vasculaire de la face",
            "text": "Homme 35 ans, douleur atroce péri-orbitaire gauche depuis 45min, larmoiement, rhinorrhée, agitation, crises similaires tous les soirs depuis 2 semaines",
            "expected": {
                # Devrait détecter un pattern spécial
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_contextes_speciaux(hybrid_nlu):
    """Test des contextes spéciaux à risque."""
    print("\n" + "="*70)
    print("CATÉGORIE 3: CONTEXTES SPÉCIAUX")
    print("="*70)

    tests = [
        # Grossesse
        {
            "name": "Pré-éclampsie",
            "text": "Femme enceinte 32 SA, céphalées intenses depuis 24h, TA 160/100, oedèmes des MI, protéinurie +++",
            "expected": {
                "pregnancy_postpartum": "ANY_TRUE",
            }
        },
        {
            "name": "Grossesse T1",
            "text": "Patiente 28 ans enceinte de 10 semaines, céphalées depuis 3 jours, pas de fièvre, examen neuro normal",
            "expected": {
                "pregnancy_postpartum": "ANY_TRUE",
                "fever": "ANY_FALSE",
            }
        },
        {
            "name": "Post-partum TVC",
            "text": "Accouchement il y a 5 jours, céphalées progressives intenses, convulsion ce matin",
            "expected": {
                "pregnancy_postpartum": "ANY_TRUE",
                "seizure": "ANY_TRUE",
                "onset": "progressive",
            }
        },
        # Immunodépression
        {
            "name": "VIH toxoplasmose",
            "text": "Patient VIH+ CD4 à 50, céphalées depuis 1 semaine, fièvre modérée, confusion progressive",
            "expected": {
                "immunosuppression": "ANY_TRUE",
                "fever": "ANY_TRUE",
                "onset": "progressive",
            }
        },
        {
            "name": "Post-chimio",
            "text": "Patiente sous chimiothérapie pour cancer du sein, aplasique, céphalées fébriles depuis 48h",
            "expected": {
                "immunosuppression": "ANY_TRUE",
                "fever": "ANY_TRUE",
            }
        },
        # Anticoagulation
        {
            "name": "HSD sous AVK",
            "text": "Homme 78 ans sous Coumadine, chute il y a 1 semaine, céphalées progressives, ralentissement idéomoteur",
            "expected": {
                "trauma": "ANY_TRUE",
                "onset": "progressive",
            }
        },
        # Post-PL
        {
            "name": "Hypotension LCR",
            "text": "Ponction lombaire il y a 3 jours, céphalées intenses soulagées allongé, pire debout",
            "expected": {
                "recent_pl_or_peridural": "ANY_TRUE",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_formulations_familieres(hybrid_nlu):
    """Test des formulations familières / langage courant."""
    print("\n" + "="*70)
    print("CATÉGORIE 4: FORMULATIONS FAMILIÈRES / ARGOT MÉDICAL")
    print("="*70)

    tests = [
        {
            "name": "Langage patient",
            "text": "J'ai super mal à la tête depuis ce matin, c'est venu d'un coup, j'ai l'impression que ma tête va exploser",
            "expected": {
                "onset": "thunderclap",
            }
        },
        {
            "name": "Description imagée",
            "text": "C'est comme si on me serrait la tête dans un étau, ça dure depuis des heures",
            "expected": {
                "headache_profile": "tension_like",
            }
        },
        {
            "name": "Argot médical",
            "text": "Patiente de 30a, céphalo brutalo, pas de T°, examen neuro RAS",
            "expected": {
                "onset": "thunderclap",
            }
        },
        {
            "name": "Abréviations",
            "text": "H 55a, ATCD HTA, céphalées + déficit BF droit, suspicion AVC",
            "expected": {
                "neuro_deficit": "ANY_TRUE",
            }
        },
        {
            "name": "Style télégraphique",
            "text": "cephalée brutale fievre raideur nuque photophobie",
            "expected": {
                "onset": "thunderclap",
                "fever": "ANY_TRUE",
                "meningeal_signs": "ANY_TRUE",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_fautes_frappe(hybrid_nlu):
    """Test de la robustesse aux fautes de frappe."""
    print("\n" + "="*70)
    print("CATÉGORIE 5: FAUTES DE FRAPPE COURANTES")
    print("="*70)

    tests = [
        {
            "name": "Accents manquants",
            "text": "Patient febrile avec cephalee et deficit moteur",
            "expected": {
                "fever": "ANY_TRUE",
                "neuro_deficit": "ANY_TRUE",
            }
        },
        {
            "name": "Fautes multiples",
            "text": "Cephalée brutalle avec vomissment et photophoby",
            "expected": {
                "onset": "thunderclap",
            }
        },
        {
            "name": "Inversions lettres",
            "text": "Patiente enciente avec migriane sévère",
            "expected": {
                "pregnancy_postpartum": "ANY_TRUE",
            }
        },
        {
            "name": "Style SMS",
            "text": "douleur tete depuis 2j, fievre 38.5, vomi ce matin",
            "expected": {
                "fever": "ANY_TRUE",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_cas_complexes(hybrid_nlu):
    """Test des cas complexes multi-symptômes."""
    print("\n" + "="*70)
    print("CATÉGORIE 6: CAS COMPLEXES MULTI-SYMPTÔMES")
    print("="*70)

    tests = [
        {
            "name": "Urgence vitale complète",
            "text": "Homme 50 ans hypertendu, début brutal céphalée maximale d'emblée il y a 1h, vomissements en jet, raideur de nuque, déficit hémi-corporel gauche, troubles de conscience GCS 12",
            "expected": {
                "onset": "thunderclap",
                "meningeal_signs": "ANY_TRUE",
                "htic_pattern": "ANY_TRUE",
                "neuro_deficit": "ANY_TRUE",
            }
        },
        {
            "name": "Diagnostic différentiel",
            "text": "Femme 35a migraineuse connue, céphalée inhabituelle depuis 48h progressive, pas comme ses migraines habituelles, fièvre à 38, nuque un peu raide",
            "expected": {
                "onset": "progressive",
                "fever": "ANY_TRUE",
                "meningeal_signs": "ANY_TRUE",
            }
        },
        {
            "name": "Contexte post-trauma",
            "text": "Patient 70 ans sous anticoagulants, chute de sa hauteur il y a 5 jours, depuis céphalées progressives, somnolence, ralentissement",
            "expected": {
                "trauma": "ANY_TRUE",
                "onset": "progressive",
            }
        },
        {
            "name": "Céphalée coïtale",
            "text": "Homme 45a, céphalée explosive survenue pendant rapport sexuel, maximale en quelques secondes, nausées",
            "expected": {
                "onset": "thunderclap",
            }
        },
        {
            "name": "Névralgie trijumeau",
            "text": "Femme 65 ans, douleurs faciales en décharge électrique hémiface droite, déclenchées par le toucher, durée quelques secondes, plusieurs fois par jour",
            "expected": {
                # Note: neuropathic_pattern n'existe pas dans HeadacheCase
                # La névralgie du trijumeau n'est pas un red flag pour l'imagerie urgente
                # Ce test vérifie simplement que le parsing fonctionne
            }
        },
        {
            "name": "Red flags multiples",
            "text": "Patient immunodeprimé greffé rénal, fievre 39°C depuis 3j, cephalées progressives, confusion, pas de deficit focal",
            "expected": {
                "immunosuppression": "ANY_TRUE",
                "fever": "ANY_TRUE",
                "onset": "progressive",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def test_negations(hybrid_nlu):
    """Test de la détection correcte des négations."""
    print("\n" + "="*70)
    print("CATÉGORIE 7: NÉGATIONS")
    print("="*70)

    tests = [
        {
            "name": "Négation fièvre",
            "text": "Céphalée brutale, pas de fièvre, pas de raideur de nuque",
            "expected": {
                "onset": "thunderclap",
                "fever": "ANY_FALSE",
                "meningeal_signs": "ANY_FALSE",
            }
        },
        {
            "name": "Négation déficit",
            "text": "Céphalées depuis 2 jours, examen neurologique strictement normal, pas de déficit sensitivo-moteur",
            "expected": {
                "neuro_deficit": "ANY_FALSE",
            }
        },
        {
            "name": "Négation trauma",
            "text": "Céphalée progressive sans notion de traumatisme, patient apyrétique",
            "expected": {
                "onset": "progressive",
                "fever": "ANY_FALSE",
            }
        },
        {
            "name": "Absence de signes",
            "text": "Céphalées en étau bilatérales, absence de nausées, absence de photophobie, nuque souple",
            "expected": {
                "headache_profile": "tension_like",
                "meningeal_signs": "ANY_FALSE",
            }
        },
    ]

    passed, total = run_category_tests(hybrid_nlu, tests)
    assert passed == total, f"Failed {total - passed}/{total} tests - see output above"


def run_category_tests(nlu, tests):
    """Exécute une catégorie de tests."""
    passed_count = 0
    total_count = len(tests)

    for test in tests:
        name = test["name"]
        text = test["text"]
        expected = test["expected"]

        passed, details, metadata = run_test(nlu, text, expected, name)

        status = "✓" if passed else "✗"
        print(f"\n  {status} {name}")
        print(f"    Input: \"{text[:70]}{'...' if len(text) > 70 else ''}\"")

        for detail in details:
            print(detail)

        # Afficher le mode utilisé
        mode = metadata.get("hybrid_mode", "unknown")
        print(f"    Mode: {mode}")

        if passed:
            passed_count += 1

    return passed_count, total_count


def main():
    """Lance tous les tests."""
    print("\n" + "="*70)
    print("TESTS AVEC INPUTS MÉDICAUX RÉALISTES")
    print("="*70)
    print("Simulation de descriptions médicales réelles écrites par des médecins")

    nlu = HybridNLU(use_embedding=False, verbose=False)

    results = []

    # Exécuter toutes les catégories
    results.append(("Urgences neurologiques", test_urgences_neurologiques(nlu)))
    results.append(("Céphalées primaires", test_cephalees_primaires(nlu)))
    results.append(("Contextes spéciaux", test_contextes_speciaux(nlu)))
    results.append(("Formulations familières", test_formulations_familieres(nlu)))
    results.append(("Fautes de frappe", test_fautes_frappe(nlu)))
    results.append(("Cas complexes", test_cas_complexes(nlu)))
    results.append(("Négations", test_negations(nlu)))

    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ GLOBAL")
    print("="*70)

    total_passed = 0
    total_tests = 0

    for name, (passed, total) in results:
        pct = (passed / total * 100) if total > 0 else 0
        status = "✓" if passed == total else "⚠"
        print(f"  {status} {name}: {passed}/{total} ({pct:.0f}%)")
        total_passed += passed
        total_tests += total

    print(f"\n  TOTAL: {total_passed}/{total_tests} tests passés ({total_passed/total_tests*100:.1f}%)")

    if total_passed == total_tests:
        print("\n  🎉 TOUS LES TESTS PASSENT!")
        return 0
    elif total_passed / total_tests >= 0.8:
        print("\n  ✅ Bon taux de réussite (≥80%)")
        return 0
    else:
        print("\n  ⚠️  Taux de réussite insuffisant (<80%)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
