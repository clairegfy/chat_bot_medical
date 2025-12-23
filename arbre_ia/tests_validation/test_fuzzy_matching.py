#!/usr/bin/env python3
"""Tests pour le système de fuzzy matching / correction orthographique.

Ce script valide:
1. La distance de Levenshtein
2. La correction des fautes de frappe courantes
3. L'intégration dans le pipeline HybridNLU
4. La préservation du sens médical après correction
"""

import sys
sys.path.insert(0, '.')

from headache_assistants.nlu_hybrid import (
    levenshtein_distance,
    similarity_ratio,
    fuzzy_correct_text,
    apply_fuzzy_corrections,
    HybridNLU,
    CRITICAL_MEDICAL_TERMS
)


def test_levenshtein_distance():
    """Test de la distance de Levenshtein."""
    print("\n" + "="*60)
    print("TEST 1: Distance de Levenshtein")
    print("="*60)

    test_cases = [
        # (s1, s2, expected_distance)
        ("", "", 0),
        ("a", "", 1),
        ("", "a", 1),
        ("abc", "abc", 0),
        ("abc", "ab", 1),
        ("abc", "abd", 1),
        ("fievre", "fièvre", 1),  # Accent manquant
        ("cephalee", "céphalée", 2),  # 2 accents manquants
        ("brutal", "brutal", 0),
        ("brutale", "brutalle", 1),  # Lettre en trop
    ]

    all_passed = True
    for s1, s2, expected in test_cases:
        result = levenshtein_distance(s1, s2)
        if result == expected:
            print(f"  ✓ distance('{s1}', '{s2}') = {result}")
        else:
            print(f"  ✗ distance('{s1}', '{s2}') = {result} (attendu: {expected})")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_similarity_ratio():
    """Test du ratio de similarité."""
    print("\n" + "="*60)
    print("TEST 2: Ratio de similarité")
    print("="*60)

    test_cases = [
        # (s1, s2, min_expected_similarity)
        ("fievre", "fièvre", 0.80),
        ("cephalee", "céphalée", 0.70),
        ("brutale", "brutale", 1.0),
        ("meningite", "méningite", 0.85),
        ("convulsions", "convulsion", 0.90),
        ("completement", "céphalée", 0.0),  # Mots différents
    ]

    all_passed = True
    for s1, s2, min_sim in test_cases:
        result = similarity_ratio(s1, s2)
        if result >= min_sim:
            print(f"  ✓ similarity('{s1}', '{s2}') = {result:.2f} (>= {min_sim})")
        else:
            print(f"  ✗ similarity('{s1}', '{s2}') = {result:.2f} (attendu >= {min_sim})")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_fuzzy_correction_basic():
    """Test de la correction basique des fautes."""
    print("\n" + "="*60)
    print("TEST 3: Correction orthographique basique")
    print("="*60)

    test_cases = [
        # (input_text, expected_corrections)
        ("Patient avec fievre", [("fievre", "fièvre")]),
        ("Cephalee brutale", [("cephalee", "céphalée")]),
        ("Syndrome meningé", [("meningé", "méningé")]),
        ("Deficit moteur", [("deficit", "déficit")]),
        ("Patient febrile", [("febrile", "fébrile")]),
    ]

    all_passed = True
    for input_text, expected_corrections in test_cases:
        corrected, matches = fuzzy_correct_text(input_text)

        # Vérifier que les corrections attendues sont présentes
        actual_corrections = [(m.original, m.corrected) for m in matches]

        for expected in expected_corrections:
            if expected in actual_corrections:
                print(f"  ✓ '{input_text}' → '{expected[0]}' corrigé en '{expected[1]}'")
            else:
                print(f"  ✗ '{input_text}' → correction '{expected}' non trouvée")
                print(f"      Corrections trouvées: {actual_corrections}")
                all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_no_false_positives():
    """Test qu'on ne corrige pas les mots corrects."""
    print("\n" + "="*60)
    print("TEST 4: Pas de faux positifs")
    print("="*60)

    # Ces textes ne doivent PAS être modifiés
    correct_texts = [
        "Patient avec fièvre",
        "Céphalée brutale",
        "Syndrome méningé",
        "Déficit moteur",
        "Patient fébrile",
        "Convulsions généralisées",
        "Femme enceinte",
    ]

    all_passed = True
    for text in correct_texts:
        corrected, matches = fuzzy_correct_text(text)

        if not matches:
            print(f"  ✓ '{text}' → pas de correction (correct)")
        else:
            print(f"  ✗ '{text}' → corrections non désirées: {[(m.original, m.corrected) for m in matches]}")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_multiple_corrections():
    """Test avec plusieurs fautes dans le même texte."""
    print("\n" + "="*60)
    print("TEST 5: Corrections multiples")
    print("="*60)

    text = "Patient febrile avec cephalee et deficit moteur"
    corrected, matches = fuzzy_correct_text(text)

    print(f"  Texte original: '{text}'")
    print(f"  Texte corrigé:  '{corrected}'")
    print(f"  Corrections effectuées:")
    for m in matches:
        print(f"    - '{m.original}' → '{m.corrected}' (sim={m.similarity:.2f})")

    # Vérifier qu'on a au moins 2 corrections
    assert len(matches) >= 2, f"Seulement {len(matches)} correction(s), attendu >= 2"
    print(f"  ✓ {len(matches)} corrections effectuées")


