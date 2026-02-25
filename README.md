# Headache Assistant - Aide à la Décision Médicale

**Système d'aide à la prescription d'imagerie cérébrale pour l'évaluation des céphalées**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![Tests](https://img.shields.io/badge/Tests-206%20passed-brightgreen.svg)

---

## Contexte et Motivation

Ce projet est né d'un constat alarmant : **environ 30% des prescriptions d'imagerie cérébrale pour céphalées seraient inappropriées** - soit par excès (examens inutiles exposant le patient à des radiations et coûtant au système de santé), soit par défaut (urgences non détectées mettant en jeu le pronostic vital).

Ce système a été développé dans un cadre académique en partenariat avec un hôpital, avec l'objectif de fournir aux médecins un outil d'aide à la décision basé sur les **guidelines médicales françaises** pour l'évaluation des céphalées.

### Objectifs

- **Détecter les urgences** (HSA, méningite, HTIC) qui nécessitent une imagerie immédiate
- **Réduire les erreurs de prescription** en guidant le praticien à travers un arbre décisionnel validé
- **Éviter les examens inutiles** pour les céphalées bénignes bien caractérisées
- **Adapter les recommandations** aux contextes spécifiques (grossesse, immunodépression, âge)

---

## Quick Start

### 1. Installation

```bash
# Cloner le repository
git clone https://github.com/AlexPeirano/chat_bot_medical.git
cd chat_bot_medical

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances Python
pip install -r arbre_ia/requirements_hybrid.txt

# Installer les dépendances frontend
cd frontend/frontend_arbre
npm install
```

### 2. Lancer l'application

**Terminal 1 - Backend API :**
```bash
uvicorn arbre_ia.api:app --port 8000 --reload
```

**Terminal 2 - Frontend Web :**
```bash
cd frontend/frontend_arbre
npm run tauri dev
```

Ouvrir http://localhost:5173 dans le navigateur.

---

## Architecture du Système

```
chat_bot_medical/
├── arbre_ia/                      # Backend Python (FastAPI)
│   ├── api.py                     # API REST
│   ├── headache_assistants/       # Moteur médical principal
│   │   ├── models.py              # Modèles Pydantic (HeadacheCase)
│   │   ├── dialogue.py            # Gestionnaire de dialogue
│   │   ├── rules_engine.py        # Moteur de règles (31 règles)
│   │   ├── prescription.py        # Génération d'ordonnances
│   │   ├── nlu_hybrid.py          # NLU hybride (règles + embeddings)
│   │   ├── nlu_base.py            # Extraction de base
│   │   └── medical_vocabulary.py  # Ontologie médicale
│   └── rules/
│       └── headache_rules.json    # 31 règles médicales
│
├── frontend/
│   └── frontend_arbre/            # Application React
│       └── src/
│           ├── App.jsx            # Interface chat
│           └── services/          # Appels API
│
└── tests_validation/              # Suite de tests (206 tests)
```

---

## Fonctionnement

### Pipeline de Décision

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRÉE : Description clinique (texte libre)                │
│  "Patient 45 ans, céphalée brutale intense depuis 2h"       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  NLU HYBRIDE                                                │
│  ├─ N-grams + Keywords (expressions médicales)              │
│  ├─ Fuzzy matching (tolérance fautes)                       │
│  ├─ Règles regex (âge, durée, intensité)                    │
│  └─ Embeddings (si confiance < 70%)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  DIALOGUE INTERACTIF                                        │
│  Questions ciblées pour red flags manquants :               │
│  • Fièvre ? Signes méningés ?                               │
│  • Déficit neurologique ? Crise d'épilepsie ?               │
│  • Mode de début ? Intensité ?                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  MOTEUR DE RÈGLES (31 règles médicales)                     │
│  ├─ Urgences : HSA, méningite, HTIC, dissection             │
│  ├─ Contextes : grossesse, immunodépression, cancer         │
│  └─ Adaptations : trimestre, contre-indications IRM         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SORTIE : Recommandation                                    │
│  • Imagerie recommandée (IRM, Scanner, aucun)               │
│  • Niveau d'urgence (immédiat, urgent, différé)             │
│  • Précautions spécifiques                                  │
│  • Génération d'ordonnance (PDF)                            │
└─────────────────────────────────────────────────────────────┘
```

### Exemple de Cas Clinique

**Entrée :** `"Femme 28 ans enceinte de 8 semaines, céphalée brutale depuis 2h"`

**Analyse automatique :**
| Champ | Valeur détectée |
|-------|-----------------|
| Âge | 28 ans |
| Sexe | Féminin |
| Grossesse | T1 (8 semaines) |
| Onset | Thunderclap (brutal) |
| Durée | 2 heures |

**Recommandation :**
- **Urgence :** IMMÉDIATE
- **Imagerie :** Scanner cérébral sans injection
- **Suspicion :** HSA - Hémorragie sous-arachnoïdienne
- **Précautions :** Éviter gadolinium (T1), protocole urgence obstétricale

---

## API REST

### Endpoints disponibles

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/chat` | Envoyer un message et recevoir la réponse |
| `POST` | `/prescription` | Générer une ordonnance |
| `GET` | `/session-log/{id}` | Récupérer le log d'une session |

