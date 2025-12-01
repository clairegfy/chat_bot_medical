# Headache Assistant - Backend Python

Assistant médical spécialisé dans l'évaluation des céphalées et la prescription d'imagerie.

## 📋 Description

Ce projet est une bibliothèque Python (sans API web) pour analyser les symptômes de céphalées et recommander les examens d'imagerie appropriés basés sur des règles médicales validées.

## 🏗️ Structure du projet

```
arbre_ia/
├── headache_assistants/      # Package principal
│   ├── __init__.py           # Exports publics
│   ├── models.py             # Modèles de données (dataclasses)
│   ├── rules_engine.py       # Moteur de règles médicales
│   ├── nlu.py                # Compréhension du langage naturel
│   └── dialogue.py           # Gestionnaire de dialogue
├── rules/                    # Règles médicales
│   ├── headache_rules.txt    # Règles source (texte)
│   └── headache_rules.json   # Règles structurées (JSON)
├── tests/                    # Tests unitaires
│   ├── test_rules_engine.py
│   └── test_nlu.py
├── requirements.txt          # Dépendances
└── README.md                 # Ce fichier
```

## 🚀 Installation

### Prérequis

- Python 3.11+

### Installation des dépendances

```bash
pip install -r requirements.txt
```

## 💻 Utilisation

### Exemple 1 : Évaluation simple

```python
from headache_assistants import HeadacheCharacteristics, RulesEngine

# Créer le moteur de règles
engine = RulesEngine()

# Définir les caractéristiques de la céphalée
characteristics = HeadacheCharacteristics(
    onset_type="brutal",
    is_recent=True,
    has_fever=True,
    intensity=9
)

# Évaluer
result = engine.evaluate(characteristics)

# Afficher les résultats
print(f"Diagnostic : {result.primary_diagnosis.headache_type}")
print(f"Confiance : {result.primary_diagnosis.confidence:.0%}")
print(f"Signes d'alarme : {result.red_flags}")
print(f"Imagerie recommandée : {result.imaging_recommendation}")
```

### Exemple 2 : Utilisation du dialogue manager

```python
from headache_assistants import DialogueManager

# Créer le gestionnaire de dialogue
dialogue = DialogueManager()

# Démarrer une session
session = dialogue.start_session()
print(f"Session ID : {session.session_id}")

# Question initiale
print(dialogue.get_initial_question())

# Traiter la réponse du patient
response = dialogue.process_user_input(
    session.session_id,
    "J'ai une douleur brutale qui a commencé il y a 2 heures, très intense avec de la fièvre"
)

print(response["message"])
print(f"Type : {response['type']}")

# Obtenir le résumé de la session
summary = dialogue.get_session_summary(session.session_id)
print(summary)
```

### Exemple 3 : Extraction NLU

```python
from headache_assistants import NLUEngine

# Créer le moteur NLU
nlu = NLUEngine()

# Analyser une description textuelle
text = "J'ai une douleur pulsatile d'un côté, qui a commencé progressivement. L'intensité est à 8/10."

characteristics = nlu.extract_characteristics(text)

print(f"Type de douleur : {characteristics.pain_type}")
print(f"Latéralité : {characteristics.laterality}")
print(f"Intensité : {characteristics.intensity}")
```

### Exemple 4 : Script complet

```python
from headache_assistants import DialogueManager, HeadacheCharacteristics

def main():
    # Initialiser le dialogue
    dialogue = DialogueManager()
    session = dialogue.start_session()
    
    print("=== Assistant Céphalées ===")
    print(dialogue.get_initial_question())
    print()
    
    # Simulation d'un échange
    user_inputs = [
        "J'ai une douleur intense qui a commencé brutalement ce matin",
        "Oui, j'ai de la fièvre",
        "La douleur est à 9/10"
    ]
    
    for user_input in user_inputs:
        print(f"Patient : {user_input}")
        response = dialogue.process_user_input(session.session_id, user_input)
        print(f"Assistant : {response['message']}")
        print()
        
        if response['type'] == 'emergency':
            print("⚠️ URGENCE DÉTECTÉE")
            break
    
    # Résumé final
    summary = dialogue.get_session_summary(session.session_id)
    if summary and summary['diagnostic_result']:
        print(f"Diagnostic : {summary['diagnostic_result']}")

if __name__ == "__main__":
    main()
```

## 🧪 Tests

Exécuter tous les tests :

```bash
pytest tests/ -v
```

Exécuter un fichier de test spécifique :

```bash
pytest tests/test_rules_engine.py -v
pytest tests/test_nlu.py -v
```

Avec couverture de code :

```bash
pytest tests/ --cov=headache_assistants --cov-report=html
```

## 📚 Architecture

### Composants principaux

1. **models.py** : Définit les structures de données
   - `HeadacheCharacteristics` : Caractéristiques de la céphalée
   - `Diagnosis` : Résultat diagnostique
   - `ImagingRecommendation` : Recommandations d'imagerie
   - `DialogueState` : État du dialogue

2. **rules_engine.py** : Moteur de règles médicales
   - Charge les règles depuis `headache_rules.json`
   - Évalue les symptômes
   - Détecte les red flags (signes d'alarme)
   - Génère les recommandations d'imagerie

3. **nlu.py** : Compréhension du langage naturel
   - Extraction de caractéristiques depuis texte libre
   - Détection de patterns
   - Normalisation du texte

4. **dialogue.py** : Gestion du dialogue
   - Orchestration de la conversation
   - Génération de questions
   - Coordination NLU + Rules Engine

### Flux de données

```
Entrée utilisateur (texte)
    ↓
NLU Engine → HeadacheCharacteristics
    ↓
Rules Engine → DiagnosticResult
    ↓
Dialogue Manager → Réponse formatée
```

## 🔧 Configuration

Les règles médicales sont dans `rules/headache_rules.json`. Ce fichier contient :
- Définitions des types de céphalées
- Critères diagnostiques
- Red flags (signes d'alarme)
- Protocoles d'imagerie
- Arbre de décision

## 📝 TODO / Améliorations futures

- [ ] Implémenter la logique complète d'évaluation dans `rules_engine.py`
- [ ] Enrichir les patterns NLU
- [ ] Ajouter l'intégration avec des modèles de langage (GPT, etc.)
- [ ] Créer une interface CLI interactive
- [ ] Ajouter la sérialisation des sessions (JSON, DB)
- [ ] Internationalisation (i18n)
- [ ] Logging et monitoring

## ⚕️ Avertissement médical

**Ce logiciel est destiné à des fins éducatives et de recherche uniquement.**

Il ne remplace en aucun cas l'avis d'un professionnel de santé qualifié. En cas de symptômes graves ou d'urgence médicale, consultez immédiatement un médecin.

## 📄 Licence

À définir selon vos besoins.

## 👥 Auteur

AlexPeirano

## 🤝 Contribution

Pour contribuer :
1. Créer une branche feature
2. Ajouter des tests
3. Soumettre une pull request
