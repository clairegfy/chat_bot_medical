# Headache Assistant - Aide a la Decision Medicale

**Backend Python pour l'evaluation des cephalees et la prescription d'imagerie cerebrale**

---

## Contexte et Motivation

Ce projet est ne d'un constat alarmant : **environ 30% des prescriptions d'imagerie cerebrale pour cephalees seraient inappropriees** - soit par exces (examens inutiles exposant le patient a des radiations et coutant au systeme de sante), soit par defaut (urgences non detectees mettant en jeu le pronostic vital).

Ce systeme a ete developpe dans un cadre academique en partenariat avec un hopital, avec l'objectif de fournir aux medecins un outil d'aide a la decision base sur les **guidelines medicales francaises** pour l'evaluation des cephalees.

### Objectifs

1. **Reduire les erreurs de prescription** en guidant le praticien a travers un arbre decisionnel valide
2. **Detecter les urgences** (HSA, meningite, HTIC) qui necessitent une imagerie immediate
3. **Eviter les examens inutiles** pour les cephalees benignes bien caracterisees
4. **Adapter les recommandations** aux contextes specifiques (grossesse, immunodepression, age)

---

## Architecture du Systeme

Ce repository constitue le **backend** du systeme. Un frontend web sera developpe separement pour l'interface utilisateur finale.

```
arbre_ia/
├── main_hybrid.py                 # Interface CLI interactive (demo)
├── headache_assistants/           # Package Python principal
│   ├── models.py                  # Modeles Pydantic (HeadacheCase, etc.)
│   ├── dialogue.py                # Gestionnaire de dialogue interactif
│   ├── rules_engine.py            # Moteur de regles medicales (31 regles)
│   ├── prescription.py            # Generation d'ordonnances
│   ├── logging_config.py          # Audit trail des decisions
│   │
│   ├── nlu_base.py                # Extraction de base (age, sexe, intensite)
│   ├── nlu_v2.py                  # NLU regles + vocabulaire medical
│   ├── nlu_hybrid.py              # NLU hybride (regles + embeddings)
│   ├── medical_vocabulary.py      # Ontologie medicale (2400 lignes)
│   ├── medical_examples_corpus.py # Corpus d'exemples annotes (86 cas)
│   └── pregnancy_utils.py         # Detection trimestre de grossesse
│
├── rules/
│   └── headache_rules.json        # 31 regles medicales structurees
│
├── tests_validation/              # Suite de tests (206 tests)
│   ├── test_inputs_utilisateur_reels.py # Tests avec inputs realistes (46 tests)
│   ├── test_scenarios_dialogue.py # Tests des scenarios utilisateur
│   ├── test_nlu_hybrid.py         # Tests du NLU hybride
│   ├── test_medical_vocabulary.py # Tests du vocabulaire medical
│   └── ...
│
└── ordonnances/                   # Ordonnances generees (sortie)
```

---

## Fonctionnement

### Pipeline de Decision

```
Description clinique (texte libre)
         |
         v
+-----------------------------------------------------+
|  NLU HYBRIDE                                        |
|  - Extraction: age, sexe, duree, intensite          |
|  - Detection: red flags, profil temporel            |
|  - Enrichissement: embeddings si confiance basse    |
+-----------------------------------------------------+
         |
         v
+-----------------------------------------------------+
|  DIALOGUE INTERACTIF                                |
|  Questions ciblees pour informations manquantes     |
|  (fievre? syndrome meninge? aggravation recente?)   |
+-----------------------------------------------------+
         |
         v
+-----------------------------------------------------+
|  MOTEUR DE REGLES (31 regles medicales)             |
|  - Urgences: HSA, meningite, HTIC, dissection       |
|  - Contextes: grossesse, immunodepression           |
|  - Adaptations: trimestre, contre-indications       |
+-----------------------------------------------------+
         |
         v
    Recommandation
    (imagerie, urgence, precautions)
```

### Exemple de Cas Clinique

**Entree:** "Femme 28 ans enceinte de 8 semaines, cephalee brutale depuis 2h"

**Analyse:**
- Age: 28 ans
- Sexe: F
- Grossesse: Oui (T1 - 8 semaines)
- Onset: Brutal (thunderclap)
- Duree: 2 heures

**Sortie:**
- **Urgence:** IMMEDIATE
- **Imagerie:** Scanner cerebral sans injection (IRM contre-indiquee T1 sauf urgence vitale)
- **Suspicion:** HSA - Hemorragie sous-arachnoidienne
- **Precautions:** Eviter gadolinium, protocole urgence obstetricale

---

## Installation

### Prerequis

- Python 3.11+
- pip

### Installation des dependances

```bash
pip install -r requirements_hybrid.txt
```

**Dependances principales:**
- `pydantic>=2.0.0` - Validation des donnees
- `sentence-transformers>=2.2.0` - Embeddings pour NLU hybride
- `torch>=2.0.0` - Backend pour sentence-transformers
- `pytest>=7.0.0` - Tests

---

## Utilisation

### Mode Demo (CLI Interactive)

```bash
python main_hybrid.py
```

Le systeme demarre en mode dialogue interactif:

```
======================================================================
ASSISTANT MEDICAL - EVALUATION DES CEPHALEES (NLU HYBRIDE)
======================================================================

Bonjour Docteur,
Decrivez le cas clinique de votre patient.

Commandes disponibles:
  /aide        - Afficher cette aide
  /ordonnance  - Generer une ordonnance (apres evaluation)
  /logs        - Voir guidelines et logs de session
  /reset       - Commencer un nouveau cas
  /quit        - Quitter le programme
======================================================================

Vous: patient 50 ans cephalee brutale intense
```

