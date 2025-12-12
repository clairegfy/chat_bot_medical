"""Tests pour la détection des caractéristiques de céphalée.

Vérifie la détection de photophobie, phonophobie, position en chien de fusil,
et autres caractéristiques cliniques des céphalées.
"""

import pytest
from headache_assistants.medical_vocabulary import MedicalVocabulary


class TestHeadacheCharacteristics:
    """Tests pour detect_headache_characteristics."""

    def setup_method(self):
        """Initialise le vocabulaire médical avant chaque test."""
        self.vocab = MedicalVocabulary()

    def test_photophobie_detection(self):
        """Détecte photophobie comme caractéristique de migraine."""
        texts = [
            "céphalée avec photophobie",
            "photophobie importante",
            "gêné par la lumière",
            "intolérance à la lumière"
        ]
        for text in texts:
            result = self.vocab.detect_headache_characteristics(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "migraine_like"
            assert "photophobie" in result.matched_term or "lumière" in result.matched_term

    def test_phonophobie_detection(self):
        """Détecte phonophobie comme caractéristique de migraine."""
        texts = [
            "céphalée avec phonophobie",
            "phonophobie marquée",
            "gêné par le bruit",
            "intolérance au bruit"
        ]
        for text in texts:
            result = self.vocab.detect_headache_characteristics(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "migraine_like"
            assert "phonophobie" in result.matched_term or "bruit" in result.matched_term

    def test_migraine_complete(self):
        """Détecte un profil migraineux complet."""
        text = "céphalée unilatérale pulsatile avec photophobie et phonophobie"
        result = self.vocab.detect_headache_characteristics(text)
        assert result.detected
        assert result.value == "migraine_like"
        assert result.confidence == 0.85

    def test_tension_headache(self):
        """Détecte un profil de céphalée de tension."""
        texts = [
            "céphalée bilatérale en casque",
            "douleur en pression des deux côtés",
            "serrement en bandeau"
        ]
        for text in texts:
            result = self.vocab.detect_headache_characteristics(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "tension_like"

    def test_cluster_headache(self):
        """Détecte un profil d'algie vasculaire de la face."""
        texts = [
            "douleur périorbitaire en salves",
            "douleur orbitaire avec larmoiement",
            "AVF avec œil rouge"
        ]
        for text in texts:
            result = self.vocab.detect_headache_characteristics(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "cluster_like"

    def test_medical_notation(self):
        """Détecte les notations médicales (photo+, phono+, n/v)."""
        texts = [
            "céphalée avec photo+",
            "phono+ et n/v",
            "photo+ phono+ nv"
        ]
        for text in texts:
            result = self.vocab.detect_headache_characteristics(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value == "migraine_like"

    def test_chien_de_fusil_meningeal(self):
        """Vérifie que 'chien de fusil' reste un signe méningé."""
        texts = [
            "position en chien de fusil",
            "patient en chien de fusil",
            "chien de fusil"
        ]
        for text in texts:
            result = self.vocab.detect_meningeal_signs(text)
            assert result.detected, f"Failed for: {text}"
            assert result.value is True
            assert result.source == "clinical_sign"


class TestHeadacheCharacteristicsPriority:
    """Tests de priorité entre profils."""

    def setup_method(self):
        """Initialise le vocabulaire médical avant chaque test."""
        self.vocab = MedicalVocabulary()

    def test_migraine_over_tension(self):
        """Migraine avec plus de critères doit primer sur tension."""
        text = "céphalée unilatérale pulsatile avec photophobie (profil migraine = 3 critères)"
        result = self.vocab.detect_headache_characteristics(text)
        assert result.detected
        assert result.value == "migraine_like"

    def test_multiple_profiles_highest_score_wins(self):
        """Le profil avec le plus de matches gagne."""
        # Texte avec critères mixtes mais dominance migraine
        text = "céphalée unilatérale pulsatile battante avec photophobie phonophobie nausées"
        result = self.vocab.detect_headache_characteristics(text)
        assert result.detected
        assert result.value == "migraine_like"  # 6 critères migraine


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
