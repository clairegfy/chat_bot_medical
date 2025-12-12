"""Tests des règles fondamentales du système NLU.

Ces tests vérifient que le système respecte les RÈGLES CRITIQUES:
1. Négations correctement détectées ("pas de fièvre" → fever=False, PAS True)
2. Mots-clés médicaux bien identifiés
3. Valeurs numériques correctement extraites (température, âge, intensité)
4. Priorité temporelle respectée (état actuel > état passé)
5. Pas de faux positifs sur termes similaires

IMPORTANT: Chaque test simule un INPUT UTILISATEUR RÉEL sous forme de string.
"""

import pytest
from headache_assistants.nlu_hybrid import HybridNLU
from headache_assistants.nlu_v2 import NLUv2
from headache_assistants.medical_vocabulary import MedicalVocabulary


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def hybrid_nlu():
    """NLU hybride partagé entre les tests."""
    return HybridNLU(confidence_threshold=0.7, verbose=False)


@pytest.fixture(scope="module")
def nlu_v2():
    """NLU v2 (règles uniquement)."""
    return NLUv2()


@pytest.fixture(scope="module")
def vocab():
    """Vocabulaire médical pour tests unitaires."""
    return MedicalVocabulary()


# ============================================================================
# RÈGLE 1: NÉGATIONS - "pas de X" NE DOIT PAS être classé comme X=True
# ============================================================================

class TestNegationsFievre:
    """Tests critiques: la négation de fièvre doit être détectée correctement."""

    def test_pas_de_fievre_simple(self, nlu_v2):
        """'pas de fièvre' → fever=False, PAS True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient 40 ans céphalées pas de fièvre"
        )
        assert case.fever is False, "ERREUR CRITIQUE: 'pas de fièvre' classé comme fever=True!"

    def test_sans_fievre(self, nlu_v2):
        """'sans fièvre' → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Homme 35 ans céphalée brutale sans fièvre"
        )
        assert case.fever is False, "'sans fièvre' doit donner fever=False"

    def test_apyretique(self, nlu_v2):
        """'apyrétique' (terme médical) → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient apyrétique avec céphalées depuis 24h"
        )
        assert case.fever is False, "'apyrétique' doit donner fever=False"

    def test_afebrile(self, nlu_v2):
        """'afébrile' → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Femme 28 ans afébrile, céphalées occipitales"
        )
        assert case.fever is False, "'afébrile' doit donner fever=False"

    def test_absence_de_fievre(self, nlu_v2):
        """'absence de fièvre' → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Examen: absence de fièvre, céphalées frontales"
        )
        assert case.fever is False, "'absence de fièvre' doit donner fever=False"

    def test_aucune_fievre(self, nlu_v2):
        """'aucune fièvre' → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient ne présente aucune fièvre"
        )
        assert case.fever is False, "'aucune fièvre' doit donner fever=False"

    def test_temperature_normale_37(self, nlu_v2):
        """Température 37°C (normale) → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Homme 45 ans T°37°C céphalées depuis ce matin"
        )
        assert case.fever is False, "T°37°C (normale) doit donner fever=False"

    def test_temperature_normale_36_5(self, nlu_v2):
        """Température 36.5°C → fever=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patiente température 36.5 céphalées"
        )
        assert case.fever is False, "T°36.5 doit donner fever=False"

    def test_fievre_positive_explicite(self, nlu_v2):
        """'fièvre à 39°C' → fever=True (cas positif de référence)."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient fébrile à 39°C avec céphalées"
        )
        assert case.fever is True, "T°39°C doit donner fever=True"

    def test_fievre_40_degres(self, nlu_v2):
        """'40°C' → fever=True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Femme 30 ans céphalées 40°C raideur nuque"
        )
        assert case.fever is True, "T°40°C doit donner fever=True"


