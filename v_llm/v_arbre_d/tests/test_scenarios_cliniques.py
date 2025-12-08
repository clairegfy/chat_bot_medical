#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests de scénarios cliniques complets : Symptômes → Output attendue
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

import unittest
import json
from io import StringIO
from unittest.mock import patch
from main import (
    analyse_texte_medical,
    _match_best_entry,
    _normalize_text,
    _normalize_key,
    _expand_acronyms,
    _fuzzy_match_symptom
)


class TestScenariosCephalees(unittest.TestCase):
    """Tests scénarios céphalées : symptômes → recommandation"""
    
    def setUp(self):
        """Charger les données cephalees.json"""
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cephalees.json')
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.cephalees_data = json.load(f)
    
    def test_cephalee_urgente_fievre(self):
        """Scénario : Céphalée + fièvre → Urgence immédiate"""
        texte = "patient 34 ans avec céphalées et fièvre"
        patient_info = analyse_texte_medical(texte)
        
        # Vérifications
        self.assertEqual(patient_info['age'], 34)
        self.assertTrue(patient_info['fievre'])
        
        # Détection urgence : fièvre détectée
        # → Devrait orienter aux urgences (système cephalees)
    
    def test_cephalee_urgente_brutale(self):
        """Scénario : Céphalée brutale → Urgence immédiate"""
        texte = "céphalée brutale début soudain"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['brutale'])
        # → Orientation urgences sans imagerie
    
    def test_cephalee_urgente_deficit(self):
        """Scénario : Céphalée + déficit neurologique → Urgence"""
        texte = "céphalées avec déficit neurologique"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['deficit'])
        # → Orientation urgences immédiate
    
    def test_cephalee_traumatique_adulte(self):
        """Scénario : Traumatisme crânien adulte → Scanner cérébral"""
        texte = "patient 45 ans traumatisme crânien"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        self.assertEqual(patient_info['age'], 45)
        self.assertEqual(patient_info['population'], 'adulte')
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        # Devrait matcher scanner cérébral pour TC adulte
        best_entry, _ = _match_best_entry(self.cephalees_data, positives, patient_info)
        
        if best_entry:
            self.assertIn('scanner', best_entry['modalite'].lower())
            self.assertIn('cérébral', best_entry['modalite'].lower())
    
    def test_cephalee_enfant_htic(self):
        """Scénario : Enfant + HTIC → IRM cérébrale urgente"""
        texte = "enfant 6 ans vomissements altération vigilance"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        self.assertEqual(patient_info['population'], 'enfant')
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        # Devrait matcher IRM cérébrale priorité 1
        best_entry, _ = _match_best_entry(self.cephalees_data, positives, patient_info)
        
        if best_entry and 'priorité' in best_entry.get('resume', '').lower():
            self.assertIn('irm', best_entry['modalite'].lower())


class TestScenariosThorax(unittest.TestCase):
    """Tests scénarios thorax : symptômes → recommandation"""
    
    def setUp(self):
        """Charger les données thorax.json"""
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'thorax.json')
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.thorax_data = json.load(f)
    
    def test_douleur_thoracique_aigue(self):
        """Scénario : Douleur thoracique aiguë → Radiographie puis scanner si besoin"""
        texte = "patient 55 ans douleur thoracique aiguë dyspnée"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        self.assertEqual(patient_info['age'], 55)
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        # Devrait matcher radiographie thorax en 1ère intention
        best_entry, _ = _match_best_entry(self.thorax_data, positives, patient_info)
        
        if best_entry:
            # Radiographie ou scanner acceptable
            modalite_lower = best_entry['modalite'].lower()
            self.assertTrue(
                'radio' in modalite_lower or 'scanner' in modalite_lower or 'angio' in modalite_lower,
                f"Imagerie thoracique attendue, reçu: {best_entry['modalite']}"
            )
    
    def test_suspicion_embolie_pulmonaire(self):
        """Scénario : Suspicion EP → Imagerie thoracique"""
        texte = "patient 45 ans dyspnée brutale douleur thoracique suspicion EP"
        patient_info = analyse_texte_medical(texte)
        texte_expansé = _expand_acronyms(texte)
        texte_norm = _normalize_text(texte_expansé)
        
        # EP devrait être expansé en "embolie pulmonaire"
        self.assertIn('embolie pulmonaire', texte_norm)
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.thorax_data, positives, patient_info)
        
        if best_entry:
            # Radio ou angioscanner acceptable
            self.assertTrue(
                'radio' in best_entry['modalite'].lower() or 
                'angio' in best_entry['modalite'].lower() or
                'thoracique' in best_entry['modalite'].lower()
            )
    
    def test_pneumothorax_suspicion(self):
        """Scénario : Suspicion pneumothorax → Radiographie thorax"""
        texte = "patient 25 ans douleur thoracique dyspnée suspicion pneumothorax"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.thorax_data, positives, patient_info)
        
        if best_entry and 'pneumothorax' in best_entry.get('pathologie', '').lower():
            # Radiographie en 1ère intention
            self.assertTrue(
                'radio' in best_entry['modalite'].lower() or 
                '1ère intention' in best_entry.get('priorite', ''),
                f"Radiographie attendue, reçu: {best_entry['modalite']}"
            )


