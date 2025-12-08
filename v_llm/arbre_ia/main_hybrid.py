"""Point d'entrée principal pour le NLU Hybride.

Lancement interactif du système de détection NLU hybride
pour l'analyse de céphalées médicales.
"""

import sys
import time
from typing import Dict, Any
from headache_assistants.nlu_hybrid import HybridNLU
from headache_assistants.models import HeadacheCase


def print_separator(char="=", length=70):
    """Affiche une ligne de séparation."""
    print(char * length)


def print_case_details(case: HeadacheCase, metadata: Dict[str, Any]):
    """Affiche les détails du cas analysé de manière lisible."""
    print_separator()
    print("CAS DETECTE")
    print_separator()

    # Informations temporelles
    if case.onset and case.onset != "unknown":
        print(f"Debut (Onset):           {case.onset}")
    if case.profile and case.profile != "unknown":
        print(f"Profil temporel:         {case.profile}")
    if case.duration_current_episode_hours:
        hours = case.duration_current_episode_hours
        if hours < 24:
            print(f"Duree:                  {hours:.1f}h")
        elif hours < 168:  # < 1 semaine
            print(f"Duree:                  {hours/24:.1f} jours")
        else:
            print(f"Duree:                  {hours/24/7:.1f} semaines")

    # Red Flags
    print(f"\nRED FLAGS:")
    red_flags = []

    if case.fever is True:
        red_flags.append("Fièvre")
    elif case.fever is False:
        print(f"   • Fièvre:                Non")

    if case.meningeal_signs is True:
        red_flags.append("Syndrome méningé")
    elif case.meningeal_signs is False:
        print(f"   • Syndrome méningé:      Non")

    if case.htic_pattern is True:
        red_flags.append("Signes HTIC")
    elif case.htic_pattern is False:
        print(f"   • HTIC:                  Non")

    if case.neuro_deficit is True:
        red_flags.append("Déficit neurologique")
    elif case.neuro_deficit is False:
        print(f"   • Déficit neuro:         Non")

    if case.trauma is True:
        red_flags.append("Traumatisme crânien")
    elif case.trauma is False:
        print(f"   • Traumatisme:           Non")

    if case.seizure is True:
        red_flags.append("Crises/Convulsions")
    elif case.seizure is False:
        print(f"   • Crises:                Non")

    if case.pregnancy_postpartum is True:
        red_flags.append("Grossesse/Post-partum")
    elif case.pregnancy_postpartum is False:
        print(f"   • Grossesse/PP:          Non")

    if case.immunosuppression is True:
        red_flags.append("Immunodépression")
    elif case.immunosuppression is False:
        print(f"   • Immunodépression:      Non")

    if red_flags:
        print(f"\n   RED FLAGS DETECTES:")
        for flag in red_flags:
            print(f"      • {flag}")

    # Profil clinique
    if case.headache_profile and case.headache_profile != "unknown":
        profile_names = {
            "migraine_like": "Migraine",
            "tension_like": "Céphalée de tension",
            "cluster_like": "Algie vasculaire (Cluster)"
        }
        print(f"\nProfil clinique:        {profile_names.get(case.headache_profile, case.headache_profile)}")

    # Intensité
    if case.intensity:
        print(f"\nIntensite (EVA):        {case.intensity}/10")

    # Métadonnées NLU
    print(f"\nMETADONNEES NLU:")
    print(f"   • Mode:                  {metadata.get('hybrid_mode', 'N/A')}")
    print(f"   • Embedding utilise:     {metadata.get('embedding_used', False)}")
    print(f"   • Confiance globale:     {metadata.get('overall_confidence', 0):.2f}")
    print(f"   • Champs detectes:       {len(metadata.get('detected_fields', []))}")

    # Enrichissement par embedding
    if metadata.get('embedding_used'):
        enriched = metadata.get('enhancement_details', {}).get('enriched_fields', [])
        if enriched:
            print(f"\n   Champs enrichis par embedding:")
            for field in enriched:
                print(f"      • {field['field']}: {field['value']} "
                      f"(confiance {field['confidence']:.2f})")

        # Top matches
        top_matches = metadata.get('enhancement_details', {}).get('top_matches', [])
        if top_matches:
            print(f"\n   🔍 Exemples similaires utilisés:")
            for match in top_matches[:3]:
                print(f"      • [{match['similarity']:.2f}] {match['text'][:60]}...")

    print_separator()


