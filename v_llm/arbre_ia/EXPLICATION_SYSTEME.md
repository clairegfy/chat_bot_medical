# Explication du Système d'Évaluation des Céphalées

## Vue d'ensemble

Ce système est un **assistant médical intelligent** qui aide les médecins à évaluer les cas de céphalées (maux de tête) et à déterminer quels examens d'imagerie prescrire. Il fonctionne comme un chatbot conversationnel qui pose des questions au médecin sur son patient.

---

## Architecture du Système

```
┌─────────────────────────────────────────────────────────────┐
│                        UTILISATEUR                          │
│                    (Médecin via Terminal)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                       main.py                               │
│              (Interface Conversationnelle)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    dialogue.py                              │
│              (Gestion de la Conversation)                   │
│  • Pose des questions au médecin                            │
│  • Mémorise les réponses dans une session                   │
│  • Interprète les réponses contextuelles (oui/non)          │
└────────┬──────────────────────────────┬─────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐        ┌──────────────────────────┐
│      nlu.py         │        │    rules_engine.py       │
│ (Compréhension du   │        │  (Moteur de Décision)    │
│  Langage Naturel)   │        │  • Charge les règles     │
│  • Extrait les      │        │  • Applique la logique   │
│    informations du  │        │  • Adapte selon le       │
│    texte libre      │        │    contexte (grossesse,  │
│  • Détecte les      │        │    âge, etc.)            │
│    symptômes        │        │  • Recommande les        │
└─────────────────────┘        │    examens               │
                               └────────┬─────────────────┘
                                        │
                                        ▼
                               ┌────────────────────────┐
                               │  headache_rules.json   │
                               │   (Base de Règles      │
                               │    Médicales)          │
                               │  • 17 règles           │
                               │  • Conditions          │
                               │  • Examens à prescrire │
                               └────────────────────────┘
```

---

## Description Détaillée des Fichiers

### 📁 **main.py** - Point d'Entrée du Programme
**Technologie**: Python 3.11+, Programmation Procédurale

**Rôle**: C'est le fichier que vous exécutez pour lancer le chatbot. Il crée l'interface en ligne de commande.

**Ce qu'il fait**:
- Affiche un message de bienvenue au médecin
- Lit les messages du médecin depuis le terminal (fonction `input()`)
- Envoie chaque message au gestionnaire de dialogue
- Affiche les réponses de l'assistant
- Gère les commandes spéciales:
  - `/aide` - Afficher l'aide
  - `/ordonnance` - Générer une ordonnance
  - `/reset` - Recommencer un nouveau cas
  - `/quit` - Quitter le programme

**Concepts utilisés**:
- **Boucle while**: Permet de maintenir la conversation active
- **Session ID**: Un identifiant unique pour chaque conversation (comme un numéro de dossier temporaire)
- **Historique**: Mémorise tous les messages échangés

---

### 📁 **headache_assistants/models.py** - Structures de Données
**Technologie**: Pydantic (Bibliothèque de Validation de Données)

**Rôle**: Définit les "moules" (modèles) qui structurent les informations médicales.

**Analogie**: Imaginez un formulaire médical papier avec des cases à cocher et des champs à remplir. Les modèles Pydantic sont l'équivalent numérique.

**Principaux Modèles**:

1. **HeadacheCase** (Cas de Céphalée)
   ```python
   {
     "age": 45,
     "sex": "F",
     "onset": "progressive",          # Comment la douleur a commencé
     "profile": "subacute",            # Aigu, subaigu, ou chronique
     "fever": true,                    # Fièvre présente
     "meningeal_signs": true,          # Raideur de la nuque
     "intensity": 8,                   # Échelle de 0 à 10
     "pregnancy_postpartum": false,    # Grossesse ou post-partum
     ...
   }
   ```

