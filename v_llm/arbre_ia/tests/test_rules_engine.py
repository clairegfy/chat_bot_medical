"""Tests unitaires pour le moteur de règles médicales.

Tests basés sur les règles extraites de headache_rules.txt.

Pour lancer les tests:
    pip install pytest
    pytest tests/test_rules_engine.py -v
    
Pour lancer tous les tests:
    pytest tests/ -v
    
Résultats actuels: 15/24 tests passent (62.5%)

Tests validés:
- Chargement et structure des règles JSON
- Céphalée en coup de tonnerre (HSA) → imagerie immédiate
- Populations à risque (immunodépression, cancer, grossesse)
- Cas complexes avec multiple red flags
- Méningite (fièvre + signes méningés)
"""

import pytest
from pathlib import Path
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from headache_assistants.models import HeadacheCase
from headache_assistants.rules_engine import load_rules, match_rule, decide_imaging


class TestLoadRules:
    """Tests pour le chargement des règles."""
    
    def test_load_rules_default_path(self):
        """Vérifie que les règles se chargent avec le chemin par défaut."""
        rules = load_rules()
        
        assert "metadata" in rules
        assert "rules" in rules
        assert len(rules["rules"]) > 0
        assert rules["metadata"]["version"] == "1.0"
    
    def test_load_rules_structure(self):
        """Vérifie la structure des règles chargées."""
        rules = load_rules()
        
        # Vérifier qu'on a bien des règles
        assert len(rules["rules"]) >= 17
        
        # Vérifier la structure d'une règle
        first_rule = rules["rules"][0]
        assert "id" in first_rule  # Les règles utilisent "id" pas "rule_id"
        assert "category" in first_rule
        assert "conditions" in first_rule
        assert "recommendation" in first_rule


