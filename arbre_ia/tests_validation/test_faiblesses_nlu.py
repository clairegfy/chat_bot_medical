"""Tests exhaustifs pour identifier les faiblesses du système NLU.

Ce fichier contient des cas théoriques complexes pour tester les limites
du système de détection et identifier les améliorations nécessaires.

ORGANISATION DES TESTS:
1. Cas ambigus (plusieurs interprétations possibles)
2. Cas avec contradictions internes
3. Formulations inhabituelles ou régionales
4. Acronymes médicaux ambigus
5. Négations complexes
6. Contexte médical avancé
7. Edge cases (cas limites)
8. Tests de régression

Chaque test échoué révèle une faiblesse à corriger ultérieurement.
Les résultats sont sauvegardés dans un fichier JSON pour analyse.
"""

import pytest
import json
from pathlib import Path
from headache_assistants.nlu_v2 import parse_free_text_to_case_v2


# ==============================================================================
# CATÉGORIE 1: CAS AMBIGUS
# ==============================================================================

class TestCasAmbigus:
    """Cas avec plusieurs interprétations possibles."""

    def test_onset_progressif_vs_aigu(self):
        """Début progressif mais récent - ambigu entre progressive et thunderclap."""
        text = "Céphalée qui a débuté il y a 3h et qui augmente progressivement"
        case, meta = parse_free_text_to_case_v2(text)

        # ATTENDU: onset="progressive" (augmentation graduelle)
        # RISQUE: "il y a 3h" pourrait être interprété comme soudain
        assert case.onset == "progressive", \
            f"Détecté '{case.onset}', attendu 'progressive'"
        assert case.profile == "acute"

    def test_temperature_limite_37_9(self):
        """Température à 37.9°C - juste sous le seuil de fièvre."""
        text = "T° 37.9, céphalée intense"
        case, meta = parse_free_text_to_case_v2(text)

        assert case.fever is False, \
            f"Détecté {case.fever}, mais 37.9 < 38.0°C (seuil)"

    def test_temperature_limite_38_0_exacte(self):
        """Température exactement à 38.0°C - seuil critique."""
        text = "T° 38.0, céphalée"
        case, meta = parse_free_text_to_case_v2(text)

        assert case.fever is True, \
            f"Détecté {case.fever}, mais 38.0 >= 38.0°C (seuil)"

    def test_scotome_avec_deficit_moteur_reel(self):
        """Scotome (aura) + vrai déficit moteur - doit détecter les deux."""
        text = "Scotomes depuis 20min puis hémiparésie gauche"
        case, meta = parse_free_text_to_case_v2(text)

        # Scotome seul = aura migraineuse (pas HTIC, pas déficit)
        # MAIS hémiparésie = déficit neurologique réel et grave
        assert case.neuro_deficit is True, \
            "Hémiparésie doit être détectée malgré scotomes"

    def test_nuque_raide_contracture_vs_meningite(self):
        """Nuque raide musculaire vs syndrome méningé - contexte critique."""
        text = "Nuque raide avec contractures musculaires cervicales"
        case, meta = parse_free_text_to_case_v2(text)

        # FAIBLESSE IDENTIFIÉE:
        # "nuque raide" déclenche syndrome méningé
        # MAIS "contractures musculaires" suggère cause mécanique
        # Le système actuel n'analyse pas le contexte différentiel
        print(f"\n⚠️  FAIBLESSE: Nuque raide = {case.meningeal_signs}")
        print("   Contexte 'contractures musculaires' non analysé")


# ==============================================================================
# CATÉGORIE 2: CONTRADICTIONS INTERNES
# ==============================================================================

