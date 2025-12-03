#!/usr/bin/env python3
"""
Tests de variations syntaxiques RÉELLES utilisées par médecins français.
Focus sur les abréviations, tournures, et formulations du langage médical quotidien.
"""

import sys
for m in list(sys.modules.keys()):
    if 'headache' in m:
        del sys.modules[m]

from headache_assistants.nlu import parse_free_text_to_case
from headache_assistants.models import HeadacheCase


# ==============================================================================
# VARIATIONS SYNTAXIQUES MÉDICALES FRANÇAISES
# ==============================================================================

TESTS_SYNTAXE = [
    # === FIÈVRE - Variations notation ===
    {
        'category': 'Fièvre - Notations',
        'cases': [
            ('T 38.5', {'fever': True}),
            ('T= 39', {'fever': True}),
            ('temp 39°', {'fever': True}),
            ('38°5', {'fever': True}),
            ('féb à 39', {'fever': True}),
            ('apyrétique', {'fever': False}),
            ('apyr', {'fever': False}),
            ('afébrile', {'fever': False}),
        ]
    },
    
    # === INTENSITÉ - Notations EVA/EN ===
    {
        'category': 'Intensité - Échelles',
        'cases': [
            ('EVA 8', {'intensity': 8}),
            ('EVA= 9/10', {'intensity': 9}),
            ('EN 7', {'intensity': 7}),  # Échelle Numérique
            ('douleur 9/10', {'intensity': 9}),
            ('8/10', {'intensity': 8}),
            ('insupportable', {'intensity': 10}),
            ('terrible', {'intensity': 9}),
            ('modérée', {'intensity': 5}),
            ('légère', {'intensity': 3}),
        ]
    },
    
    # === DÉBUT - Variations temporelles ===
    {
        'category': 'Début - Temporalité',
        'cases': [
            ('depuis 2j', {'profile': 'acute'}),
            ('dep 48h', {'profile': 'acute'}),
            ('il y a 3 jours', {'profile': 'acute'}),
            ('J-2', {'profile': 'acute'}),
            ('dep 2 sem', {'profile': 'subacute'}),
            ('depuis 10j', {'profile': 'subacute'}),
            ('depuis 6 mois', {'profile': 'chronic'}),
            ('chronique', {'profile': 'chronic'}),
            ('de longue date', {'profile': 'chronic'}),
        ]
    },
    
    # === DÉFICIT NEURO - Variations cliniques ===
    {
        'category': 'Déficit Neuro - Terminologie',
        'cases': [
            ('hémipar D', {'neuro_deficit': True}),
            ('hémiplégie G', {'neuro_deficit': True}),
            ('déficit MSD', {'neuro_deficit': True}),  # Membre Supérieur Droit
            ('déficit MSG', {'neuro_deficit': True}),  # Membre Supérieur Gauche
            ('déficit MID', {'neuro_deficit': True}),  # Membre Inférieur Droit
            ('déficit MIG', {'neuro_deficit': True}),  # Membre Inférieur Gauche
            ('faiblesse mb sup D', {'neuro_deficit': True}),
            ('PF centrale', {'neuro_deficit': True}),  # Paralysie Faciale
            ('PF périph', {'neuro_deficit': True}),
            ('diplopie', {'neuro_deficit': True}),
            ('vision double', {'neuro_deficit': True}),
            ('flou visuel', {'neuro_deficit': True}),
            ('scotomes', {'neuro_deficit': True}),
            ('confusion', {'neuro_deficit': True}),
            ('désorientation', {'neuro_deficit': True}),
            ('troubles mnésiques', {'neuro_deficit': True}),
            ('GCS 14', {'neuro_deficit': True}),  # Glasgow Coma Scale
            ('Glasgow 13', {'neuro_deficit': True}),
        ]
    },
    
    # === SIGNES MÉNINGÉS - Variations examen ===
    {
        'category': 'Signes Méningés - Examen',
        'cases': [
            ('RDN +', {'meningeal_signs': True}),
            ('RDN ++', {'meningeal_signs': True}),
            ('raideur nuque', {'meningeal_signs': True}),
            ('Kernig +', {'meningeal_signs': True}),
            ('Brudzinski +', {'meningeal_signs': True}),
            ('Kernig pos', {'meningeal_signs': True}),
            ('sdm méningé', {'meningeal_signs': True}),
            ('sg méningés', {'meningeal_signs': True}),
            ('RDN -', {'meningeal_signs': False}),
            ('Kernig -', {'meningeal_signs': False}),
            ('Kernig nég', {'meningeal_signs': False}),
            ('pas de RDN', {'meningeal_signs': False}),
        ]
    },
    
    # === CONVULSIONS - Variations description ===
    {
        'category': 'Convulsions - Description',
        'cases': [
            ('crise ce matin', {'seizure': True}),
            ('CGT', {'seizure': True}),
            ('crise tonico-clonique', {'seizure': True}),
            ('crise TC', {'seizure': True}),
            ('crise comitiale', {'seizure': True}),
            ('convulsions', {'seizure': True}),
            ('a convulsé', {'seizure': True}),
            ('mouvements anormaux', {'seizure': True}),
            ('secousses', {'seizure': True}),
            ('perte connaissance + secousses', {'seizure': True}),
        ]
    },
    
    # === GROSSESSE - Notations obstétricales ===
    {
        'category': 'Grossesse - Obstétrique',
        'cases': [
            ('G1P0', {'pregnancy_postpartum': True}),
            ('G2P1', {'pregnancy_postpartum': True}),
            ('G3P2', {'pregnancy_postpartum': True}),
            ('8 SA', {'pregnancy_postpartum': True}),
            ('12SA', {'pregnancy_postpartum': True}),
            ('28 SA', {'pregnancy_postpartum': True}),
            ('T1', {'pregnancy_postpartum': True}),  # Trimestre 1
            ('T2', {'pregnancy_postpartum': True}),
            ('T3', {'pregnancy_postpartum': True}),
            ('gravidique', {'pregnancy_postpartum': True}),
            ('enceinte', {'pregnancy_postpartum': True}),
            ('gestante', {'pregnancy_postpartum': True}),
            ('J5 post-partum', {'pregnancy_postpartum': True}),
            ('post-partum', {'pregnancy_postpartum': True}),
        ]
    },
    
    # === TRAUMATISME - Notations temporelles ===
    {
        'category': 'Traumatisme - Contexte',
        'cases': [
            ('chute J-1', {'trauma': True}),
            ('TCC hier', {'trauma': True}),
            ('AVP ce matin', {'trauma': True}),
            ('choc crâne', {'trauma': True}),
            ('coup tête', {'trauma': True}),
            ('contusion crânienne', {'trauma': True}),
            ('trauma crânien', {'trauma': True}),
            ('sans trauma', {'trauma': False}),
            ('nie trauma', {'trauma': False}),
        ]
    },
    
    # === IMMUNOSUPPRESSION - Contexte médical ===
    {
        'category': 'Immunosuppression - ATCD',
        'cases': [
            ('VIH+', {'immunosuppression': True}),
            ('VIH +', {'immunosuppression': True}),
            ('séropositif', {'immunosuppression': True}),
            ('CD4 < 200', {'immunosuppression': True}),
            ('K poumon', {'immunosuppression': True}),
            ('K sein', {'immunosuppression': True}),
            ('K colon', {'immunosuppression': True}),
            ('chimio en cours', {'immunosuppression': True}),
            ('sous chimio', {'immunosuppression': True}),
            ('greffé rénal', {'immunosuppression': True}),
            ('greffe rein', {'immunosuppression': True}),
            ('ttt immunosup', {'immunosuppression': True}),
            ('cortico au long cours', {'immunosuppression': True}),
            ('sous corticoïdes', {'immunosuppression': True}),
        ]
    },
    
    # === HTIC - Signes cliniques ===
    {
        'category': 'HTIC - Symptômes',
        'cases': [
            ('vomissements en jet', {'htic_pattern': True}),
            ('vom en jet', {'htic_pattern': True}),
            ('céphalée matinale', {'htic_pattern': True}),
            ('céph + vom matin', {'htic_pattern': True}),
            ('pire le matin', {'htic_pattern': True}),
            ('aggravée toux', {'htic_pattern': True}),
            ('aggravée effort', {'htic_pattern': True}),
            ('œdème papillaire', {'htic_pattern': True}),
            ('OP', {'htic_pattern': True}),  # Œdème Papillaire
            ('sdm HTIC', {'htic_pattern': True}),
        ]
    },
    
    # === CAS COMPLEXES - Syntaxe médecin réelle ===
    {
        'category': 'Complexes - Syntaxe réelle',
        'cases': [
            # Urgences réelles
            (
                'F 45a, céph brutale, T 39, RDN ++, confusion',
                {
                    'age': 45,
                    'sex': 'F',
                    'onset': 'thunderclap',
                    'fever': True,
                    'meningeal_signs': True,
                    'neuro_deficit': True
                }
            ),
            (
                'H 28a, G1P0 12SA, céph intense EVA 9, scotomes',
                {
                    'age': 28,
                    'sex': 'F',  # G1P0 implique sexe féminin
                    'intensity': 9,
                    'pregnancy_postpartum': True,
                    'neuro_deficit': True
                }
            ),
            (
                'Pt 60a, VIH+ CD4 50, céph fébrile T=38.5, confusion',
                {
                    'age': 60,
                    'fever': True,
                    'immunosuppression': True,
                    'neuro_deficit': True
                }
            ),
            (
                'F 32a, AVP J-2, céph croissante, vom, GCS 14',
                {
                    'age': 32,
                    'sex': 'F',
                    'trauma': True,
                    'neuro_deficit': True
                }
            ),
            (
                'H 55a, céph dep 2j, CGT ce matin, hémipar D',
                {
                    'age': 55,
                    'sex': 'M',
                    'profile': 'acute',
                    'seizure': True,
                    'neuro_deficit': True
                }
            ),
        ]
    },
    
    # === ABRÉVIATIONS COURANTES ===
    {
        'category': 'Abréviations - Courantes',
        'cases': [
            ('céph', {}),  # Céphalée
            ('céphal', {}),
            ('pt', {}),  # Patient
            ('dep', {}),  # Depuis
            ('sg', {}),  # Signes
            ('sdm', {}),  # Syndrome
            ('vom', {}),  # Vomissements
            ('mb', {}),  # Membre
            ('sup', {}),  # Supérieur
            ('inf', {}),  # Inférieur
            ('pos', {}),  # Positif
            ('nég', {}),  # Négatif
            ('ATCD', {}),  # Antécédents
            ('ttt', {}),  # Traitement
        ]
    },
]


