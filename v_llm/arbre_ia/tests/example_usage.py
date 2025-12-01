#!/usr/bin/env python3
"""Script d'exemple d'utilisation du chatbot médical pour les céphalées.

Ce script montre comment utiliser la bibliothèque headache_assistants
dans un programme Python.
"""

from headache_assistants import (
    DialogueManager,
    HeadacheCharacteristics,
    RulesEngine,
    NLUEngine
)


def example_1_direct_evaluation():
    """Exemple 1 : Évaluation directe avec caractéristiques connues."""
    print("=" * 60)
    print("EXEMPLE 1 : Évaluation directe")
    print("=" * 60)
    
    # Créer le moteur de règles
    engine = RulesEngine()
    
    # Définir les caractéristiques de la céphalée
    characteristics = HeadacheCharacteristics(
        onset_type="brutal",
        is_recent=True,
        is_unusual=True,
        has_fever=True,
        intensity=9,
        laterality="unilateral",
        has_vomiting=True
    )
    
    # Évaluer
    result = engine.evaluate(characteristics)
    
    # Afficher les résultats
    print(f"\n📊 Résultats de l'évaluation :")
    if result.primary_diagnosis:
        print(f"  Diagnostic principal : {result.primary_diagnosis.headache_type}")
        print(f"  Confiance : {result.primary_diagnosis.confidence:.0%}")
    
    if result.red_flags:
        print(f"\n⚠️  Signes d'alarme détectés :")
        for flag in result.red_flags:
            print(f"  - {flag}")
    
    if result.imaging_recommendation:
        print(f"\n🏥 Recommandation d'imagerie :")
        print(f"  Urgence : {result.imaging_recommendation.urgency.value}")
        print(f"  Recommandée : {result.imaging_recommendation.recommended}")
    
    print("\n" + "=" * 60 + "\n")


def example_2_nlu_extraction():
    """Exemple 2 : Extraction NLU depuis texte libre."""
    print("=" * 60)
    print("EXEMPLE 2 : Extraction NLU")
    print("=" * 60)
    
    # Créer le moteur NLU
    nlu = NLUEngine()
    
    # Description textuelle du patient
    patient_text = (
        "J'ai une douleur pulsatile d'un seul côté de la tête, à gauche. "
        "Ça a commencé progressivement ce matin. L'intensité est à 8/10. "
        "J'ai aussi des nausées et je suis gêné par la lumière."
    )
    
    print(f"\n📝 Texte du patient :")
    print(f"  \"{patient_text}\"")
    
    # Extraire les caractéristiques
    characteristics = nlu.extract_characteristics(patient_text)
    
    print(f"\n🔍 Caractéristiques extraites :")
    print(f"  Type de douleur : {characteristics.pain_type}")
    print(f"  Latéralité : {characteristics.laterality}")
    print(f"  Début : {characteristics.onset_type}")
    print(f"  Intensité : {characteristics.intensity}/10")
    print(f"  Nausées : {characteristics.has_nausea}")
    print(f"  Photophobie : {characteristics.has_photophobia}")
    
    # Évaluer avec le moteur de règles
    engine = RulesEngine()
    result = engine.evaluate(characteristics)
    
    print(f"\n📊 Résultat de l'évaluation :")
    print(f"  {result.get_summary()}")
    
    print("\n" + "=" * 60 + "\n")


def example_3_dialogue_manager():
    """Exemple 3 : Utilisation du gestionnaire de dialogue."""
    print("=" * 60)
    print("EXEMPLE 3 : Gestionnaire de dialogue")
    print("=" * 60)
    
    # Initialiser le dialogue
    dialogue = DialogueManager()
    session = dialogue.start_session()
    
    print(f"\n🆔 Session ID : {session.session_id}")
    print(f"\n🤖 Assistant : {dialogue.get_initial_question()}")
    
    # Simulation d'échanges
    exchanges = [
        "J'ai une douleur intense qui a commencé brutalement ce matin, comme un coup de tonnerre",
        "Oui, j'ai de la fièvre à 38.5°C",
        "La douleur est à 9/10, c'est terrible"
    ]
    
    for i, user_input in enumerate(exchanges, 1):
        print(f"\n👤 Patient : {user_input}")
        
        response = dialogue.process_user_input(session.session_id, user_input)
        
        print(f"🤖 Assistant : {response['message'][:200]}...")
        print(f"   Type de réponse : {response['type']}")
        
        if response['type'] == 'emergency':
            print("\n⚠️  URGENCE VITALE DÉTECTÉE !")
            break
        
        if not response['should_continue']:
            break
    
    # Résumé final
    print(f"\n📋 Résumé de la session :")
    summary = dialogue.get_session_summary(session.session_id)
    if summary:
        print(f"  Symptômes collectés : {summary['collected_symptoms_count']}")
        if summary['diagnostic_result']:
            print(f"  Diagnostic : {summary['diagnostic_result']}")
    
    # Terminer la session
    dialogue.end_session(session.session_id)
    print(f"\n✅ Session terminée")
    
    print("\n" + "=" * 60 + "\n")


def example_4_interactive_demo():
    """Exemple 4 : Démonstration interactive simplifiée."""
    print("=" * 60)
    print("EXEMPLE 4 : Démonstration interactive")
    print("=" * 60)
    
    dialogue = DialogueManager()
    session = dialogue.start_session()
    
    print("\n🏥 Bienvenue dans l'assistant médical pour les céphalées")
    print("=" * 60)
    
    # Scénario pré-défini pour la démo
    scenario = {
        "description": "Migraine typique",
        "inputs": [
            "J'ai mal à la tête depuis ce matin",
            "Non, j'ai déjà eu ce type de mal de tête avant",
            "C'est une douleur qui bat, comme le pouls, d'un seul côté",
            "L'intensité est à 7/10",
            "Oui, j'ai des nausées et la lumière me gêne"
        ]
    }
    
    print(f"\n📖 Scénario : {scenario['description']}\n")
    
    for i, user_input in enumerate(scenario['inputs'], 1):
        print(f"[Étape {i}]")
        print(f"👤 Patient : {user_input}")
        
        response = dialogue.process_user_input(session.session_id, user_input)
        
        print(f"🤖 Assistant : {response['message']}\n")
        
        if response['diagnostic'] and i == len(scenario['inputs']):
            print(f"📊 Diagnostic final : {response['diagnostic']}")
            break
    
    dialogue.end_session(session.session_id)
    print("\n" + "=" * 60 + "\n")


def main():
    """Fonction principale - exécute tous les exemples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "CHATBOT MÉDICAL - CÉPHALÉES" + " " * 20 + "║")
    print("║" + " " * 15 + "Exemples d'utilisation" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    try:
        # Exécuter tous les exemples
        example_1_direct_evaluation()
        example_2_nlu_extraction()
        example_3_dialogue_manager()
        example_4_interactive_demo()
        
        print("✅ Tous les exemples ont été exécutés avec succès !")
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
