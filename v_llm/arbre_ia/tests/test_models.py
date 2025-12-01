"""Tests pour les modèles Pydantic.

Teste la validation des données, les méthodes des modèles,
et la cohérence avec les règles médicales.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from headache_assistants.models import (
    HeadacheCase,
    ImagingRecommendation,
    ChatMessage,
    ChatResponse
)


class TestHeadacheCase:
    """Tests pour le modèle HeadacheCase."""
    
    def test_minimal_valid_case(self):
        """Test avec les champs minimaux requis."""
        case = HeadacheCase(age=45, sex="M")
        assert case.age == 45
        assert case.sex == "M"
        assert case.profile == "unknown"
        assert case.onset == "unknown"
    
    def test_complete_case(self):
        """Test avec tous les champs renseignés."""
        case = HeadacheCase(
            age=55,
            sex="F",
            profile="acute",
            onset="thunderclap",
            duration_current_episode_hours=2.5,
            fever=True,
            meningeal_signs=True,
            neuro_deficit=False,
            seizure=False,
            htic_pattern=False,
            pregnancy_postpartum=False,
            trauma=False,
            recent_pl_or_peridural=False,
            immunosuppression=False,
            red_flag_context=["age>50", "first_headache"],
            headache_profile="unknown"
        )
        assert case.age == 55
        assert case.onset == "thunderclap"
        assert case.fever is True
        assert len(case.red_flag_context) == 2
    
    def test_age_validation_negative(self):
        """Test validation d'âge négatif."""
        with pytest.raises(ValidationError):
            HeadacheCase(age=-5, sex="M")
    
    def test_age_validation_too_high(self):
        """Test validation d'âge trop élevé."""
        with pytest.raises(ValidationError):
            HeadacheCase(age=150, sex="M")
    
    def test_duration_validation_negative(self):
        """Test validation de durée négative."""
        with pytest.raises(ValidationError):
            HeadacheCase(
                age=45,
                sex="M",
                duration_current_episode_hours=-5.0
            )
    
    def test_has_red_flags_thunderclap(self):
        """Test détection de red flag avec coup de tonnerre."""
        case = HeadacheCase(
            age=45,
            sex="M",
            onset="thunderclap"
        )
        assert case.has_red_flags() is True
    
    def test_has_red_flags_fever(self):
        """Test détection de red flag avec fièvre."""
        case = HeadacheCase(
            age=45,
            sex="M",
            fever=True
        )
        assert case.has_red_flags() is True
    
    def test_has_red_flags_age_over_50(self):
        """Test détection de red flag âge > 50 avec céphalée aiguë."""
        case = HeadacheCase(
            age=55,
            sex="F",
            profile="acute"
        )
        assert case.has_red_flags() is True
    
    def test_no_red_flags(self):
        """Test cas sans red flags."""
        case = HeadacheCase(
            age=30,
            sex="M",
            profile="chronic",
            onset="chronic",
            fever=False
        )
        assert case.has_red_flags() is False
    
    def test_is_emergency_thunderclap(self):
        """Test urgence vitale avec coup de tonnerre."""
        case = HeadacheCase(
            age=45,
            sex="M",
            onset="thunderclap"
        )
        assert case.is_emergency() is True
    
    def test_is_emergency_meningitis(self):
        """Test urgence vitale avec suspicion de méningite."""
        case = HeadacheCase(
            age=35,
            sex="F",
            fever=True,
            meningeal_signs=True
        )
        assert case.is_emergency() is True
    
    def test_is_not_emergency(self):
        """Test cas non urgent."""
        case = HeadacheCase(
            age=30,
            sex="M",
            profile="chronic"
        )
        assert case.is_emergency() is False


class TestImagingRecommendation:
    """Tests pour le modèle ImagingRecommendation."""
    
    def test_minimal_recommendation(self):
        """Test recommandation minimale."""
        rec = ImagingRecommendation(
            urgency="none",
            comment="Pas d'imagerie nécessaire"
        )
        assert rec.urgency == "none"
        assert rec.imaging == []
        assert rec.applied_rule_id is None
    
    def test_emergency_recommendation(self):
        """Test recommandation urgente."""
        rec = ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection", "ponction_lombaire"],
            urgency="immediate",
            comment="Suspicion d'HSA - urgence vitale",
            applied_rule_id="HSA_001"
        )
        assert rec.urgency == "immediate"
        assert len(rec.imaging) == 2
        assert rec.is_emergency() is True
        assert rec.requires_imaging() is True
    
    def test_invalid_imaging_type(self):
        """Test validation d'examen invalide."""
        with pytest.raises(ValidationError):
            ImagingRecommendation(
                imaging=["examen_invalide"],
                urgency="urgent",
                comment="Test"
            )
    
    def test_valid_imaging_types(self):
        """Test types d'examens valides."""
        valid_exams = [
            "scanner_cerebral_sans_injection",
            "IRM_cerebrale",
            "ponction_lombaire",
            "angioscanner_cerebral"
        ]
        rec = ImagingRecommendation(
            imaging=valid_exams,
            urgency="urgent",
            comment="Examens multiples"
        )
        assert len(rec.imaging) == 4
    
    def test_no_imaging_needed(self):
        """Test cas sans imagerie."""
        rec = ImagingRecommendation(
            imaging=["aucun"],
            urgency="none",
            comment="Migraine typique, pas d'imagerie"
        )
        assert rec.requires_imaging() is False