def interactive_mode(nlu: HybridNLU):
    """Mode interactif avec dialogue (pose des questions si infos manquantes)."""
    from headache_assistants.dialogue import handle_user_message, _active_sessions
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
            print("  /reset       - Commencer un nouveau cas")
            print("  /quit        - Quitter le programme\n")
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
        start = time.time()
        response = handle_user_message(history, user_message, session_id)
        elapsed = (time.time() - start) * 1000

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

        # Si recommandation disponible, l'afficher
        if response.imaging_recommendation:
            # Stocker pour génération d'ordonnance
            if session_id and session_id in _active_sessions:
                last_case = _active_sessions[session_id].get('current_case')
                last_recommendation = response.imaging_recommendation

            print("\n" + "-"*70)
            print("RESUME")
            print("-"*70)
            rec = response.imaging_recommendation

            # Afficher l'urgence de manière lisible
            urgency_display = {
                "immediate": "URGENCE VITALE",
                "urgent": "URGENTE",
                "delayed": "PROGRAMMEE",
                "none": "NON URGENTE"
            }
            print(f"Urgence: {urgency_display.get(rec.urgency, rec.urgency.upper())}")

            if rec.imaging:
                print(f"Examens recommandes:")
                for exam in rec.imaging:
                    print(f"  - {exam}")
            print("-"*70 + "\n")

            # Afficher le cas complet
            if response.headache_case:
                print_case_summary(response.headache_case)

            # Proposer ordonnance et nouveau cas
            print("Options: [O]rdonnance, [N]ouveau cas, [Q]uitter")
            choix = input("Vous: ").strip().lower()

            if choix in ['ordonnance', 'o', '/ordonnance']:
                try:
                    doctor_name = input("Nom du prescripteur (ou Entree pour 'Dr. [NOM]'): ").strip()
                    if not doctor_name:
                        doctor_name = "Dr. [NOM]"

                    filepath = generate_prescription(last_case, last_recommendation, doctor_name)
                    print(f"\nOrdonnance generee: {filepath}\n")
                except Exception as e:
                    print(f"\nErreur lors de la generation: {e}\n")

            if choix in ['nouveau', 'n', '/reset']:
                print("\nAssistant: Nouveau cas. Decrivez le cas clinique de votre patient.\n")
                history = []
                session_id = None
                last_case = None
                last_recommendation = None

            if choix in ['quitter', 'q', '/quit']:
                print("\nAssistant: Au revoir Docteur.\n")
                break

        elif response.headache_case:
            # Afficher progression du cas en cours
            case = response.headache_case
            detected_count = sum([
                case.onset != "unknown" and case.onset is not None,
                case.profile != "unknown" and case.profile is not None,
                case.fever is not None,
                case.meningeal_signs is not None,
                case.htic_pattern is not None,
                case.neuro_deficit is not None,
                case.trauma is not None,
                case.seizure is not None,
            ])
            total_fields = 8
            print(f"Progression: {detected_count}/{total_fields} champs detectes ({detected_count/total_fields*100:.0f}%)\n")


def print_case_summary(case: HeadacheCase):
    """Affiche un résumé du cas sans émojis."""
    print("\nCAS CLINIQUE:")
    print("-"*70)

    # Informations temporelles
    if case.onset and case.onset != "unknown":
        print(f"Debut (Onset): {case.onset}")
    if case.profile and case.profile != "unknown":
        print(f"Profil temporel: {case.profile}")

    # Red Flags
    red_flags = []
    if case.fever is True:
        red_flags.append("Fievre")
    if case.meningeal_signs is True:
        red_flags.append("Syndrome meningé")
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

    if red_flags:
        print(f"\nRED FLAGS DETECTES:")
        for flag in red_flags:
            print(f"  - {flag}")

    # Profil clinique
    if case.headache_profile and case.headache_profile != "unknown":
        profile_names = {
            "migraine_like": "Migraine",
            "tension_like": "Cephalée de tension",
            "cluster_like": "Algie vasculaire (Cluster)"
        }
        print(f"\nProfil clinique: {profile_names.get(case.headache_profile, case.headache_profile)}")

    print("-"*70 + "\n")