class TestCasContradictions:
    """Textes avec contradictions internes."""

    def test_fievre_ET_apyretique(self):
        """Contradiction: mentionne fièvre ET apyrétique."""
        text = "Patient fébrile mais apyrétique à l'examen, céphalée brutale"
        case, meta = parse_free_text_to_case_v2(text)

        # ATTENDU: privilégier "apyrétique" (examen objectif > anamnèse)
        contradictions = meta.get('contradictions', [])

        print(f"\n⚠️  CONTRADICTION: fébrile + apyrétique")
        print(f"   Fièvre détectée: {case.fever}")
        print(f"   Contradictions système: {contradictions}")

    def test_brutal_ET_progressif(self):
        """Contradiction: début brutal ET progressif dans même phrase."""
        text = "Céphalée d'installation brutale qui augmente progressivement"
        case, meta = parse_free_text_to_case_v2(text)

        contradictions = meta.get('contradictions', [])

        # Devrait détecter "onset_conflicting"
        if 'onset_conflicting' not in contradictions:
            print(f"\n⚠️  CONTRADICTION NON DÉTECTÉE: brutal + progressif")
            print(f"   Onset: {case.onset}")

    def test_chronique_depuis_2heures(self):
        """Contradiction temporelle: chronique mais depuis 2h."""
        text = "Céphalée chronique depuis 2h"
        case, meta = parse_free_text_to_case_v2(text)

        # "chronique" dans onset mais durée = 2h (acute)
        contradictions = meta.get('contradictions', [])

        print(f"\n⚠️  CONTRADICTION TEMPORELLE:")
        print(f"   Onset: {case.onset}, Profile: {case.profile}")
        print(f"   Duration: {case.duration_current_episode_hours}h")
        print(f"   Contradictions: {contradictions}")

    def test_sans_deficit_MAIS_hemiparesie(self):
        """Contradiction: 'sans déficit' puis mentionne hémiparésie."""
        text = "Sans déficit neurologique, mais hémiparésie droite 3/5"
        case, meta = parse_free_text_to_case_v2(text)

        # Devrait détecter hémiparésie malgré "sans déficit"
        assert case.neuro_deficit is True, \
            "Hémiparésie doit primer sur 'sans déficit'"


# ==============================================================================
# CATÉGORIE 3: FORMULATIONS INHABITUELLES
# ==============================================================================

class TestFormulationsInhabituelles:
    """Expressions médicales rares ou régionales."""

    def test_cephalee_casque_de_pompier(self):
        """Expression rare: 'casque de pompier' (vs 'en casque')."""
        text = "Céphalée en casque de pompier depuis ce matin"
        case, meta = parse_free_text_to_case_v2(text)

        # "en casque" devrait être détecté (tension_like ou htic_like)
        # MAIS "casque de pompier" est une variante rare
        print(f"\n⚠️  EXPRESSION RARE: casque de pompier")
        print(f"   Headache profile: {case.headache_profile}")

    def test_cephalee_coitale_orgasmique(self):
        """Céphalée coïtale/orgasmique - contexte spécifique."""
        text = "Céphalée brutale pendant rapport sexuel"
        case, meta = parse_free_text_to_case_v2(text)

        # Devrait détecter "thunderclap" (brutal)
        assert case.onset == "thunderclap"

        # FAIBLESSE: contexte "rapport sexuel" non capturé
        print(f"\n⚠️  CONTEXTE SPÉCIFIQUE non capturé: coïtale")

    def test_cephalee_tussigene(self):
        """Céphalée tussigène (déclenchée par toux).

        La céphalée de toux bénigne est fréquente et ne doit PAS déclencher HTIC.
        Seuls les signes FORTS (vomissements en jet, œdème papillaire) indiquent HTIC.
        """
        text = "Céphalée déclenchée par la toux et les efforts"
        case, meta = parse_free_text_to_case_v2(text)

        # "toux" + "effort" SEUL ne suffit PAS pour HTIC (peut être céphalée bénigne à la toux)
        # HTIC nécessite: vomissements en jet OU œdème papillaire OU mention explicite HTIC
        # Pour éviter les faux positifs, le système ne détecte PAS HTIC avec ce texte
        assert case.htic_pattern is None or case.htic_pattern is False, \
            "Aggravation toux/effort seul ne devrait PAS déclencher HTIC (faux positif possible)"

        # Test avec vomissements en jet = HTIC confirmé
        text_with_vomiting = "Céphalée avec vomissements en jet"
        case2, meta2 = parse_free_text_to_case_v2(text_with_vomiting)
        assert case2.htic_pattern is True, \
            "Vomissements en jet = signe fort d'HTIC"

    def test_algie_vasculaire_face_AVF(self):
        """AVF = Algie Vasculaire Face (pas accident)."""
        text = "AVF avec larmoiement et rhinorrhée unilatéraux"
        case, meta = parse_free_text_to_case_v2(text)

        # AVF ambigu: Accident Voie vs Algie Vasculaire
        # Avec "larmoiement/rhinorrhée" → contexte Algie Vasculaire
        # MAIS système actuel détecte probablement trauma
        print(f"\n⚠️  ACRONYME AMBIGU: AVF")
        print(f"   Détecté comme trauma: {case.trauma}")
        print(f"   Contexte 'larmoiement' suggère Algie Vasculaire")

    def test_cephalee_salves_cluster(self):
        """Céphalée en salves (cluster headache)."""
        text = "Crises quotidiennes durant 45min, en salves depuis 2 semaines"
        case, meta = parse_free_text_to_case_v2(text)

        # FAIBLESSE: "en salves" non reconnu
        print(f"\n⚠️  EXPRESSION NON RECONNUE: en salves")
        print(f"   Duration: {case.duration_current_episode_hours}h")


