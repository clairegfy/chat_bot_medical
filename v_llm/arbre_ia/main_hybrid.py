"""Point d'entrée principal pour le système de dialogue médical interactif."""

from headache_assistants.nlu_hybrid import HybridNLU
from headache_assistants.models import HeadacheCase
from headache_assistants.rules_engine import load_rules
from typing import Optional, Dict, Any, List


# Stockage des logs de session pour affichage
_session_logs: List[Dict[str, Any]] = []


def print_separator(char="=", length=70):
    """Affiche une ligne de séparation."""
    print(char * length)


def add_session_log(log_type: str, data: Dict[str, Any]):
    """Ajoute une entrée au journal de session."""
    from datetime import datetime
    _session_logs.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "type": log_type,
        "data": data
    })
    # Garder seulement les 50 derniers logs
    if len(_session_logs) > 50:
        _session_logs.pop(0)


def display_logs_menu():
    """Affiche le menu des logs et guidelines."""
    print("\n" + "="*70)
    print("LOGS & GUIDELINES")
    print("="*70)
    print("\n[1] Voir les GUIDELINES (regles medicales)")
    print("[2] Voir les LOGS de session (decisions prises)")
    print("[3] Voir les CATEGORIES de regles")
    print("[4] Rechercher une regle par mot-cle")
    print("[R] Retour")
    print()

    choix = input("Choix: ").strip().lower()

    if choix == '1':
        display_guidelines()
    elif choix == '2':
        display_session_logs()
    elif choix == '3':
        display_rule_categories()
    elif choix == '4':
        search_rules()
    elif choix in ['r', 'retour', '']:
        return
    else:
        print("Choix invalide.")


def display_guidelines():
    """Affiche les guidelines medicales (regles disponibles)."""
    try:
        rules_data = load_rules()
        rules = rules_data.get("rules", [])
        metadata = rules_data.get("metadata", {})

        print("\n" + "="*70)
        print("GUIDELINES MEDICALES - REGLES D'EVALUATION DES CEPHALEES")
        print("="*70)
        print(f"Version: {metadata.get('version', 'N/A')}")
        print(f"Source: {metadata.get('source', 'N/A')}")
        print(f"Nombre de regles: {len(rules)}")
        print("-"*70)

        # Grouper par catégorie
        categories = {}
        for rule in rules:
            cat = rule.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(rule)

        # Afficher par catégorie
        category_names = {
            "acute_emergency": "URGENCES AIGUES",
            "pregnancy": "GROSSESSE / POST-PARTUM",
            "subacute": "CEPHALEES SUBAIGUES",
            "chronic": "CEPHALEES CHRONIQUES",
            "specific_context": "CONTEXTES SPECIFIQUES",
            "age_related": "LIES A L'AGE",
            "benign": "PRESENTATIONS BENIGNES",
            "other": "AUTRES"
        }

        for cat, cat_rules in categories.items():
            cat_display = category_names.get(cat, cat.upper())
            print(f"\n{cat_display} ({len(cat_rules)} regles)")
            print("-"*40)

            for rule in cat_rules[:5]:  # Limiter à 5 par catégorie pour lisibilité
                print(f"  [{rule.get('id')}] {rule.get('name')}")

            if len(cat_rules) > 5:
                print(f"  ... et {len(cat_rules) - 5} autres regles")

        print("\n" + "-"*70)
        print("Tapez /logs puis [4] pour rechercher une regle specifique")
        print("-"*70 + "\n")

    except Exception as e:
        print(f"\nErreur lors du chargement des regles: {e}\n")


def display_session_logs():
    """Affiche les logs de la session courante."""
    print("\n" + "="*70)
    print("LOGS DE SESSION")
    print("="*70)

    if not _session_logs:
        print("\nAucun log enregistre pour cette session.\n")
        return

    for log in _session_logs:
        timestamp = log["timestamp"]
        log_type = log["type"]
        data = log["data"]

        if log_type == "decision":
            print(f"\n[{timestamp}] DECISION MEDICALE")
            print(f"  Regle: {data.get('rule', 'N/A')}")
            print(f"  Examens: {', '.join(data.get('imaging', [])) or 'Aucun'}")
            print(f"  Urgence: {data.get('urgency', 'N/A')}")
            if data.get('comment'):
                # Tronquer le commentaire pour lisibilité
                comment = data['comment'][:150] + "..." if len(data.get('comment', '')) > 150 else data.get('comment', '')
                print(f"  Guideline: {comment}")

        elif log_type == "nlu":
            print(f"\n[{timestamp}] ANALYSE NLU")
            print(f"  Champs detectes: {', '.join(data.get('fields', [])) or 'Aucun'}")
            print(f"  Confiance: {data.get('confidence', 0):.0%}")
            print(f"  Methode: {data.get('method', 'rules')}")

        elif log_type == "prescription":
            print(f"\n[{timestamp}] ORDONNANCE GENEREE")
            print(f"  Fichier: {data.get('filepath', 'N/A')}")

    print("\n" + "-"*70 + "\n")


