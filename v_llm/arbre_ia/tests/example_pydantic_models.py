#!/usr/bin/env python3
"""Exemples d'utilisation des modèles Pydantic.

Ce script démontre comment utiliser les modèles HeadacheCase,
ImagingRecommendation, ChatMessage et ChatResponse.
"""

from headache_assistants.models import (
    HeadacheCase,
    ImagingRecommendation,
    ChatMessage,
    ChatResponse
)


def example_1_simple_headache_case():
    """Exemple 1: Créer un cas simple de céphalée."""
    print("=" * 60)
    print("EXEMPLE 1: Cas simple de céphalée")
    print("=" * 60)
    
    case = HeadacheCase(
        age=45,
        sex="M",
        profile="chronic",
        onset="chronic",
        headache_profile="migraine_like"
    )
    
    print(f"\n📋 Cas créé:")
    print(f"  Âge: {case.age} ans")
    print(f"  Sexe: {case.sex}")
    print(f"  Profil: {case.profile}")
    print(f"  Red flags: {case.has_red_flags()}")
    print(f"  Urgence: {case.is_emergency()}")
    
    print("\n" + "=" * 60 + "\n")


def example_2_emergency_case():
    """Exemple 2: Cas d'urgence vitale (HSA)."""
    print("=" * 60)
    print("EXEMPLE 2: Urgence vitale - Suspicion HSA")
    print("=" * 60)
    
    case = HeadacheCase(
        age=55,
        sex="F",
        profile="acute",
        onset="thunderclap",
        duration_current_episode_hours=2.0,
        fever=False,
        meningeal_signs=False,
        neuro_deficit=False,
        seizure=False,
        htic_pattern=False,
        headache_profile="unknown"
    )
    
    print(f"\n📋 Cas d'urgence:")
    print(f"  Âge: {case.age} ans")
    print(f"  Profil: {case.profile}")
    print(f"  Début: {case.onset} (coup de tonnerre)")
    print(f"  Durée: {case.duration_current_episode_hours}h")
    print(f"\n⚠️  Red flags détectés: {case.has_red_flags()}")
    print(f"🚨 Urgence vitale: {case.is_emergency()}")
    
    # Créer la recommandation d'imagerie
    recommendation = ImagingRecommendation(
        imaging=["scanner_cerebral_sans_injection", "ponction_lombaire"],
        urgency="immediate",
        comment=(
            "Céphalée en coup de tonnerre évocatrice d'hémorragie sous-arachnoïdienne. "
            "Scanner cérébral en urgence, puis ponction lombaire si scanner normal."
        ),
        applied_rule_id="THUNDERCLAP_HSA_001"
    )
    
    print(f"\n🏥 Recommandation d'imagerie:")
    print(f"  Urgence: {recommendation.urgency}")
    print(f"  Examens: {', '.join(recommendation.imaging)}")
    print(f"  Commentaire: {recommendation.comment}")
    
    print("\n" + "=" * 60 + "\n")


def example_3_meningitis_case():
    """Exemple 3: Suspicion de méningite."""
    print("=" * 60)
    print("EXEMPLE 3: Suspicion de méningite")
    print("=" * 60)
    
    case = HeadacheCase(
        age=28,
        sex="M",
        profile="acute",
        onset="progressive",
        duration_current_episode_hours=24.0,
        fever=True,
        meningeal_signs=True,
        neuro_deficit=False,
        seizure=False,
        red_flag_context=["fièvre", "signes méningés"],
        headache_profile="unknown"
    )
    
    print(f"\n📋 Cas suspect:")
    print(f"  Âge: {case.age} ans")
    print(f"  Fièvre: {case.fever}")
    print(f"  Signes méningés: {case.meningeal_signs}")
    print(f"  Durée: {case.duration_current_episode_hours}h")
    print(f"\n⚠️  Red flags: {case.red_flag_context}")
    print(f"🚨 Urgence: {case.is_emergency()}")
    
    recommendation = ImagingRecommendation(
        imaging=["ponction_lombaire"],
        urgency="immediate",
        comment=(
            "Syndrome méningé fébrile. Ponction lombaire en urgence après élimination "
            "de contre-indications. Scanner si signes de focalisation."
        ),
        applied_rule_id="MENINGITE_001"
    )
    
    print(f"\n🏥 Recommandation:")
    print(f"  Urgence: {recommendation.urgency}")
    print(f"  Examen: {recommendation.imaging[0]}")
    
    print("\n" + "=" * 60 + "\n")


