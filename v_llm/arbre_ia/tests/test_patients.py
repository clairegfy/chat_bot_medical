#!/usr/bin/env python3
"""
Patients tests pour valider le système d'évaluation des céphalées.

Ce fichier contient des cas cliniques types pour tester les différentes
règles médicales et précautions du système.
"""

from headache_assistants.models import HeadacheCase
from headache_assistants.rules_engine import decide_imaging


# =============================================================================
# CAS D'URGENCE ABSOLUE
# =============================================================================

def test_hsa_coup_tonnerre():
    """HSA suspectée - Céphalée en coup de tonnerre"""
    print("\n" + "="*70)
    print("CAS 1: HSA - Coup de tonnerre (Homme 55 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=55, sex="M",
        onset="thunderclap",
        profile="acute",
        intensity=10
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


def test_meningite():
    """Méningite - Fièvre + signes méningés"""
    print("\n" + "="*70)
    print("CAS 2: MÉNINGITE (Femme 28 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=28, sex="F",
        profile="acute",
        fever=True,
        meningeal_signs=True,
        intensity=8
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


def test_deficit_neurologique():
    """Déficit neurologique aigu"""
    print("\n" + "="*70)
    print("CAS 3: DÉFICIT NEUROLOGIQUE (Homme 68 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=68, sex="M",
        profile="acute",
        onset="progressive",
        neuro_deficit=True,
        intensity=7
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS CONTEXTE À RISQUE - GROSSESSE
# =============================================================================

def test_grossesse_brutale():
    """Grossesse + céphalée brutale - Risque TVC"""
    print("\n" + "="*70)
    print("CAS 4: GROSSESSE + COUP DE TONNERRE (Femme 32 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=32, sex="F",
        onset="thunderclap",
        profile="acute",
        pregnancy_postpartum=True,
        intensity=9
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


def test_grossesse_progressive():
    """Grossesse + céphalée progressive"""
    print("\n" + "="*70)
    print("CAS 5: GROSSESSE + CÉPHALÉE PROGRESSIVE (Femme 29 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=29, sex="F",
        onset="progressive",
        profile="subacute",
        pregnancy_postpartum=True,
        intensity=6,
        duration_current_episode_hours=240  # 10 jours
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS PRÉCAUTIONS SCANNER - FEMME < 50 ANS
# =============================================================================

def test_femme_jeune_scanner():
    """Femme < 50 ans nécessitant scanner - Test grossesse obligatoire"""
    print("\n" + "="*70)
    print("CAS 6: FEMME 35 ANS - Scanner requis")
    print("="*70)
    
    case = HeadacheCase(
        age=35, sex="F",
        profile="unknown",  # Déclenchera fallback scanner
        intensity=5
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS HTIC (HYPERTENSION INTRACRÂNIENNE)
# =============================================================================

def test_htic():
    """HTIC - Céphalée matinale, vomissements"""
    print("\n" + "="*70)
    print("CAS 7: HTIC SUSPECTÉE (Homme 45 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=45, sex="M",
        profile="subacute",
        onset="progressive",
        htic_pattern=True,
        intensity=7,
        duration_current_episode_hours=336  # 14 jours
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS PERSONNE ÂGÉE
# =============================================================================

def test_personne_agee():
    """Personne âgée > 60 ans - Vérifications créatinine"""
    print("\n" + "="*70)
    print("CAS 8: PERSONNE ÂGÉE (Femme 72 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=72, sex="F",
        profile="acute",
        onset="progressive",
        intensity=6
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS TRAUMATISME
# =============================================================================

def test_trauma_recent():
    """Traumatisme crânien récent"""
    print("\n" + "="*70)
    print("CAS 9: TRAUMATISME RÉCENT (Homme 25 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=25, sex="M",
        profile="acute",
        onset="progressive",
        trauma=True,
        intensity=7
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS IMMUNODÉPRESSION
# =============================================================================

def test_immunodepression():
    """Patient immunodéprimé avec céphalée"""
    print("\n" + "="*70)
    print("CAS 10: IMMUNODÉPRESSION (Homme 52 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=52, sex="M",
        profile="subacute",
        onset="progressive",
        immunosuppression=True,
        intensity=6,
        duration_current_episode_hours=168  # 7 jours
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# CAS CHRONIQUE SANS RED FLAGS
# =============================================================================

def test_chronique_bénin():
    """Céphalée chronique sans signes d'alarme"""
    print("\n" + "="*70)
    print("CAS 11: CÉPHALÉE CHRONIQUE BÉNIGNE (Femme 38 ans)")
    print("="*70)
    
    case = HeadacheCase(
        age=38, sex="F",
        profile="chronic",
        onset="progressive",
        fever=False,
        meningeal_signs=False,
        neuro_deficit=False,
        intensity=5
    )
    
    decision = decide_imaging(case)
    print(f"Urgence: {decision.urgency.upper()}")
    print(f"Examens: {', '.join(decision.imaging)}")
    print(f"\nCommentaire:\n{decision.comment}")


# =============================================================================
# EXÉCUTION DES TESTS
# =============================================================================

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# TESTS PATIENTS - SYSTÈME D'ÉVALUATION DES CÉPHALÉES")
    print("#"*70)
    
    # Tests urgences absolues
    test_hsa_coup_tonnerre()
    test_meningite()
    test_deficit_neurologique()
    
    # Tests contexte grossesse
    test_grossesse_brutale()
    test_grossesse_progressive()
    
    # Tests précautions
    test_femme_jeune_scanner()
    test_personne_agee()
    
    # Tests contextes spéciaux
    test_htic()
    test_trauma_recent()
    test_immunodepression()
    
    # Test chronique
    test_chronique_bénin()
    
    print("\n" + "#"*70)
    print("# FIN DES TESTS")
    print("#"*70 + "\n")
