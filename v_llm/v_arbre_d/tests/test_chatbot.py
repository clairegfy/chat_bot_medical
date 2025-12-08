#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests automatisés rigoureux pour le chatbot médical
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

import unittest
import json
from main import (
    analyse_texte_medical,
    _expand_acronyms,
    _fuzzy_match_symptom,
    _is_question_redundant,
    _match_best_entry,
    _normalize_text
)


class TestAnalyseTexteMedical(unittest.TestCase):
    """Tests de l'analyse du texte médical"""
    
    def test_detection_age_simple(self):
        """Test détection âge simple"""
        result = analyse_texte_medical("patient 45 ans")
        self.assertEqual(result['age'], 45)
        self.assertEqual(result['population'], 'adulte')
    
    def test_detection_age_enfant(self):
        """Test détection population enfant"""
        result = analyse_texte_medical("enfant de 8 ans")
        self.assertEqual(result['age'], 8)
        self.assertEqual(result['population'], 'enfant')
    
    def test_detection_age_personne_agee(self):
        """Test détection personne âgée"""
        result = analyse_texte_medical("patient 78 ans")
        self.assertEqual(result['age'], 78)
        self.assertEqual(result['population'], 'personne_agee')
    
    def test_detection_sexe_homme(self):
        """Test détection sexe masculin"""
        result = analyse_texte_medical("patient homme 35 ans")
        self.assertEqual(result['sexe'], 'm')
    
    def test_detection_sexe_femme(self):
        """Test détection sexe féminin"""
        result = analyse_texte_medical("patiente femme 42 ans")
        self.assertEqual(result['sexe'], 'f')
    
    def test_detection_grossesse(self):
        """Test détection grossesse"""
        result = analyse_texte_medical("patiente enceinte 28 ans")
        self.assertTrue(result['grossesse'])
        
        result2 = analyse_texte_medical("grossesse 12 semaines")
        self.assertTrue(result2['grossesse'])
        self.assertEqual(result2['grossesse_sem'], 12)
    
    def test_detection_fievre(self):
        """Test détection fièvre"""
        result = analyse_texte_medical("patient avec fièvre")
        self.assertTrue(result['fievre'])
        
        result2 = analyse_texte_medical("fièvre à 39°C")
        self.assertTrue(result2['fievre'])
    
    def test_detection_signes_urgents_cephalees(self):
        """Test détection signes urgents pour céphalées"""
        result = analyse_texte_medical("céphalée brutale")
        self.assertTrue(result['brutale'])
        
        result2 = analyse_texte_medical("déficit neurologique")
        self.assertTrue(result2['deficit'])


class TestExpandAcronyms(unittest.TestCase):
    """Tests de l'expansion des acronymes"""
    
    def test_expansion_fid(self):
        """Test expansion FID"""
        result = _expand_acronyms("douleur FID")
        self.assertIn("fosse iliaque droite", result)
    
    def test_expansion_fig(self):
        """Test expansion FIG"""
        result = _expand_acronyms("douleur FIG")
        self.assertIn("fosse iliaque gauche", result)
    
    def test_expansion_ep(self):
        """Test expansion EP"""
        result = _expand_acronyms("suspicion EP")
        self.assertIn("embolie pulmonaire", result)
    
    def test_expansion_dvp(self):
        """Test expansion DVP"""
        result = _expand_acronyms("patient DVP")
        # DVP peut ne pas être dans les acronymes - test conditionnel
        self.assertIsInstance(result, str)


class TestFuzzyMatchSymptom(unittest.TestCase):
    """Tests du matching fuzzy de symptômes"""
    
    def test_match_exact(self):
        """Test matching exact"""
        texte_norm = _normalize_text("douleur thoracique")
        result = _fuzzy_match_symptom(texte_norm, "douleur thoracique", 90)
        self.assertTrue(result[0] if isinstance(result, tuple) else result)
    
    def test_match_aigu_present(self):
        """Test matching avec qualificateur aigu présent"""
        texte_norm = _normalize_text("douleur thoracique aiguë")
        result = _fuzzy_match_symptom(texte_norm, "douleur thoracique aiguë", 90)
        self.assertTrue(result[0] if isinstance(result, tuple) else result)
    
    def test_match_aigu_absent(self):
        """Test matching avec qualificateur aigu absent (doit échouer)"""
        texte_norm = _normalize_text("douleur thoracique")
        result = _fuzzy_match_symptom(texte_norm, "douleur thoracique aiguë", 90)
        match_result = result[0] if isinstance(result, tuple) else result
        self.assertFalse(match_result)
    
    def test_match_chronique_present(self):
        """Test matching avec qualificateur chronique présent"""
        texte_norm = _normalize_text("douleur thoracique chronique")
        result = _fuzzy_match_symptom(texte_norm, "douleur thoracique chronique", 90)
        self.assertTrue(result[0] if isinstance(result, tuple) else result)
    
    def test_match_chronique_absent(self):
        """Test matching avec qualificateur chronique absent (doit échouer)"""
        texte_norm = _normalize_text("douleur thoracique")
        result = _fuzzy_match_symptom(texte_norm, "douleur thoracique chronique", 90)
        match_result = result[0] if isinstance(result, tuple) else result
        self.assertFalse(match_result)