def example_4_chat_interaction():
    """Exemple 4: Interaction de chat complète."""
    print("=" * 60)
    print("EXEMPLE 4: Interaction de chat")
    print("=" * 60)
    
    # Message utilisateur
    user_msg = ChatMessage(
        role="user",
        content="J'ai une douleur intense à la tête qui a commencé brutalement ce matin",
        metadata={"raw_input": True}
    )
    
    print(f"\n👤 Message utilisateur:")
    print(f"  Contenu: {user_msg.content}")
    print(f"  Timestamp: {user_msg.timestamp}")
    
    # Réponse de l'assistant
    assistant_msg = ChatMessage(
        role="assistant",
        content="Je comprends. Avez-vous de la fièvre ?",
        metadata={"question_type": "yes_no", "field": "fever"}
    )
    
    print(f"\n🤖 Réponse assistant:")
    print(f"  Contenu: {assistant_msg.content}")
    
    # Construire progressivement le cas
    case = HeadacheCase(
        age=52,
        sex="F",
        profile="acute",
        onset="thunderclap"
    )
    
    # Réponse avec recommandation
    response = ChatResponse(
        message=(
            "⚠️ ATTENTION: Votre description suggère une urgence médicale. "
            "Je vous recommande de consulter immédiatement les urgences."
        ),
        session_id="chat-session-001",
        next_question=None,
        headache_case=case,
        imaging_recommendation=ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection"],
            urgency="immediate",
            comment="Suspicion HSA - début brutal"
        ),
        requires_more_info=False,
        dialogue_complete=True,
        confidence_score=0.90
    )
    
    print(f"\n📤 Réponse finale:")
    print(f"  Message: {response.message}")
    print(f"  Dialogue terminé: {response.dialogue_complete}")
    print(f"  Confiance: {response.confidence_score:.0%}")
    print(f"  Urgence: {response.is_emergency_response()}")
    
    print("\n" + "=" * 60 + "\n")


def example_5_json_export():
    """Exemple 5: Export JSON des modèles."""
    print("=" * 60)
    print("EXEMPLE 5: Export JSON")
    print("=" * 60)
    
    case = HeadacheCase(
        age=35,
        sex="M",
        profile="chronic",
        onset="chronic",
        fever=False,
        headache_profile="migraine_like",
        red_flag_context=[]
    )
    
    # Export en dictionnaire
    case_dict = case.model_dump()
    print(f"\n📄 Dictionnaire Python:")
    print(f"  Clés: {list(case_dict.keys())[:5]}...")
    
    # Export en JSON
    case_json = case.model_dump_json(indent=2)
    print(f"\n📄 JSON (extrait):")
    print(case_json[:200] + "...")
    
    # Import depuis JSON
    case_reloaded = HeadacheCase.model_validate_json(case_json)
    print(f"\n✅ Cas rechargé depuis JSON:")
    print(f"  Âge: {case_reloaded.age}")
    print(f"  Profil: {case_reloaded.profile}")
    
    print("\n" + "=" * 60 + "\n")


def example_6_validation_errors():
    """Exemple 6: Gestion des erreurs de validation."""
    print("=" * 60)
    print("EXEMPLE 6: Validation des données")
    print("=" * 60)
    
    print("\n✅ Cas valide:")
    try:
        valid_case = HeadacheCase(age=45, sex="M")
        print(f"  Cas créé: {valid_case.age} ans, {valid_case.sex}")
    except Exception as e:
        print(f"  Erreur: {e}")
    
    print("\n❌ Âge négatif:")
    try:
        invalid_case = HeadacheCase(age=-5, sex="M")
    except Exception as e:
        print(f"  Erreur détectée: {type(e).__name__}")
    
    print("\n❌ Durée négative:")
    try:
        invalid_case = HeadacheCase(
            age=45,
            sex="M",
            duration_current_episode_hours=-10.0
        )
    except Exception as e:
        print(f"  Erreur détectée: {type(e).__name__}")
    
    print("\n❌ Examen d'imagerie invalide:")
    try:
        invalid_rec = ImagingRecommendation(
            imaging=["examen_qui_nexiste_pas"],
            urgency="urgent",
            comment="Test"
        )
    except Exception as e:
        print(f"  Erreur détectée: {type(e).__name__}")
    
    print("\n✅ La validation Pydantic protège contre les données incorrectes!")
    
    print("\n" + "=" * 60 + "\n")


def main():
    """Fonction principale - exécute tous les exemples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "MODÈLES PYDANTIC - CHATBOT CÉPHALÉES" + " " * 12 + "║")
    print("║" + " " * 18 + "Exemples d'utilisation" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    try:
        example_1_simple_headache_case()
        example_2_emergency_case()
        example_3_meningitis_case()
        example_4_chat_interaction()
        example_5_json_export()
        example_6_validation_errors()
        
        print("✅ Tous les exemples ont été exécutés avec succès!")
        print("\n💡 Les modèles Pydantic offrent:")
        print("  - Validation automatique des données")
        print("  - Sérialisation JSON native")
        print("  - Documentation intégrée (docstrings)")
        print("  - Type hints stricts")
        print("  - Méthodes de validation personnalisées")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
