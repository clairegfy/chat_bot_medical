#!/usr/bin/env python3
"""
Assistant Médical Interactif pour l'évaluation des céphalées.

Lance un chatbot conversationnel qui pose des questions au patient
et recommande les examens d'imagerie appropriés.
"""

from headache_assistants.models import ChatMessage
from headache_assistants.dialogue import handle_user_message, _active_sessions
from headache_assistants.prescription import generate_prescription


def print_header():
    """Affiche l'en-tête du programme."""
    print("\n" + "="*70)
    print("ASSISTANT MÉDICAL - ÉVALUATION DES CÉPHALÉES")
    print("="*70)
    print("\nBonjour Docteur,")
    print("Décrivez le cas clinique de votre patient.")
    print("Je poserai des questions pour déterminer les examens nécessaires.")
    print("\nATTENTION : Outil d'aide à la décision uniquement.")
    print("="*70 + "\n")


def print_help():
    """Affiche l'aide."""
    print("\nCommandes disponibles:")
    print("  /aide        - Afficher cette aide")
    print("  /ordonnance  - Générer une ordonnance (après évaluation)")
    print("  /reset       - Commencer un nouveau cas")
    print("  /quit        - Quitter le programme")
    print()


def main():
    """Fonction principale - chatbot interactif."""
    print_header()
    print_help()
    
    # Initialisation
    history = []
    session_id = None
    conversation_active = True
    last_case = None
    last_recommendation = None
    
    print("Tapez /aide pour voir les commandes disponibles.\n")
    
    while conversation_active:
        try:
            # Lecture de l'entrée utilisateur
            user_input = input("Vous: ").strip()
            
            # Gestion des commandes
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print("\nAssistant: Au revoir Docteur.\n")
                break
            
            if user_input.lower() in ['/aide', '/help', '/h']:
                print_help()
                continue
            
            if user_input.lower() in ['/ordonnance', '/ord']:
                if last_case and last_recommendation:
                    try:
                        doctor_name = input("Nom du prescripteur (ou Entrée pour 'Dr. [NOM]'): ").strip()
                        if not doctor_name:
                            doctor_name = "Dr. [NOM]"
                        
                        filepath = generate_prescription(last_case, last_recommendation, doctor_name)
                        print(f"\nOrdonnance générée: {filepath}\n")
                    except Exception as e:
                        print(f"\nErreur lors de la génération: {e}\n")
                else:
                    print("\nAucune évaluation en cours. Veuillez d'abord évaluer un cas.\n")
                continue
            
            if user_input.lower() == '/reset':
                history = []
                session_id = None
                print("\nAssistant: Nouveau cas. Décrivez le cas clinique de votre patient.\n")
                continue
            
            # Ignorer les entrées vides
            if not user_input:
                continue
            
            # Créer le message utilisateur
            user_message = ChatMessage(
                role="user",
                content=user_input
            )
            
            # Traiter la requête
            response = handle_user_message(history, user_message, session_id=session_id)
            
            # Mettre à jour le session_id
            if response.session_id:
                session_id = response.session_id
            
            # Afficher la réponse
            if response.dialogue_complete:
                # Dialogue terminé - afficher la réponse complète
                print(f"\nAssistant: {response.message}\n")
            elif response.next_question:
                # Dialogue en cours - afficher seulement la prochaine question (pas le message)
                print(f"\nAssistant: {response.next_question}\n")
            else:
                # Fallback
                print(f"\nAssistant: {response.message}\n")
            
            # Si le dialogue est terminé, afficher un résumé
            if response.dialogue_complete:
                # Stocker pour génération d'ordonnance
                if session_id and session_id in _active_sessions:
                    last_case = _active_sessions[session_id].get('current_case')
                    last_recommendation = response.imaging_recommendation
                
                if response.imaging_recommendation:
                    rec = response.imaging_recommendation
                    print("\n" + "-"*70)
                    print("RÉSUMÉ")
                    print("-"*70)
                    
                    # Afficher l'urgence de manière lisible
                    urgency_display = {
                        "immediate": "URGENCE VITALE",
                        "urgent": "URGENTE",
                        "delayed": "PROGRAMMÉE",
                        "none": "NON URGENTE"
                    }
                    print(f"Urgence: {urgency_display.get(rec.urgency, rec.urgency.upper())}")
                    
                    if rec.imaging:
                        print(f"Examens recommandés:")
                        for exam in rec.imaging:
                            print(f"  - {exam}")
                    print("-"*70 + "\n")
                
                # Proposer ordonnance et nouveau cas
                print("Options: [O]rdonnance, [N]ouveau cas, [Q]uitter")
                choix = input("Vous: ").strip().lower()
                
                if choix in ['ordonnance', 'o', '/ordonnance']:
                    try:
                        doctor_name = input("Nom du prescripteur (ou Entrée pour 'Dr. [NOM]'): ").strip()
                        if not doctor_name:
                            doctor_name = "Dr. [NOM]"
                        
                        filepath = generate_prescription(last_case, last_recommendation, doctor_name)
                        print(f"\nOrdonnance générée: {filepath}\n")
                        
                        # Après ordonnance, demander nouveau cas
                        print("Nouveau cas ? (oui/non)")
                        nouveau = input("Vous: ").strip().lower()
                        if nouveau in ['oui', 'o', 'yes', 'y']:
                            history = []
                            session_id = None
                            print("\nAssistant: Nouveau cas. Décrivez le cas clinique de votre patient.\n")
                        else:
                            print("\nAssistant: Au revoir Docteur.\n")
                            break
                    except Exception as e:
                        print(f"\nErreur: {e}\n")
                
                elif choix in ['nouveau', 'n', 'new']:
                    history = []
                    session_id = None
                    print("\nAssistant: Nouveau cas. Décrivez le cas clinique de votre patient.\n")
                
                elif choix in ['quitter', 'q', 'quit', 'exit']:
                    print("\nAssistant: Au revoir Docteur.\n")
                    break
                
                else:
                    # Par défaut : quitter
                    print("\nAssistant: Au revoir Docteur.\n")
                    break
            else:
                # Mettre à jour l'historique
                history.append(user_message)
                history.append(ChatMessage(role="assistant", content=response.message))
        
        except KeyboardInterrupt:
            print("\n\nAssistant: Interruption détectée. Au revoir Docteur.\n")
            break
        
        except Exception as e:
            print(f"\nErreur: {e}")
            print("Tapez /reset pour recommencer ou /quit pour quitter.\n")


if __name__ == "__main__":
    main()