def display_rule_categories():
    """Affiche les categories de regles avec description."""
    print("\n" + "="*70)
    print("CATEGORIES DE REGLES MEDICALES")
    print("="*70)

    categories_info = {
        "acute_emergency": {
            "name": "Urgences Aigues",
            "description": "HSA, meningite, HTIC, dissection - Imagerie immediate",
            "urgency": "IMMEDIATE"
        },
        "pregnancy": {
            "name": "Grossesse / Post-partum",
            "description": "TVC, eclampsie, PRES - IRM preferee au scanner",
            "urgency": "URGENT"
        },
        "subacute": {
            "name": "Cephalees Subaigues",
            "description": "Evolution sur jours/semaines - IRM sous 7 jours",
            "urgency": "PROGRAMME"
        },
        "chronic": {
            "name": "Cephalees Chroniques",
            "description": "Migraine, tension, CCQ - Imagerie si changement",
            "urgency": "NON URGENT"
        },
        "specific_context": {
            "name": "Contextes Specifiques",
            "description": "Immunodepression, cancer, post-PL",
            "urgency": "VARIABLE"
        }
    }

    for cat_id, info in categories_info.items():
        print(f"\n{info['name'].upper()}")
        print(f"  {info['description']}")
        print(f"  Urgence typique: {info['urgency']}")

    print("\n" + "-"*70 + "\n")


def search_rules():
    """Recherche une regle par mot-cle."""
    keyword = input("\nMot-cle a rechercher: ").strip().lower()

    if not keyword:
        print("Aucun mot-cle fourni.")
        return

    try:
        rules_data = load_rules()
        rules = rules_data.get("rules", [])

        matches = []
        for rule in rules:
            # Chercher dans id, name, description, comment
            searchable = " ".join([
                rule.get("id", ""),
                rule.get("name", ""),
                rule.get("description", ""),
                rule.get("recommendation", {}).get("comment", "")
            ]).lower()

            if keyword in searchable:
                matches.append(rule)

        print(f"\n{len(matches)} regle(s) trouvee(s) pour '{keyword}':")
        print("-"*70)

        for rule in matches[:10]:  # Limiter à 10 résultats
            print(f"\n[{rule.get('id')}] {rule.get('name')}")
            print(f"  Categorie: {rule.get('category', 'N/A')}")
            print(f"  {rule.get('description', '')[:100]}...")

            rec = rule.get("recommendation", {})
            print(f"  Examens: {', '.join(rec.get('imaging', []))}")
            print(f"  Urgence: {rec.get('urgency', 'N/A')}")

        if len(matches) > 10:
            print(f"\n... et {len(matches) - 10} autres resultats")

        print("\n" + "-"*70 + "\n")

    except Exception as e:
        print(f"\nErreur lors de la recherche: {e}\n")