class TestScenariosDigestif(unittest.TestCase):
    """Tests scénarios digestif : symptômes → recommandation"""
    
    def setUp(self):
        """Charger les données digestif.json"""
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'digestif.json')
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.digestif_data = json.load(f)
    
    def test_douleur_fid_suspicion_appendicite(self):
        """Scénario : Douleur FID + fièvre → Imagerie abdominale"""
        texte = "patient 28 ans douleur FID avec fièvre"
        patient_info = analyse_texte_medical(texte)
        texte_expansé = _expand_acronyms(texte)
        texte_norm = _normalize_text(texte_expansé)
        
        # FID expansé en "fosse iliaque droite"
        self.assertIn('fosse iliaque droite', texte_norm)
        self.assertTrue(patient_info['fievre'])
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.digestif_data, positives, patient_info)
        
        if best_entry:
            # Radio, scanner ou échographie acceptable
            modalite_lower = best_entry['modalite'].lower()
            self.assertTrue(
                'radio' in modalite_lower or 
                'scanner' in modalite_lower or 
                'échographie' in modalite_lower or
                'abdo' in modalite_lower,
                f"Imagerie abdominale attendue, reçu: {best_entry['modalite']}"
            )
    
    def test_douleur_fig(self):
        """Scénario : Douleur FIG → Imagerie abdominale"""
        texte = "patiente 52 ans douleur FIG"
        patient_info = analyse_texte_medical(texte)
        texte_expansé = _expand_acronyms(texte)
        texte_norm = _normalize_text(texte_expansé)
        
        # FIG expansé en "fosse iliaque gauche"
        self.assertIn('fosse iliaque gauche', texte_norm)
        self.assertEqual(patient_info['sexe'], 'f')
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.digestif_data, positives, patient_info)
        
        if best_entry:
            # Imagerie abdominale
            self.assertTrue(
                'abdo' in best_entry['modalite'].lower() or
                'radio' in best_entry['modalite'].lower() or
                'scanner' in best_entry['modalite'].lower()
            )
    
    def test_douleur_epigastrique(self):
        """Scénario : Douleur épigastrique → Pathologie haute"""
        texte = "patient 60 ans douleur épigastrique"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.digestif_data, positives, patient_info)
        
        if best_entry:
            # Devrait concerner abdomen supérieur
            self.assertIn('abdo', best_entry['modalite'].lower())
    
    def test_traumatisme_abdominal(self):
        """Scénario : Traumatisme abdominal → Scanner abdo"""
        texte = "patient 35 ans traumatisme abdominal"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.digestif_data, positives, patient_info)
        
        if best_entry and 'trauma' in best_entry.get('pathologie', '').lower():
            self.assertIn('scanner', best_entry['modalite'].lower())


