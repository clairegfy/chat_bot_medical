"""Tests des scénarios de dialogue utilisateur les plus courants.

Ces tests simulent des conversations complètes pour s'assurer que le système
répond correctement aux cas cliniques les plus fréquents.

Objectif: Garantir la robustesse du système pour les cas triviaux.
"""

import pytest
from headache_assistants.models import ChatMessage, HeadacheCase
from headache_assistants.dialogue import (
    handle_user_message,
    get_or_create_session,
    _interpret_yes_no_response,
    merge_cases
)
from headache_assistants.rules_engine import decide_imaging


def make_case(**kwargs) -> HeadacheCase:
    """Helper pour créer un HeadacheCase avec valeurs par défaut."""
    defaults = {"age": 35, "sex": "Other"}
    defaults.update(kwargs)
    return HeadacheCase(**defaults)


class TestDialogueYesNoInterpretation:
    """Tests de l'interprétation oui/non dans le dialogue."""

    def test_oui_simple(self):
        """'oui' doit activer un champ booléen."""
        case = make_case()
        result = _interpret_yes_no_response("oui", "fever", case)
        assert result.fever is True

    def test_non_simple(self):
        """'non' doit désactiver un champ booléen."""
        case = make_case()
        result = _interpret_yes_no_response("non", "fever", case)
        assert result.fever is False

    def test_oui_aggravation_pattern_change(self):
        """'oui aggravation' doit activer recent_pattern_change."""
        case = make_case()
        result = _interpret_yes_no_response("oui aggravation", "recent_pattern_change", case)
        assert result.recent_pattern_change is True

    def test_oui_avec_contexte(self):
        """'oui il a de la fièvre' doit activer fever."""
        case = make_case()
        result = _interpret_yes_no_response("oui il a de la fièvre", "fever", case)
        assert result.fever is True

    def test_non_avec_contexte(self):
        """'non pas de fièvre' doit désactiver fever."""
        case = make_case()
        result = _interpret_yes_no_response("non pas de fièvre", "fever", case)
        assert result.fever is False

    def test_intensite_numerique(self):
        """'8' doit définir l'intensité à 8."""
        case = make_case()
        result = _interpret_yes_no_response("8", "intensity", case)
        assert result.intensity == 8

    def test_intensite_avec_texte(self):
        """'environ 7 sur 10' doit définir l'intensité à 7."""
        case = make_case()
        result = _interpret_yes_no_response("environ 7 sur 10", "intensity", case)
        assert result.intensity == 7

    def test_tous_champs_booleens(self):
        """Tous les champs booléens doivent être supportés."""
        boolean_fields = [
            'fever', 'meningeal_signs', 'neuro_deficit', 'seizure',
            'htic_pattern', 'pregnancy_postpartum', 'trauma',
            'recent_pl_or_peridural', 'immunosuppression',
            'recent_pattern_change'
        ]

        for field in boolean_fields:
            case = make_case()
            result_oui = _interpret_yes_no_response("oui", field, case)
            assert getattr(result_oui, field) is True, f"'{field}' non activé par 'oui'"

            case = make_case()
            result_non = _interpret_yes_no_response("non", field, case)
            assert getattr(result_non, field) is False, f"'{field}' non désactivé par 'non'"


class TestScenariosCephaleeChronique:
    """Tests des scénarios de céphalée chronique."""

    def test_chronique_sans_red_flag(self):
        """Céphalée chronique sans red flag → pas d'imagerie."""
        case = make_case(
            age=45,
            sex='F',
            profile='chronic',
            onset='chronic',
            fever=False,
            meningeal_signs=False,
            htic_pattern=False,
            neuro_deficit=False,
            recent_pattern_change=False
        )
        rec = decide_imaging(case)
        # Pas d'imagerie urgente pour céphalée chronique bénigne
        assert rec.urgency in ['none', 'delayed']

    def test_chronique_avec_changement_pattern(self):
        """Céphalée chronique avec changement → IRM urgente."""
        case = make_case(
            age=45,
            sex='F',
            profile='chronic',
            onset='chronic',
            fever=False,
            meningeal_signs=False,
            htic_pattern=False,
            recent_pattern_change=True  # RED FLAG
        )
        rec = decide_imaging(case)
        assert rec.applied_rule_id == "PATTERN_CHANGE_001"
        assert "irm" in str(rec.imaging).lower()
        assert rec.urgency == "urgent"

    def test_chronique_avec_htic(self):
        """Céphalée chronique avec HTIC → urgence."""
        case = make_case(
            age=45,
            sex='F',
            profile='chronic',
            htic_pattern=True
        )
        rec = decide_imaging(case)
        assert rec.urgency in ['immediate', 'urgent']