class TestNegationsSignesMeninges:
    """Tests des négations pour syndrome méningé."""

    def test_pas_de_raideur_nuque(self, nlu_v2):
        """'pas de raideur de nuque' → meningeal_signs=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient céphalée fébrile, pas de raideur de nuque"
        )
        assert case.meningeal_signs is False, "'pas de raideur nuque' doit donner meningeal_signs=False"

    def test_sans_raideur_nuque(self, nlu_v2):
        """'sans raideur nuque' → meningeal_signs=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Céphalée aiguë sans raideur nuque"
        )
        assert case.meningeal_signs is False

    def test_nuque_souple(self, nlu_v2):
        """'nuque souple' → meningeal_signs=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Examen: nuque souple, pas de signe méningé"
        )
        assert case.meningeal_signs is False

    def test_kernig_negatif(self, nlu_v2):
        """'Kernig négatif' → meningeal_signs=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Examen neuro: Kernig négatif, Brudzinski négatif"
        )
        assert case.meningeal_signs is False

    def test_rdn_moins(self, nlu_v2):
        """'RDN-' (abréviation négative) → meningeal_signs=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient 35a céphalées RDN-"
        )
        assert case.meningeal_signs is False

    def test_raideur_nuque_positive(self, nlu_v2):
        """'raideur de nuque' (positif de référence) → meningeal_signs=True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient fébrile avec raideur de nuque"
        )
        assert case.meningeal_signs is True

    def test_rdn_plus(self, nlu_v2):
        """'RDN+' → meningeal_signs=True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Femme 28a fièvre 39 RDN+ céphalées"
        )
        assert case.meningeal_signs is True


class TestNegationsDeficitNeuro:
    """Tests des négations pour déficit neurologique."""

    def test_pas_de_deficit_neurologique(self, nlu_v2):
        """'pas de déficit neurologique' → neuro_deficit=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient céphalée brutale, pas de déficit neurologique"
        )
        assert case.neuro_deficit is False or case.neuro_deficit is None

    def test_sans_deficit(self, nlu_v2):
        """'sans déficit' → neuro_deficit=False ou None."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Examen neurologique normal, sans déficit focal"
        )
        assert case.neuro_deficit is not True

    def test_examen_neuro_normal(self, nlu_v2):
        """'examen neurologique normal' → neuro_deficit=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Céphalée aiguë, examen neurologique normal"
        )
        assert case.neuro_deficit is not True

    def test_hemiparesie_positive(self, nlu_v2):
        """'hémiparésie' (positif référence) → neuro_deficit=True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Céphalée brutale avec hémiparésie droite"
        )
        assert case.neuro_deficit is True


class TestNegationsTrauma:
    """Tests des négations pour traumatisme."""

    def test_pas_de_traumatisme(self, nlu_v2):
        """'pas de traumatisme' → trauma=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Céphalée brutale, pas de traumatisme"
        )
        assert case.trauma is False or case.trauma is None

    def test_sans_trauma(self, nlu_v2):
        """'sans trauma' → trauma=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Patient 45 ans céphalées sans trauma récent"
        )
        assert case.trauma is not True

    def test_nie_tout_traumatisme(self, nlu_v2):
        """'nie tout traumatisme' → trauma=False."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Interrogatoire: nie tout traumatisme, nie tout AVP"
        )
        assert case.trauma is not True

    def test_chute_positive(self, nlu_v2):
        """'chute' + contexte trauma → trauma=True."""
        case, metadata = nlu_v2.parse_free_text_to_case(
            "Céphalées depuis chute à vélo hier, choc à la tête"
        )
        assert case.trauma is True


# ============================================================================
# RÈGLE 2: EXTRACTION NUMÉRIQUE - Valeurs correctes
# ============================================================================

