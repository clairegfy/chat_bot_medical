#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug du système de matching pour comprendre pourquoi les mauvaises entrées sont sélectionnées."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import re
import unicodedata
from source.main import analyse_texte_medical, _normalize_key, _fuzzy_match_symptom, _normalize_text

def load_cephalees():
    with open('data/cephalees.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def score_entry(entry, positives, patient_info):
    """Calcule le score de correspondance (même logique que _match_best_entry)."""
    items = set()
    items_with_labels = {}
    for fld in ("symptomes", "indications_positives"):
        for v in (entry.get(fld) or []):
            key = _normalize_key(v)
            items.add(key)
            items_with_labels[key] = v
    
    if not items:
        return 0
    
    # Score avec bonus spécificité
    matched_items = items & positives
    score = 0.0
    for matched_key in matched_items:
        original_label = items_with_labels.get(matched_key, "")
        word_count = len(original_label.split())
        
        if word_count >= 5:
            score += 15.0
        elif word_count >= 4:
            score += 12.0
        elif word_count >= 3:
            score += 5.0
        elif word_count == 2:
            score += 2.0
        else:
            score += 0.5
    
    # Pénalité indications négatives
    neg_items = set()
    for v in (entry.get("indications_negatives") or []):
        neg_items.add(_normalize_key(v))
    if neg_items & positives:
        score -= len(neg_items & positives) * 10.0
    
    # Bonus population (petit)
    populations = entry.get("populations") or []
    detected_population = patient_info.get("population")
    if detected_population and detected_population in populations:
        score += 0.5
    elif patient_info.get("age"):
        age = patient_info["age"]
        if age < 18 and "enfant" in populations:
            score += 0.25
        elif 18 <= age < 65 and "adulte" in populations:
            score += 0.25
        elif age >= 65 and "personne_agee" in populations:
            score += 0.25
    
    if patient_info.get("sexe") == "f" and "femme" in populations:
        score += 0.1
    if patient_info.get("grossesse") and "enceinte" in populations:
        score += 1.0
    
    return score

def debug_patient(patient_data, patient_id):
    """Analyse en détail le matching d'un patient."""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG PATIENT {patient_id}")
    print(f"{'='*80}\n")
    
    # Construire le texte médical
    age = patient_data['age']
    sexe = 'homme' if patient_data['sexe'] == 'M' else 'femme'
    
    text_parts = [f"{sexe} de {age} ans"]
    if patient_data.get('context'):
        text_parts.append(patient_data['context'])
    if patient_data.get('signes'):
        text_parts.extend(patient_data['signes'])
    if patient_data.get('terrain') and patient_data['terrain'] != 'aucun':
        text_parts.append('Terrain: ' + patient_data['terrain'])
    
    text = '. '.join(text_parts) + '.'
    
    print(f"📝 Texte analysé:")
    print(f"   {text}\n")
    
    # Analyse du texte
    patient_info = analyse_texte_medical(text)
    print(f"👤 Informations extraites:")
    print(f"   Âge: {patient_info.get('age')}")
    print(f"   Sexe: {patient_info.get('sexe')}")
    print(f"   Population: {patient_info.get('population')}")
    print(f"   Grossesse: {patient_info.get('grossesse')}")
    
    # Symptômes détectés
    print(f"\n🔎 Symptômes détectés automatiquement:")
    entries = load_cephalees()
    
    # Normaliser le texte pour matching
    text_norm = _normalize_text(text)
    
    # Extraire tous les symptômes possibles
    all_symptoms = set()
    for e in entries:
        for fld in ('symptomes', 'indications_positives'):
            for v in (e.get(fld) or []):
                all_symptoms.add(v)
    
    matched_symptoms = []
    for symptom in all_symptoms:
        # Utiliser matching STRICT pour détection automatique
        symptom_norm = _normalize_text(symptom)
        
        # Méthode 1: Match exact
        if symptom_norm in text_norm:
            matched_symptoms.append(symptom)
            print(f"   ✓ {symptom} (exact)")
            continue
        
        # Méthode 2: Fuzzy très strict (95+)
        matched, score = _fuzzy_match_symptom(text_norm, symptom, threshold=95)
        if matched and score >= 95:
            matched_symptoms.append(symptom)
            print(f"   ✓ {symptom} (fuzzy {score})")
    
    # Créer le set de positives
    positives = set(_normalize_key(s) for s in matched_symptoms)
    
    print(f"\n🎯 Clés normalisées positives ({len(positives)}):")
    for p in sorted(positives):
        print(f"   • {p}")
    
    # Scorer TOUTES les entrées
    print(f"\n📊 TOP 10 ENTRÉES PAR SCORE:\n")
    
    scored_entries = []
    for entry in entries:
        score = score_entry(entry, positives, patient_info)
        if score > 0:  # N'afficher que celles avec score > 0
            scored_entries.append((score, entry))
    
    scored_entries.sort(reverse=True, key=lambda x: x[0])
    
    for i, (score, entry) in enumerate(scored_entries[:10], 1):
        print(f"{i}. Score: {score:.1f} → {entry['id']}")
        print(f"   Pathologie: {entry['pathologie']}")
        print(f"   Populations: {entry.get('populations', [])}")
        
        # Montrer quels symptômes matchent
        entry_symptoms = set()
        for fld in ("symptomes", "indications_positives"):
            for v in (entry.get(fld) or []):
                entry_symptoms.add(_normalize_key(v))
        
        matched = entry_symptoms & positives
        print(f"   Symptômes matchés ({len(matched)}): {', '.join(sorted(matched)[:3])}{'...' if len(matched) > 3 else ''}")
        
        # Indications négatives qui pénalisent
        neg_items = set()
        for v in (entry.get("indications_negatives") or []):
            neg_items.add(_normalize_key(v))
        neg_matched = neg_items & positives
        if neg_matched:
            print(f"   ⚠️  Indications négatives matchées: {neg_matched}")
        
        print()
    
    if len(scored_entries) == 0:
        print("   ❌ AUCUNE ENTRÉE AVEC SCORE > 0!")

if __name__ == '__main__':
    # Charger les patients
    with open('tests/patients.json', 'r', encoding='utf-8') as f:
        patients_list = json.load(f)
    
    # Convertir en dict
    patients = {p['id']: p for p in patients_list}
    
    # Patients les plus problématiques
    problematic = ['P001', 'P004', 'P005', 'P006']
    
    for patient_id in problematic:
        patient = patients[patient_id]
        debug_patient(patient, patient_id)
        input("\n[Appuyez sur ENTRÉE pour continuer...]\n")
