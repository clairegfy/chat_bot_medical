#!/usr/bin/env python3
"""Tests automatisés pour le système thorax."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

import json
from main import (
    _load_system_entries, 
    _normalize_key, 
    _normalize_text,
    _match_best_entry,
    analyse_texte_medical
)

def test_entry(entry, system="thorax"):
    """Teste qu'une entrée JSON produit la bonne recommandation."""
    entry_id = entry.get('id')
    expected_modality = entry.get('modalite')
    
    # Construire un texte libre avec tous les symptômes et indications positives
    symptoms = entry.get('symptomes', [])
    indications = entry.get('indications_positives', [])
    
    # Créer un texte simulé
    text_parts = ["patient 30 ans"]
    text_parts.extend(symptoms[:3])  # Prendre les 3 premiers symptômes
    if indications:
        text_parts.extend(indications[:2])  # Prendre 2 indications
    
    texte = ", ".join(text_parts)
    
    # Analyser
    f = analyse_texte_medical(texte)
    
    # Charger toutes les entrées
    entries = _load_system_entries(system)
    
    # Créer le mapping des symptômes/indications
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
        actual_modality = best.get('modalite')
        actual_id = best.get('id')
        
        # Vérifier si c'est la bonne entrée
        success = (actual_id == entry_id)
        
        return {
            'success': success,
            'entry_id': entry_id,
            'expected_modality': expected_modality,
            'actual_modality': actual_modality,
            'actual_id': actual_id,
            'score': score,
            'positives_count': len(positives),
            'text': texte[:80] + "..." if len(texte) > 80 else texte
        }
    else:
        return {
            'success': False,
            'entry_id': entry_id,
            'expected_modality': expected_modality,
            'actual_modality': "AUCUNE",
            'actual_id': "AUCUNE",
            'score': 0,
            'positives_count': len(positives),
            'text': texte[:80] + "..." if len(texte) > 80 else texte
        }

def run_tests(system="thorax"):
    """Lance tous les tests pour un système."""
    print("=" * 80)
    print(f"TESTS AUTOMATISÉS - {system.upper()}")
    print("=" * 80)
    
    entries = _load_system_entries(system)
    print(f"\n{len(entries)} entrées à tester\n")
    
    results = []
    for entry in entries:
        result = test_entry(entry, system)
        results.append(result)
    
    # Statistiques
    successes = sum(1 for r in results if r['success'])
    failures = len(results) - successes
    success_rate = (successes / len(results) * 100) if results else 0
    
    print("\n" + "=" * 80)
    print("RÉSULTATS")
    print("=" * 80)
    print(f"Total: {len(results)}")
    print(f"✓ Succès: {successes} ({success_rate:.1f}%)")
    print(f"✗ Échecs: {failures}")
    
    if failures > 0:
        print("\n" + "-" * 80)
        print("ÉCHECS DÉTAILLÉS")
        print("-" * 80)
        for r in results:
            if not r['success']:
                print(f"\n✗ {r['entry_id']}")
                print(f"  Attendu: {r['expected_modality']}")
                print(f"  Obtenu:  {r['actual_modality']} (ID: {r['actual_id']})")
                print(f"  Score: {r['score']}, Positifs: {r['positives_count']}")
                print(f"  Texte: {r['text']}")
    
    # Afficher quelques succès pour vérification
    print("\n" + "-" * 80)
    print("EXEMPLES DE SUCCÈS (5 premiers)")
    print("-" * 80)
    success_examples = [r for r in results if r['success']][:5]
    for r in success_examples:
        print(f"\n✓ {r['entry_id']}")
        print(f"  Modalité: {r['expected_modality']}")
        print(f"  Score: {r['score']}, Positifs: {r['positives_count']}")
        print(f"  Texte: {r['text']}")
    
    return results

if __name__ == "__main__":
    import sys
    system = sys.argv[1] if len(sys.argv) > 1 else "thorax"
    results = run_tests(system)
    
    # Code de sortie basé sur le taux de réussite
    successes = sum(1 for r in results if r['success'])
    success_rate = (successes / len(results) * 100) if results else 0
    
    if success_rate >= 80:
        sys.exit(0)  # Succès
    else:
        sys.exit(1)  # Échec