class TestExtractionAge:
    """Tests de l'extraction d'âge."""

    def test_age_format_standard(self, nlu_v2):
        """'Homme 45 ans' → age=45."""
        case, _ = nlu_v2.parse_free_text_to_case("Homme 45 ans céphalées")
        assert case.age == 45

    def test_age_format_abbreviation(self, nlu_v2):
        """'H 52a' → age=52."""
        case, _ = nlu_v2.parse_free_text_to_case("H 52a céphalée brutale")
        assert case.age == 52

    def test_age_femme(self, nlu_v2):
        """'Femme 38 ans' → age=38, sex='F'."""
        case, _ = nlu_v2.parse_free_text_to_case("Femme 38 ans enceinte céphalées")
        assert case.age == 38
        assert case.sex == "F"

    def test_age_patient(self, nlu_v2):
        """'Patient de 62 ans' → age=62."""
        case, _ = nlu_v2.parse_free_text_to_case("Patient de 62 ans céphalée progressive")
        assert case.age == 62

    def test_age_tres_jeune(self, nlu_v2):
        """'Enfant 8 ans' → age=8."""
        case, _ = nlu_v2.parse_free_text_to_case("Enfant 8 ans céphalées fébriles")
        assert case.age == 8

    def test_age_tres_vieux(self, nlu_v2):
        """'92 ans' → age=92."""
        case, _ = nlu_v2.parse_free_text_to_case("Patient 92 ans première céphalée de sa vie")
        assert case.age == 92


class TestExtractionTemperature:
    """Tests de l'extraction de température et seuil de fièvre."""

    def test_temperature_39_degres(self, vocab):
        """T° 39°C → fièvre détectée."""
        result = vocab.detect_fever("Céphalée fébrile 39°C")
        assert result.detected is True
        assert result.value is True

    def test_temperature_38_5(self, vocab):
        """T° 38.5 → fièvre détectée."""
        result = vocab.detect_fever("Patient T° 38.5")
        assert result.detected is True
        assert result.value is True

    def test_temperature_37_8_pas_fievre(self, vocab):
        """T° 37.8°C (sous seuil 38) → pas de fièvre."""
        result = vocab.detect_fever("Patient T° 37.8")
        # 37.8 est sous le seuil de 38.0, donc pas de fièvre
        assert result.value is False or result.value is None

    def test_temperature_format_francais(self, vocab):
        """T° 39°5 (notation française) → fièvre détectée."""
        result = vocab.detect_fever("Fièvre 39°5")
        assert result.detected is True
        assert result.value is True

    def test_temperature_40_degres_c(self, vocab):
        """'40°C' → fièvre détectée."""
        result = vocab.detect_fever("Patient 40°C céphalées")
        assert result.detected is True
        assert result.value is True


class TestExtractionIntensite:
    """Tests de l'extraction d'intensité (EVA)."""

    def test_eva_10_sur_10(self, nlu_v2):
        """'EVA 10/10' → intensity=10."""
        case, _ = nlu_v2.parse_free_text_to_case("Céphalée EVA 10/10")
        assert case.intensity == 10

    def test_eva_8_sur_10(self, nlu_v2):
        """'EVA 8/10' → intensity=8."""
        case, _ = nlu_v2.parse_free_text_to_case("Douleur EVA 8/10")
        assert case.intensity == 8

    def test_intensite_5(self, nlu_v2):
        """'intensité 5' → intensity=5."""
        case, _ = nlu_v2.parse_free_text_to_case("Céphalée intensité 5/10")
        assert case.intensity == 5


# ============================================================================
# RÈGLE 3: DÉTECTION ONSET (Type de début)
# ============================================================================

class TestDetectionOnset:
    """Tests de la détection du type de début."""

    def test_coup_de_tonnerre(self, vocab):
        """'coup de tonnerre' → onset=thunderclap."""
        result = vocab.detect_onset("Céphalée en coup de tonnerre")
        assert result.detected is True
        assert result.value == "thunderclap"

    def test_brutale(self, vocab):
        """'brutale' → onset=thunderclap."""
        result = vocab.detect_onset("Céphalée brutale")
        assert result.detected is True
        assert result.value == "thunderclap"

    def test_soudaine(self, vocab):
        """'soudaine' → onset=thunderclap."""
        result = vocab.detect_onset("Installation soudaine")
        assert result.detected is True
        assert result.value == "thunderclap"

    def test_explosive(self, nlu_v2):
        """'explosive' → onset=thunderclap."""
        case, _ = nlu_v2.parse_free_text_to_case("H 50a céphalée explosive")
        assert case.onset == "thunderclap"

    def test_pire_douleur_de_ma_vie(self, vocab):
        """'pire douleur de ma vie' → onset=thunderclap."""
        result = vocab.detect_onset("C'est la pire douleur de ma vie")
        assert result.detected is True
        assert result.value == "thunderclap"

    def test_progressive(self, vocab):
        """'progressive' → onset=progressive."""
        result = vocab.detect_onset("Céphalée d'installation progressive")
        assert result.detected is True
        assert result.value == "progressive"

    def test_progressivement(self, vocab):
        """'progressivement' → onset=progressive."""
        result = vocab.detect_onset("Céphalée installée progressivement")
        assert result.detected is True
        assert result.value == "progressive"

    def test_chronique(self, vocab):
        """'depuis des mois' → onset=chronic."""
        result = vocab.detect_onset("Céphalées quotidiennes depuis des mois")
        assert result.detected is True
        assert result.value == "chronic"