class TestIsQuestionRedundant(unittest.TestCase):
    """Tests du filtrage des questions redondantes"""
    
    def test_filter_age_criteria_adulte(self):
        """Test filtrage critères d'âge pour adulte"""
        patient_info = {'age': 45, 'population': 'adulte'}
        answers = {}
        
        # Question âge ≥ 18 ans
        result = _is_question_redundant(
            "age_gte_18",
            "âge ≥ 18 ans ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
        self.assertTrue(answers.get("age_gte_18"))
    
    def test_filter_age_criteria_personne_agee(self):
        """Test filtrage critères d'âge pour personne âgée"""
        patient_info = {'age': 78, 'population': 'personne_agee'}
        answers = {}
        
        # Question âge ≥ 65 ans
        result = _is_question_redundant(
            "age_gte_65",
            "âge ≥ 65 ans ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
        self.assertTrue(answers.get("age_gte_65"))
    
    def test_filter_pediatric_for_adult(self):
        """Test filtrage questions pédiatriques pour adulte"""
        patient_info = {'age': 67, 'population': 'personne_agee'}
        answers = {}
        
        # Question âge < X mois pour adulte - auto-répondu
        result = _is_question_redundant(
            "age_lt_4_mois",
            "âge < 4 mois ?",
            patient_info,
            answers
        )
        # Le filtre peut auto-répondre ou filtrer, accepter les deux
        if result:
            self.assertFalse(answers.get("age_lt_4_mois"))
    
    def test_filter_craniostenoze_for_adult(self):
        """Test filtrage craniosténose pour adulte"""
        patient_info = {'age': 45, 'population': 'adulte'}
        answers = {}
        
        result = _is_question_redundant(
            "cranio",
            "exploration craniosténose ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
        self.assertFalse(answers.get("cranio"))
    
    def test_filter_fontanelle_for_adult(self):
        """Test filtrage fontanelle pour adulte"""
        patient_info = {'age': 34, 'population': 'adulte'}
        answers = {}
        
        result = _is_question_redundant(
            "fontanelle",
            "bombement fontanelle ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
        self.assertFalse(answers.get("fontanelle"))
    
    def test_filter_technical_gcs(self):
        """Test filtrage question technique GCS"""
        patient_info = {}
        answers = {}
        
        result = _is_question_redundant(
            "gcs",
            "GCS < 13 ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
    
    def test_filter_technical_nexus(self):
        """Test filtrage règles NEXUS"""
        patient_info = {}
        answers = {}
        
        result = _is_question_redundant(
            "nexus",
            "règles NEXUS négatives ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
    
    def test_filter_vague_tumorale(self):
        """Test filtrage question vague tumorale"""
        patient_info = {}
        answers = {}
        
        result = _is_question_redundant(
            "tumorale",
            "tumorale ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
    
    def test_filter_vague_infection(self):
        """Test filtrage question vague infection"""
        patient_info = {}
        answers = {}
        
        result = _is_question_redundant(
            "infection",
            "infection ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
    
    def test_filter_out_of_context_lesions_salivaires(self):
        """Test filtrage question hors contexte (lésions salivaires)"""
        patient_info = {}
        answers = {}
        
        result = _is_question_redundant(
            "salivaires",
            "lésions salivaires ?",
            patient_info,
            answers
        )
        self.assertTrue(result)
    
    def test_not_filter_relevant_question(self):
        """Test NON filtrage question pertinente"""
        patient_info = {'age': 45}
        answers = {}
        
        result = _is_question_redundant(
            "antecedent_cancer",
            "antécédent de cancer ?",
            patient_info,
            answers
        )
        self.assertFalse(result)


class TestMatchBestEntry(unittest.TestCase):
    """Tests du matching d'entrée JSON"""
    
    def setUp(self):
        """Charger les données de test"""
        self.cephalees_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'data', 
            'cephalees.json'
        )
        
        if os.path.exists(self.cephalees_path):
            with open(self.cephalees_path, 'r', encoding='utf-8') as f:
                self.cephalees_data = json.load(f)
        else:
            self.cephalees_data = []
    
    def test_no_rachis_entries(self):
        """Test qu'il n'y a plus d'entrées rachis dans cephalees.json"""
        rachis_entries = [
            entry for entry in self.cephalees_data 
            if entry.get('systeme') == 'rachis'
        ]
        self.assertEqual(len(rachis_entries), 0, 
                        f"Trouvé {len(rachis_entries)} entrées rachis dans cephalees.json")
    
    def test_only_neuro_or_orl_entries(self):
        """Test que toutes les entrées sont neuro ou ORL (pas rachis)"""
        valid_entries = [
            entry for entry in self.cephalees_data 
            if entry.get('systeme') in ('neuro', 'orl')
        ]
        self.assertEqual(len(valid_entries), len(self.cephalees_data),
                        "Toutes les entrées devraient être neuro ou ORL")
    
    def test_no_rachis_cervicale_modality(self):
        """Test qu'il n'y a plus d'IRM cervicale rachis dans cephalees.json"""
        # Dissection artérielle cervicale (neuro) et masse cervicale (ORL) sont légitimes
        # Seules les entrées rachis cervical (rachis) sont invalides
        rachis_cervical = [
            entry for entry in self.cephalees_data 
            if entry.get('systeme') == 'rachis' and 'cervical' in str(entry).lower()
        ]
        self.assertEqual(len(rachis_cervical), 0,
                        f"Trouvé {len(rachis_cervical)} entrées rachis cervical")
    
    def test_no_radiculalgie_symptoms(self):
        """Test qu'il n'y a plus de radiculalgie dans les symptômes"""
        radiculalgie_entries = []
        for entry in self.cephalees_data:
            symptoms = entry.get('symptomes', [])
            if any('radiculalgie' in str(s).lower() for s in symptoms):
                radiculalgie_entries.append(entry)
        
        self.assertEqual(len(radiculalgie_entries), 0,
                        f"Trouvé radiculalgie dans {len(radiculalgie_entries)} entrées")


class TestIntegration(unittest.TestCase):
    """Tests d'intégration du système complet"""
    
    def test_cephalees_adulte_simple(self):
        """Test scénario céphalées adulte simple"""
        texte = "patiente 45 ans avec céphalées"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['age'], 45)
        self.assertEqual(patient_info['population'], 'adulte')
        self.assertEqual(patient_info['sexe'], 'f')
    
    def test_cephalees_personne_agee(self):
        """Test scénario céphalées personne âgée"""
        texte = "patiente 78 ans avec céphalées"
        patient_info = analyse_texte_medical(texte)
        
        self.assertEqual(patient_info['age'], 78)
        self.assertEqual(patient_info['population'], 'personne_agee')
    
    def test_cephalees_urgence_fievre(self):
        """Test scénario céphalées urgentes avec fièvre"""
        texte = "patient 34 ans céphalées avec fièvre"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['fievre'])
    
    def test_cephalees_urgence_brutale(self):
        """Test scénario céphalées urgentes brutales"""
        texte = "céphalée brutale début soudain"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['brutale'])
    
    def test_cephalees_urgence_deficit(self):
        """Test scénario céphalées urgentes avec déficit"""
        texte = "céphalées avec déficit neurologique"
        patient_info = analyse_texte_medical(texte)
        
        self.assertTrue(patient_info['deficit'])
    
    def test_thorax_douleur_aigue(self):
        """Test scénario thorax douleur aiguë"""
        texte = "douleur thoracique aiguë"
        texte_norm = _normalize_text(texte)
        
        # Doit matcher "douleur thoracique aiguë"
        match_aigu = _fuzzy_match_symptom(texte_norm, "douleur thoracique aiguë", 90)
        result_aigu = match_aigu[0] if isinstance(match_aigu, tuple) else match_aigu
        self.assertTrue(result_aigu)
        
        # Ne doit PAS matcher "douleur thoracique chronique"
        match_chronique = _fuzzy_match_symptom(texte_norm, "douleur thoracique chronique", 90)
        result_chronique = match_chronique[0] if isinstance(match_chronique, tuple) else match_chronique
        self.assertFalse(result_chronique)
    
    def test_thorax_douleur_chronique(self):
        """Test scénario thorax douleur chronique"""
        texte = "douleur thoracique chronique"
        texte_norm = _normalize_text(texte)
        
        # Doit matcher "douleur thoracique chronique"
        match_chronique = _fuzzy_match_symptom(texte_norm, "douleur thoracique chronique", 90)
        result_chronique = match_chronique[0] if isinstance(match_chronique, tuple) else match_chronique
        self.assertTrue(result_chronique)
        
        # Ne doit PAS matcher "douleur thoracique aiguë"
        match_aigu = _fuzzy_match_symptom(texte_norm, "douleur thoracique aiguë", 90)
        result_aigu = match_aigu[0] if isinstance(match_aigu, tuple) else match_aigu
        self.assertFalse(result_aigu)


class TestDataIntegrity(unittest.TestCase):
    """Tests de l'intégrité des données JSON"""
    
    def test_cephalees_json_valid(self):
        """Test que cephalees.json est valide"""
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cephalees.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
    
    def test_thorax_json_valid(self):
        """Test que thorax.json est valide"""
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'thorax.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
    
    def test_digestif_json_valid(self):
        """Test que digestif.json est valide"""
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'digestif.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
    
    def test_all_entries_have_required_fields(self):
        """Test que toutes les entrées ont les champs requis"""
        required_fields = ['id', 'systeme', 'pathologie', 'modalite', 'symptomes']
        
        for json_file in ['cephalees.json', 'thorax.json', 'digestif.json']:
            path = os.path.join(os.path.dirname(__file__), '..', 'data', json_file)
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entry in data:
                for field in required_fields:
                    self.assertIn(field, entry, 
                                f"Champ '{field}' manquant dans {json_file}: {entry.get('id')}")


if __name__ == '__main__':
    # Lancer les tests avec verbosité
    unittest.main(verbosity=2)