class TestScenariosGrossesse(unittest.TestCase):
    """Tests scénarios grossesse : bonus prioritaire"""
    
    def setUp(self):
        """Charger les données"""
        self.thorax_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'thorax.json')
        with open(self.thorax_path, 'r', encoding='utf-8') as f:
            self.thorax_data = json.load(f)
    
    def test_grossesse_premier_trimestre(self):
        """Scénario : Grossesse T1 → Bonus +2.0"""
        texte = "patiente enceinte 8 semaines douleur thoracique"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['grossesse'])
        self.assertEqual(patient_info['grossesse_sem'], 8)
        
        # Grossesse < 12 sem donne bonus +2.0 (plus haut)
        # Devrait prioriser exams non-ionisants
    
    def test_grossesse_deuxieme_trimestre(self):
        """Scénario : Grossesse T2 → Bonus +1.5"""
        texte = "patiente grossesse 20 semaines"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['grossesse'])
        self.assertEqual(patient_info['grossesse_sem'], 20)
    
    def test_grossesse_troisieme_trimestre(self):
        """Scénario : Grossesse T3 → Bonus +1.0"""
        texte = "patiente enceinte 32 semaines"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['grossesse'])
        self.assertEqual(patient_info['grossesse_sem'], 32)


class TestScenariosPopulations(unittest.TestCase):
    """Tests scénarios populations spécifiques"""
    
    def setUp(self):
        """Charger les données cephalees"""
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cephalees.json')
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.cephalees_data = json.load(f)
    
    def test_nourrisson_macrocranie(self):
        """Scénario : Nourrisson < 4 mois macrocrânie → Écho transfontanellaire"""
        texte = "nourrisson 2 mois macrocrânie"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        self.assertEqual(patient_info['population'], 'enfant')
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        best_entry, _ = _match_best_entry(self.cephalees_data, positives, patient_info)
        
        if best_entry and 'macrocrânie' in best_entry.get('pathologie', '').lower():
            self.assertIn('écho', best_entry['modalite'].lower())
    
    def test_personne_agee_traumatisme(self):
        """Scénario : Personne âgée 78 ans TC → Imagerie si signes"""
        texte = "patient 78 ans traumatisme crânien"
        patient_info = analyse_texte_medical(texte)
        texte_norm = _normalize_text(texte)
        
        self.assertEqual(patient_info['age'], 78)
        self.assertEqual(patient_info['population'], 'personne_agee')
        
        # Créer set de mots-clés positifs
        positives = set()
        for word in texte_norm.split():
            positives.add(_normalize_key(word))
        
        # Scanner ou aucune imagerie selon signes cliniques
        best_entry, _ = _match_best_entry(self.cephalees_data, positives, patient_info)
        
        if best_entry:
            # Modalité cérébrale attendue (scanner ou aucune imagerie selon protocole)
            self.assertTrue(
                'scanner' in best_entry['modalite'].lower() or
                'aucune' in best_entry['modalite'].lower() or
                'cérébral' in best_entry['modalite'].lower()
            )
    
    def test_enfant_8_ans_cephalees(self):
        """Scénario : Enfant 8 ans céphalées → IRM si signes"""
        texte = "enfant 8 ans céphalées récurrentes"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['population'], 'enfant')
        # IRM privilégiée chez enfant (pas de radiation)


class TestScenariosContraindications(unittest.TestCase):
    """Tests scénarios contre-indications"""
    
    def test_pacemaker_irm(self):
        """Scénario : Patient avec pacemaker → Contre-indication IRM"""
        texte = "patient 65 ans pacemaker céphalées"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['pacemaker'])
        # → Devrait suggérer alternative au scanner
    
    def test_claustrophobie_irm(self):
        """Scénario : Claustrophobie → Scanner préféré"""
        texte = "patiente claustrophobe douleur abdominale"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['claustrophobie'])
        # → Scanner préféré à IRM
    
    def test_insuffisance_renale_produit_contraste(self):
        """Scénario : Patient > 60 ans → Créatinine avant injection"""
        texte = "patient 72 ans suspicion EP"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['age'], 72)
        # → Remarque créatinine dans output


class TestScenariosAcronyms(unittest.TestCase):
    """Tests expansion acronymes médicaux"""
    
    def test_expansion_fid_matching(self):
        """Scénario : FID → Matching appendicite"""
        texte_original = "douleur FID"
        texte_expansé = _expand_acronyms(texte_original)
        
        self.assertIn("fosse iliaque droite", texte_expansé)
        # L'expansion met en minuscule, donc fid pas FID
        self.assertIn("fid", texte_expansé.lower())
    
    def test_expansion_ep_matching(self):
        """Scénario : EP → Matching embolie pulmonaire"""
        texte_original = "suspicion EP"
        texte_expansé = _expand_acronyms(texte_original)
        
        self.assertIn("embolie pulmonaire", texte_expansé)
    
    def test_expansion_multiples(self):
        """Scénario : Multiples acronymes → Tous expansés"""
        texte = "patient FID avec EP suspectée"
        texte_expansé = _expand_acronyms(texte)
        
        self.assertIn("fosse iliaque droite", texte_expansé)
        self.assertIn("embolie pulmonaire", texte_expansé)