class TestChatMessage:
    """Tests pour le modèle ChatMessage."""
    
    def test_user_message(self):
        """Test message utilisateur."""
        msg = ChatMessage(
            role="user",
            content="J'ai mal à la tête"
        )
        assert msg.role == "user"
        assert msg.content == "J'ai mal à la tête"
        assert isinstance(msg.timestamp, datetime)
    
    def test_assistant_message(self):
        """Test message assistant."""
        msg = ChatMessage(
            role="assistant",
            content="Depuis combien de temps ?",
            metadata={"confidence": 0.95}
        )
        assert msg.role == "assistant"
        assert msg.metadata["confidence"] == 0.95
    
    def test_empty_content_validation(self):
        """Test validation contenu vide."""
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="")
    
    def test_whitespace_only_content(self):
        """Test validation contenu avec espaces uniquement."""
        with pytest.raises(ValidationError):
            ChatMessage(role="user", content="   ")
    
    def test_content_trimming(self):
        """Test nettoyage du contenu."""
        msg = ChatMessage(
            role="user",
            content="  Message avec espaces  "
        )
        assert msg.content == "Message avec espaces"


class TestChatResponse:
    """Tests pour le modèle ChatResponse."""
    
    def test_minimal_response(self):
        """Test réponse minimale."""
        resp = ChatResponse(
            message="Bonjour",
            session_id="test-123"
        )
        assert resp.message == "Bonjour"
        assert resp.session_id == "test-123"
        assert resp.requires_more_info is True
        assert resp.dialogue_complete is False
    
    def test_complete_dialogue_response(self):
        """Test réponse avec dialogue complet."""
        case = HeadacheCase(age=45, sex="M")
        recommendation = ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection"],
            urgency="urgent",
            comment="Suspicion de lésion"
        )
        
        resp = ChatResponse(
            message="Voici ma recommandation",
            session_id="test-123",
            headache_case=case,
            imaging_recommendation=recommendation,
            requires_more_info=False,
            dialogue_complete=True,
            confidence_score=0.85
        )
        
        assert resp.dialogue_complete is True
        assert resp.confidence_score == 0.85
        assert resp.headache_case is not None
        assert resp.imaging_recommendation is not None
    
    def test_confidence_validation_too_high(self):
        """Test validation score de confiance trop élevé."""
        with pytest.raises(ValidationError):
            ChatResponse(
                message="Test",
                session_id="test-123",
                confidence_score=1.5
            )
    
    def test_confidence_validation_negative(self):
        """Test validation score de confiance négatif."""
        with pytest.raises(ValidationError):
            ChatResponse(
                message="Test",
                session_id="test-123",
                confidence_score=-0.5
            )
    
    def test_is_emergency_response(self):
        """Test détection de réponse d'urgence."""
        recommendation = ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection"],
            urgency="immediate",
            comment="Urgence vitale"
        )
        
        resp = ChatResponse(
            message="URGENCE",
            session_id="test-123",
            imaging_recommendation=recommendation
        )
        
        assert resp.is_emergency_response() is True


class TestModelsIntegration:
    """Tests d'intégration des modèles."""
    
    def test_complete_workflow(self):
        """Test workflow complet: case → recommendation → response."""
        # Créer un cas
        case = HeadacheCase(
            age=60,
            sex="M",
            profile="acute",
            onset="thunderclap",
            fever=False,
            neuro_deficit=False
        )
        
        assert case.has_red_flags() is True
        assert case.is_emergency() is True
        
        # Créer une recommandation
        recommendation = ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection", "ponction_lombaire"],
            urgency="immediate",
            comment="Suspicion HSA - coup de tonnerre",
            applied_rule_id="THUNDERCLAP_001"
        )
        
        assert recommendation.is_emergency() is True
        
        # Créer une réponse
        response = ChatResponse(
            message="⚠️ URGENCE VITALE: Consultez immédiatement les urgences",
            session_id="emergency-001",
            headache_case=case,
            imaging_recommendation=recommendation,
            requires_more_info=False,
            dialogue_complete=True,
            confidence_score=0.95
        )
        
        assert response.is_emergency_response() is True
        assert response.dialogue_complete is True
    
    def test_json_serialization(self):
        """Test sérialisation JSON des modèles."""
        case = HeadacheCase(
            age=45,
            sex="F",
            profile="chronic"
        )
        
        # Test model_dump (Pydantic v2)
        case_dict = case.model_dump()
        assert case_dict["age"] == 45
        assert case_dict["sex"] == "F"
        
        # Test model_dump_json
        case_json = case.model_dump_json()
        assert isinstance(case_json, str)
        assert "45" in case_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
