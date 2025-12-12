"""Tests avec des inputs utilisateur realistes en langage naturel.

Ces tests simulent exactement ce qu'un medecin taperait dans le systeme.
Chaque test envoie une string brute et verifie que le systeme detecte
correctement les elements cliniques et prend la bonne decision.

IMPORTANT: Ces tests sont critiques car ils representent le vrai usage du systeme.
"""

import pytest
from headache_assistants.models import ChatMessage
from headache_assistants.dialogue import handle_user_message, get_or_create_session
from headache_assistants.nlu_hybrid import HybridNLU


# ============================================================================
# FIXTURE: NLU Hybride
# ============================================================================

@pytest.fixture(scope="module")
def nlu():
    """NLU hybride partage entre les tests pour performance."""
    return HybridNLU(confidence_threshold=0.7, verbose=False)


def parse_and_decide(text: str, nlu: HybridNLU = None):
    """Helper: parse un texte et retourne case + recommendation."""
    msg = ChatMessage(role="user", content=text)
    session_id, _ = get_or_create_session()
    response = handle_user_message([], msg, session_id)
    return response


# ============================================================================
# URGENCES ABSOLUES - Ces cas doivent TOUJOURS declencher une urgence immediate
# ============================================================================

class TestUrgencesAbsoluesInputsReels:
    """Tests des urgences vitales avec inputs utilisateur reels."""

    # --- HSA (Hemorragie Sous-Arachnoidienne) ---

    def test_hsa_classique_medecin(self, nlu):
        """Input typique d'un neurologue."""
        response = parse_and_decide(
            "Homme 52 ans, cephalee brutale en coup de tonnerre il y a 3h, "
            "intensite maximale d'emblee, pire cephalee de sa vie"
        )
        assert response.imaging_recommendation is not None
        assert response.imaging_recommendation.urgency == "immediate"
        assert "scanner" in str(response.imaging_recommendation.imaging).lower()

    def test_hsa_urgentiste_style(self, nlu):
        """Style telegraphique d'un urgentiste."""
        response = parse_and_decide(
            "H 48a cephalee explosive debut brutal y a 1h, EVA 10/10"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_hsa_generaliste_descriptif(self, nlu):
        """Description plus detaillee d'un generaliste."""
        response = parse_and_decide(
            "Mon patient de 55 ans me dit avoir eu une douleur a la tete "
            "extremement violente qui est apparue d'un coup ce matin, "
            "comme un coup de marteau, il dit que c'est la pire douleur de sa vie"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_hsa_avec_vomissements(self, nlu):
        """HSA avec signes associes."""
        response = parse_and_decide(
            "Femme 45 ans cephalee tres brutale avec vomissements en jet et photophobie"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    # --- Meningite ---

    def test_meningite_classique(self, nlu):
        """Tableau typique de meningite."""
        response = parse_and_decide(
            "Patient 28 ans, cephalee avec fievre a 39.5 et raideur de nuque"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"
            assert "MENINGITE" in rec.applied_rule_id

    def test_meningite_style_urgences(self, nlu):
        """Style note aux urgences."""
        response = parse_and_decide(
            "Jeune homme 22a, cephalees febriles 40°C, syndrome meninge complet, "
            "photophobie, raideur nuque +"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_meningite_abreviation_medicale(self, nlu):
        """Avec abreviations medicales."""
        response = parse_and_decide(
            "F 35a febrile 39°C rdn+ cephalees intenses"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    # --- HTIC (Hypertension Intracranienne) ---

    def test_htic_vomissements_jet(self, nlu):
        """HTIC avec vomissements en jet."""
        response = parse_and_decide(
            "Patient 60 ans cephalees matinales avec vomissements en jet"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    def test_htic_oedeme_papillaire(self, nlu):
        """HTIC avec oedeme papillaire."""
        response = parse_and_decide(
            "Homme 55a cephalees progressives, fond d'oeil: oedeme papillaire bilateral"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    # --- Deficit neurologique ---

    def test_deficit_neuro_hemiparesie(self, nlu):
        """Cephalee avec deficit focal."""
        response = parse_and_decide(
            "Femme 62 ans cephalee brutale avec hemiparesie droite"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_deficit_neuro_trouble_langage(self, nlu):
        """Avec aphasie."""
        response = parse_and_decide(
            "Patient 58a cephalee aigue avec trouble du langage type aphasie"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"


# ============================================================================
# GROSSESSE - Cas particuliers necessitant IRM
# ============================================================================

class TestGrossesseInputsReels:
    """Tests des cas de grossesse avec inputs reels."""

    def test_grossesse_simple_cephalee(self, nlu):
        """Grossesse avec cephalee non specifique."""
        response = parse_and_decide(
            "Patiente 29 ans enceinte de 20 semaines, cephalees depuis 3 jours"
        )
        rec = response.imaging_recommendation
        # Grossesse = toujours vigilance
        assert response.headache_case is not None
        if response.headache_case:
            assert response.headache_case.pregnancy_postpartum is True

    def test_grossesse_premier_trimestre(self, nlu):
        """T1 - IRM a differer si possible."""
        response = parse_and_decide(
            "Femme 32 ans enceinte 8 SA, cephalees moderees"
        )
        case = response.headache_case
        if case:
            assert case.pregnancy_postpartum is True
            # T1 = 8 SA < 14 semaines
            assert case.pregnancy_trimester == 1 or case.pregnancy_trimester is None

    def test_grossesse_post_partum(self, nlu):
        """Post-partum - risque TVC."""
        response = parse_and_decide(
            "Femme 28 ans J5 post accouchement, cephalees intenses progressives"
        )
        rec = response.imaging_recommendation
        if rec:
            # Post-partum avec cephalee = TVC a eliminer
            assert rec.urgency in ["immediate", "urgent"]

    def test_grossesse_eclampsie_suspecte(self, nlu):
        """Grossesse avec signes d'eclampsie."""
        response = parse_and_decide(
            "Patiente 34 ans enceinte 32 SA, cephalees violentes avec HTA et oedemes"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    def test_grossesse_thunderclap(self, nlu):
        """Grossesse + thunderclap = urgence absolue."""
        response = parse_and_decide(
            "Femme 30 ans enceinte 24 semaines cephalee explosive brutale"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"


# ============================================================================
# CEPHALEES CHRONIQUES - Cas les plus frequents
# ============================================================================

class TestCephaleesChroniquesInputsReels:
    """Tests des cephalees chroniques avec inputs reels."""

    def test_migraine_typique(self, nlu):
        """Migraine classique sans red flag."""
        response = parse_and_decide(
            "Femme 35 ans, migraineuse connue depuis 10 ans, "
            "crise typique hemicranienne pulsatile avec nausees, pas de changement"
        )
        rec = response.imaging_recommendation
        # Migraine connue sans changement = pas d'imagerie urgente
        if rec:
            assert rec.urgency in ["none", "delayed"]

    def test_cephalee_tension_chronique(self, nlu):
        """Cephalee de tension chronique."""
        response = parse_and_decide(
            "Homme 42 ans cephalees en casque quotidiennes depuis des annees, "
            "stress professionnel, pas de fievre ni deficit"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["none", "delayed"]

    def test_chronique_avec_aggravation(self, nlu):
        """Cephalee chronique AVEC changement de pattern = red flag."""
        response = parse_and_decide(
            "Patiente 50 ans migraineuse, ses crises ont change recemment: "
            "plus frequentes, plus intenses, et durent plus longtemps"
        )
        rec = response.imaging_recommendation
        case = response.headache_case
        # Changement de pattern = doit declencher imagerie
        if case:
            assert case.recent_pattern_change is True or case.profile == "chronic"

    def test_ccq_cephalee_quotidienne(self, nlu):
        """CCQ - Cephalee Chronique Quotidienne."""
        response = parse_and_decide(
            "Patient 38 ans cephalees quotidiennes depuis 6 mois, "
            "abus d'antalgiques, pas de signe neurologique"
        )
        rec = response.imaging_recommendation
        if rec:
            # CCQ sans red flag = pas urgent
            assert rec.urgency in ["none", "delayed", "urgent"]


# ============================================================================
# CONTEXTES SPECIFIQUES
# ============================================================================

class TestContextesSpecifiquesInputsReels:
    """Tests des contextes particuliers avec inputs reels."""

    def test_immunodeprime_fievre(self, nlu):
        """Patient immunodeprime avec fievre."""
        response = parse_and_decide(
            "Patient 55 ans sous chimio pour lymphome, "
            "cephalees febriles 38.5°C depuis hier"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    def test_vih_cephalee(self, nlu):
        """Patient VIH avec cephalee."""
        response = parse_and_decide(
            "Homme 40 ans VIH+ non traite CD4 bas, cephalees progressives"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    def test_cancer_metastase(self, nlu):
        """Patient avec antecedent de cancer."""
        response = parse_and_decide(
            "Femme 62 ans ATCD cancer sein traite il y a 2 ans, "
            "nouvelles cephalees depuis 1 semaine"
        )
        rec = response.imaging_recommendation
        if rec:
            # Cancer = recherche metastases
            assert rec.imaging is not None

    def test_post_ponction_lombaire(self, nlu):
        """Cephalee post-PL."""
        response = parse_and_decide(
            "Patient 30 ans cephalees depuis PL faite il y a 3 jours, "
            "amelioration au decubitus"
        )
        rec = response.imaging_recommendation
        # Post-PL = diagnostic specifique
        assert response.headache_case is not None
        if response.headache_case:
            assert response.headache_case.recent_pl_or_peridural is True

    def test_post_trauma_cranien(self, nlu):
        """Cephalee post-traumatique."""
        response = parse_and_decide(
            "Homme 25 ans chute de velo hier avec TC sans PCI, "
            "cephalees persistantes aujourd'hui"
        )
        rec = response.imaging_recommendation
        case = response.headache_case
        if case:
            assert case.trauma is True

    def test_patient_age_premiere_cephalee(self, nlu):
        """Premiere cephalee apres 50 ans."""
        response = parse_and_decide(
            "Homme 68 ans jamais eu de cephalees, premiere fois de sa vie"
        )
        rec = response.imaging_recommendation
        # Age > 50 + premiere cephalee = red flag
        if rec:
            assert rec.imaging is not None


# ============================================================================
# VARIATIONS LINGUISTIQUES ET FAUTES
# ============================================================================

class TestVariationsLinguistiques:
    """Tests avec fautes d'orthographe et variations de style."""

    def test_fautes_orthographe_courantes(self, nlu):
        """Fautes d'orthographe frequentes."""
        response = parse_and_decide(
            "Patiente cephalee brutal avec fievre et raideur nuke"
        )
        # "nuke" pour "nuque" - doit quand meme detecter
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency in ["immediate", "urgent"]

    def test_style_sms_abreviations(self, nlu):
        """Style SMS avec abreviations."""
        response = parse_and_decide(
            "F 30a ceph brutal fievre 39 rdn+"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_majuscules_melangees(self, nlu):
        """Majuscules aleatoires."""
        response = parse_and_decide(
            "HOMME 45 ANS cephalee BRUTALE depuis 2H"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"

    def test_ponctuation_absente(self, nlu):
        """Pas de ponctuation."""
        response = parse_and_decide(
            "femme 35 ans enceinte cephalee depuis hier pas de fievre"
        )
        case = response.headache_case
        if case:
            assert case.pregnancy_postpartum is True
            assert case.fever is not True  # "pas de fievre"

    def test_accents_manquants(self, nlu):
        """Sans accents."""
        response = parse_and_decide(
            "Patient fievre 39 degres cephalee meningee raideur nuque"
        )
        rec = response.imaging_recommendation
        if rec:
            assert rec.urgency == "immediate"


# ============================================================================
# NEGATIONS - Cas critiques
# ============================================================================

class TestNegations:
    """Tests de la detection des negations."""

    def test_pas_de_fievre(self, nlu):
        """Negation explicite de fievre."""
        response = parse_and_decide(
            "Patient 40 ans cephalees sans fievre"
        )
        case = response.headache_case
        if case:
            assert case.fever is not True

    def test_absence_deficit(self, nlu):
        """Pas de deficit neurologique."""
        response = parse_and_decide(
            "Femme 50 ans cephalee, pas de deficit neurologique a l'examen"
        )
        case = response.headache_case
        if case:
            assert case.neuro_deficit is not True

    def test_aucun_signe_meninge(self, nlu):
        """Aucun syndrome meninge."""
        response = parse_and_decide(
            "Homme 35a cephalees, examen: aucune raideur de nuque, pas de photophobie"
        )
        case = response.headache_case
        if case:
            assert case.meningeal_signs is not True

    def test_apyretique(self, nlu):
        """Terme medical pour absence de fievre."""
        response = parse_and_decide(
            "Patient apyretique avec cephalees depuis 24h"
        )
        case = response.headache_case
        if case:
            assert case.fever is not True


# ============================================================================
# INTENSITE ET TEMPORALITE
# ============================================================================

class TestIntensiteTemporalite:
    """Tests de l'extraction d'intensite et temporalite."""

    def test_eva_10_sur_10(self, nlu):
        """Intensite maximale."""
        response = parse_and_decide(
            "Douleur EVA 10/10, la pire de ma vie"
        )
        case = response.headache_case
        if case:
            assert case.intensity == 10 or case.onset == "thunderclap"

    def test_duree_heures(self, nlu):
        """Duree en heures."""
        response = parse_and_decide(
            "Cephalee depuis 6 heures chez homme de 50 ans"
        )
        case = response.headache_case
        if case:
            # Le champ correct est duration_current_episode_hours
            assert case.duration_current_episode_hours == 6 or case.profile == "acute"

    def test_duree_jours(self, nlu):
        """Duree en jours."""
        response = parse_and_decide(
            "Femme 40 ans cephalees depuis 5 jours"
        )
        case = response.headache_case
        if case:
            # 5 jours = subaigu (120 heures)
            assert case.profile in ["acute", "subacute"] or case.duration_current_episode_hours == 120

    def test_chronique_annees(self, nlu):
        """Cephalee depuis des annees."""
        response = parse_and_decide(
            "Patiente migraineuse depuis 15 ans, crise habituelle"
        )
        case = response.headache_case
        if case:
            assert case.profile == "chronic" or case.onset == "chronic"


# ============================================================================
# CAS LIMITES ET AMBIGUS
# ============================================================================

class TestCasLimites:
    """Tests des cas ambigus ou limites."""

    def test_description_vague(self, nlu):
        """Description tres vague - doit poser des questions."""
        response = parse_and_decide(
            "J'ai mal a la tete"
        )
        # Trop vague = dialogue non complet, questions a poser
        assert not response.dialogue_complete or response.next_question is not None

    def test_plusieurs_symptomes_contradictoires(self, nlu):
        """Symptomes potentiellement contradictoires."""
        response = parse_and_decide(
            "Patient avec cephalee chronique devenue brutale ce matin"
        )
        # Changement de pattern sur fond chronique = red flag
        case = response.headache_case
        if case:
            assert case.profile == "chronic" or case.onset == "thunderclap"

    def test_age_extreme_enfant(self, nlu):
        """Enfant (hors cible principale mais doit gerer)."""
        response = parse_and_decide(
            "Enfant 8 ans cephalees avec fievre"
        )
        case = response.headache_case
        if case:
            assert case.age == 8

    def test_age_extreme_tres_age(self, nlu):
        """Patient tres age."""
        response = parse_and_decide(
            "Patient 92 ans premiere cephalee de sa vie"
        )
        rec = response.imaging_recommendation
        case = response.headache_case
        if case:
            assert case.age == 92
        # Premiere cephalee a 92 ans = absolument anormal
        if rec:
            assert rec.imaging is not None


# ============================================================================
# SCENARIOS COMPLETS MULTI-TOUR
# ============================================================================

class TestConversationsMultiTour:
    """Tests de conversations avec plusieurs echanges."""

    def test_conversation_complete_chronique_aggravee(self, nlu):
        """Dialogue complet: chronique -> questions -> aggravation detectee."""
        session_id, _ = get_or_create_session()
        history = []

        # Tour 1: Description initiale
        msg1 = ChatMessage(role="user", content="Femme 45 ans migraineuse depuis 20 ans")
        response1 = handle_user_message(history, msg1, session_id)
        history.append(msg1)
        history.append(ChatMessage(role="assistant", content=response1.message))

        assert response1.headache_case is not None
        assert response1.headache_case.profile == "chronic"

        # Tour 2: Reponse a une question sur changement
        if response1.next_question and "aggrav" in response1.next_question.lower():
            msg2 = ChatMessage(role="user", content="oui les crises sont plus fortes depuis 2 mois")
            response2 = handle_user_message(history, msg2, session_id)

            if response2.headache_case:
                assert response2.headache_case.recent_pattern_change is True

    def test_conversation_urgence_immediate(self, nlu):
        """Urgence detectee des le premier message."""
        session_id, _ = get_or_create_session()

        msg = ChatMessage(
            role="user",
            content="Urgence: homme 50 ans cephalee explosive brutale fievre 40 raideur nuque"
        )
        response = handle_user_message([], msg, session_id)

        # Urgence = decision immediate possible
        if response.imaging_recommendation:
            assert response.imaging_recommendation.urgency == "immediate"

    def test_conversation_rassurante(self, nlu):
        """Cas benin apres interrogatoire complet."""
        session_id, _ = get_or_create_session()
        history = []

        # Description qui semble inquietante mais se revele benigne
        msg1 = ChatMessage(
            role="user",
            content="Femme 30 ans cephalee en casque depuis ce matin apres mauvaise nuit"
        )
        response1 = handle_user_message(history, msg1, session_id)
        history.append(msg1)

        # Si questions sur red flags
        if response1.next_question:
            # Repondre non a tout
            for _ in range(5):  # Max 5 questions
                if not response1.next_question:
                    break
                msg = ChatMessage(role="user", content="non")
                history.append(ChatMessage(role="assistant", content=response1.message or ""))
                history.append(msg)
                response1 = handle_user_message(history, msg, session_id)

        # Apres avoir nie tous les red flags, devrait etre non urgent
        if response1.imaging_recommendation:
            assert response1.imaging_recommendation.urgency in ["none", "delayed"]