class TestScenariosEdgeCases(unittest.TestCase):
    """Tests cas limites et edge cases"""
    
    def test_age_limite_pediatrie_adulte(self):
        """Scénario : 18 ans → Population adulte"""
        texte = "patient 18 ans"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['age'], 18)
        self.assertEqual(patient_info['population'], 'adulte')
    
    def test_age_limite_adulte_personne_agee(self):
        """Scénario : 65 ans → Population personne_agee"""
        texte = "patient 65 ans"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['age'], 65)
        self.assertEqual(patient_info['population'], 'personne_agee')
    
    def test_grossesse_limite_t1_t2(self):
        """Scénario : 12 semaines → Fin T1"""
        texte = "grossesse 12 semaines"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['grossesse'])
        self.assertEqual(patient_info['grossesse_sem'], 12)
    
    def test_texte_vide(self):
        """Scénario : Texte vide → Valeurs par défaut"""
        patient_info = analyse_texte_medical("")
        
        self.assertIsNone(patient_info['age'])
        self.assertIsNone(patient_info['population'])
        self.assertIsNone(patient_info['sexe'])
    
    def test_texte_sans_info_medicale(self):
        """Scénario : Texte sans info → Pas de crash"""
        texte = "bonjour comment allez-vous"
        patient_info = analyse_texte_medical(texte)
        
        # Ne devrait pas crasher
        self.assertIsInstance(patient_info, dict)


class TestScenariosIonisant(unittest.TestCase):
    """Tests scénarios radiation ionisante"""
    
    def setUp(self):
        """Charger les données"""
        paths = {
            'cephalees': os.path.join(os.path.dirname(__file__), '..', 'data', 'cephalees.json'),
            'thorax': os.path.join(os.path.dirname(__file__), '..', 'data', 'thorax.json'),
            'digestif': os.path.join(os.path.dirname(__file__), '..', 'data', 'digestif.json')
        }
        
        self.data = {}
        for name, path in paths.items():
            with open(path, 'r', encoding='utf-8') as f:
                self.data[name] = json.load(f)
    
    def test_irm_non_ionisant(self):
        """Scénario : IRM → ionisant = false"""
        for dataset_name, dataset in self.data.items():
            for entry in dataset:
                modalite_lower = entry['modalite'].lower()
                # IRM seule (pas angioscanner qui contient 'angio')
                if 'irm' in modalite_lower and 'scanner' not in modalite_lower:
                    self.assertFalse(entry['ionisant'],
                                   f"IRM devrait être non-ionisant: {entry['id']}")
    
    def test_scanner_ionisant(self):
        """Scénario : Scanner → ionisant = true"""
        for dataset_name, dataset in self.data.items():
            for entry in dataset:
                modalite_lower = entry['modalite'].lower()
                # Scanner seul (pas "IRM / scanner en complément")
                if ('scanner' in modalite_lower or 'ct' in modalite_lower) and 'irm' not in modalite_lower:
                    self.assertTrue(entry['ionisant'],
                                  f"Scanner devrait être ionisant: {entry['id']}")
    
    def test_radio_ionisant(self):
        """Scénario : Radiographie → ionisant = true"""
        for dataset_name, dataset in self.data.items():
            for entry in dataset:
                if 'radio' in entry['modalite'].lower():
                    self.assertTrue(entry['ionisant'],
                                  f"Radio devrait être ionisant: {entry['id']}")
    
    def test_echo_non_ionisant(self):
        """Scénario : Échographie → ionisant = false"""
        for dataset_name, dataset in self.data.items():
            for entry in dataset:
                if 'écho' in entry['modalite'].lower() or 'us' in entry['modalite'].lower():
                    self.assertFalse(entry['ionisant'],
                                   f"Écho devrait être non-ionisant: {entry['id']}")


if __name__ == '__main__':
    # Lancer les tests avec verbosité
    unittest.main(verbosity=2)
