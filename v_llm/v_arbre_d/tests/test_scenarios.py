#!/usr/bin/env python3
"""Tests de scénarios cliniques réels."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from main import (
    _load_system_entries, 
    _normalize_key, 
    _normalize_text,
    _match_best_entry,
    analyse_texte_medical
)

# Scénarios de test avec entrée texte et résultat attendu
SCENARIOS_THORAX = [
    {
        "nom": "Toux chronique simple",
        "texte": "patient 55 ans, toux chronique depuis 2 mois, fumeur",
        "expected_contains": "radiographie thoracique",
        "expected_id": "thorax_toux_adulte_rx_face_v1"
    },
    {
        "nom": "Dyspnée aiguë avec suspicion EP",
        "texte": "femme 40 ans dyspnée aiguë, tachycardie, suspicion embolie pulmonaire",
        "expected_contains": "angioscanner",
        "expected_id": "thorax_dyspnee_aigue_adulte_ct_ou_angioct_v1"
    },
    {
        "nom": "Hémoptysie",
        "texte": "homme 60 ans hémoptysie massive",
        "expected_contains": "angioscanner thoracique",
        "expected_id": "thorax_hemoptysie_angioct_v1"
    },
    {
        "nom": "Enfant avec dyspnée et suspicion corps étranger",
        "texte": "enfant 5 ans dyspnée expiratoire aiguë, fièvre, suspicion corps étranger",
        "expected_contains": "radiographie thoracique",
        "expected_id": "thorax_dyspnee_aigue_enfant_rx_v1"
    },
    {
        "nom": "Douleur thoracique adulte urgence",
        "texte": "homme 50 ans douleur thoracique aiguë transfixiante instabilité hémodynamique",
        "expected_contains": "scanner thoracique ou angioscanner",
        "expected_id": "thorax_douleur_adulte_ct_ou_angioct_v1"
    },
    {
        "nom": "Bruits respiratoires anormaux - radio simple",
        "texte": "patiente 22 ans bruits respiratoires anormaux sibilants",
        "expected_contains": "radiographie thoracique de face",
        "expected_id": "thorax_bruits_anormaux_rx_face_v1"
    },
    {
        "nom": "Bruits respiratoires avec anomalie radio existante",
        "texte": "patient 45 ans bruits respiratoires anormaux, anomalie non caractérisée à la radio, radiographie non contributive",
        "expected_contains": "scanner thoracique sans injection",
        "expected_id": "thorax_bruits_anormaux_ct_sans_injection_v1"
    }
]

SCENARIOS_DIGESTIF = [
    {
        "nom": "Appendicite enfant",
        "texte": "enfant 10 ans douleur fosse iliaque droite mal au ventre",
        "expected_contains": "échographie abdominale",
        "expected_id": "abdomen_appendicite_enfant_v2"
    },
    {
        "nom": "Appendicite adulte",
        "texte": "homme 35 ans douleur FID fièvre suspicion appendicite",
        "expected_contains": "échographie-Doppler abdominopelvienne",
        "expected_id": "abdomen_appendicite_adulte_v1"
    },
    {
        "nom": "Appendicite grossesse",
        "texte": "femme 28 ans enceinte grossesse douleur FID",
        "expected_contains": "IRM abdominopelvienne",
        "expected_id": "abdomen_appendicite_grossesse_v1"
    },
    {
        "nom": "Diverticulite",
        "texte": "homme 65 ans douleur abdominale suspicion de diverticulite",
        "expected_contains": "scanner abdominopelvien avec injection",
        "expected_id": "abdomen_diverticulite_v1"
    },
    {
        "nom": "Cancer du côlon",
        "texte": "patient 70 ans cancer colique bilan d'extension",
        "expected_contains": "scanner thoracoabdominopelvien avec injection",
        "expected_id": "abdomen_cancer_colon_v1"
    },
    {
        "nom": "Lithiase vésiculaire",
        "texte": "femme 50 ans colique hépatique cholécystite",
        "expected_contains": "échographie-Doppler foie-voies biliaires-pancréas",
        "expected_id": "abdomen_lithiase_vesiculaire_v1"
    },
    {
        "nom": "Cirrhose avec nodule",
        "texte": "patient 60 ans cirrhose suivi hépatopathie chronique",
        "expected_contains": "échographie-Doppler abdominale",
        "expected_id": "abdomen_cirrhose_v1"
    }
]

def test_scenario(scenario, system):
    """Teste un scénario clinique."""
    texte = scenario['texte']
    expected_id = scenario['expected_id']
    expected_contains = scenario['expected_contains']
    
    # Analyser
    f = analyse_texte_medical(texte)
    
    # Charger toutes les entrées
    entries = _load_system_entries(system)
    
    # Créer le mapping
    all_items_map = {}
    for e in entries:
        for fld in ("symptomes", "indications_positives"):
            for s in (e.get(fld) or []):
                key = _normalize_key(s)
                all_items_map[key] = s
    
    # Simuler les réponses positives
    t_norm = _normalize_text(texte)
    positives = set()
    
    for key, original_label in all_items_map.items():
        label_normalized = _normalize_text(original_label)
        label_words = [w for w in label_normalized.split() if len(w) > 2]
        
        matched = False
        if len(label_words) == 0:
            matched = False
        elif len(label_words) == 1:
            matched = label_words[0] in t_norm
        else:
            matches = sum(1 for w in label_words if w in t_norm)
            matched = matches >= max(2, len(label_words) * 0.5)
        
        if matched:
            positives.add(key)
    
    # Trouver la meilleure correspondance
    best, score = _match_best_entry(entries, positives, f)
    
    if best:
        actual_id = best.get('id')
        actual_modality = best.get('modalite')
        
        # Vérifications
        id_match = (actual_id == expected_id)
        modality_match = (expected_contains.lower() in actual_modality.lower())
        
        return {
            'success': id_match and modality_match,
            'id_match': id_match,
            'modality_match': modality_match,
            'nom': scenario['nom'],
            'expected_id': expected_id,
            'actual_id': actual_id,
            'expected_modality': expected_contains,
            'actual_modality': actual_modality,
            'score': score
        }
    else:
        return {
            'success': False,
            'id_match': False,
            'modality_match': False,
            'nom': scenario['nom'],
            'expected_id': expected_id,
            'actual_id': "AUCUNE",
            'expected_modality': expected_contains,
            'actual_modality': "AUCUNE",
            'score': 0
        }

def run_scenario_tests(scenarios, system):
    """Lance tous les tests de scénarios."""
    print("=" * 80)
    print(f"TESTS DE SCÉNARIOS CLINIQUES - {system.upper()}")
    print("=" * 80)
    print(f"\n{len(scenarios)} scénarios à tester\n")
    
    results = []
    for scenario in scenarios:
        result = test_scenario(scenario, system)
        results.append(result)
        
        # Affichage immédiat
        status = "✓" if result['success'] else "✗"
        print(f"{status} {result['nom']}")
        if not result['success']:
            if not result['id_match']:
                print(f"    ID: attendu {result['expected_id']}, obtenu {result['actual_id']}")
            if not result['modality_match']:
                print(f"    Modalité: attendu '{result['expected_modality']}'")
                print(f"              obtenu '{result['actual_modality']}'")
    
    # Statistiques
    successes = sum(1 for r in results if r['success'])
    success_rate = (successes / len(results) * 100) if results else 0
    
    print("\n" + "=" * 80)
    print("RÉSULTATS")
    print("=" * 80)
    print(f"Total: {len(results)}")
    print(f"✓ Succès: {successes} ({success_rate:.1f}%)")
    print(f"✗ Échecs: {len(results) - successes}")
    
    return results

if __name__ == "__main__":
    print("\n")
    
    # Tests thorax
    results_thorax = run_scenario_tests(SCENARIOS_THORAX, "thorax")
    
    print("\n\n")
    
    # Tests digestif
    results_digestif = run_scenario_tests(SCENARIOS_DIGESTIF, "digestif")
    
    # Résumé global
    total_tests = len(results_thorax) + len(results_digestif)
    total_success = sum(1 for r in results_thorax + results_digestif if r['success'])
    global_rate = (total_success / total_tests * 100) if total_tests else 0
    
    print("\n" + "=" * 80)
    print("RÉSUMÉ GLOBAL")
    print("=" * 80)
    print(f"Total: {total_tests} tests")
    print(f"✓ Succès: {total_success} ({global_rate:.1f}%)")
    print(f"✗ Échecs: {total_tests - total_success}")
    print("=" * 80)
    
    # Code de sortie
    sys.exit(0 if global_rate >= 90 else 1)