# ============================================================================
# RÈGLE 4: GROSSESSE / POST-PARTUM
# ============================================================================

class TestGrossesse:
    """Tests de la détection de grossesse."""

    def test_enceinte(self, vocab):
        """'enceinte' → pregnancy_postpartum=True."""
        result = vocab.detect_pregnancy_postpartum("Femme enceinte céphalées")
        assert result.detected is True
        assert result.value is True

    def test_grossesse_semaines(self, nlu_v2):
        """'enceinte de 20 semaines' → pregnancy=True + trimestre."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Patiente 30 ans enceinte de 20 semaines céphalées"
        )
        assert case.pregnancy_postpartum is True
        # 20 semaines = T2
        assert case.pregnancy_trimester == 2

    def test_post_partum(self, vocab):
        """'post-partum' → pregnancy_postpartum=True."""
        result = vocab.detect_pregnancy_postpartum("Femme J5 post-partum céphalées")
        assert result.detected is True
        assert result.value is True

    def test_accouchement_recent(self, nlu_v2):
        """'après accouchement' → pregnancy_postpartum=True."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Femme 28 ans céphalées intenses après accouchement il y a 3 jours"
        )
        assert case.pregnancy_postpartum is True


# ============================================================================
# RÈGLE 5: IMMUNODÉPRESSION
# ============================================================================

class TestImmunodepression:
    """Tests de la détection d'immunodépression."""

    def test_vih_positif(self, vocab):
        """'VIH+' → immunosuppression=True."""
        result = vocab.detect_immunosuppression("Patient VIH+ céphalées")
        assert result.detected is True
        assert result.value is True

    def test_chimio(self, vocab):
        """'sous chimio' → immunosuppression=True."""
        result = vocab.detect_immunosuppression("Patiente sous chimiothérapie")
        assert result.detected is True
        assert result.value is True

    def test_greffe(self, vocab):
        """'greffé' → immunosuppression=True."""
        result = vocab.detect_immunosuppression("Patient greffé rénal")
        assert result.detected is True
        assert result.value is True


# ============================================================================
# RÈGLE 6: ANTÉCÉDENT CANCER
# ============================================================================

class TestAntecedentCancer:
    """Tests de la détection d'antécédent de cancer."""

    def test_atcd_cancer(self, vocab):
        """'ATCD cancer sein' → cancer_history=True."""
        result = vocab.detect_cancer_history("Femme ATCD cancer sein")
        assert result.detected is True
        assert result.value is True

    def test_k_poumon(self, vocab):
        """'K poumon' (abréviation) → cancer_history=True."""
        result = vocab.detect_cancer_history("Patient K poumon traité")
        assert result.detected is True
        assert result.value is True

    def test_metastases(self, vocab):
        """'métastases cérébrales' → cancer_history=True."""
        result = vocab.detect_cancer_history("Recherche métastases cérébrales")
        assert result.detected is True
        assert result.value is True


# ============================================================================
# RÈGLE 7: CHANGEMENT DE PATTERN (céphalées chroniques)
# ============================================================================