def test_case_preservation():
    """Test que la casse est préservée."""
    print("\n" + "="*60)
    print("TEST 6: Préservation de la casse")
    print("="*60)

    test_cases = [
        ("Fievre élevée", "Fièvre"),  # Majuscule préservée
        ("FIEVRE", "Fièvre"),  # Majuscule au début préservée
        ("fievre", "fièvre"),  # Minuscule préservée
    ]

    all_passed = True
    for input_text, expected_word in test_cases:
        corrected, _ = fuzzy_correct_text(input_text)

        if expected_word.lower() in corrected.lower():
            print(f"  ✓ '{input_text}' → '{corrected}'")
        else:
            print(f"  ✗ '{input_text}' → '{corrected}' (attendu: '{expected_word}')")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_hybrid_nlu_integration():
    """Test de l'intégration dans HybridNLU."""
    print("\n" + "="*60)
    print("TEST 7: Intégration HybridNLU")
    print("="*60)

    nlu = HybridNLU(use_embedding=False, verbose=False)

    test_cases = [
        # (texte avec fautes, champ attendu, valeur attendue)
        ("Cephalee brutale", "onset", "thunderclap"),
        ("Patient febrile", "fever", True),
        ("Deficit moteur gauche", "neuro_deficit", True),
    ]

    all_passed = True
    for text, expected_field, expected_value in test_cases:
        result = nlu.parse_hybrid(text)
        case_dict = result.case.model_dump()
        actual_value = case_dict.get(expected_field)

        # Vérifier les corrections dans metadata
        fuzzy_corrections = result.metadata.get("fuzzy_corrections", [])

        if actual_value == expected_value:
            print(f"  ✓ '{text}' → {expected_field}={expected_value}")
            if fuzzy_corrections:
                print(f"      Corrections: {[c['original'] + '→' + c['corrected'] for c in fuzzy_corrections]}")
        else:
            print(f"  ✗ '{text}' → {expected_field}={actual_value} (attendu: {expected_value})")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_metadata_includes_corrections():
    """Test que les métadonnées incluent les corrections."""
    print("\n" + "="*60)
    print("TEST 8: Métadonnées de correction")
    print("="*60)

    nlu = HybridNLU(use_embedding=False, verbose=False)

    text = "Patient avec fievre et cephalee"
    result = nlu.parse_hybrid(text)

    fuzzy_corrections = result.metadata.get("fuzzy_corrections", [])
    original_text = result.metadata.get("original_text")
    corrected_text = result.metadata.get("corrected_text")

    print(f"  Texte original:  '{text}'")
    print(f"  Texte corrigé:   '{corrected_text}'")
    print(f"  Corrections: {len(fuzzy_corrections)}")

    all_passed = True

    if fuzzy_corrections:
        print("  ✓ fuzzy_corrections présent dans metadata")
        for c in fuzzy_corrections:
            print(f"      - {c['original']} → {c['corrected']} (sim={c['similarity']})")
    else:
        print("  ✗ fuzzy_corrections absent ou vide")
        all_passed = False

    if original_text == text:
        print("  ✓ original_text correct")
    else:
        print(f"  ✗ original_text incorrect: '{original_text}'")
        all_passed = False

    if corrected_text and corrected_text != text:
        print("  ✓ corrected_text différent de l'original")
    else:
        print("  ✗ corrected_text non modifié")
        all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_critical_terms_coverage():
    """Vérifie la couverture du dictionnaire de termes médicaux."""
    print("\n" + "="*60)
    print("TEST 9: Couverture des termes médicaux")
    print("="*60)

    print(f"  Total termes médicaux: {len(CRITICAL_MEDICAL_TERMS)}")

    # Vérifier les catégories
    categories = {
        "onset": ["brutale", "soudaine", "progressive"],
        "fever": ["fièvre", "fébrile", "hyperthermie"],
        "neuro": ["déficit", "paralysie", "aphasie"],
        "meningeal": ["méningé", "méningite", "photophobie"],
    }

    all_covered = True
    for category, terms in categories.items():
        covered = [t for t in terms if t in CRITICAL_MEDICAL_TERMS]
        print(f"  {category}: {len(covered)}/{len(terms)} termes couverts")
        if len(covered) < len(terms):
            missing = [t for t in terms if t not in CRITICAL_MEDICAL_TERMS]
            print(f"      Manquants: {missing}")
            all_covered = False

    if all_covered:
        print("  ✓ Toutes les catégories critiques couvertes")

    assert all_covered, "Not all critical categories are covered - see output above"


def main():
    """Lance tous les tests."""
    print("\n" + "="*60)
    print("TESTS DU SYSTÈME DE FUZZY MATCHING (v6)")
    print("="*60)

    results = []

    results.append(("Distance Levenshtein", test_levenshtein_distance()))
    results.append(("Ratio similarité", test_similarity_ratio()))
    results.append(("Correction basique", test_fuzzy_correction_basic()))
    results.append(("Pas de faux positifs", test_no_false_positives()))
    results.append(("Corrections multiples", test_multiple_corrections()))
    results.append(("Préservation casse", test_case_preservation()))
    results.append(("Intégration HybridNLU", test_hybrid_nlu_integration()))
    results.append(("Métadonnées correction", test_metadata_includes_corrections()))
    results.append(("Couverture termes", test_critical_terms_coverage()))

    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passés")

    if passed == total:
        print("\n  🎉 TOUS LES TESTS PASSENT!")
        return 0
    else:
        print("\n  ⚠️  Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())
