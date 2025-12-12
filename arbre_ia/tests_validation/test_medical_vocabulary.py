"""Tests pour le vocabulaire médical robuste (medical_vocabulary.py).

Valide la détection d'acronymes, synonymes et variations linguistiques.
"""

import pytest
from headache_assistants.medical_vocabulary import MedicalVocabulary, DetectionResult


class TestMedicalVocabularyOnset:
    """Tests pour la détection du type de début (onset)."""

    def setup_method(self):
        """Initialise le vocabulaire avant chaque test."""
        self.vocab = MedicalVocabulary()

    def test_thunderclap_canonical(self):
        """Détecte 'coup de tonnerre' (terme canonique)."""
        result = self.vocab.detect_onset("céphalée en coup de tonnerre")
        assert result.detected
        assert result.value == "thunderclap"
        assert result.confidence >= 0.95
        assert result.source == "canonical"

    def test_thunderclap_english(self):
        """Détecte 'thunderclap' (anglais médical)."""
        result = self.vocab.detect_onset("thunderclap headache")
        assert result.detected
        assert result.value == "thunderclap"

    def test_thunderclap_synonyms(self):
        """Détecte les synonymes de coup de tonnerre."""
        texts = [
            "céphalée brutale",
            "début soudain",
            "installation brutale",
            "d'emblée maximale"
        ]
        for text in texts:
            result = self.vocab.detect_onset(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "thunderclap"

    def test_thunderclap_patient_language(self):
        """Détecte le langage familier du patient."""
        texts = [
            "c'est venu d'un coup",
            "pire douleur de ma vie",
            "jamais eu aussi mal",
            "du jour au lendemain"
        ]
        for text in texts:
            result = self.vocab.detect_onset(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "thunderclap"

    def test_thunderclap_medical_term(self):
        """Détecte HSA suspectée."""
        result = self.vocab.detect_onset("HSA suspectée")
        assert result.detected
        assert result.value == "thunderclap"
        assert result.source == "medical_term"

    def test_progressive(self):
        """Détecte le début progressif."""
        texts = [
            "céphalée progressive",
            "installation progressive",
            "qui augmente progressivement",
            "en quelques heures"
        ]
        for text in texts:
            result = self.vocab.detect_onset(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "progressive"

    def test_chronic(self):
        """Détecte le caractère chronique."""
        texts = [
            "céphalée chronique",
            "depuis des mois",
            "tous les jours",
            "permanente"
        ]
        for text in texts:
            result = self.vocab.detect_onset(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "chronic"

    def test_no_onset_detected(self):
        """Aucun onset détecté si absent."""
        result = self.vocab.detect_onset("patient de 45 ans")
        assert not result.detected
        assert result.value is None


class TestMedicalVocabularyFever:
    """Tests pour la détection de fièvre."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_fever_canonical(self):
        """Détecte 'fièvre' (terme canonique)."""
        result = self.vocab.detect_fever("patient avec fièvre")
        assert result.detected
        assert result.value is True
        assert result.confidence >= 0.90

    def test_fever_acronym(self):
        """Détecte les acronymes (féb, T°)."""
        texts = [
            "féb à 39",
            "fébrile",
            "T° 39"
        ]
        for text in texts:
            result = self.vocab.detect_fever(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_fever_numeric_threshold(self):
        """Valide le seuil de température ≥38°C."""
        # Fièvre confirmée
        texts_fever = [
            "T° 38.5",  # Avec °
            "38°5",
            "T=39",
            "T°=38.5"
        ]
        for text in texts_fever:
            result = self.vocab.detect_fever(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True, f"Should be fever for: {text}"
            # Source peut être "numeric" ou "canonical" selon l'ordre de détection
            assert result.source in ["numeric", "canonical"]

        # Température normale (< 38°C)
        texts_normal = [
            "T° 37.5",  # Avec °
            "température 37.2",
            "36°8"
        ]
        for text in texts_normal:
            result = self.vocab.detect_fever(text)
            if result.detected:
                # Si détecté, doit être False (pas de fièvre)
                assert result.value is False, f"Should be no fever for: {text}"

    def test_fever_negation(self):
        """Détecte l'absence de fièvre (négations)."""
        texts = [
            "sans fièvre",
            "apyrétique",
            "pas de fièvre",
            "afébrile"
        ]
        for text in texts:
            result = self.vocab.detect_fever(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is False

    def test_fever_false_positive_age(self):
        """Évite le faux positif avec '40a' (âge)."""
        # "40a" = 40 ans, PAS fièvre
        result = self.vocab.detect_fever("patient de 40a")
        # Ne devrait PAS détecter de fièvre
        assert not result.detected or result.value is False


class TestMedicalVocabularyMeningealSigns:
    """Tests pour la détection du syndrome méningé."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_meningeal_canonical(self):
        """Détecte 'syndrome méningé'."""
        result = self.vocab.detect_meningeal_signs("syndrome méningé")
        assert result.detected
        assert result.value is True
        assert result.confidence >= 0.95

    def test_meningeal_acronyms(self):
        """Détecte les acronymes médicaux."""
        texts = [
            "sdm méningé",
            "rdn+",
            "RDN++"
        ]
        for text in texts:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True
            assert result.source == "acronym"

        # kernig+ et brudzinski+ peuvent être détectés comme "clinical_sign" (contient le mot)
        texts_clinical = ["kernig+", "brudzinski+"]
        for text in texts_clinical:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_meningeal_clinical_signs(self):
        """Détecte les signes cliniques."""
        texts = [
            "raideur de la nuque",
            "signe de kernig positif",
            "brudzinski positif",
            "nuque raide",
            "chien de fusil"
        ]
        for text in texts:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_meningeal_patient_language(self):
        """Détecte le langage du patient."""
        texts = [
            "ne peut pas bouger le cou",
            "impossible de tourner la tête",
            "cou bloqué",
            "nuque douloureuse"
        ]
        for text in texts:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True
            assert result.source == "patient_language"

    def test_meningeal_negation(self):
        """Détecte l'absence de signes méningés."""
        texts = [
            "sans signe méningé",
            "rdn-",
            "kernig négatif",
            "nuque souple"
        ]
        for text in texts:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is False


class TestMedicalVocabularyHTIC:
    """Tests pour la détection de l'HTIC."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_htic_acronym(self):
        """Détecte 'HTIC'."""
        result = self.vocab.detect_htic("signes d'HTIC")
        assert result.detected
        assert result.value is True

    def test_htic_clinical_patterns(self):
        """Détecte les patterns cliniques FORTS d'HTIC.

        Note: Les signes faibles (céphalée matutinale, aggravation toux/effort seuls)
        ont été retirés de la détection pour éviter les faux positifs.
        Seuls les signes FORTS déclenchent HTIC : vomissements en jet, œdème papillaire.
        """
        # Signes FORTS - doivent être détectés
        strong_signs = [
            "vomissements en jet",
        ]
        for text in strong_signs:
            result = self.vocab.detect_htic(text)
            assert result.detected, f"Signe fort non détecté: {text}"
            assert result.value is True

        # Signes FAIBLES - ne doivent PAS déclencher HTIC seuls
        # (peuvent être migraine, céphalée de tension, céphalée bénigne de toux)
        weak_signs = [
            "céphalée matutinale",
            "aggravation par la toux",
            "aggravée par l'effort"
        ]
        for text in weak_signs:
            result = self.vocab.detect_htic(text)
            # Ces signes seuls ne doivent PAS être détectés comme HTIC
            assert not result.detected, f"Faux positif HTIC pour signe faible: {text}"

    def test_htic_ophtalmo_signs(self):
        """Détecte les signes ophtalmologiques."""
        texts = [
            "œdème papillaire",
            "op++",
            "flou visuel",
            "éclipses visuelles"
        ]
        for text in texts:
            result = self.vocab.detect_htic(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_htic_exclusion_aura(self):
        """Exclut les scotomes (aura migraineuse ≠ HTIC)."""
        # Scotomes = aura migraineuse, pas HTIC
        result = self.vocab.detect_htic("scotomes scintillants")
        assert not result.detected

        # HTIC détecté avec signe FORT (vomissements en jet)
        result = self.vocab.detect_htic("vomissements en jet")
        assert result.detected


class TestMedicalVocabularyTrauma:
    """Tests pour la détection du traumatisme crânien."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_trauma_acronyms(self):
        """Détecte les acronymes médicaux."""
        texts = [
            "TCC récent",
            "AVP hier",
            "PDC après chute"
        ]
        for text in texts:
            result = self.vocab.detect_trauma(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True
            assert result.source == "acronym"

    def test_trauma_mechanisms(self):
        """Détecte les mécanismes de traumatisme."""
        texts = [
            "chute de sa hauteur",
            "choc à la tête",
            "coup sur le crâne"
        ]
        for text in texts:
            result = self.vocab.detect_trauma(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_trauma_temporal_context(self):
        """Détecte le contexte temporel."""
        texts = [
            "depuis traumatisme",
            "après chute",
            "contexte de trauma"
        ]
        for text in texts:
            result = self.vocab.detect_trauma(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_trauma_negation(self):
        """Détecte l'absence de traumatisme."""
        texts = [
            "pas de traumatisme",
            "sans choc",
            "nie traumatisme"
        ]
        for text in texts:
            result = self.vocab.detect_trauma(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is False


class TestMedicalVocabularyNeuroDeficit:
    """Tests pour la détection du déficit neurologique."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_neuro_acronyms(self):
        """Détecte les acronymes."""
        texts = [
            "DSM gauche",
            "PF périphérique",
            "GCS 14"
        ]
        for text in texts:
            result = self.vocab.detect_neuro_deficit(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_neuro_motor_deficits(self):
        """Détecte les déficits moteurs."""
        texts = [
            "hémiparésie droite",
            "faiblesse du bras",
            "paralysie faciale"
        ]
        for text in texts:
            result = self.vocab.detect_neuro_deficit(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_neuro_language_deficits(self):
        """Détecte les troubles du langage."""
        texts = [
            "aphasie",
            "difficulté à parler",
            "troubles de la parole"
        ]
        for text in texts:
            result = self.vocab.detect_neuro_deficit(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_neuro_visual_deficits(self):
        """Détecte les troubles visuels."""
        texts = [
            "diplopie",
            "vision double",
            "flou visuel"
        ]
        for text in texts:
            result = self.vocab.detect_neuro_deficit(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_neuro_negation(self):
        """Détecte l'absence de déficit."""
        texts = [
            "pas de déficit",
            "examen neurologique normal",
            "sans trouble moteur"
        ]
        for text in texts:
            result = self.vocab.detect_neuro_deficit(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is False


class TestMedicalVocabularySeizure:
    """Tests pour la détection des crises d'épilepsie."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_seizure_acronyms(self):
        """Détecte les acronymes."""
        texts = [
            "CGT ce matin",
            "crise TC"
        ]
        for text in texts:
            result = self.vocab.detect_seizure(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_seizure_medical_terms(self):
        """Détecte les termes médicaux."""
        texts = [
            "crise comitiale",
            "crise tonico-clonique",
            "crise convulsive"
        ]
        for text in texts:
            result = self.vocab.detect_seizure(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_seizure_generic(self):
        """Détecte les termes génériques."""
        texts = [
            "convulsions",
            "a convulsé",
            "fait une crise"
        ]
        for text in texts:
            result = self.vocab.detect_seizure(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_seizure_negation(self):
        """Détecte l'absence de crise."""
        texts = [
            "pas de crise",
            "sans convulsion"
        ]
        for text in texts:
            result = self.vocab.detect_seizure(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is False


class TestMedicalVocabularyPregnancy:
    """Tests pour la détection de grossesse/post-partum."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_pregnancy_canonical(self):
        """Détecte 'enceinte', 'grossesse'."""
        texts = [
            "patiente enceinte",
            "en cours de grossesse"
        ]
        for text in texts:
            result = self.vocab.detect_pregnancy_postpartum(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_pregnancy_obstetric_acronyms(self):
        """Détecte les acronymes obstétricaux."""
        texts = [
            "G1P0",
            "12 SA",
            "T2"
        ]
        for text in texts:
            result = self.vocab.detect_pregnancy_postpartum(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_pregnancy_postpartum(self):
        """Détecte le post-partum."""
        texts = [
            "post-partum J5",
            "a accouché il y a 3 jours",
            "suite à accouchement"
        ]
        for text in texts:
            result = self.vocab.detect_pregnancy_postpartum(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_pregnancy_trimester(self):
        """Détecte les trimestres."""
        texts = [
            "1er trimestre",
            "2ème trimestre"
        ]
        for text in texts:
            result = self.vocab.detect_pregnancy_postpartum(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True


class TestMedicalVocabularyImmunosuppression:
    """Tests pour la détection de l'immunodépression."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_immunosup_medical_conditions(self):
        """Détecte les conditions médicales."""
        texts = [
            "VIH+",
            "séropositif",
            "SIDA"
        ]
        for text in texts:
            result = self.vocab.detect_immunosuppression(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_immunosup_treatments(self):
        """Détecte les traitements immunosuppresseurs."""
        texts = [
            "sous chimiothérapie",
            "corticothérapie au long cours",
            "ttt immunosup"
        ]
        for text in texts:
            result = self.vocab.detect_immunosuppression(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True

    def test_immunosup_oncology(self):
        """Détecte le contexte oncologique."""
        texts = [
            "k poumon",
            "cancer du sein"
        ]
        for text in texts:
            result = self.vocab.detect_immunosuppression(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True


class TestNormalization:
    """Tests pour la normalisation de texte."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_normalize_accents(self):
        """Normalise les accents (é → e)."""
        normalized = self.vocab.normalize_text("fièvre aigüe")
        assert normalized == "fievre aigue"

    def test_normalize_case(self):
        """Convertit en minuscules."""
        normalized = self.vocab.normalize_text("FIÈVRE")
        assert normalized == "fievre"

    def test_normalize_spaces(self):
        """Normalise les espaces multiples."""
        normalized = self.vocab.normalize_text("céphalée    brutale")
        assert normalized == "cephalee brutale"

    def test_normalize_medical_punctuation(self):
        """Préserve la ponctuation médicale (+, -)."""
        normalized = self.vocab.normalize_text("RDN + +")
        assert "+" in normalized


class TestConfidenceScores:
    """Tests pour les scores de confiance."""

    def setup_method(self):
        self.vocab = MedicalVocabulary()

    def test_confidence_canonical_higher(self):
        """Le terme canonique a une confiance plus élevée."""
        result_canonical = self.vocab.detect_onset("coup de tonnerre")
        result_synonym = self.vocab.detect_onset("brutale")

        assert result_canonical.confidence >= result_synonym.confidence

    def test_confidence_numeric_fever_high(self):
        """La température numérique a une haute confiance."""
        result = self.vocab.detect_fever("T 39°C")
        # Confiance élevée (>= 0.85) car terme médical ou numérique
        assert result.confidence >= 0.85

    def test_confidence_critical_signs_high(self):
        """Les signes critiques ont une haute confiance."""
        result = self.vocab.detect_meningeal_signs("syndrome méningé")
        assert result.confidence >= 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