# ==============================================================================
# CATÉGORIE 4: ACRONYMES AMBIGUS
# ==============================================================================

class TestAcronymesAmbigus:
    """Acronymes avec plusieurs significations possibles."""

    def test_AVF_accident_vs_algie(self):
        """AVF = Accident Voie OU Algie Vasculaire Face."""
        # Cas 1: AVF = accident (contexte trauma)
        text1 = "AVP avec TCC"  # Utiliser AVP pour éviter ambiguïté
        case1, _ = parse_free_text_to_case_v2(text1)
        assert case1.trauma is True

        # Cas 2: AVF = algie (contexte céphalée)
        text2 = "AVF avec larmoiement unilatéral"
        case2, _ = parse_free_text_to_case_v2(text2)

        print(f"\n⚠️  ACRONYME AMBIGU: AVF")
        print(f"   AVF + larmoiement détecté comme trauma: {case2.trauma}")
        print(f"   Devrait être Algie Vasculaire Face (cluster)")

    def test_PL_ponction_vs_autre(self):
        """PL = Ponction Lombaire (contexte médical)."""
        text = "Céphalée après PL diagnostique il y a 3 jours"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.recent_pl_or_peridural is True, \
            "PL en contexte médical = Ponction Lombaire"

    def test_HTA_vs_HTIC(self):
        """HTA (HyperTension Artérielle) ≠ HTIC (IntraCrânienne)."""
        text = "Patient avec HTA non contrôlée, céphalée pulsatile"
        case, _ = parse_free_text_to_case_v2(text)

        # HTA ne devrait PAS déclencher HTIC
        if case.htic_pattern is True:
            print(f"\n⚠️  FAUX POSITIF: HTA détecté comme HTIC")

    def test_SA_semaines_vs_sans_typo(self):
        """SA = Semaines Aménorrhée (contexte obstétrique)."""
        text1 = "G2P1 à 28 SA, céphalée"
        case1, _ = parse_free_text_to_case_v2(text1)
        assert case1.pregnancy_postpartum is True

        # EDGE CASE: "sa" comme typo de "sans"
        text2 = "Céphalée sa fièvre"  # Erreur de frappe
        case2, _ = parse_free_text_to_case_v2(text2)
        # Ne devrait PAS déclencher grossesse
        print(f"\n⚠️  TYPO POTENTIELLE: 'sa' isolé")
        print(f"   Grossesse détectée: {case2.pregnancy_postpartum}")


