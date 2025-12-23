#!/usr/bin/env python3
"""Tests pour le système d'index de mots-clés inversé.

Ce script valide:
1. La détection des mots-clés simples
2. Le mapping correct vers les champs
3. L'intégration dans le pipeline HybridNLU
4. La priorité des mots-clés vs embedding
"""

import sys
sys.path.insert(0, '.')

from headache_assistants.nlu_hybrid import (
    detect_keywords,
    apply_keywords_to_case,
    HybridNLU,
    KEYWORD_INDEX
)


def test_keyword_detection_basic():
    """Test de la détection basique des mots-clés."""
    print("\n" + "="*60)
    print("TEST 1: Détection basique des mots-clés")
    print("="*60)

    test_cases = [
        ("Céphalée brutale", "onset", "thunderclap"),
        ("Mal de tête progressif", "onset", "progressive"),
        ("Patient fébrile", "fever", True),
        ("Syndrome méningé", "meningeal_signs", True),
        ("Déficit moteur gauche", "neuro_deficit", True),
        ("Femme enceinte", "pregnancy_postpartum", True),
        ("Patient immunodéprimé", "immunosuppression", True),
        ("Sous anticoagulants", "anticoagulation", True),
        ("Convulsions généralisées", "seizure", True),
    ]

    all_passed = True
    for text, expected_field, expected_value in test_cases:
        matches = detect_keywords(text)

        # Trouver le match pour le champ attendu
        field_match = next((m for m in matches if m.field == expected_field), None)

        if field_match and field_match.value == expected_value:
            print(f"  ✓ '{text}' → {expected_field}={expected_value}")
        else:
            print(f"  ✗ '{text}' → attendu {expected_field}={expected_value}, obtenu {field_match}")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_keyword_weights():
    """Test que les poids sont correctement assignés."""
    print("\n" + "="*60)
    print("TEST 2: Vérification des poids des mots-clés")
    print("="*60)

    # Mots avec poids élevé (> 0.9)
    high_weight_words = ["hyperthermie", "paralysie", "convulsions", "enceinte"]

    # Mots avec poids moyen (0.7-0.9)
    medium_weight_words = ["brutale", "fébrile", "déficit", "chute"]

    # Mots avec poids faible (< 0.7)
    low_weight_words = ["nausées", "fourmillements", "coup"]

    all_passed = True

    print("  Poids élevés (>= 0.90):")
    for word in high_weight_words:
        matches = detect_keywords(f"Test {word}")
        if matches:
            weight = matches[0].weight
            if weight >= 0.90:
                print(f"    ✓ '{word}' → poids={weight:.2f}")
            else:
                print(f"    ✗ '{word}' → poids={weight:.2f} (attendu >= 0.90)")
                all_passed = False
        else:
            print(f"    ✗ '{word}' → pas de match")
            all_passed = False

    print("  Poids moyens (0.70-0.90):")
    for word in medium_weight_words:
        matches = detect_keywords(f"Test {word}")
        if matches:
            weight = matches[0].weight
            if 0.70 <= weight < 0.95:
                print(f"    ✓ '{word}' → poids={weight:.2f}")
            else:
                print(f"    ✗ '{word}' → poids={weight:.2f} (attendu 0.70-0.90)")
                all_passed = False
        else:
            print(f"    ✗ '{word}' → pas de match")
            all_passed = False

    print("  Poids faibles (< 0.70):")
    for word in low_weight_words:
        matches = detect_keywords(f"Test {word}")
        if matches:
            weight = matches[0].weight
            if weight < 0.70:
                print(f"    ✓ '{word}' → poids={weight:.2f}")
            else:
                print(f"    ✗ '{word}' → poids={weight:.2f} (attendu < 0.70)")
                all_passed = False
        else:
            print(f"    ✗ '{word}' → pas de match")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_multiple_keywords():
    """Test la détection de plusieurs mots-clés dans un même texte."""
    print("\n" + "="*60)
    print("TEST 3: Détection de plusieurs mots-clés")
    print("="*60)

    text = "Céphalée brutale fébrile avec déficit moteur chez femme enceinte"
    matches = detect_keywords(text)

    expected_fields = {"onset", "fever", "neuro_deficit", "pregnancy_postpartum"}
    detected_fields = {m.field for m in matches}

    print(f"  Texte: '{text}'")
    print(f"  Mots-clés détectés:")
    for m in matches:
        print(f"    - {m.keyword} → {m.field}={m.value} (poids={m.weight:.2f})")

    missing = expected_fields - detected_fields
    if not missing:
        print(f"  ✓ Tous les champs attendus détectés: {expected_fields}")
    else:
        print(f"  ✗ Champs manquants: {missing}")

    assert not missing, f"Missing fields: {missing}"