def run_syntax_tests():
    """Exécute tous les tests de syntaxe et retourne les résultats."""
    
    total_tests = 0
    total_passed = 0
    results_by_category = {}
    
    print('='*80)
    print('TESTS VARIATIONS SYNTAXIQUES - MÉDECINS FRANÇAIS')
    print('='*80)
    
    for test_group in TESTS_SYNTAXE:
        category = test_group['category']
        cases = test_group['cases']
        
        passed = 0
        failed = 0
        failures = []
        
        print(f"\n{'='*80}")
        print(f"{category} ({len(cases)} tests)")
        print('='*80)
        
        for text, expected in cases:
            total_tests += 1
            case, meta = parse_free_text_to_case(text)
            
            # Vérifier chaque champ attendu
            test_passed = True
            mismatches = []
            
            for field, expected_value in expected.items():
                actual_value = getattr(case, field, None)
                
                if actual_value != expected_value:
                    test_passed = False
                    mismatches.append({
                        'field': field,
                        'expected': expected_value,
                        'actual': actual_value
                    })
            
            if test_passed:
                passed += 1
                total_passed += 1
                print(f"  ✓ '{text}'")
            else:
                failed += 1
                failures.append({
                    'text': text,
                    'expected': expected,
                    'mismatches': mismatches
                })
                print(f"  ✗ '{text}'")
                for m in mismatches:
                    print(f"      → {m['field']}: attendu={m['expected']}, obtenu={m['actual']}")
        
        # Résumé de la catégorie
        success_rate = (passed / len(cases) * 100) if cases else 0
        print(f"\n  {category}: {passed}/{len(cases)} ({success_rate:.1f}%)")
        
        results_by_category[category] = {
            'total': len(cases),
            'passed': passed,
            'failed': failed,
            'success_rate': success_rate,
            'failures': failures
        }
    
    # === RÉSUMÉ GLOBAL ===
    print('\n' + '='*80)
    print('RÉSUMÉ GLOBAL')
    print('='*80)
    
    overall_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\nTests réussis: {total_passed}/{total_tests} ({overall_rate:.1f}%)")
    
    print('\nPar catégorie:')
    for category, results in results_by_category.items():
        print(f"  {category:40} {results['passed']:3}/{results['total']:3} ({results['success_rate']:5.1f}%)")
    
    # === PATTERNS MANQUANTS ===
    print('\n' + '='*80)
    print('PATTERNS À AMÉLIORER (échecs > 20%)')
    print('='*80)
    
    for category, results in results_by_category.items():
        if results['success_rate'] < 80 and results['failures']:
            print(f"\n{category} ({results['success_rate']:.1f}%):")
            
            # Grouper par champ manquant
            fields_missing = {}
            for failure in results['failures']:
                for m in failure['mismatches']:
                    field = m['field']
                    if field not in fields_missing:
                        fields_missing[field] = []
                    fields_missing[field].append(failure['text'])
            
            for field, texts in fields_missing.items():
                print(f"  Champ '{field}' ({len(texts)} échecs):")
                for text in texts[:3]:  # Montrer max 3 exemples
                    print(f"    - '{text}'")
                if len(texts) > 3:
                    print(f"    ... et {len(texts) - 3} autres")
    
    return {
        'total_tests': total_tests,
        'total_passed': total_passed,
        'overall_rate': overall_rate,
        'by_category': results_by_category
    }


if __name__ == '__main__':
    results = run_syntax_tests()
    
    print('\n' + '='*80)
    print(f"🎯 Taux de réussite global: {results['overall_rate']:.1f}%")
    print('='*80)
    
    # Sauvegarder les résultats
    import json
    with open('test_syntaxe_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print('\n💾 Résultats sauvegardés dans: test_syntaxe_results.json')