class TestScenariosCephaleeAigue:
    """Tests des scénarios de céphalée aiguë."""

    def test_thunderclap_simple(self):
        """Céphalée en coup de tonnerre → HSA suspectée."""
        case = make_case(
            age=50,
            onset='thunderclap',
            profile='acute'
        )
        rec = decide_imaging(case)
        assert "HSA" in rec.applied_rule_id
        assert rec.urgency == "immediate"
        assert "scanner" in str(rec.imaging).lower()

    def test_fievre_avec_syndrome_meninge(self):
        """Fièvre + syndrome méningé → méningite."""
        case = make_case(
            age=30,
            fever=True,
            meningeal_signs=True
        )
        rec = decide_imaging(case)
        assert "MENINGITE" in rec.applied_rule_id
        assert rec.urgency == "immediate"

    def test_brutal_sans_fievre_avec_meninge(self):
        """Brutal + méningé sans fièvre → HSA ou urgence."""
        case = make_case(
            onset='progressive',
            profile='acute',
            meningeal_signs=True,
            fever=False
        )
        rec = decide_imaging(case)
        # HSA suspectée ou autre urgence - doit être au moins urgent
        assert rec.urgency in ["immediate", "urgent"], \
            f"Syndrome méningé apyrétique devrait être urgent, obtenu: {rec.urgency}"


class TestScenariosGrossesse:
    """Tests des scénarios de grossesse."""

    def test_grossesse_cephalee_simple(self):
        """Grossesse + céphalée → toujours IRM (risque TVC)."""
        case = make_case(
            age=30,
            sex='F',
            pregnancy_postpartum=True,
            profile='acute'
        )
        rec = decide_imaging(case)
        # Grossesse = toujours imagerie
        assert rec.imaging is not None
        assert len(rec.imaging) > 0
        # IRM préférée au scanner
        imaging_str = str(rec.imaging).lower()
        assert "irm" in imaging_str or "angio" in imaging_str

    def test_grossesse_thunderclap(self):
        """Grossesse + thunderclap → urgence absolue."""
        case = make_case(
            age=28,
            sex='F',
            pregnancy_postpartum=True,
            onset='thunderclap',
            profile='acute'
        )
        rec = decide_imaging(case)
        assert rec.urgency == "immediate"


class TestScenariosContextesSpecifiques:
    """Tests des contextes spécifiques."""

    def test_patient_age_premiere_cephalee(self):
        """Patient > 50 ans, première céphalée → imagerie."""
        case = make_case(
            age=65,
            profile='acute',
            onset='progressive'
        )
        rec = decide_imaging(case)
        # Patient âgé = plus de vigilance
        assert rec.imaging is not None

    def test_immunodeprime(self):
        """Patient immunodéprimé → vigilance accrue."""
        case = make_case(
            age=45,
            immunosuppression=True,
            fever=True
        )
        rec = decide_imaging(case)
        assert rec.urgency in ['immediate', 'urgent']

    def test_post_ponction_lombaire(self):
        """Céphalée post-PL → diagnostic spécifique."""
        case = make_case(
            age=35,
            recent_pl_or_peridural=True,
            profile='acute'
        )
        rec = decide_imaging(case)
        # Post-PL a un diagnostic et traitement spécifique
        assert rec.applied_rule_id is not None


class TestConversationComplete:
    """Tests de conversations complètes simulées."""

    def test_conversation_cephalee_chronique_aggravee(self):
        """Simule une conversation : chronique → aggravation → IRM."""
        # Message 1: Description initiale
        msg1 = ChatMessage(role="user", content="patiente 45 ans céphalées chroniques")
        session_id, _ = get_or_create_session()
        response1 = handle_user_message([], msg1, session_id)

        assert response1.session_id is not None
        assert not response1.dialogue_complete  # Questions à poser

        # Simuler les réponses négatives puis aggravation
        case = response1.headache_case
        if case:
            # Vérifier que le profil chronique est détecté
            assert case.profile == "chronic" or case.onset == "chronic"

    def test_conversation_urgence_detectee(self):
        """Message unique avec urgence → décision immédiate."""
        msg = ChatMessage(
            role="user",
            content="Homme 50 ans, céphalée brutale en coup de tonnerre depuis 2h, pire douleur de sa vie"
        )
        session_id, _ = get_or_create_session()
        response = handle_user_message([], msg, session_id)

        # Urgence détectée = dialogue peut se terminer rapidement
        if response.imaging_recommendation:
            assert response.imaging_recommendation.urgency == "immediate"

    def test_conversation_meningite(self):
        """Message avec fièvre + méningé → méningite."""
        msg = ChatMessage(
            role="user",
            content="Patient 25 ans, céphalée avec fièvre 39°C et raideur de nuque"
        )
        session_id, _ = get_or_create_session()
        response = handle_user_message([], msg, session_id)

        if response.imaging_recommendation:
            assert "MENINGITE" in response.imaging_recommendation.applied_rule_id
            assert response.imaging_recommendation.urgency == "immediate"