### Generation d'ordonnance

```python
from headache_assistants.prescription import generate_prescription

# Apres evaluation complete
filepath = generate_prescription(
    case=response.headache_case,
    recommendation=response.imaging_recommendation,
    doctor_name="Dr. Martin"
)
print(f"Ordonnance generee: {filepath}")
```

---

## Tests

Le projet dispose d'une suite de **206 tests** couvrant:
- **46 tests avec inputs utilisateur realistes** (strings en langage naturel)
- Scenarios de dialogue utilisateur
- Extraction NLU (age, sexe, profils temporels)
- Detection des red flags medicaux
- Gestion des negations ("pas de fievre", "aucune raideur de nuque")
- Moteur de regles medicales
- Cas de non-regression

### Lancer tous les tests

```bash
pytest tests_validation/ -v
```

### Lancer un fichier specifique

```bash
pytest tests_validation/test_scenarios_dialogue.py -v
```

### Avec couverture

```bash
pytest tests_validation/ --cov=headache_assistants --cov-report=html
```

---

## Regles Medicales

Le systeme utilise **31 regles medicales** categorisees par niveau d'urgence:

| Categorie | Exemples | Urgence |
|-----------|----------|---------|
| **Urgences aigues** | HSA, Meningite, HTIC, Dissection arterielle | IMMEDIATE |
| **Grossesse/Post-partum** | TVC, Eclampsie, PRES | URGENT |
| **Contextes specifiques** | Immunodepression + fievre, Cancer + cephalee | URGENT |
| **Subaigues** | Arterite temporale, Tumeur suspectee | PROGRAMME (< 7j) |
| **Chroniques** | Migraine, Tension, CCQ sans changement | NON URGENT |

### Acces aux guidelines

Depuis le mode interactif, tapez `/logs` puis `[1]` pour consulter les regles.

---

## Logging et Tracabilite

Le systeme integre un **audit trail** pour la tracabilite des decisions medicales:

```python
from headache_assistants.logging_config import setup_logging, log_medical_decision

# Activer les logs en mode debug
setup_logging(level=logging.DEBUG, enable_console=True)

# Les decisions sont automatiquement tracees
# Format: [timestamp] DECISION MEDICALE: HSA_001 (urgence: immediate, confiance: 95%)
```

Par defaut, les logs sont desactives en console pour ne pas polluer l'interface.

---

## Composants Techniques

### NLU Hybride (3 couches)

1. **nlu_base.py** - Extraction regex (age, sexe, duree, intensite)
2. **nlu_v2.py** - Vocabulaire medical + patterns cliniques
3. **nlu_hybrid.py** - Enrichissement par embeddings si confiance < 70%

**Performance:**
- 90% des cas traites par regles seules (< 10ms)
- 10% enrichis par embeddings (~50ms)

### Vocabulaire Medical

`medical_vocabulary.py` contient une ontologie de 2400 lignes couvrant:
- Synonymes medicaux (rdn = raideur de nuque)
- Acronymes (HSA, HTIC, TVC)
- Variations linguistiques (fievre/febrile/hyperthermie)
- Anti-patterns pour eviter les faux positifs

### Detection Grossesse

`pregnancy_utils.py` detecte le trimestre depuis des formats varies:
- "8 semaines", "8 SA", "2 mois"
- "1er trimestre", "T2", "3eme trimestre"
- Calcul automatique: T1 < 14 sem, T2 14-27 sem, T3 >= 28 sem

---

## Avertissement Medical

**ATTENTION: Cet outil est une aide a la decision, pas un dispositif medical certifie.**

- L'evaluation clinique du medecin reste primordiale
- En cas de doute, un avis specialise est recommande
- Ne remplace pas un examen neurologique complet

---

## Licences et Conformite

### Code Source du Projet

Le code source de ce projet (headache_assistants/, rules/, tests_validation/) est developpe dans un cadre academique. Pour tout usage en production hospitaliere, contactez l'auteur.

### Dependances et Licences

| Dependance | Licence | Notes |
|------------|---------|-------|
| **Python** | PSF License | Langage de programmation |
| **Pydantic** | MIT | [Licence MIT](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| **PyTorch** | BSD-3-Clause | [Licence BSD](https://github.com/pytorch/pytorch/blob/main/LICENSE) |
| **NumPy** | BSD-3-Clause | Calcul numerique |
| **pytest** | MIT | Outil de test uniquement |
| **sentence-transformers** | Apache 2.0 | Embeddings NLP |


### Regles Medicales (rules/headache_rules.json)

Les regles medicales sont basees sur les **guidelines medicales francaises** publiques. Elles ne contiennent pas de contenu sous copyright tiers.

### Recommandation pour Deploiement Hospitalier

Pour un deploiement en production dans un hopital, nous recommandons :

1. Audit juridique par le service juridique de l'etablissement
2. Desactivation ou remplacement du modele d'embedding (Option A ou B ci-dessus)
3. Validation par le comite d'ethique si applicable
4. Tests cliniques avant mise en production

---

## Auteurs

Alex Peirano, Chrissy AUBOU, Noam BENICHOU, Sara EL BARI, Claire GEOFFROY, Julie MAUREL, Ethan SAMSON - Projet academique en partenariat hospitalier


