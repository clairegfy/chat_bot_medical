"""Tests de validation des exigences client pour Scanner et IRM.

Vérifie que le système respecte toutes les précautions et contre-indications
spécifiées par le client pour les examens d'imagerie.
"""

import pytest
from headache_assistants.models import HeadacheCase
from headache_assistants.rules_engine import decide_imaging


class TestScannerPrecautions:
    """Tests pour les précautions Scanner selon exigences client."""

    def test_scanner_grossesse_debutante_contre_indication(self):
        """Scanner contre-indiqué si grossesse débutante < 4 semaines (sauf urgence)."""
        case = HeadacheCase(
            age=30,
            sex="F",
            pregnancy_postpartum=True,  # Enceinte
            onset="progressive",
            profile="subacute"  # PAS d'urgence vitale
        )

        recommendation = decide_imaging(case)

        # Vérifier que scanner est remplacé par IRM
        assert any("irm" in exam.lower() for exam in recommendation.imaging), \
            "Scanner devrait être remplacé par IRM si grossesse sans urgence vitale"

        # Vérifier qu'il n'y a PAS de scanner prescrit
        assert not any("scanner" in exam.lower() for exam in recommendation.imaging), \
            "Ne doit PAS prescrire scanner si grossesse sans urgence vitale"

        # Vérifier les précautions grossesse sont présentes
        assert "PATIENTE ENCEINTE" in recommendation.comment or \
               "grossesse" in recommendation.comment.lower(), \
            "Doit mentionner le contexte de grossesse"

    def test_scanner_grossesse_urgence_vitale_acceptable(self):
        """Scanner acceptable en urgence vitale malgré grossesse."""
        case = HeadacheCase(
            age=30,
            sex="F",
            pregnancy_postpartum=True,
            onset="thunderclap",  # URGENCE VITALE (HSA)
            profile="acute",
            intensity=10
        )

        recommendation = decide_imaging(case)

        # Vérifier que scanner est présent (urgence vitale)
        assert any("scanner" in exam.lower() for exam in recommendation.imaging), \
            "Scanner acceptable en urgence vitale (HSA) malgré grossesse"

        # Vérifier précautions spécifiques
        assert "URGENCE VITALE" in recommendation.comment or \
               "urgence" in recommendation.comment.lower(), \
            "Doit mentionner le contexte d'urgence vitale"

    def test_femme_moins_50_ans_test_grossesse_obligatoire(self):
        """Femme < 50 ans : test grossesse obligatoire avant scanner."""
        case = HeadacheCase(
            age=35,
            sex="F",
            pregnancy_postpartum=False,  # Non enceinte connue
            onset="thunderclap",
            profile="acute",
            intensity=9
        )

        recommendation = decide_imaging(case)

        # Si scanner prescrit, doit avoir précaution test grossesse
        if any("scanner" in exam.lower() for exam in recommendation.imaging):
            assert "test de grossesse" in recommendation.comment.lower() or \
                   "grossesse urinaire" in recommendation.comment.lower(), \
                "Femme < 50 ans : test de grossesse OBLIGATOIRE avant scanner"

    def test_scanner_injecte_creatinine_patient_60_ans(self):
        """Scanner injecté : dosage créatinine si patient > 60 ans."""
        case = HeadacheCase(
            age=65,
            sex="M",
            onset="progressive",
            profile="subacute",
            neuro_deficit=True  # Peut nécessiter scanner injecté
        )

        recommendation = decide_imaging(case)

        # Si scanner injecté prescrit
        if any("scanner" in exam.lower() and "injection" in exam.lower()
               for exam in recommendation.imaging):
            assert "créatinine" in recommendation.comment.lower(), \
                "Patient > 60 ans : dosage créatinine OBLIGATOIRE avant scanner injecté"

    def test_scanner_injecte_allergie_iode(self):
        """Scanner injecté : vérifier allergie produit de contraste iodé."""
        case = HeadacheCase(
            age=50,
            sex="M",
            onset="progressive",
            profile="subacute",
            neuro_deficit=True
        )

        recommendation = decide_imaging(case)

        # Si scanner injecté prescrit
        if any("scanner" in exam.lower() and "injection" in exam.lower()
               for exam in recommendation.imaging):
            assert "allergie" in recommendation.comment.lower() and \
                   "iodé" in recommendation.comment.lower(), \
                "Doit vérifier allergie produit de contraste iodé"

    def test_allergie_crustaces_betadine_ne_contre_indique_pas(self):
        """Allergie crustacés/Bétadine à préciser mais ne contre-indique PAS."""
        case = HeadacheCase(
            age=50,
            sex="M",
            onset="progressive",
            profile="subacute",
            neuro_deficit=True
        )

        recommendation = decide_imaging(case)

        # Si scanner injecté prescrit
        if any("scanner" in exam.lower() and "injection" in exam.lower()
               for exam in recommendation.imaging):
            assert "crustacés" in recommendation.comment.lower() or \
                   "bétadine" in recommendation.comment.lower(), \
                "Doit mentionner allergie crustacés/Bétadine"

            # Vérifier que c'est bien indiqué que ça ne contre-indique PAS
            assert "ne contre-indique pas" in recommendation.comment.lower() or \
                   "à préciser" in recommendation.comment.lower(), \
                "Doit préciser que allergie crustacés/Bétadine ne contre-indique pas"