def show_examples():
    """Affiche des exemples de cas à tester."""
    print("\n" + "="*70)
    print("EXEMPLES DE CAS À TESTER".center(70))
    print("="*70)

    examples = [
        ("HSA classique", "Céphalée brutale pire douleur de ma vie avec vomissements"),
        ("Méningite", "Mal de tête avec fièvre 39°C et raideur de nuque importante"),
        ("Migraine", "Céphalée unilatérale pulsatile avec photophobie et nausées"),
        ("HTIC", "Céphalée matutinale aggravée par la toux avec vomissements en jet"),
        ("Traumatisme", "Mal de tête depuis chute hier avec choc au crâne"),
        ("AVC suspicion", "Céphalée brutale avec faiblesse du bras droit et confusion"),
        ("Cluster", "Douleur atroce derrière l'œil gauche avec larmoiement"),
        ("Formulation patient", "J'ai une sensation d'explosion dans la tête quand je tousse"),
    ]

    for i, (category, text) in enumerate(examples, 1):
        print(f"\n{i}. {category}:")
        print(f"   {text}")

    print("\n" + "="*70)


def batch_test_mode(nlu: HybridNLU, test_cases: list):
    """Mode test batch avec plusieurs cas."""
    print("\n" + "="*70)
    print("MODE TEST BATCH".center(70))
    print("="*70)
    print(f"\n📊 Analyse de {len(test_cases)} cas cliniques...\n")

    results = []

    for i, text in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"CAS #{i}/{len(test_cases)}")
        print(f"{'='*70}")
        print(f"📝 Texte: {text}")

        start = time.time()
        result = nlu.parse_hybrid(text)
        elapsed = (time.time() - start) * 1000

        print(f"\n⚡ Analysé en {elapsed:.1f}ms")
        print_case_details(result.case, result.metadata)

        results.append({
            "text": text,
            "case": result.case,
            "metadata": result.metadata,
            "latency_ms": elapsed
        })

    # Statistiques globales
    print("\n" + "="*70)
    print("STATISTIQUES GLOBALES".center(70))
    print("="*70)

    total_latency = sum(r["latency_ms"] for r in results)
    avg_latency = total_latency / len(results)
    embedding_used = sum(1 for r in results if r["metadata"].get("embedding_used"))

    print(f"\n📊 Performance:")
    print(f"   • Latence moyenne:       {avg_latency:.1f}ms")
    print(f"   • Latence totale:        {total_latency:.1f}ms")
    print(f"   • Embedding utilisé:     {embedding_used}/{len(results)} cas ({embedding_used/len(results)*100:.0f}%)")

    avg_confidence = sum(r["metadata"].get("overall_confidence", 0) for r in results) / len(results)
    print(f"   • Confiance moyenne:     {avg_confidence:.2f}")

    print("\n" + "="*70)


def main():
    """Point d'entrée principal."""
    print("\n╔" + "="*68 + "╗")
    print("║" + " NLU HYBRIDE - Système d'analyse de céphalées ".center(68) + "║")
    print("║" + " (Règles + Embedding) ".center(68) + "║")
    print("╚" + "="*68 + "╝")

    # Initialisation
    print("\n[INIT] Initialisation du système NLU Hybride...")
    print("       (Chargement du modèle embedding, cela peut prendre 2-3 secondes...)")

    start = time.time()
    nlu = HybridNLU(confidence_threshold=0.7)
    init_time = time.time() - start

    print(f"[OK] Système initialise en {init_time:.1f}s")
    print(f"     • Corpus: {len(nlu.examples)} exemples medicaux")
    print(f"     • Modele: {nlu.embedder.get_sentence_embedding_dimension() if nlu.embedder else 'N/A'} dimensions")

    # Mode de lancement
    if len(sys.argv) > 1:
        # Mode batch avec arguments
        mode = sys.argv[1]

        if mode == "--test":
            # Cas de test prédéfinis
            test_cases = [
                "Céphalée brutale pire douleur de ma vie",
                "Mal de tête avec fièvre 39 et raideur nuque",
                "Céphalée progressive depuis 3 semaines avec vomissements matinaux",
                "Douleur d'un côté qui bat avec gêne à la lumière",
                "Sensation d'explosion dans la tête pendant que je courais",
                "Patient confus avec faiblesse bras droit depuis ce matin",
                "Mal de tête atroce derrière l'œil avec larmoiement",
                "Céphalée après chute hier avec choc au crâne",
            ]
            batch_test_mode(nlu, test_cases)

        elif mode == "--interactive" or mode == "-i":
            interactive_mode(nlu)

        else:
            # Analyser le texte fourni
            text = " ".join(sys.argv[1:])
            print(f"\n📝 Analyse de: {text}\n")

            start = time.time()
            result = nlu.parse_hybrid(text)
            elapsed = (time.time() - start) * 1000

            print(f"⚡ Analysé en {elapsed:.1f}ms")
            print_case_details(result.case, result.metadata)

    else:
        # Mode interactif par défaut
        interactive_mode(nlu)


if __name__ == "__main__":
    main()
