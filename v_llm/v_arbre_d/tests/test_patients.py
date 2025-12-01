#!/usr/bin/env python3
"""
Test du système avec cas patients réels
Valide les recommandations du système contre les réponses attendues
"""

import sys
import os
import json
from typing import Dict, List, Tuple

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from source.main import (
    analyse_texte_medical,
    _load_system_entries,
    _normalize_key,
    _fuzzy_match_symptom,
    _normalize_text,
    _match_best_entry
)


class PatientTestRunner:
    """Teste le système avec des cas patients"""
    
    def __init__(self, patients_file: str, reponses_file: str):
        self.patients_file = patients_file
        self.reponses_file = reponses_file
        self.patients = []
        self.reponses = {}
        self.results = []
        
    def load_data(self):
        """Charge les données patients et réponses"""
        # Charger patients
        with open(self.patients_file, 'r', encoding='utf-8') as f:
            self.patients = json.load(f)
        
        # Charger réponses
        with open(self.reponses_file, 'r', encoding='utf-8') as f:
            reponses_list = json.load(f)
            self.reponses = {r['id']: r for r in reponses_list}
        
        print(f"✅ {len(self.patients)} patients chargés")
        print(f"✅ {len(self.reponses)} réponses attendues chargées\n")
    
    def build_patient_text(self, patient: Dict) -> str:
        """Construit le texte descriptif du patient"""
        sexe_text = "femme" if patient['sexe'] == 'F' else "homme"
        text_parts = [
            sexe_text,
            f"{patient['age']} ans",
            patient['context']
        ]
        
        # Ajouter signes
        if patient.get('signes'):
            text_parts.extend(patient['signes'])
        
        # Ajouter terrain
        if patient.get('terrain') and patient['terrain'] != 'aucun':
            text_parts.append(patient['terrain'])
        
        # Ajouter grossesse
        if patient.get('grossesse'):
            text_parts.append('grossesse')
        
        return ' '.join(text_parts)
    
    def analyze_patient(self, patient: Dict) -> Dict:
        """Analyse un patient et retourne la recommandation"""
        # Construire le texte
        text = self.build_patient_text(patient)
        
        # Analyser le texte
        info = analyse_texte_medical(text)
        
        # Charger les données céphalées
        entries = _load_system_entries('cephalees')
        
        # Pré-remplir les symptômes détectés
        t_norm = _normalize_text(text)
        answers = {}
        
        # Extraire tous les symptômes possibles
        all_symptoms_map = {}
        for e in entries:
            for s in (e.get("symptomes") or []):
                key = _normalize_key(s)
                all_symptoms_map[key] = s
        
        # Pré-remplir automatiquement depuis le texte (matching STRICT pour éviter faux positifs)
        for key, original_label in all_symptoms_map.items():
            # Utiliser matching EXACT ou très strict seulement (pas fuzzy)
            # Pour éviter de matcher "raideur de nuque" avec 200 symptômes différents
            symptom_norm = _normalize_text(original_label)
            
            # Méthode 1: Match exact
            if symptom_norm in t_norm:
                answers[key] = True
                continue
            
            # Méthode 2: Détection de mots-clés médicaux critiques SPÉCIFIQUES
            # Utiliser uniquement des termes très spécifiques pour éviter faux positifs
            critical_keywords = [
                'immunodepr',  # immunodéprimé, immunodépression
                'vih', 'sida', 'greffe',
                'cancer', 'metasta', 'oncolog',
                'anticoagul',
                'traumat',  # traumatisme
                'grossesse', 'enceinte', 'gestation',
                'deficit', 'hemiplegi', 'paresi',
                'convulsion', 'epileps',
                'confusion', 'coma',
                'hemorrhag', 'avc', 'hsa',
                'fracture', 'plaie',
                'post-partum', 'postpartum', 'accouchement',
                'diplopie', 'diplopi',  # diplopie souvent associée à thrombose veineuse
                'thrombose'  # thrombose veineuse cérébrale
            ]
            
            symptom_has_keyword = False
            matched_keyword = None
            for keyword in critical_keywords:
                if keyword in symptom_norm:
                    symptom_has_keyword = True
                    matched_keyword = keyword
                    break
            
            # Si le symptôme contient un mot-clé critique et que ce mot-clé est aussi dans le texte
            if symptom_has_keyword and matched_keyword in t_norm:
                answers[key] = True
                continue
            
            # Méthode 2b: Détection de combinaisons pour céphalées primaires
            # "ATCD migraine" + "pulsatile" → céphalée primaire
            if 'atcd' in symptom_norm and 'migraine' in symptom_norm:
                if 'atcd' in t_norm and 'migraine' in t_norm:
                    answers[key] = True
                    continue
            
            # "céphalée pulsatile" spécifique pour migraine
            if 'pulsatil' in symptom_norm and 'cephalee' in symptom_norm:
                if 'pulsatil' in t_norm and 'cephalee' in t_norm:
                    answers[key] = True
                    continue
            
            # Méthode 3: Match strict par mots-clés principaux (seuil 95+) pour le reste
            matched, score = _fuzzy_match_symptom(t_norm, original_label, threshold=95)
            if matched and score >= 95:  # Très strict
                answers[key] = True
            else:
                answers[key] = False
        
        # Construire l'ensemble des réponses positives
        positives = {k for k, v in answers.items() if v}
        
        # Trouver la meilleure entrée
        best, score = _match_best_entry(entries, positives, info)
        
        if best and score > 0:
            # Vérifier si cette entrée recommande imagerie ou non
            decision_imagerie = best.get('decision_imagerie')
            
            # Si decision_imagerie n'est pas explicitement False, considérer True
            if decision_imagerie is False:
                imaging_decision = False
            else:
                imaging_decision = True
            
            # Vérifier si urgence_enum est "aucune" → pas d'imagerie
            urgence = best.get('urgence_enum', '')
            if urgence and urgence.lower() == 'aucune':
                imaging_decision = False
            
            return {
                'decision_imagerie': imaging_decision,
                'modalite': best.get('modalite', ''),
                'urgence': urgence,
                'ionisant': best.get('ionisant', False),
                'requires_contrast': best.get('requires_contrast', 'no'),
                'pathologie': best.get('pathologie', ''),
                'resume': best.get('resume', ''),
                'score': score,
                'entry_id': best.get('id', '')
            }
        else:
            return {
                'decision_imagerie': False,
                'modalite': None,
                'urgence': None,
                'score': 0
            }
    
    def compare_results(self, patient_id: str, result: Dict, expected: Dict) -> Tuple[bool, List[str]]:
        """Compare le résultat obtenu avec le résultat attendu"""
        errors = []
        
        # 1. Décision d'imagerie
        if result['decision_imagerie'] != expected['decision_imagerie']:
            errors.append(
                f"Décision imagerie: obtenu={result['decision_imagerie']}, "
                f"attendu={expected['decision_imagerie']}"
            )
            return False, errors
        
        # Si pas d'imagerie attendue et système dit non → OK
        if not expected['decision_imagerie'] and not result['decision_imagerie']:
            return True, []
        
        # Si imagerie recommandée, vérifier les détails
        if expected['decision_imagerie']:
            # 2. Type d'imagerie
            modalite_lower = result['modalite'].lower()
            expected_type = expected['type_imagerie'].lower()
            
            # Vérifier Scanner vs IRM
            if 'scanner' in expected_type or 'ct' in expected_type:
                if 'scanner' not in modalite_lower and 'ct' not in modalite_lower:
                    errors.append(
                        f"Type imagerie: obtenu='{result['modalite']}', "
                        f"attendu contient 'scanner'"
                    )
            elif 'irm' in expected_type or 'mri' in expected_type:
                if 'irm' not in modalite_lower and 'mri' not in modalite_lower:
                    errors.append(
                        f"Type imagerie: obtenu='{result['modalite']}', "
                        f"attendu contient 'IRM'"
                    )
            
            # 3. Contraste
            # Vérifier d'abord si requires_contrast est explicitement dans expected
            if 'requires_contrast' in expected:
                expected_contrast = expected['requires_contrast']
                if expected_contrast == 'depends':
                    # Si on attend "depends", accepter "depends"
                    if result['requires_contrast'] != 'depends':
                        errors.append(
                            f"Contraste: obtenu={result['requires_contrast']}, "
                            f"attendu='depends'"
                        )
                elif expected_contrast == 'yes':
                    if result['requires_contrast'] not in ['yes', True]:
                        errors.append(
                            f"Contraste: obtenu={result['requires_contrast']}, "
                            f"attendu='yes' (avec contraste)"
                        )
                elif expected_contrast == 'no':
                    if result['requires_contrast'] not in ['no', False]:
                        errors.append(
                            f"Contraste: obtenu={result['requires_contrast']}, "
                            f"attendu='no' (sans injection)"
                        )
            # Sinon vérifier via le type_imagerie
            elif 'sans_injection' in expected_type or 'sans_contraste' in expected_type:
                if result['requires_contrast'] not in ['no']:
                    errors.append(
                        f"Contraste: obtenu={result['requires_contrast']}, "
                        f"attendu='no' (sans injection)"
                    )
            elif 'avec_contraste' in expected_type:
                if result['requires_contrast'] not in ['yes', 'depends']:
                    errors.append(
                        f"Contraste: obtenu={result['requires_contrast']}, "
                        f"attendu='yes' (avec contraste)"
                    )
            
            # 4. Urgence
            urgence_map = {
                'immédiate': ['immédiate'],
                'rapide': ['rapide (<6h)', 'rapide'],
                'sous_quelques_jours': ['standard', 'sous_quelques_jours'],
                'standard': ['standard'],
                'depends': ['depends']  # Accepter depends quand attendu
            }
            
            expected_urgence = expected.get('urgence', '')
            result_urgence = result.get('urgence', '')
            
            if expected_urgence in urgence_map:
                valid_urgences = urgence_map[expected_urgence]
                
                if result_urgence not in valid_urgences:
                    errors.append(
                        f"Urgence: obtenu='{result_urgence}', "
                        f"attendu='{expected_urgence}'"
                    )
        
        return len(errors) == 0, errors
    
    def run_tests(self):
        """Exécute tous les tests"""
        print("="*70)
        print("TESTS PATIENTS RÉELS")
        print("="*70)
        print()
        
        total = len(self.patients)
        passed = 0
        failed = 0
        
        for patient in self.patients:
            patient_id = patient['id']
            expected = self.reponses.get(patient_id)
            
            if not expected:
                print(f"❌ {patient_id}: Pas de réponse attendue trouvée")
                failed += 1
                continue
            
            # Analyser le patient
            result = self.analyze_patient(patient)
            
            # Comparer avec attendu
            success, errors = self.compare_results(patient_id, result, expected)
            
            # Stocker le résultat
            self.results.append({
                'patient_id': patient_id,
                'patient': patient,
                'result': result,
                'expected': expected,
                'success': success,
                'errors': errors
            })
            
            # Afficher le résultat
            if success:
                print(f"✅ {patient_id}: {patient['context']}")
                if result['decision_imagerie']:
                    print(f"   → {result['modalite']} - {result['urgence']}")
                else:
                    print(f"   → Pas d'imagerie (correct)")
                passed += 1
            else:
                print(f"❌ {patient_id}: {patient['context']}")
                print(f"   Patient: {patient['age']} ans, {patient['sexe']}")
                print(f"   Attendu: {expected.get('justification', 'N/A')}")
                if result['decision_imagerie']:
                    print(f"   Obtenu: {result['modalite']} - {result['urgence']}")
                    print(f"   Score: {result['score']}")
                else:
                    print(f"   Obtenu: Pas d'imagerie")
                
                for error in errors:
                    print(f"   ⚠️  {error}")
                failed += 1
            
            print()
        
        # Résumé
        print("="*70)
        print(f"RÉSULTATS: {passed}/{total} tests passent ({passed*100//total}%)")
        print(f"  ✅ Réussis: {passed}")
        print(f"  ❌ Échoués: {failed}")
        print("="*70)
        
        return passed == total
    
    def generate_detailed_report(self):
        """Génère un rapport détaillé"""
        print("\n" + "="*70)
        print("RAPPORT DÉTAILLÉ")
        print("="*70)
        
        for res in self.results:
            if not res['success']:
                patient = res['patient']
                result = res['result']
                expected = res['expected']
                
                print(f"\n🔍 {res['patient_id']}: {patient['context']}")
                print(f"   Âge: {patient['age']} ans, Sexe: {patient['sexe']}")
                print(f"   Signes: {', '.join(patient['signes'])}")
                print(f"   Terrain: {patient['terrain']}")
                print()
                print(f"   📋 ATTENDU:")
                print(f"      Imagerie: {expected['decision_imagerie']}")
                if expected['decision_imagerie']:
                    print(f"      Type: {expected['type_imagerie']}")
                    print(f"      Urgence: {expected['urgence']}")
                    print(f"      Justification: {expected['justification']}")
                print()
                print(f"   🔬 OBTENU:")
                print(f"      Imagerie: {result['decision_imagerie']}")
                if result['decision_imagerie']:
                    print(f"      Modalité: {result['modalite']}")
                    print(f"      Urgence: {result['urgence']}")
                    print(f"      Pathologie: {result.get('pathologie', 'N/A')}")
                    print(f"      Entry ID: {result.get('entry_id', 'N/A')}")
                    print(f"      Score: {result['score']}")
                print()
                print(f"   ⚠️  ERREURS:")
                for error in res['errors']:
                    print(f"      • {error}")
                print()


def main():
    """Point d'entrée principal"""
    # Chemins des fichiers
    script_dir = os.path.dirname(os.path.abspath(__file__))
    patients_file = os.path.join(script_dir, 'patients.json')
    reponses_file = os.path.join(script_dir, 'patients_réponses.json')
    
    # Vérifier l'existence des fichiers
    if not os.path.exists(patients_file):
        print(f"❌ Fichier patients non trouvé: {patients_file}")
        return 1
    
    if not os.path.exists(reponses_file):
        print(f"❌ Fichier réponses non trouvé: {reponses_file}")
        return 1
    
    # Créer le runner
    runner = PatientTestRunner(patients_file, reponses_file)
    
    # Charger les données
    runner.load_data()
    
    # Exécuter les tests
    success = runner.run_tests()
    
    # Générer rapport détaillé si échecs
    if not success:
        runner.generate_detailed_report()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