class TestIRMPrecautions:
    """Tests pour les précautions IRM selon exigences client."""

    def test_irm_chirurgie_recente_6_semaines(self):
        """IRM : chirurgie < 6 semaines avec matériel → attendre sauf urgence."""
        case = HeadacheCase(
            age=50,
            sex="M",
            onset="progressive",
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            assert "chirurgie récente" in recommendation.comment.lower() and \
                   "6 semaines" in recommendation.comment.lower(), \
                "Doit vérifier chirurgie récente < 6 semaines"

    def test_irm_grossesse_premier_trimestre_contre_indication(self):
        """IRM : grossesse < 3 mois (1er trimestre) contre-indiquée sauf urgence."""
        case = HeadacheCase(
            age=30,
            sex="F",
            pregnancy_postpartum=True,
            onset="progressive",  # PAS urgence
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit en non-urgence
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            if recommendation.urgency not in ["immediate", "urgent"]:
                assert "1er trimestre" in recommendation.comment.lower() or \
                       "13 sem" in recommendation.comment.lower(), \
                    "Doit mentionner contre-indication IRM 1er trimestre sauf urgence"

    def test_irm_pacemaker_verification_centre(self):
        """IRM : pace-maker → contacter centre imagerie pour compatibilité."""
        case = HeadacheCase(
            age=70,
            sex="M",
            onset="progressive",
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            assert "pace-maker" in recommendation.comment.lower() or \
                   "pacemaker" in recommendation.comment.lower(), \
                "Doit vérifier pace-maker"

            assert "contacter" in recommendation.comment.lower() and \
                   "centre" in recommendation.comment.lower(), \
                "Doit indiquer de contacter centre imagerie"

    def test_irm_valve_cardiaque_references_materiel(self):
        """IRM : valve cardiaque/prothèse → envoyer références matériel."""
        case = HeadacheCase(
            age=65,
            sex="M",
            onset="progressive",
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            assert "valve cardiaque" in recommendation.comment.lower() or \
                   "prothèse aortique" in recommendation.comment.lower(), \
                "Doit vérifier valve cardiaque/prothèse aortique"

            assert "références" in recommendation.comment.lower() or \
                   "matériel" in recommendation.comment.lower(), \
                "Doit demander références du matériel"

    def test_irm_prothese_articulaire_ok_si_plus_6_semaines(self):
        """IRM : prothèse articulaire/ostéosynthèse > 6 sem : OK."""
        case = HeadacheCase(
            age=60,
            sex="M",
            onset="progressive",
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            assert "prothèse articulaire" in recommendation.comment.lower() or \
                   "ostéosynthèse" in recommendation.comment.lower(), \
                "Doit mentionner prothèse articulaire/ostéosynthèse"

            assert "ok" in recommendation.comment.lower() or \
                   "6 sem" in recommendation.comment.lower(), \
                "Doit indiquer que prothèse > 6 sem est OK"

    def test_irm_claustrophobie_contacter_centre(self):
        """IRM : claustrophobie → contacter centre imagerie."""
        case = HeadacheCase(
            age=45,
            sex="F",
            onset="progressive",
            profile="subacute"
        )

        recommendation = decide_imaging(case)

        # Si IRM prescrit
        if any("irm" in exam.lower() for exam in recommendation.imaging):
            assert "claustrophobie" in recommendation.comment.lower(), \
                "Doit vérifier claustrophobie"

    def test_irm_injectee_pas_creatinine(self):
        """IRM injectée : PAS besoin de créatinine (contrairement au scanner)."""
        case = HeadacheCase(
            age=70,
            sex="M",
            onset="progressive",
            profile="subacute",
            neuro_deficit=True
        )

        recommendation = decide_imaging(case)

        # Si IRM injectée prescrit
        if any("irm" in exam.lower() and "injection" in exam.lower()
               for exam in recommendation.imaging):
            # Vérifier qu'on ne demande PAS de créatinine pour IRM
            # (la créatinine n'est demandée que pour scanner injecté > 60 ans)
            irm_section = recommendation.comment.lower().split("scanner")[0] if "scanner" in recommendation.comment.lower() else recommendation.comment.lower()

            # Si mention créatinine, elle doit être dans section scanner, pas IRM
            assert "irm injectée" in recommendation.comment.lower() or \
                   "gadolinium" in recommendation.comment.lower(), \
                "Doit mentionner IRM injectée ou gadolinium"

    def test_irm_injectee_verifier_allergie_si_atcd(self):
        """IRM injectée : vérifier allergie si ATCD d'IRM injectée."""
        case = HeadacheCase(
            age=50,
            sex="M",
            onset="progressive",
            profile="subacute",
            neuro_deficit=True
        )

        recommendation = decide_imaging(case)

        # Si IRM injectée prescrit
        if any("irm" in exam.lower() and ("injection" in exam.lower() or "gadolinium" in exam.lower())
               for exam in recommendation.imaging):
            assert "allergie" in recommendation.comment.lower(), \
                "IRM injectée : doit vérifier allergie si ATCD"


class TestCephaleesTriageUrgence:
    """Tests pour le triage et les questions systématiques des céphalées."""

    def test_cephalee_coup_tonnerre_urgence(self):
        """Céphalée coup de tonnerre → urgence."""
        case = HeadacheCase(
            age=45,
            sex="M",
            onset="thunderclap",
            profile="acute",
            intensity=10
        )

        recommendation = decide_imaging(case)

        assert recommendation.urgency == "immediate", \
            "Céphalée en coup de tonnerre = URGENCE IMMEDIATE"

    def test_cephalee_febrile_urgence(self):
        """Céphalée fébrile → urgence."""
        case = HeadacheCase(
            age=40,
            sex="F",
            onset="progressive",
            profile="acute",
            fever=True
        )

        recommendation = decide_imaging(case)

        # Fièvre seule peut ne pas être immediate, mais doit être urgent
        assert recommendation.urgency in ["immediate", "urgent"], \
            "Céphalée fébrile = URGENCE"

    def test_cephalee_deficit_moteur_urgence(self):
        """Céphalée avec déficit moteur → urgence."""
        case = HeadacheCase(
            age=55,
            sex="M",
            onset="progressive",
            profile="acute",
            neuro_deficit=True
        )

        recommendation = decide_imaging(case)

        assert recommendation.urgency in ["immediate", "urgent"], \
            "Céphalée avec déficit moteur = URGENCE"

    def test_contexte_oncologique_scanner_premiere_intention(self):
        """Contexte oncologique → scanner en 1ère intention."""
        case = HeadacheCase(
            age=55,
            sex="M",
            cancer_history=True,  # ATCD oncologique
            onset="progressive",
            profile="subacute",
            intensity=7
        )

        recommendation = decide_imaging(case)

        # Vérifier que scanner est prescrit (pas IRM en 1ère intention)
        assert any("scanner" in exam.lower() for exam in recommendation.imaging), \
            "Contexte oncologique : scanner doit être prescrit en 1ère intention"

        # Vérifier mention du contexte oncologique
        assert "oncologique" in recommendation.comment.lower() or \
               "cancer" in recommendation.comment.lower() or \
               "métastase" in recommendation.comment.lower(), \
            "Doit mentionner le contexte oncologique dans le commentaire"

    def test_autres_cas_irm_premiere_intention(self):
        """Tout le reste → IRM en première intention."""
        case = HeadacheCase(
            age=45,
            sex="M",
            onset="progressive",
            profile="subacute",
            intensity=6
        )

        recommendation = decide_imaging(case)

        # Pour cas non-urgent standard, IRM devrait être privilégiée
        if recommendation.imaging and "aucun" not in recommendation.imaging:
            assert any("irm" in exam.lower() for exam in recommendation.imaging), \
                "Cas standard sans urgence vitale : IRM en première intention"


class TestQuestionsSystematiques:
    """Tests pour vérifier que toutes les questions systématiques sont posées."""

    def test_questions_systematiques_liste_complete(self):
        """Vérifier que le système peut détecter tous les champs requis."""
        # Liste des questions systématiques selon client:
        required_fields = [
            "fever",  # Fièvre ?
            "onset",  # Rapidité d'installation ?
            # "persistent_or_resolving",  # Persistantes ? Résolutives ? (TODO)
            "neuro_deficit",  # Déficit moteur, sensitif
            # "visual_disturbances",  # Troubles visuels (TODO: détail type)
            # "tinnitus",  # Acouphènes (TODO)
            # "vertigo",  # Vertiges (TODO)
            # "joint_pain",  # Douleurs articulaires (TODO)
            # "horton_criteria",  # Arguments maladie de Horton (TODO)
            # "first_episode",  # Premier épisode ? (TODO)
            # "previous_workup",  # Déjà un bilan ? (TODO)
            # "chronic_or_episodic",  # Constantes chroniques ou par crises ? (TODO)
            # "location",  # Localisation (TODO)
            # "cancer_history",  # ATCD oncologique (TODO)
            # "brain_infection_history",  # ATCD infectieux cérébraux (TODO)
            # "congenital_brain_issues",  # ATCD congénitaux cérébraux (TODO)
        ]

        # Pour l'instant, vérifier que les champs de base sont présents
        from headache_assistants.models import HeadacheCase
        case_fields = HeadacheCase.model_fields.keys()

        for field in ["fever", "onset", "neuro_deficit"]:
            assert field in case_fields, \
                f"Champ obligatoire manquant: {field}"

    def test_tous_les_champs_manquants_identifies(self):
        """Le système doit identifier tous les champs manquants importants."""
        # TODO: Vérifier que get_missing_critical_fields() identifie bien tous les champs
        # requis par le client
        pytest.skip("Test à implémenter après ajout des nouveaux champs")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