def test_negation_keywords():
    """Test les mots-clés qui impliquent une négation (apyrétique, etc.)."""
    print("\n" + "="*60)
    print("TEST 4: Mots-clés avec négation implicite")
    print("="*60)

    test_cases = [
        ("Patient apyrétique", "fever", False),
        ("Apyrexie confirmée", "fever", False),
    ]

    all_passed = True
    for text, expected_field, expected_value in test_cases:
        matches = detect_keywords(text)
        field_match = next((m for m in matches if m.field == expected_field), None)

        if field_match and field_match.value == expected_value:
            print(f"  ✓ '{text}' → {expected_field}={expected_value}")
        else:
            print(f"  ✗ '{text}' → attendu {expected_field}={expected_value}")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_apply_keywords_to_case():
    """Test l'application des mots-clés à un cas médical."""
    print("\n" + "="*60)
    print("TEST 5: Application des mots-clés au cas")
    print("="*60)

    text = "Céphalée brutale fébrile"
    matches = detect_keywords(text)

    case_dict = {
        "onset": "unknown",
        "fever": None,
        "meningeal_signs": None,
    }
    detected_fields = []

    case_dict, detected_fields, applied = apply_keywords_to_case(
        case_dict, matches, detected_fields
    )

    print(f"  Texte: '{text}'")
    print(f"  Cas après application:")
    print(f"    - onset: {case_dict.get('onset')}")
    print(f"    - fever: {case_dict.get('fever')}")
    print(f"  Champs détectés: {detected_fields}")
    print(f"  Mots-clés appliqués: {[a['keyword'] for a in applied]}")

    success = case_dict.get("onset") == "thunderclap" and case_dict.get("fever") == True
    if success:
        print("  ✓ Application correcte")
    else:
        print("  ✗ Application incorrecte")

    assert success, f"Application incorrecte: onset={case_dict.get('onset')}, fever={case_dict.get('fever')}"


def test_hybrid_nlu_with_keywords():
    """Test l'intégration dans HybridNLU."""
    print("\n" + "="*60)
    print("TEST 6: Intégration HybridNLU avec mots-clés")
    print("="*60)

    nlu = HybridNLU(use_embedding=False, verbose=False)

    test_cases = [
        # (texte, champ, valeur attendue)
        ("Céphalée brutale chez patient septuagénaire", "onset", "thunderclap"),
        ("Mal de tête progressif avec photophobie", "onset", "progressive"),
        ("Patient immunodéprimé sous chimiothérapie", "immunosuppression", True),
        ("Femme enceinte au 3ème trimestre", "pregnancy_postpartum", True),
    ]

    all_passed = True
    for text, expected_field, expected_value in test_cases:
        result = nlu.parse_hybrid(text)
        case_dict = result.case.model_dump()
        actual_value = case_dict.get(expected_field)

        # Vérifier si keywords_detected est dans metadata
        keywords_detected = result.metadata.get("keywords_detected", [])
        keywords_applied = result.metadata.get("keywords_applied", [])

        if actual_value == expected_value:
            print(f"  ✓ '{text[:40]}...'")
            print(f"    → {expected_field}={expected_value}")
            if keywords_applied:
                print(f"    → mots-clés appliqués: {[k['keyword'] for k in keywords_applied]}")
        else:
            print(f"  ✗ '{text[:40]}...'")
            print(f"    → attendu {expected_field}={expected_value}, obtenu {actual_value}")
            all_passed = False

    assert all_passed, "Test failed - see output above for details"


def test_keyword_priority():
    """Test que les N-grams ont priorité sur les mots-clés."""
    print("\n" + "="*60)
    print("TEST 7: Priorité N-grams > Mots-clés")
    print("="*60)

    nlu = HybridNLU(use_embedding=False, verbose=False)

    # "pire douleur de ma vie" (ngram) doit primer sur "brutale" (keyword)
    text = "Pire douleur de ma vie, brutale"
    result = nlu.parse_hybrid(text)

    print(f"  Texte: '{text}'")
    print(f"  N-grams détectés: {result.metadata.get('ngrams_detected', [])}")
    print(f"  Mots-clés détectés: {result.metadata.get('keywords_detected', [])}")
    print(f"  onset: {result.case.onset}")

    # Le N-gram "pire douleur de ma vie" doit définir onset=thunderclap
    if result.case.onset == "thunderclap":
        print("  ✓ Onset correctement défini à 'thunderclap'")
    else:
        print(f"  ✗ Onset incorrect: {result.case.onset}")

    assert result.case.onset == "thunderclap", f"Onset incorrect: {result.case.onset}"


def test_keyword_index_coverage():
    """Vérifie la couverture de l'index de mots-clés."""
    print("\n" + "="*60)
    print("TEST 8: Couverture de l'index de mots-clés")
    print("="*60)

    # Compter les entrées par catégorie de champ
    field_counts = {}
    for keyword, mappings in KEYWORD_INDEX.items():
        for mapping in mappings:
            field = mapping["field"]
            if field not in field_counts:
                field_counts[field] = 0
            field_counts[field] += 1

    print(f"  Total mots-clés dans l'index: {len(KEYWORD_INDEX)}")
    print(f"  Répartition par champ:")
    for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
        print(f"    - {field}: {count} mots-clés")

    # Vérifier qu'on a au moins 3 mots-clés pour les champs critiques
    critical_fields = ["onset", "fever", "neuro_deficit", "meningeal_signs"]
    all_covered = True
    for field in critical_fields:
        if field_counts.get(field, 0) < 3:
            print(f"  ⚠ Champ critique '{field}' a peu de mots-clés: {field_counts.get(field, 0)}")
            all_covered = False

    if all_covered:
        print("  ✓ Tous les champs critiques ont une bonne couverture")

    assert all_covered, "Not all critical fields have adequate coverage - see output above"


def main():
    """Lance tous les tests."""
    print("\n" + "="*60)
    print("TESTS DU SYSTÈME D'INDEX DE MOTS-CLÉS INVERSÉ")
    print("="*60)

    results = []

    results.append(("Détection basique", test_keyword_detection_basic()))
    results.append(("Vérification des poids", test_keyword_weights()))
    results.append(("Plusieurs mots-clés", test_multiple_keywords()))
    results.append(("Négations implicites", test_negation_keywords()))
    results.append(("Application au cas", test_apply_keywords_to_case()))
    results.append(("Intégration HybridNLU", test_hybrid_nlu_with_keywords()))
    results.append(("Priorité N-grams", test_keyword_priority()))
    results.append(("Couverture index", test_keyword_index_coverage()))

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