2. **ImagingRecommendation** (Recommandation d'Imagerie)
   ```python
   {
     "imaging": ["ponction_lombaire"],
     "urgency": "immediate",           # immediate/urgent/delayed/none
     "comment": "Méningite suspectée..."
   }
   ```

**Ce que fait Pydantic**:
- **Validation automatique**: Vérifie que l'âge est entre 0 et 120, que l'intensité est entre 0 et 10, etc.
- **Conversion de types**: Transforme "45" (texte) en 45 (nombre)
- **Documentation**: Chaque champ a une description claire

---

### 📁 **headache_assistants/nlu.py** - Compréhension du Langage Naturel
**Technologie**: NLU (Natural Language Understanding), Expressions Régulières (Regex)

**Rôle**: Transforme du texte libre en données structurées.

**NLU - Qu'est-ce que c'est?**

NLU = **Natural Language Understanding** (Compréhension du Langage Naturel)

C'est la capacité d'un ordinateur à comprendre ce que dit un humain dans son langage quotidien, sans avoir à utiliser des commandes strictes.

**Exemple concret**:
```
Texte du médecin: "Patiente de 45 ans avec céphalées depuis 3 jours, fièvre à 39°C"

Ce que le NLU extrait:
├─ Age: 45
├─ Sexe: F (détecté par "Patiente")
├─ Profil: subacute (3 jours = subaigu)
├─ Fièvre: true (détecté par "fièvre" et "39°C")
└─ Intensité: non mentionnée → reste None
```

**Comment ça marche?**

Le module utilise des **expressions régulières** (regex) - des motifs de recherche de texte:

```python
FEVER_PATTERNS = [
    r"fièvre",           # Recherche le mot "fièvre"
    r"fébrile",          # Recherche le mot "fébrile"
    r"température",      # Recherche le mot "température"
    r"\d+°C",           # Recherche un nombre suivi de "°C" (ex: 39°C)
    r"\d+\s*degrés"     # Recherche un nombre suivi de "degrés"
]
```

**Dictionnaires de Patterns**:
- `ONSET_PATTERNS`: Détecte si la douleur a commencé brutalement, progressivement, ou chroniquement
- `PROFILE_PATTERNS`: Identifie si c'est aigu (heures/jours), subaigu (semaines), ou chronique (mois/années)
- `FEVER_PATTERNS`: Repère les mentions de fièvre
- `MENINGEAL_SIGNS_PATTERNS`: Détecte "raideur de la nuque", "signe de Kernig", etc.
- `PREGNANCY_PATTERNS`: Identifie grossesse ou post-partum
- etc.

**Pourquoi c'est utile?**

Sans NLU, le médecin devrait remplir un formulaire avec des menus déroulants et cases à cocher. Avec NLU, il peut simplement décrire le cas naturellement : "Homme 55 ans, céphalée brutale en coup de tonnerre, intensité 10/10".

---

### 📁 **headache_assistants/dialogue.py** - Gestionnaire de Conversation
**Technologie**: Machine à États (State Machine), Gestion de Session

**Rôle**: Orchestre la conversation entre le médecin et le système.

**Concept de Session**:
Une **session** est comme un dossier médical temporaire en mémoire:
```python
session = {
    "id": "abc123-def456-...",           # Identifiant unique
    "current_case": HeadacheCase(...),   # Cas en cours de construction
    "asked_fields": ["fever", "onset"],  # Champs déjà questionnés
    "last_asked_field": "meningeal_signs", # Dernier champ questionné
    "history": [message1, message2, ...]   # Historique des messages
}
```

**Stratégie de Conversation**:

1. **Analyse du Message**:
   - Le médecin envoie un message
   - Le système vérifie s'il répond à une question précédente (contexte)
   - Si oui: interprète "oui"/"non" → `meningeal_signs = true/false`
   - Si non: utilise le NLU pour extraire les informations

2. **Identification des Champs Manquants**:
   ```python
   # Champs critiques par priorité:
   1. Urgence vitale: onset, fever, meningeal_signs, intensity
   2. Signes HTIC: htic_pattern, neuro_deficit, seizure
   3. Profil temporel: profile
   4. Contextes à risque: pregnancy_postpartum, trauma
   5. Classification: headache_profile
   ```

3. **Questions Ciblées**:
   - Le système pose UNE question à la fois
   - Évite de demander deux fois la même chose (grâce à `asked_fields`)
   - Adapte les questions selon le contexte:
     - Si femme en âge de procréer → "La patiente est-elle enceinte?"
     - Si homme âgé → "Le patient a-t-il eu un traumatisme?"

4. **Interprétation Contextuelle**:
   ```python
   # Exemple:
   Assistant: "Le patient a-t-il de la fièvre?"
   Médecin: "oui"
   
   # Le système sait que "oui" répond à la question sur la fièvre
   # et met automatiquement fever = True
   ```

**Fonctions Principales**:
- `handle_user_message()`: Fonction centrale qui traite chaque message
- `_interpret_yes_no_response()`: Interprète "oui"/"non" selon le contexte
- `prioritize_missing_fields()`: Classe les champs manquants par importance
- `generate_question_for_field()`: Génère des questions adaptées

---

### 📁 **headache_assistants/rules_engine.py** - Moteur de Décision Médicale
**Technologie**: Moteur de Règles (Rule Engine), Logique Conditionnelle

**Rôle**: Applique les règles médicales pour décider quels examens prescrire.

**Qu'est-ce qu'un Moteur de Règles?**

C'est un système qui applique automatiquement des règles "SI... ALORS...":

```
SI (onset = "thunderclap" ET intensity >= 7 ET profile = "acute")
ALORS recommander:
  - Scanner cérébral sans injection
  - Ponction lombaire
  - Urgence: IMMÉDIATE
  - Commentaire: "HSA suspectée..."
```

**Comment ça marche?**

1. **Chargement des Règles**:
   ```python
   rules = load_rules()  # Lit headache_rules.json
   # Contient 17 règles médicales
   ```

2. **Évaluation du Cas**:
   ```python
   for rule in rules:
       if match_rule(case, rule):
           # Cette règle s'applique !
           return rule.recommendation
   ```

3. **Logique de Matching**:
   ```json
   {
     "logic": "all",  // Toutes les conditions doivent être vraies (ET)
     "conditions": {
       "fever": true,
       "meningeal_signs": true
     }
   }
   ```
   
   ou
   
   ```json
   {
     "logic": "any",  // Au moins une condition (OU)
     "conditions": {
       "seizure": true,
       "neuro_deficit": true
     }
   }
   ```

4. **Adaptations Contextuelles**:
   
   La fonction `_apply_contextual_adaptations()` modifie les recommandations selon le contexte:
   
   **Exemple - Grossesse**:
   ```python
   # Si la patiente est enceinte:
   Scanner cérébral → IRM cérébrale (radiation = danger)
   + Ajout d'angio-IRM veineuse (risque de thrombose)
   + Avertissement: "IRM contre-indiquée si <3 mois de grossesse"
   ```
   
   **Exemple - Femme jeune**:
   ```python
   # Si femme < 50 ans:
   Avant scanner → Test de grossesse obligatoire
   ```
   
   **Exemple - Patient âgé**:
   ```python
   # Si âge > 60 ans ET scanner avec injection:
   Précaution: Vérifier créatinine (fonction rénale)
   ```

**Système de Priorité**:
Les règles sont triées par priorité (0-100):
```
100: Urgence vitale (HSA, méningite)
90:  Urgence neurologique (déficit, HTIC)
80:  Contextes à risque (grossesse, trauma)
70:  Subaigu avec red flags
50:  Chronique avec signes d'alarme
```

---

### 📁 **headache_assistants/prescription.py** - Générateur d'Ordonnances
**Technologie**: Génération de Texte Formaté, Gestion de Fichiers

**Rôle**: Crée des ordonnances médicales au format texte à partir des recommandations.

**Fonctionnement**:

1. **Entrées**:
   - Cas clinique (HeadacheCase)
   - Recommandation d'imagerie (ImagingRecommendation)
   - Nom du médecin prescripteur

2. **Génération**:
   ```
   ================================================================
                           ORDONNANCE MÉDICALE
   ================================================================
   
   Date: 01/12/2025 14:30
   Prescripteur: Dr. Martin Dupont
   
   ----------------------------------------------------------------
                          INFORMATIONS PATIENT
   ----------------------------------------------------------------
   Âge: 45 ans
   Sexe: Féminin
   Contexte: Aucun contexte particulier
   
   ----------------------------------------------------------------
                       INDICATION CLINIQUE
   ----------------------------------------------------------------
   Céphalée subaiguë (progressive)
   
   Red Flags Détectés:
     • Fièvre
     • Signes méningés
   
   ----------------------------------------------------------------
                       EXAMENS DEMANDÉS
   ----------------------------------------------------------------
   1. Ponction Lombaire
   
   ----------------------------------------------------------------
                           URGENCE
   ----------------------------------------------------------------
   ⚠️  URGENCE IMMÉDIATE - Adresser le patient aux urgences
   
   ----------------------------------------------------------------
                         PRÉCAUTIONS
   ----------------------------------------------------------------
   • Méningite bactérienne suspectée
   
   ----------------------------------------------------------------
                       NOTES CLINIQUES
   ----------------------------------------------------------------
   Méningite bactérienne suspectée. Ponction lombaire en urgence...
   
   ================================================================
   ```

3. **Sauvegarde**:
   - Fichier créé dans `ordonnances/ordonnance_20251201_143000.txt`
   - Timestamp unique pour chaque ordonnance

---

### 📁 **rules/headache_rules.json** - Base de Connaissances Médicales
**Technologie**: JSON (JavaScript Object Notation), Base de Règles Déclarative

**Rôle**: Contient toutes les règles médicales pour la prise de décision.

**Structure d'une Règle**:
```json
{
  "id": "MENINGITE_001",
  "name": "Méningite bactérienne",
  "description": "Céphalée avec fièvre et signes méningés",
  "category": "acute_emergency",
  "priority": 100,
  
  "logic": "all",
  "conditions": {
    "fever": true,
    "meningeal_signs": true
  },
  
  "recommendation": {
    "imaging": ["ponction_lombaire"],
    "urgency": "immediate",
    "comment": "Méningite bactérienne suspectée. Ponction lombaire en urgence..."
  }
}
```

**Les 17 Règles Principales**:

1. **HSA_001**: Hémorragie sous-arachnoïdienne (coup de tonnerre)
2. **HSA_002**: HSA avec syndrome méningé
3. **MENINGITE_001**: Méningite bactérienne
4. **MENINGITE_002**: Méningo-encéphalite
5. **NEURO_001**: Déficit neurologique focal
6. **HTIC_001**: Hypertension intracrânienne
7. **EPILEPSIE_001**: Céphalée post-critique
8. **TVC_001**: Thrombose veineuse cérébrale
9. **TRAUMA_001**: Post-traumatique récent
10. **IMMUNOSUPP_001**: Patient immunodéprimé
11. **SUBACUTE_001**: Subaigu avec red flags
12. **CHRONIC_001**: Chronique avec aggravation
13. **MIGRAINE_001**: Migraine typique
14. **TENSION_001**: Céphalée de tension
15. **FALLBACK_ACUTE**: Cas aigu sans red flag
16. **FALLBACK_SUBACUTE**: Cas subaigu sans red flag
17. **FALLBACK_CHRONIC**: Cas chronique bénin

---

### 📁 **test_patients.py** - Cas de Test
**Technologie**: Tests Fonctionnels, Validation

**Rôle**: Valide le système avec 11 cas cliniques prédéfinis.

**Exemples de Tests**:

1. **Urgence Vitale - HSA**:
   ```python
   patient = HeadacheCase(
       age=55, sex="M",
       onset="thunderclap",
       intensity=10,
       profile="acute"
   )
   # Attendu: Scanner + PL, URGENCE IMMÉDIATE
   ```

2. **Méningite**:
   ```python
   patient = HeadacheCase(
       age=30, sex="F",
       fever=True,
       meningeal_signs=True
   )
   # Attendu: Ponction lombaire, URGENCE IMMÉDIATE
   ```

3. **Grossesse + Céphalée Brutale**:
   ```python
   patient = HeadacheCase(
       age=28, sex="F",
       pregnancy_postpartum=True,
       onset="thunderclap"
   )
   # Attendu: IRM (pas scanner!), angio-IRM veineuse
   ```

---

## Technologies et Concepts Clés

### 1. **Pydantic** (Validation de Données)
- Bibliothèque Python pour créer des modèles de données avec validation automatique
- Assure que les données sont toujours dans le bon format
- Génère automatiquement de la documentation

### 2. **NLU - Natural Language Understanding** (Compréhension du Langage Naturel)
- Permet au système de comprendre du texte écrit naturellement
- Utilise des expressions régulières (regex) pour détecter des patterns
- Alternative simple aux grands modèles de langage (LLM) comme GPT

### 3. **Moteur de Règles** (Rule Engine)
- Système qui applique automatiquement des règles "SI... ALORS..."
- Séparation entre la logique (règles JSON) et le code (Python)
- Facile à maintenir : modifier une règle ne nécessite pas de changer le code

### 4. **Gestion de Session** (State Management)
- Mémorise l'état de la conversation
- Permet de poser des questions une par une
- Interprète les réponses dans leur contexte

### 5. **Expressions Régulières** (Regex)
- Langage de patterns pour rechercher du texte
- Exemple: `r"fièvre|fébrile|température"` trouve "fièvre" OU "fébrile" OU "température"
- Exemple: `r"\d+°C"` trouve un nombre suivi de "°C" (39°C, 38.5°C, etc.)

---

## Flux de Données

```
1. Médecin tape: "Patiente 45 ans, céphalées progressives, fièvre, raideur nuque"
                                    ↓
2. main.py reçoit le texte → Envoie à dialogue.py
                                    ↓
3. dialogue.py → nlu.py pour extraction
                                    ↓
4. nlu.py analyse le texte:
   - Age: 45 (détecté par "\d+" près de "ans")
   - Sexe: F (détecté par "Patiente")
   - Onset: progressive (détecté par pattern ONSET_PATTERNS)
   - Fever: true (détecté par "fièvre")
   - Meningeal_signs: true (détecté par "raideur nuque")
                                    ↓
5. dialogue.py crée HeadacheCase(age=45, sex="F", ...)
                                    ↓
6. Vérifie champs manquants → Pose question: "Intensité de la douleur?"
                                    ↓
7. Médecin répond: "8"
                                    ↓
8. dialogue.py interprète "8" → intensity = 8 (contexte: dernière question)
                                    ↓
9. Cas complet → Envoie à rules_engine.py
                                    ↓
10. rules_engine.py charge headache_rules.json
                                    ↓
11. Teste chaque règle:
    - HSA_001? Non (onset ≠ thunderclap)
    - MENINGITE_001? OUI (fever=true ET meningeal_signs=true)
                                    ↓
12. Applique MENINGITE_001:
    - Examens: ponction_lombaire
    - Urgence: immediate
    - Commentaire: "Méningite bactérienne suspectée..."
                                    ↓
13. _apply_contextual_adaptations():
    - Vérifie grossesse → Non
    - Vérifie âge > 60 → Non
    - Pas d'adaptation nécessaire
                                    ↓
14. Retourne ImagingRecommendation à dialogue.py
                                    ↓
15. dialogue.py formate le message final
                                    ↓
16. main.py affiche:
    "URGENCE MÉDICALE DÉTECTÉE
     Méningite bactérienne suspectée...
     Examens: ponction_lombaire
     Adresser le patient aux urgences immédiatement."
```

---

## Avantages de cette Architecture

### ✅ **Séparation des Responsabilités**
Chaque fichier a un rôle clair:
- `nlu.py` = Comprendre le texte
- `rules_engine.py` = Appliquer les règles médicales
- `dialogue.py` = Gérer la conversation
- `prescription.py` = Générer les ordonnances

### ✅ **Facilité de Maintenance**
- Modifier une règle médicale → Éditer `headache_rules.json` (pas besoin de toucher le code)
- Ajouter un nouveau pattern → Modifier `nlu.py`
- Changer le format d'ordonnance → Modifier `prescription.py`

### ✅ **Validation Stricte**
- Pydantic garantit que les données sont toujours valides
- Impossible d'avoir un âge négatif ou une intensité > 10

### ✅ **Traçabilité**
- Chaque règle a un ID unique
- L'historique de conversation est conservé
- Les ordonnances sont horodatées

### ✅ **Extensibilité**
- Facile d'ajouter de nouvelles règles médicales
- Possible d'intégrer un vrai LLM (GPT, Claude) à la place du NLU simple
- Structure prête pour une interface web (FastAPI, Flask)

---

## Limitations Actuelles et Évolutions Possibles

### Limitations:
1. **NLU basique**: Utilise des regex au lieu d'un vrai modèle de langage
2. **Questions fixes**: Les questions sont prédéfinies, pas générées dynamiquement
3. **Pas de base de données**: Les sessions sont en mémoire (perdues à la fermeture)
4. **Interface en ligne de commande**: Pas d'interface graphique

### Évolutions Possibles:
1. **Intégrer un LLM** (GPT-4, Claude):
   ```python
   # Au lieu de regex, appeler un LLM:
   response = openai.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": medical_text}]
   )
   ```

2. **Interface Web** (FastAPI + React):
   ```
   Frontend (React) ←→ API (FastAPI) ←→ Backend (dialogue.py, rules_engine.py)
   ```

3. **Base de Données** (PostgreSQL):
   ```python
   # Sauvegarder les sessions:
   db.save_session(session_id, current_case, history)
   ```

4. **Apprentissage Continu**:
   - Analyser les cas traités
   - Affiner les règles médicales
   - Détecter les patterns fréquents

---

## Glossaire

- **API**: Application Programming Interface - Interface permettant à des programmes de communiquer
- **JSON**: Format de fichier texte pour stocker des données structurées
- **Regex**: Expression Régulière - Pattern pour rechercher du texte
- **NLU**: Natural Language Understanding - Compréhension du langage naturel
- **LLM**: Large Language Model - Grand modèle de langage (comme GPT)
- **Pydantic**: Bibliothèque Python de validation de données
- **Session**: Mémoire temporaire d'une conversation
- **State Machine**: Système qui gère différents états (en cours, terminé, etc.)
- **Rule Engine**: Moteur qui applique des règles SI...ALORS
- **Red Flags**: Signes d'alarme médicaux nécessitant une action urgente

---

## Comment Démarrer

1. **Installer les dépendances**:
   ```bash
   pip install pydantic
   ```

2. **Lancer le chatbot**:
   ```bash
   python main.py
   ```

3. **Tester un cas**:
   ```
   Vous: Patiente 45 ans, céphalées progressives depuis 3 jours
   Assistant: Le patient a-t-il de la fièvre?
   Vous: oui
   Assistant: Le patient présente-t-il une raideur de la nuque?
   Vous: oui
   Assistant: URGENCE MÉDICALE DÉTECTÉE...
   ```

4. **Générer une ordonnance**:
   ```
   Vous: /ordonnance
   Assistant: Nom du prescripteur?
   Vous: Dr. Martin Dupont
   Assistant: Ordonnance générée: ordonnances/ordonnance_20251201_143000.txt
   ```

---

## Support et Documentation

- **README.md**: Documentation générale du projet
- **headache_rules.txt**: Référence médicale des règles
- **tests/**: Tests unitaires pour valider le système

---

*Ce document explique l'architecture et les technologies du système d'évaluation des céphalées. Pour toute question technique, consultez les commentaires dans chaque fichier source.*