def interactive_mode(nlu: HybridNLU):
    """Mode interactif avec dialogue (pose des questions si infos manquantes)."""
    from headache_assistants.dialogue import handle_user_message
    from headache_assistants.models import ChatMessage
    from headache_assistants.prescription import generate_prescription

    print("\n" + "="*70)
    print("ASSISTANT MEDICAL - EVALUATION DES CEPHALEES (NLU HYBRIDE)")
    print("="*70)
    print("\nBonjour Docteur,")
    print("Decrivez le cas clinique de votre patient.")
    print("Le systeme pose des questions pour determiner les examens necessaires.")
    print("\nATTENTION : Outil d'aide a la decision uniquement.")
    print("="*70)
    print("\nCommandes disponibles:")
    print("  /aide        - Afficher cette aide")
    print("  /ordonnance  - Generer une ordonnance (apres evaluation)")
    print("  /logs        - Voir guidelines et logs de session")
    print("  /reset       - Commencer un nouveau cas")
    print("  /quit        - Quitter le programme")
    print("="*70 + "\n")

    history = []
    session_id = None
    last_case = None
    last_recommendation = None

    while True:
        user_input = input("Vous: ").strip()

        if not user_input:
            continue

        # Gestion des commandes
        if user_input.lower() in ['/quit', '/exit', '/q']:
            print("\nAssistant: Au revoir Docteur.\n")
            break

        if user_input.lower() in ['/aide', '/help', '/h']:
            print("\nCommandes disponibles:")
            print("  /aide        - Afficher cette aide")
            print("  /ordonnance  - Generer une ordonnance (apres evaluation)")
            print("  /logs        - Voir guidelines et logs de session")
            print("  /reset       - Commencer un nouveau cas")
            print("  /quit        - Quitter le programme\n")
            continue

        if user_input.lower() in ['/logs', '/log', '/l', '/guidelines']:
            display_logs_menu()
            continue

        if user_input.lower() in ['/ordonnance', '/ord']:
            if last_case and last_recommendation:
                try:
                    doctor_name = input("Nom du prescripteur (ou Entree pour 'Dr. [NOM]'): ").strip()
                    if not doctor_name:
                        doctor_name = "Dr. [NOM]"

                    filepath = generate_prescription(last_case, last_recommendation, doctor_name)
                    print(f"\nOrdonnance generee: {filepath}\n")
                except Exception as e:
                    print(f"\nErreur lors de la generation: {e}\n")
            else:
                print("\nAucune evaluation en cours. Veuillez d'abord evaluer un cas.\n")
            continue

        if user_input.lower() == '/reset':
            print("\nAssistant: Nouveau cas. Decrivez le cas clinique de votre patient.\n")
            history = []
            session_id = None
            last_case = None
            last_recommendation = None
            continue

        # Créer message utilisateur
        user_message = ChatMessage(role="user", content=user_input)
        history.append(user_message)

        # Traiter avec le système de dialogue
        response = handle_user_message(history, user_message, session_id)

        # Sauvegarder session_id
        if not session_id:
            session_id = response.session_id

        # Ajouter réponse à l'historique
        assistant_message = ChatMessage(role="assistant", content=response.message)
        history.append(assistant_message)

        # Afficher réponse
        if response.dialogue_complete:
            print(f"\nAssistant: {response.message}\n")
        elif response.next_question:
            print(f"\nAssistant: {response.next_question}\n")
        else:
            print(f"\nAssistant: {response.message}\n")

        # Sauvegarder résultats pour ordonnance
        if response.imaging_recommendation:
            last_recommendation = response.imaging_recommendation
            # Logger la décision médicale
            add_session_log("decision", {
                "rule": last_recommendation.applied_rule_id,
                "imaging": list(last_recommendation.imaging) if last_recommendation.imaging else [],
                "urgency": last_recommendation.urgency,
                "comment": last_recommendation.comment
            })
        if response.headache_case:
            last_case = response.headache_case

        # Afficher résumé final si dialogue terminé
        if response.dialogue_complete and last_recommendation and last_case:
            print_case_summary(last_case)

            urgency_display = {
                "immediate": "IMMEDIATE",
                "urgent": "URGENTE",
                "delayed": "PROGRAMMEE",
                "none": "AUCUNE"
            }

            print("\n" + "-"*70)
            print("RESUME")
            print("-"*70)
            print(f"Urgence: {urgency_display.get(last_recommendation.urgency, 'INCONNUE')}")
            if last_recommendation.imaging:
                print("Examens recommandes:")
                for exam in last_recommendation.imaging:
                    print(f"  - {exam}")
            print("-"*70)
            print("\n")

            # Afficher les options après le résumé
            print("Options: [O]rdonnance, [L]ogs/Guidelines, [N]ouveau cas, [Q]uitter")
            choix = input("Vous: ").strip().lower()

            if choix in ['o', 'ordonnance']:
                doctor_name = input("Nom du prescripteur (ou Entree pour 'Dr. [NOM]'): ").strip()
                if not doctor_name:
                    doctor_name = "Dr. [NOM]"
                try:
                    filepath = generate_prescription(last_case, last_recommendation, doctor_name)
                    print(f"\nOrdonnance generee: {filepath}\n")
                    # Logger la génération
                    add_session_log("prescription", {"filepath": str(filepath)})
                except Exception as e:
                    print(f"\nErreur lors de la generation: {e}\n")

            if choix in ['l', 'logs', 'log', 'guidelines']:
                display_logs_menu()

            if choix in ['n', 'nouveau', 'nouveau cas']:
                print("\nAssistant: Nouveau cas. Decrivez le cas clinique de votre patient.\n")
                history = []
                session_id = None
                last_case = None
                last_recommendation = None

            if choix in ['quitter', 'q', '/quit']:
                print("\nAssistant: Au revoir Docteur.\n")
                break

        # Note: Progression du cas supprimée pour simplifier l'output


def print_case_summary(case: HeadacheCase):
    """Affiche un résumé du cas sans émojis."""
    print("\nCAS CLINIQUE:")
    print("-"*70)

    # Informations temporelles
    if case.onset and case.onset != "unknown":
        print(f"Debut (Onset): {case.onset}")
    if case.profile and case.profile != "unknown":
        print(f"Profil temporel: {case.profile}")

    # Red Flags détectés
    print(f"\nRED FLAGS DETECTES:")
    red_flags = []

    if case.onset == "thunderclap":
        red_flags.append("Debut brutal (thunderclap)")
    if case.fever is True:
        red_flags.append("Fievre")
    if case.meningeal_signs is True:
        red_flags.append("Syndrome meninge")
    if case.htic_pattern is True:
        red_flags.append("Signes HTIC")
    if case.neuro_deficit is True:
        red_flags.append("Deficit neurologique")
    if case.trauma is True:
        red_flags.append("Traumatisme cranien")
    if case.seizure is True:
        red_flags.append("Crises/Convulsions")
    if case.pregnancy_postpartum is True:
        red_flags.append("Grossesse/Post-partum")
    if case.immunosuppression is True:
        red_flags.append("Immunodepression")
    if case.cancer_history is True:
        red_flags.append("Antecedent oncologique")

    if red_flags:
        for flag in red_flags:
            print(f"  - {flag}")
    else:
        print("  Aucun red flag detecte")

    print("-"*70)


def main():
    """Point d'entrée principal."""
    # Initialisation silencieuse
    nlu = HybridNLU(confidence_threshold=0.7, verbose=False)

    # Lancer le mode interactif
    interactive_mode(nlu)


if __name__ == "__main__":
    main()