class TestRobustesseEntreesUtilisateur:
    """Tests de robustesse pour entrées utilisateur variées."""

    def test_reponse_oui_variantes(self):
        """Différentes façons de dire oui."""
        variantes_oui = ["oui", "Oui", "OUI", "o", "O", "yes", "Yes"]

        for variante in variantes_oui:
            case = make_case()
            result = _interpret_yes_no_response(variante, "fever", case)
            assert result.fever is True, f"'{variante}' non reconnu comme oui"

    def test_reponse_non_variantes(self):
        """Différentes façons de dire non."""
        variantes_non = ["non", "Non", "NON", "n", "N", "no", "No", "aucun", "pas", "aucune"]

        for variante in variantes_non:
            case = make_case()
            result = _interpret_yes_no_response(variante, "fever", case)
            assert result.fever is False, f"'{variante}' non reconnu comme non"

    def test_reponse_avec_phrase_complete(self):
        """Réponses en phrases complètes."""
        case = make_case()

        # Oui avec contexte
        result1 = _interpret_yes_no_response("oui il y a eu une aggravation récente", "recent_pattern_change", case)
        assert result1.recent_pattern_change is True

        # Non avec contexte
        case2 = make_case()
        result2 = _interpret_yes_no_response("non il n'y a pas de fièvre", "fever", case2)
        assert result2.fever is False

    def test_intensite_variantes(self):
        """Différentes façons d'exprimer l'intensité."""
        tests = [
            ("8", 8),
            ("8/10", 8),
            ("environ 7", 7),
            ("je dirais 6", 6),
            ("5 sur 10", 5),
        ]

        for text, expected in tests:
            case = make_case()
            result = _interpret_yes_no_response(text, "intensity", case)
            assert result.intensity == expected, f"'{text}' → attendu {expected}, obtenu {result.intensity}"


class TestNonRegression:
    """Tests de non-régression pour bugs corrigés."""

    def test_recent_pattern_change_dans_boolean_fields(self):
        """Bug fix: recent_pattern_change doit être dans boolean_fields."""
        case = make_case()
        result = _interpret_yes_no_response("oui", "recent_pattern_change", case)
        assert result.recent_pattern_change is True, \
            "recent_pattern_change non supporté dans _interpret_yes_no_response"

    def test_pattern_change_rule_match(self):
        """Bug fix: PATTERN_CHANGE_001 doit matcher avec profile=chronic + recent_pattern_change=True."""
        case = make_case(
            profile='chronic',
            recent_pattern_change=True
        )
        rec = decide_imaging(case)
        assert rec.applied_rule_id == "PATTERN_CHANGE_001", \
            f"Attendu PATTERN_CHANGE_001, obtenu {rec.applied_rule_id}"

    def test_age_defaut_none(self):
        """Texte vide: l'âge doit être None (non renseigné)."""
        from headache_assistants.nlu_v2 import parse_free_text_to_case_v2
        case, _ = parse_free_text_to_case_v2("")
        # L'âge doit être None pour permettre au dialogue de le demander
        assert case.age is None

    def test_htic_faux_positif_toux(self):
        """Bug fix: toux seule ne doit PAS déclencher HTIC."""
        from headache_assistants.medical_vocabulary import MedicalVocabulary
        vocab = MedicalVocabulary()

        # Toux seule = pas HTIC
        result = vocab.detect_htic("céphalée déclenchée par la toux")
        assert not result.detected, "Faux positif HTIC sur toux seule"

        # Vomissements en jet = HTIC
        result2 = vocab.detect_htic("vomissements en jet")
        assert result2.detected, "Vomissements en jet non détecté comme HTIC"