class TestChangementPattern:
    """Tests de la détection de changement de pattern."""

    def test_ont_change_recemment(self, vocab):
        """'ont changé récemment' → pattern_change=True."""
        result = vocab.detect_pattern_change("Ses migraines ont changé récemment")
        assert result.detected is True
        assert result.value is True

    def test_plus_frequentes(self, vocab):
        """'plus fréquentes' → pattern_change=True."""
        result = vocab.detect_pattern_change("Crises plus fréquentes depuis 1 mois")
        assert result.detected is True
        assert result.value is True

    def test_plus_intenses(self, vocab):
        """'plus intenses' → pattern_change=True."""
        result = vocab.detect_pattern_change("Céphalées plus intenses")
        assert result.detected is True
        assert result.value is True

    def test_aggravation_recente(self, vocab):
        """'aggravation récente' → pattern_change=True."""
        result = vocab.detect_pattern_change("Aggravation récente des migraines")
        assert result.detected is True
        assert result.value is True

    def test_pas_de_changement(self, vocab):
        """'pas de changement' → pattern_change=False."""
        result = vocab.detect_pattern_change("Migraine habituelle, pas de changement")
        assert result.detected is True
        assert result.value is False

    def test_comme_dhabitude(self, vocab):
        """'comme d'habitude' → pattern_change=False."""
        result = vocab.detect_pattern_change("Crise comme d'habitude")
        assert result.detected is True
        assert result.value is False


# ============================================================================
# RÈGLE 8: HTIC (éviter faux positifs)
# ============================================================================

class TestHTIC:
    """Tests HTIC - éviter les faux positifs."""

    def test_vomissements_en_jet(self, vocab):
        """'vomissements en jet' → htic=True."""
        result = vocab.detect_htic("Céphalées avec vomissements en jet")
        assert result.detected is True
        assert result.value is True

    def test_oedeme_papillaire(self, vocab):
        """'œdème papillaire' → htic=True."""
        result = vocab.detect_htic("Fond d'œil: œdème papillaire bilatéral")
        assert result.detected is True
        assert result.value is True

    def test_scotome_pas_htic(self, vocab):
        """'scotome' (aura migraineuse) → htic=False (exclusion)."""
        result = vocab.detect_htic("Migraine avec scotome scintillant")
        # Le scotome est un anti-pattern, ne doit pas être classé comme HTIC
        assert result.detected is False or result.value is not True


# ============================================================================
# RÈGLE 9: CRISES D'ÉPILEPSIE
# ============================================================================

class TestEpilepsie:
    """Tests de la détection de crises épileptiques."""

    def test_crise_convulsive(self, vocab):
        """'crise convulsive' → seizure=True."""
        result = vocab.detect_seizure("Céphalée suivie d'une crise convulsive")
        assert result.detected is True
        assert result.value is True

    def test_convulsions(self, vocab):
        """'convulsions' → seizure=True."""
        result = vocab.detect_seizure("Patient avec convulsions")
        assert result.detected is True
        assert result.value is True

    def test_a_convulse(self, vocab):
        """'a convulsé' → seizure=True."""
        result = vocab.detect_seizure("Le patient a convulsé")
        assert result.detected is True
        assert result.value is True

    def test_crise_tonico_clonique(self, vocab):
        """'crise tonico-clonique' → seizure=True."""
        result = vocab.detect_seizure("Crise généralisée tonico-clonique")
        assert result.detected is True
        assert result.value is True


# ============================================================================
# RÈGLE 10: PRIORITÉ TEMPORELLE (état actuel > passé)
# ============================================================================

class TestPrioriteTemporelle:
    """Tests de la priorité temporelle dans l'interprétation."""

    def test_evolution_fievre_actuellement_afebrile(self, vocab):
        """'fièvre hier mais actuellement apyrétique' → fever=False."""
        result = vocab.detect_fever(
            "Fièvre à 39 hier mais actuellement apyrétique"
        )
        # L'état actuel (apyrétique) doit primer
        assert result.value is False

    def test_evolution_fievre_maintenant_febrile(self, vocab):
        """'apyrétique hier mais maintenant fièvre 39' → fever=True."""
        result = vocab.detect_fever(
            "Était apyrétique hier mais maintenant fièvre 39"
        )
        # L'état actuel (fièvre) doit primer
        assert result.value is True


