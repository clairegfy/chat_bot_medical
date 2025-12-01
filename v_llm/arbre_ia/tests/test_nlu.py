"""Tests unitaires pour le module NLU (Natural Language Understanding).

Tests de l'extraction d'informations depuis du texte libre.

Pour lancer les tests:
    pip install pytest
    pytest tests/test_nlu.py -v
    
Pour lancer tous les tests:
    pytest tests/ -v
    
Résultats actuels: 42/67 tests passent (62.7%)

Tests validés:
- Détection de l'onset (thunderclap, progressive, chronic)
- Détection du profil temporel (acute, chronic)
- Détection de la fièvre
- Extraction de l'âge
- Scénarios complexes multi-critères
- Gestion des négations de base

Note: parse_free_text_to_case() retourne un tuple (HeadacheCase, Dict)
"""

import pytest
from pathlib import Path
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from headache_assistants.nlu import parse_free_text_to_case
from headache_assistants.models import HeadacheCase


class TestOnsetDetection:
    """Tests pour la détection du type de début (onset)."""
    
    def test_thunderclap_detection(self):
        """Détecte 'coup de tonnerre' comme onset thunderclap."""
        text = "Douleur brutale en coup de tonnerre depuis ce matin"
        case, _ = parse_free_text_to_case(text)
        
        assert case.onset == "thunderclap"
    
    def test_thunderclap_synonyms(self):
        """Détecte les synonymes de coup de tonnerre."""
        texts = [
            "Céphalée brutale et soudaine",
            "Douleur instantanée d'emblée maximale",
            "Mal de tête avec violence maximale d'emblée",
            "Céphalée en quelques secondes"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.onset == "thunderclap", f"Failed for: {text}"
    
    def test_progressive_onset(self):
        """Détecte onset progressif."""
        text = "Mal de tête qui a augmenté progressivement sur plusieurs heures"
        case, _ = parse_free_text_to_case(text)
        
        assert case.onset == "progressive"
    
    def test_chronic_onset(self):
        """Détecte onset chronique."""
        texts = [
            "Céphalées chroniques depuis des années",
            "Mal de tête quotidien permanent",
            "Douleur tous les jours depuis des mois"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.onset == "chronic", f"Failed for: {text}"


class TestProfileDetection:
    """Tests pour la détection du profil temporel."""
    
    def test_acute_profile(self):
        """Détecte profil aigu."""
        texts = [
            "Céphalée aiguë depuis 2 heures",
            "Mal de tête depuis quelques heures",
            "Douleur récente depuis 3 jours"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.profile == "acute", f"Failed for: {text}"
    
    def test_subacute_profile(self):
        """Détecte profil subaigu."""
        texts = [
            "Céphalée subaiguë depuis 2 semaines",
            "Mal de tête depuis quelques semaines"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.profile == "subacute", f"Failed for: {text}"
    
    def test_chronic_profile(self):
        """Détecte profil chronique."""
        texts = [
            "Céphalée chronique depuis plusieurs mois",
            "Mal de tête permanent depuis 6 mois",
            "Douleur quotidienne depuis des années"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.profile == "chronic", f"Failed for: {text}"


class TestFeverDetection:
    """Tests pour la détection de fièvre."""
    
    def test_fever_positive(self):
        """Détecte présence de fièvre."""
        texts = [
            "Patient fébrile avec température à 39°C",
            "Mal de tête avec fièvre",
            "Céphalée et hyperthermie",
            "Température > 38°C"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.fever is True, f"Failed for: {text}"
    
    def test_fever_negative(self):
        """Détecte absence de fièvre."""
        texts = [
            "Pas de fièvre",
            "Apyrétique",
            "Sans fièvre",
            "Température normale"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.fever is False, f"Failed for: {text}"
    
    def test_fever_unknown(self):
        """Fièvre non mentionnée = unknown."""
        text = "Céphalée intense sans autre symptôme"
        case, _ = parse_free_text_to_case(text)
        
        assert case.fever is None


class TestMeningealSignsDetection:
    """Tests pour la détection des signes méningés."""
    
    def test_meningeal_signs_positive(self):
        """Détecte présence de signes méningés."""
        texts = [
            "Raideur de nuque importante",
            "Signes méningés positifs",
            "Raideur méningée avec signe de Kernig",
            "Signe de Brudzinski positif"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.meningeal_signs is True, f"Failed for: {text}"
    
    def test_meningeal_signs_negative(self):
        """Détecte absence de signes méningés."""
        texts = [
            "Pas de raideur de nuque",
            "Nuque souple",
            "Pas de signes méningés",
            "Signes méningés négatifs"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.meningeal_signs is False, f"Failed for: {text}"


class TestHTICPatternDetection:
    """Tests pour la détection du pattern HTIC."""
    
    def test_htic_pattern_positive(self):
        """Détecte pattern HTIC."""
        texts = [
            "Céphalées du matin avec vomissements en jet",
            "Mal de tête pire le matin",
            "Céphalée aggravée par la toux",
            "Vomissements en jet matinaux",
            "Douleur augmentée par effort de toux"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.htic_pattern is True, f"Failed for: {text}"
    
    def test_htic_pattern_negative(self):
        """Détecte absence de pattern HTIC."""
        texts = [
            "Pas de céphalées matinales",
            "Pas de vomissements",
            "Sans aggravation par la toux"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.htic_pattern is False, f"Failed for: {text}"


class TestNeuroDeficitDetection:
    """Tests pour la détection de déficit neurologique."""
    
    def test_neuro_deficit_positive(self):
        """Détecte présence de déficit neurologique."""
        texts = [
            "Déficit moteur du membre supérieur droit",
            "Hémiparésie gauche",
            "Aphasie associée",
            "Trouble neurologique focal",
            "Paralysie faciale"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.neuro_deficit is True, f"Failed for: {text}"
    
    def test_neuro_deficit_negative(self):
        """Détecte absence de déficit neurologique."""
        texts = [
            "Pas de déficit neurologique",
            "Sans déficit moteur",
            "Aucun déficit",
            "Examen neurologique normal",
            "Pas de trouble neurologique"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.neuro_deficit is False, f"Failed for: {text}"


class TestTraumaDetection:
    """Tests pour la détection de traumatisme."""
    
    def test_trauma_positive(self):
        """Détecte présence de traumatisme."""
        texts = [
            "Traumatisme crânien hier",
            "Après une chute avec coup à la tête",
            "Notion de traumatisme récent",
            "Suite à un accident"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.trauma is True, f"Failed for: {text}"
    
    def test_trauma_negative(self):
        """Détecte absence de traumatisme."""
        texts = [
            "Pas de traumatisme",
            "Sans notion de chute",
            "Aucun antécédent traumatique",
            "Pas de coup à la tête"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.trauma is False, f"Failed for: {text}"


class TestConfusionDetection:
    """Tests pour la détection de confusion."""
    
    def test_confusion_positive(self):
        """Détecte présence de confusion."""
        texts = [
            "Patient confus et désorienté",
            "Trouble de conscience",
            "Désorientation temporo-spatiale",
            "Confusion mentale"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.confusion is True, f"Failed for: {text}"
    
    def test_confusion_negative(self):
        """Détecte absence de confusion."""
        texts = [
            "Patient bien orienté",
            "Conscience normale",
            "Pas de confusion",
            "Vigilance conservée"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.confusion is False, f"Failed for: {text}"


class TestIntensityDetection:
    """Tests pour la détection de l'intensité."""
    
    def test_intensity_severe(self):
        """Détecte intensité sévère."""
        texts = [
            "Douleur très intense 9/10",
            "Céphalée sévère insupportable",
            "Pire mal de tête de ma vie",
            "Douleur extrême",
            "Intensité 10 sur 10"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.intensity is not None
            assert case.intensity >= 7, f"Failed for: {text}"
    
    def test_intensity_moderate(self):
        """Détecte intensité modérée."""
        texts = [
            "Douleur modérée 5/10",
            "Mal de tête moyen",
            "Intensité moyenne"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.intensity is not None
            assert 4 <= case.intensity <= 6, f"Failed for: {text}"
    
    def test_intensity_mild(self):
        """Détecte intensité légère."""
        texts = [
            "Douleur légère 2/10",
            "Mal de tête faible",
            "Gêne minime"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.intensity is not None
            assert case.intensity <= 3, f"Failed for: {text}"


class TestDurationDetection:
    """Tests pour la détection de la durée."""
    
    def test_duration_hours(self):
        """Détecte durée en heures."""
        texts = [
            "Depuis 2 heures",
            "Dure depuis 12h",
            "Depuis quelques heures"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.duration is not None
            assert case.duration < 24, f"Failed for: {text}"
    
    def test_duration_days(self):
        """Détecte durée en jours."""
        texts = [
            "Depuis 3 jours",
            "Ça fait 5 jours",
            "Depuis plusieurs jours"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.duration is not None
            assert case.duration >= 24, f"Failed for: {text}"
    
    def test_duration_weeks(self):
        """Détecte durée en semaines."""
        texts = [
            "Depuis 2 semaines",
            "Ça fait 1 semaine",
            "Depuis plusieurs semaines"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.duration is not None
            assert case.duration >= 168, f"Failed for: {text}"  # 7 jours = 168h


class TestRiskFactorsDetection:
    """Tests pour la détection des facteurs de risque."""
    
    def test_immunosuppression_detection(self):
        """Détecte immunodépression."""
        texts = [
            "Patient immunodéprimé sous chimiothérapie",
            "Traitement immunosuppresseur",
            "VIH positif",
            "Sous corticoïdes au long cours"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.immunosuppression is True, f"Failed for: {text}"
    
    def test_cancer_history_detection(self):
        """Détecte antécédent de cancer."""
        texts = [
            "Antécédent de cancer du sein",
            "Néoplasie pulmonaire connue",
            "Patient avec carcinome",
            "Histoire de tumeur"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.cancer_history is True, f"Failed for: {text}"
    
    def test_pregnancy_postpartum_detection(self):
        """Détecte grossesse/post-partum."""
        texts = [
            "Patiente enceinte de 7 mois",
            "En post-partum (3 semaines)",
            "Grossesse au 3ème trimestre",
            "Accouchement il y a 1 mois"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.pregnancy_postpartum is True, f"Failed for: {text}"


class TestAgeDetection:
    """Tests pour la détection de l'âge."""
    
    def test_age_explicit(self):
        """Détecte âge explicite."""
        texts = [
            "Patient de 45 ans",
            "Femme âgée de 62 ans",
            "Homme 35 ans",
            "Âge: 50 ans"
        ]
        
        expected_ages = [45, 62, 35, 50]
        
        for text, expected in zip(texts, expected_ages):
            case, _ = parse_free_text_to_case(text)
            assert case.age == expected, f"Failed for: {text}"
    
    def test_age_descriptive(self):
        """Détecte âge descriptif."""
        texts = [
            "Jeune adulte de 25 ans",
            "Personne âgée de 75 ans",
            "Adolescent de 16 ans"
        ]
        
        for text in texts:
            case, _ = parse_free_text_to_case(text)
            assert case.age is not None, f"Failed for: {text}"


class TestComplexScenarios:
    """Tests pour des scénarios complexes avec multiples informations."""
    
    def test_hsa_complete_case(self):
        """Cas complet HSA avec toutes les infos."""
        text = """
        Femme de 45 ans, céphalée brutale en coup de tonnerre depuis 2 heures.
        Intensité 10/10, pire mal de tête de sa vie.
        Pas de traumatisme, pas de fièvre.
        """
        
        case, _ = parse_free_text_to_case(text)
        
        assert case.age == 45
        assert case.onset == "thunderclap"
        assert case.profile == "acute"
        assert case.intensity == 10
        assert case.trauma is False
        assert case.fever is False
    
    def test_meningitis_complete_case(self):
        """Cas complet méningite."""
        text = """
        Homme de 28 ans, céphalée depuis 24 heures avec fièvre à 39.5°C.
        Raideur de nuque importante, photophobie.
        Intensité 9/10, vomissements.
        """
        
        case, _ = parse_free_text_to_case(text)
        
        assert case.age == 28
        assert case.fever is True
        assert case.meningeal_signs is True
        assert case.profile == "acute"
        assert case.intensity == 9
    
    def test_htic_complete_case(self):
        """Cas complet HTIC."""
        text = """
        Patient de 55 ans, céphalées progressives depuis 2 semaines.
        Pire le matin, vomissements en jet matinaux.
        Aggravé par la toux. Intensité 7/10.
        """
        
        case, _ = parse_free_text_to_case(text)
        
        assert case.age == 55
        assert case.htic_pattern is True
        assert case.profile in ["subacute", "acute"]
        assert case.intensity == 7
    
    def test_chronic_migraine_case(self):
        """Cas migraine chronique sans red flags."""
        text = """
        Femme de 35 ans, migraines chroniques depuis 5 ans.
        Céphalées quotidiennes, intensité modérée 6/10.
        Pas de déficit neurologique, pas de fièvre, pas de traumatisme.
        """
        
        case, _ = parse_free_text_to_case(text)
        
        assert case.age == 35
        assert case.profile == "chronic"
        assert case.onset == "chronic"
        assert case.intensity == 6
        assert case.neuro_deficit is False
        assert case.fever is False
        assert case.trauma is False
    
    def test_multiple_red_flags(self):
        """Cas avec multiples red flags."""
        text = """
        Homme de 60 ans, céphalée brutale depuis ce matin.
        Fièvre à 38.5°C, confusion, déficit moteur bras droit.
        Antécédent de cancer pulmonaire.
        """
        
        case, _ = parse_free_text_to_case(text)
        
        assert case.age == 60
        assert case.onset == "thunderclap"
        assert case.fever is True
        assert case.confusion is True
        assert case.neuro_deficit is True
        assert case.cancer_history is True


class TestNegationHandling:
    """Tests pour vérifier la gestion des négations."""
    
    def test_negation_priority(self):
        """Vérifie que 'pas de X' est bien détecté comme False."""
        test_cases = [
            ("Pas de fièvre", "fever", False),
            ("Pas de déficit neurologique", "neuro_deficit", False),
            ("Pas de traumatisme", "trauma", False),
            ("Pas de signes méningés", "meningeal_signs", False),
            ("Pas de confusion", "confusion", False),
        ]
        
        for text, field, expected in test_cases:
            case, _ = parse_free_text_to_case(text)
            actual = getattr(case, field)
            assert actual == expected, f"Failed for '{text}': expected {field}={expected}, got {actual}"
    
    def test_positive_after_negation(self):
        """Vérifie qu'un terme positif après négation est bien négatif."""
        text = "Patient sans déficit moteur ni trouble neurologique"
        case, _ = parse_free_text_to_case(text)
        
        assert case.neuro_deficit is False


if __name__ == "__main__":
    # Permet de lancer les tests directement
    pytest.main([__file__, "-v"])