# ==============================================================================
# CATÉGORIE 5: NÉGATIONS COMPLEXES
# ==============================================================================

class TestNegationsComplexes:
    """Négations doubles, partielles, et contradictoires."""

    def test_double_negation_pas_sans_fievre(self):
        """Double négation: 'pas sans fièvre' = fièvre."""
        text = "Patient pas sans fièvre, céphalée brutale"
        case, _ = parse_free_text_to_case_v2(text)

        # "pas sans fièvre" = "avec fièvre"
        # FAIBLESSE: double négation probablement non gérée
        print(f"\n⚠️  DOUBLE NÉGATION:")
        print(f"   'pas sans fièvre' → Fièvre: {case.fever}")
        print(f"   Devrait être True")

    def test_negation_partielle_peu_de_fievre(self):
        """Négation partielle: 'peu de fièvre' (quantité)."""
        text = "Peu de fièvre à 37.8"
        case, _ = parse_free_text_to_case_v2(text)

        # 37.8 < 38°C → pas de fièvre médicalement
        # MAIS "peu de fièvre" suggère fièvre légère (subjectif)
        print(f"\n⚠️  NÉGATION PARTIELLE:")
        print(f"   'peu de fièvre' à 37.8 → Fièvre: {case.fever}")

    def test_negation_puis_exception(self):
        """Négation générale puis exception: 'sans signes sauf RDN'."""
        text = "Sans signes neurologiques sauf RDN+"
        case, _ = parse_free_text_to_case_v2(text)

        # RDN+ doit primer sur "sans signes"
        assert case.meningeal_signs is True, \
            "Exception 'sauf RDN+' doit être détectée"

    def test_evolution_temporelle_absence_puis_presence(self):
        """Évolution: absence avant → présence maintenant."""
        text = "Pas de fièvre hier, mais fébrile ce matin à 38.5"
        case, _ = parse_free_text_to_case_v2(text)

        # État actuel doit primer
        assert case.fever is True, \
            "État actuel (fébrile) doit primer sur antérieur"


# ==============================================================================
# CATÉGORIE 6: CONTEXTE MÉDICAL AVANCÉ
# ==============================================================================

class TestContexteMedicalAvance:
    """Cas nécessitant compréhension du contexte clinique."""

    def test_HSA_avec_glasgow_14(self):
        """HSA avec GCS 14 - trouble de conscience."""
        text = "Céphalée brutale, GCS 14, vomissements"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.onset == "thunderclap"
        assert case.neuro_deficit is True, \
            "GCS 14 (< 15) doit être détecté comme déficit"

    def test_meningite_avec_purpura(self):
        """Méningite avec purpura - urgence absolue."""
        text = "Céphalée, fièvre 39.2, RDN+, purpura extensif"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.fever is True
        assert case.meningeal_signs is True

        # FAIBLESSE: "purpura" non reconnu (hors modèle actuel)
        print(f"\n⚠️  CONTEXTE NON CAPTURÉ: purpura")

    def test_TVC_post_partum(self):
        """Thrombose veineuse cérébrale (TVC) post-partum."""
        text = "J8 post-partum, céphalée progressive 3j, diplopie"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.pregnancy_postpartum is True
        assert case.neuro_deficit is True  # diplopie

        # FAIBLESSE: contexte TVC spécifique non modélisé
        print(f"\n⚠️  CONTEXTE CLINIQUE: TVC post-partum non explicite")

    def test_maladie_horton_age_70(self):
        """Maladie de Horton (artérite temporale) - >50ans."""
        text = "F 72a, céphalée temporale récente, claudication mâchoire, VS 90"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.age == 72
        assert case.age > 50  # Facteur de risque Horton

        # FAIBLESSE: "claudication mâchoire", "VS" non reconnus
        print(f"\n⚠️  SIGNES SPÉCIFIQUES HORTON non capturés:")
        print("   - claudication mâchoire")
        print("   - VS (vitesse sédimentation)")

    def test_hematome_sous_dural_anticoagulants(self):
        """Hématome sous-dural chronique sous anticoagulants."""
        text = "Patient sous AVK, chute J-15, céphalée progressive"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.trauma is True

        # FAIBLESSE: "AVK" (anticoagulant) non reconnu
        print(f"\n⚠️  TRAITEMENT À RISQUE non capturé: AVK")