# ============================================================================
# RÈGLE 11: VARIATIONS LINGUISTIQUES
# ============================================================================

class TestVariationsLinguistiques:
    """Tests avec variations orthographiques et accents."""

    def test_sans_accent_fievre(self, vocab):
        """'fievre' (sans accent) → détecté."""
        result = vocab.detect_fever("Patient avec fievre 39")
        assert result.detected is True
        assert result.value is True

    def test_majuscules(self, vocab):
        """'FIEVRE' en majuscules → détecté."""
        result = vocab.detect_fever("Patient FÉBRILE 40°C")
        assert result.detected is True
        assert result.value is True

    def test_raideur_nuque_sans_accent(self, vocab):
        """'meninge' sans accent → détecté."""
        result = vocab.detect_meningeal_signs("syndrome meninge")
        assert result.detected is True
        assert result.value is True


# ============================================================================
# RÈGLE 12: CAS COMBINÉS RÉALISTES
# ============================================================================

class TestCasCombinesRealistes:
    """Tests avec des inputs utilisateur complets réalistes."""

    def test_meningite_complete(self, nlu_v2):
        """Tableau méningite complet bien détecté."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Homme 28 ans céphalée fébrile 39.5°C avec raideur de nuque"
        )
        assert case.fever is True
        assert case.meningeal_signs is True
        assert case.age == 28

    def test_hsa_classique(self, nlu_v2):
        """HSA classique bien détectée."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Femme 52 ans céphalée brutale en coup de tonnerre, pire de sa vie"
        )
        assert case.onset == "thunderclap"
        assert case.age == 52
        assert case.sex == "F"

    def test_migraine_sans_red_flag(self, nlu_v2):
        """Migraine typique sans red flag."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Femme 35 ans migraineuse connue, crise habituelle, "
            "pas de fièvre, pas de raideur nuque, pas de déficit"
        )
        assert case.fever is False
        assert case.meningeal_signs is False
        assert case.neuro_deficit is not True

    def test_grossesse_t3_cephalee(self, nlu_v2):
        """Grossesse T3 avec céphalée."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Patiente 32 ans enceinte 35 SA céphalées depuis 2 jours"
        )
        assert case.pregnancy_postpartum is True
        assert case.pregnancy_trimester == 3
        assert case.age == 32

    def test_immunodeprime_avec_fievre(self, nlu_v2):
        """Patient immunodéprimé avec fièvre."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Homme 55 ans VIH+ sous chimio, céphalées fébriles 38.5°C"
        )
        assert case.immunosuppression is True
        assert case.fever is True

    def test_post_trauma_avec_deficit(self, nlu_v2):
        """Post-trauma avec déficit neurologique."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Patient 25 ans chute de vélo avec TC, céphalées et hémiparésie droite"
        )
        assert case.trauma is True
        assert case.neuro_deficit is True


# ============================================================================
# RÈGLE 13: CAS NÉGATIFS - Aucun faux positif
# ============================================================================

class TestPasDeFauxPositifs:
    """Tests vérifiant qu'on n'a pas de faux positifs."""

    def test_mention_fievre_dans_negation_complete(self, nlu_v2):
        """'nie fièvre, nie trauma, nie déficit' → tout False."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Patient nie toute fièvre, nie traumatisme, nie déficit"
        )
        assert case.fever is not True
        assert case.trauma is not True
        assert case.neuro_deficit is not True

    def test_mention_raideur_dans_contexte_negatif(self, nlu_v2):
        """'pas de raideur' ne doit pas déclencher meningeal_signs=True."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Examen: pas de raideur de nuque, pas de Kernig, pas de Brudzinski"
        )
        assert case.meningeal_signs is False

    def test_temperature_dans_contexte_autre(self, nlu_v2):
        """'température de la pièce' ne doit pas déclencher fever."""
        case, _ = nlu_v2.parse_free_text_to_case(
            "Patient céphalées, aime dormir dans une pièce à basse température"
        )
        # "basse température" ne devrait pas déclencher fever=True
        assert case.fever is not True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