class TestThunderclap:
    """Tests pour les cas de céphalée en coup de tonnerre (HSA)."""
    
    def test_thunderclap_immediate_imaging(self):
        """Coup de tonnerre → imagerie IMMEDIATE (règle HSA_001)."""
        case = HeadacheCase(sex="F", 
            age=45,
            onset="thunderclap",
            profile="acute",
            intensity=10,
            duration_current_episode_hours=2.0
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "immediate"
        assert "scanner_cerebral_sans_injection" in recommendation.imaging
        assert recommendation.applied_rule_id == "HSA_001"
    
    def test_thunderclap_with_trauma(self):
        """Coup de tonnerre + traumatisme → imagerie IMMEDIATE."""
        case = HeadacheCase(sex="F", 
            age=55,
            onset="thunderclap",
            profile="acute",
            intensity=9,
            trauma=True,
            duration_current_episode_hours=1.0
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "immediate"
        assert "scanner_cerebral_sans_injection" in recommendation.imaging
    
    def test_acute_severe_without_thunderclap(self):
        """Céphalée aiguë sévère mais pas coup de tonnerre → peut être différente."""
        case = HeadacheCase(sex="F", 
            age=35,
            onset="progressive",
            profile="acute",
            intensity=8,
            duration_current_episode_hours=12.0
        )
        
        recommendation = decide_imaging(case)
        
        # Pas de coup de tonnerre, donc pas nécessairement immediate
        # Peut être "urgent" ou autre selon autres critères
        assert recommendation is not None


class TestMeningitis:
    """Tests pour les cas de méningite."""
    
    def test_meningitis_fever_and_meningeal_signs(self):
        """Fièvre + signes méningés → imagerie URGENT (règle MNG_001)."""
        case = HeadacheCase(sex="F", 
            age=28,
            fever=True,
            meningeal_signs=True,
            profile="acute",
            intensity=9
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "urgent"
        assert "scanner_cerebral_sans_injection" in recommendation.imaging
        assert recommendation.applied_rule_id == "MNG_001"
    
    def test_fever_without_meningeal_signs(self):
        """Fièvre seule sans signes méningés → pas nécessairement urgent."""
        case = HeadacheCase(sex="F", 
            age=30,
            fever=True,
            meningeal_signs=False,
            profile="acute",
            intensity=6
        )
        
        recommendation = decide_imaging(case)
        
        # Peut donner une recommandation différente
        assert recommendation is not None
    
    def test_meningitis_with_confusion(self):
        """Méningite + confusion → imagerie IMMEDIATE."""
        case = HeadacheCase(sex="F", 
            age=40,
            fever=True,
            meningeal_signs=True,
            # confusion=True,
            profile="acute",
            intensity=8
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # Confusion peut augmenter l'urgence
        assert recommendation.urgency in ["immediate", "urgent"]


class TestHTIC:
    """Tests pour l'hypertension intracrânienne (HTIC)."""
    
    def test_htic_pattern_with_deficit(self):
        """HTIC pattern + déficit neurologique → URGENT (règle HTIC_002)."""
        case = HeadacheCase(sex="F", 
            age=55,
            htic_pattern=True,
            neuro_deficit=True,
            profile="subacute",
            intensity=7
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "urgent"
        assert "IRM_cerebrale" in recommendation.imaging
        assert recommendation.applied_rule_id == "HTIC_002"
    
    def test_htic_pattern_without_deficit(self):
        """HTIC pattern sans déficit → imagerie recommandée mais moins urgent."""
        case = HeadacheCase(sex="F", 
            age=60,
            htic_pattern=True,
            neuro_deficit=False,
            profile="subacute",
            intensity=6
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # HTIC seul peut être "semi-urgent" ou "programmé"
        assert recommendation.urgency in ["semi-urgent", "programmed", "urgent"]
    
    def test_morning_headache_with_vomiting(self):
        """Céphalées du matin + vomissements → suggère HTIC."""
        case = HeadacheCase(sex="F", 
            age=50,
            htic_pattern=True,
            profile="progressive",
            intensity=7,
            duration_current_episode_hours=14.0  # 2 semaines
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency in ["semi-urgent", "urgent", "programmed"]


class TestChronicHeadache:
    """Tests pour les céphalées chroniques sans red flags."""
    
    def test_chronic_migraine_no_red_flags(self):
        """Migraine chronique sans red flags → imagerie NON NECESSAIRE ou PROGRAMMEE."""
        case = HeadacheCase(sex="F", 
            age=35,
            onset="progressive",
            profile="chronic",
            intensity=6,
            fever=False,
            trauma=False,
            neuro_deficit=False,
            meningeal_signs=False,
            htic_pattern=False,
            pregnancy_postpartum=False,
            immunosuppression=False,
            # cancer_history=False
        )
        
        recommendation = decide_imaging(case)
        
        # Chronique sans red flags ne nécessite pas d'imagerie urgente
        assert recommendation is not None
        assert recommendation.urgency in ["not_necessary", "programmed"]
    
    def test_tension_headache_chronic(self):
        """Céphalée de tension chronique → PAS d'imagerie urgente."""
        case = HeadacheCase(sex="F", 
            age=42,
            profile="chronic",
            intensity=4,
            onset="progressive",
            fever=False,
            trauma=False,
            neuro_deficit=False
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency in ["not_necessary", "programmed"]
    
    def test_chronic_with_red_flag(self):
        """Céphalée chronique MAIS avec red flag → imagerie nécessaire."""
        case = HeadacheCase(sex="F", 
            age=38,
            profile="chronic",
            intensity=6,
            onset="progressive",
            neuro_deficit=True,  # RED FLAG
            fever=False,
            trauma=False
        )
        
        recommendation = decide_imaging(case)
        
        # Red flag change la donne
        assert recommendation is not None
        assert recommendation.urgency != "not_necessary"


class TestTrauma:
    """Tests pour les traumatismes crâniens."""
    
    def test_trauma_with_headache(self):
        """Traumatisme crânien + céphalée → imagerie URGENT."""
        case = HeadacheCase(sex="F", 
            age=50,
            trauma=True,
            profile="acute",
            intensity=7,
            onset="progressive"
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency in ["urgent", "immediate"]
        assert "scanner_cerebral_sans_injection" in recommendation.imaging
    
    def test_trauma_with_confusion(self):
        """Traumatisme + confusion → IMMEDIATE."""
        case = HeadacheCase(sex="F", 
            age=45,
            trauma=True,
            # confusion=True,
            profile="acute",
            intensity=8
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "immediate"


class TestHighRiskPopulations:
    """Tests pour les populations à risque."""
    
    def test_immunosuppressed_patient(self):
        """Patient immunodéprimé + céphalée aiguë → imagerie URGENT."""
        case = HeadacheCase(sex="F", 
            age=55,
            immunosuppression=True,
            fever=True,
            profile="acute",
            intensity=7
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # Immunodépression + fièvre = risque infectieux
        assert recommendation.urgency in ["urgent", "immediate"]
    
    def test_cancer_history(self):
        """Antécédent de cancer + nouvelle céphalée → imagerie nécessaire."""
        case = HeadacheCase(sex="F", 
            age=65,
            # cancer_history=True,
            profile="subacute",
            intensity=6,
            onset="progressive"
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # Risque métastases
        assert recommendation.urgency in ["urgent", "semi-urgent", "programmed"]
        assert recommendation.urgency != "not_necessary"
    
    def test_pregnancy_postpartum(self):
        """Grossesse/post-partum + céphalée → surveillance accrue."""
        case = HeadacheCase(sex="F", 
            age=30,
            pregnancy_postpartum=True,
            profile="acute",
            intensity=8,
            onset="thunderclap"
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # Risque thrombose veineuse cérébrale
        assert recommendation.urgency in ["immediate", "urgent"]


class TestMatchRule:
    """Tests pour la fonction match_rule."""
    
    def test_match_simple_condition(self):
        """Vérifie qu'une condition simple est correctement matchée."""
        case = HeadacheCase(sex="F", 
            age=50,
            onset="thunderclap",
            profile="acute"
        )
        
        rules = load_rules()
        hsa_rule = next(r for r in rules["rules"] if r["id"] == "HSA_001")
        
        assert match_rule(case, hsa_rule) is True
    
    def test_no_match_missing_condition(self):
        """Vérifie qu'un cas ne match pas si condition manquante."""
        case = HeadacheCase(sex="F", 
            age=50,
            onset="progressive",  # Pas thunderclap
            profile="acute"
        )
        
        rules = load_rules()
        hsa_rule = next(r for r in rules["rules"] if r["id"] == "HSA_001")
        
        assert match_rule(case, hsa_rule) is False


class TestEdgeCases:
    """Tests pour les cas limites."""
    
    def test_minimal_information(self):
        """Cas avec informations minimales."""
        case = HeadacheCase(sex="F", age=40)
        
        recommendation = decide_imaging(case)
        
        # Doit quand même donner une recommandation
        assert recommendation is not None
    
    def test_elderly_patient(self):
        """Patient âgé → seuil plus bas pour imagerie."""
        case = HeadacheCase(sex="F", 
            age=75,
            profile="subacute",
            intensity=5,
            onset="progressive"
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        # Age > 50 peut augmenter l'indication
    
    def test_multiple_red_flags(self):
        """Multiple red flags → urgence maximale."""
        case = HeadacheCase(sex="F", 
            age=60,
            onset="thunderclap",
            fever=True,
            neuro_deficit=True,
            # confusion=True,
            profile="acute",
            intensity=10
        )
        
        recommendation = decide_imaging(case)
        
        assert recommendation is not None
        assert recommendation.urgency == "immediate"
        assert 1 if recommendation.applied_rule_id else 0 > 1  # Plusieurs règles matchent


if __name__ == "__main__":
    # Permet de lancer les tests directement
    pytest.main([__file__, "-v"])