### Exemple d'appel

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Patient 50 ans céphalée brutale intense"}'
```

**Réponse :**
```json
{
  "session_id": "abc-123",
  "message": "Comment la douleur a-t-elle débuté ?",
  "requires_more_info": true,
  "dialogue_complete": false
}
```

---

## Red Flags Détectés

Le système pose automatiquement des questions sur les signes d'alarme :

| Red Flag | Question posée |
|----------|----------------|
| **Onset** | Mode de début (coup de tonnerre ?) |
| **Fièvre** | Température > 38°C ? |
| **Signes méningés** | Raideur de nuque ? |
| **Déficit neurologique** | Faiblesses, troubles parole/vision ? |
| **Crise d'épilepsie** | Convulsions ? |
| **HTIC** | Céphalée matinale, vomissements en jet ? |

---

## Règles Médicales

Le système utilise **31 règles médicales** catégorisées par niveau d'urgence :

| Catégorie | Exemples | Urgence |
|-----------|----------|---------|
| **Urgences aiguës** | HSA, Méningite, HTIC, Dissection | IMMÉDIATE |
| **Grossesse/Post-partum** | TVC, Éclampsie, PRES | URGENT |
| **Contextes spécifiques** | Immunodépression + fièvre, Cancer | URGENT |
| **Subaiguës** | Artérite temporale, Tumeur | PROGRAMMÉ (< 7j) |
| **Chroniques** | Migraine, Tension sans changement | NON URGENT |

---

## Tests

Le projet dispose de **206 tests** couvrant :

- 46 tests avec inputs utilisateur réalistes
- Scénarios de dialogue complets
- Extraction NLU (âge, sexe, profils temporels)
- Détection des red flags médicaux
- Gestion des négations ("pas de fièvre", "aucune raideur")
- Moteur de règles médicales

### Lancer les tests

```bash
# Tous les tests
pytest arbre_ia/tests_validation/ -v

# Avec couverture
pytest arbre_ia/tests_validation/ --cov=arbre_ia/headache_assistants --cov-report=html
```

---

## Composants Techniques

### NLU Hybride (Pipeline)

1. **N-grams** - Détection d'expressions multi-mots ("raideur de nuque")
2. **Keywords** - Index O(1) pour termes médicaux fréquents
3. **Fuzzy matching** - Tolérance aux fautes (Levenshtein, seuil 0.75)
4. **Négations** - Détection "pas de", "sans", "aucun"
5. **Règles regex** - Extraction structurée (âge, durée, intensité)
6. **Embeddings** - Enrichissement sémantique si confiance < 70%

**Performance :**
- 90% des cas traités par règles seules (< 10ms)
- 10% enrichis par embeddings (~50ms)

### Vocabulaire Médical

`medical_vocabulary.py` contient une ontologie couvrant :
- Synonymes médicaux (rdn = raideur de nuque)
- Acronymes (HSA, HTIC, TVC)
- Variations linguistiques (fièvre/fébrile/hyperthermie)
- Anti-patterns pour éviter les faux positifs

---

## Logging et Traçabilité

Le système intègre un **audit trail** pour la traçabilité des décisions médicales.

Les logs de session incluent :
- Champs détectés par le NLU
- Questions posées durant le dialogue
- Règle médicale appliquée
- Score de confiance

---

## Avertissement Médical

> **ATTENTION : Cet outil est une aide à la décision, pas un dispositif médical certifié.**
>
> - L'évaluation clinique du médecin reste primordiale
> - En cas de doute, un avis spécialisé est recommandé
> - Ne remplace pas un examen neurologique complet

---

## Dépendances

| Package | Version | Usage |
|---------|---------|-------|
| FastAPI | 0.100+ | API REST |
| Pydantic | 2.0+ | Validation données |
| sentence-transformers | 2.2+ | Embeddings NLU |
| PyTorch | 2.0+ | Backend ML |
| React | 18+ | Frontend |

---

## Auteurs

Alex Peirano, Chrissy Aubou, Noam Benichou, Sara El Bari, Claire Geoffroy, Julie Maurel, Ethan Samson

*Projet académique en partenariat hospitalier*

---

## Licence

Code source développé dans un cadre académique. Pour tout usage en production hospitalière, contactez les auteurs.

Les règles médicales sont basées sur les guidelines médicales françaises publiques.