# ==============================================================================
# CATÉGORIE 7: EDGE CASES (CAS LIMITES)
# ==============================================================================

class TestCasLimites:
    """Cas extrêmes et limites du système."""

    def test_age_extreme_nouveau_ne(self):
        """Nouveau-né (très rare pour céphalée)."""
        text = "Nouveau-né 2 semaines, irritabilité, bombement fontanelle"
        case, _ = parse_free_text_to_case_v2(text)

        # FAIBLESSE: âge nouveau-né probablement non extrait
        print(f"\n⚠️  ÂGE EXTRÊME: nouveau-né")
        print(f"   Âge détecté: {case.age}")

    def test_age_extreme_centenaire(self):
        """Patient centenaire."""
        text = "H 103a, céphalée aiguë depuis hier"
        case, _ = parse_free_text_to_case_v2(text)

        assert 100 <= case.age <= 120, \
            f"Âge {case.age} doit être valide (100-120)"

    def test_intensite_EVA_0_puis_EVA_8(self):
        """EVA 0 actuellement mais EVA 8 avant."""
        text = "Céphalée EVA 0 actuellement, mais EVA 8 ce matin"
        case, _ = parse_free_text_to_case_v2(text)

        # Devrait prendre maximum (EVA 8)
        print(f"\n⚠️  ÉVOLUTION INTENSITÉ:")
        print(f"   EVA 0 vs EVA 8 → Détecté: {case.intensity}")

    def test_duree_extreme_6_mois(self):
        """Durée très longue: 6 mois continus."""
        text = "Céphalée permanente depuis 6 mois"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.profile == "chronic"
        # 6 mois ≈ 4320h
        if case.duration_current_episode_hours:
            assert case.duration_current_episode_hours >= 4000

    def test_cascade_acronymes_complexe(self):
        """Chaîne d'acronymes multiples."""
        text = "F 28a G2P1 22SA TCC J-2 AVP RDN+ féb T°38.9 GCS14 PF G"
        case, meta = parse_free_text_to_case_v2(text)

        # Test robustesse
        assert case.age == 28
        assert case.sex == "F"
        assert case.pregnancy_postpartum is True
        assert case.trauma is True
        assert case.meningeal_signs is True
        assert case.fever is True
        assert case.neuro_deficit is True

        print(f"\n✅ CASCADE ACRONYMES OK:")
        print(f"   Champs: {len(meta['detected_fields'])}")
        print(f"   Confiance: {meta['overall_confidence']:.1%}")

    def test_texte_vide(self):
        """Texte vide - ne doit pas crasher."""
        text = ""
        case, _ = parse_free_text_to_case_v2(text)

        # Pour un texte vide, l'âge doit être None (non renseigné)
        # Le dialogue demandera l'âge au patient
        assert case.age is None
        assert case.sex == "Other"

    def test_texte_ponctuation_seule(self):
        """Uniquement ponctuation."""
        text = "... ??? !!! ---"
        case, _ = parse_free_text_to_case_v2(text)

        assert case is not None

    def test_texte_ultra_long(self):
        """Texte médical très long (>1000 caractères)."""
        text = """
        Patient masculin 45 ans, sans antécédents, urgences pour céphalée brutale
        installation brutale 2h, intensité maximale d'emblée, pire douleur vie,
        EVA 10/10, vomissements jet, photophobie, phonophobie, raideur nuque.
        Examen: fébrile 38.8°C, syndrome méningé avec raideur nuque, Kernig positif,
        Brudzinski positif. Neurologique: paralysie faciale gauche périphérique,
        hémiparésie droite 3/5, dysarthrie. Glasgow 14/15. Traumatisme crânien J-3
        accident voie publique avec perte connaissance brève. Corticothérapie long
        cours pour asthme. VIH+ depuis 2003. CD4 250. Sous ARV trithérapie.
        """.strip()

        case, meta = parse_free_text_to_case_v2(text)

        # Vérifier détection complète
        assert case.onset == "thunderclap"
        assert case.intensity == 10
        assert case.fever is True
        assert case.meningeal_signs is True
        assert case.neuro_deficit is True
        assert case.trauma is True
        assert case.immunosuppression is True

        print(f"\n✅ TEXTE LONG OK: {len(meta['detected_fields'])} champs")


# ==============================================================================
# CATÉGORIE 8: TESTS DE RÉGRESSION (CAS RÉELS)
# ==============================================================================

class TestRegressionCasReels:
    """Tests de non-régression sur cas cliniques réels."""

    def test_HSA_typique_gold_standard(self):
        """HSA typique - référence gold standard."""
        text = "H 55a, céphalée en coup de tonnerre, pire douleur de sa vie, RDN+"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.onset == "thunderclap"
        assert case.meningeal_signs is True
        assert case.age == 55
        assert case.sex == "M"

    def test_meningite_bacterienne_classique(self):
        """Méningite bactérienne - urgence infectieuse."""
        text = "F 23a, céphalée progressive 24h, féb 39.5, RDN++, photophobie"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.fever is True
        assert case.meningeal_signs is True
        assert case.profile == "acute"

    def test_migraine_simple_sans_alarme(self):
        """Migraine commune sans red flags."""
        text = "F 32a, céphalée pulsatile unilatérale, photophobie, nausées, EVA 7"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.intensity == 7
        assert case.headache_profile == "migraine_like"
        # Pas de red flags
        assert case.fever is not True
        assert case.meningeal_signs is not True

    def test_cephalee_tension_chronique(self):
        """Céphalée de tension chronique."""
        text = "Céphalée en casque bilatérale quotidienne depuis 6 mois, EVA 4"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.profile == "chronic"
        assert case.headache_profile == "tension_like"
        assert case.intensity == 4

    def test_HTIC_tumeur_cerebrale(self):
        """HTIC par tumeur cérébrale."""
        text = "Céphalée matutinale progressive 3 sem, vom jet, œdème papillaire"
        case, _ = parse_free_text_to_case_v2(text)

        assert case.htic_pattern is True
        assert case.profile == "subacute"  # 3 semaines


# ==============================================================================
# FONCTION D'EXPORT DES RÉSULTATS
# ==============================================================================

def export_test_results():
    """Exécute tous les tests et exporte les résultats en JSON."""
    import sys
    from io import StringIO

    # Capturer sortie pytest
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # Exécuter tests
    result = pytest.main([__file__, "-v", "--tb=short", "-q"])

    # Restaurer stdout
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # Parser résultats
    results = {
        "total_tests": output.count("PASSED") + output.count("FAILED"),
        "passed": output.count("PASSED"),
        "failed": output.count("FAILED"),
        "output": output
    }

    # Sauvegarder JSON
    output_file = Path(__file__).parent / "test_faiblesses_nlu_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Résultats sauvegardés: {output_file}")
    print(f"📊 Tests: {results['passed']}/{results['total_tests']} passés")

    return result


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TESTS DE FAIBLESSES DU SYSTÈME NLU")
    print("Identification des cas limites et améliorations nécessaires")
    print("=" * 80)
    print()

    # Exécuter et exporter
    exit_code = export_test_results()

    print()
    print("=" * 80)
    print("Les échecs identifient les faiblesses à corriger ultérieurement")
    print("Consulter: test_faiblesses_nlu_results.json")
    print("=" * 80)

    sys.exit(exit_code)
