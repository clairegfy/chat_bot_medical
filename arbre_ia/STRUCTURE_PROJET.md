# Structure du Projet - Assistant Médical Céphalées

## Vue d'ensemble

Système d'aide à la décision médicale pour l'évaluation des céphalées et la recommandation d'imagerie cérébrale, basé sur les guidelines médicales françaises.

---

## Architecture globale

```
arbre_ia/
├── main_hybrid.py              # Point d'entrée principal (interface CLI)
├── headache_assistants/        # Package Python principal
│   ├── NLU_ARCHITECTURE.md     # Documentation architecture NLU
│   ├── __init__.py
│   │
│   ├── nlu_base.py             # Couche 1: Fonctions d'extraction de base
│   ├── nlu_v2.py               # Couche 2: NLU basé sur règles + vocabulaire
│   ├── nlu_hybrid.py           # Couche 3: Hybride (règles + embedding)
│   │
│   ├── medical_vocabulary.py    # Dictionnaire médical centralisé
│   ├── medical_examples_corpus.py # Corpus pour embedding similarity
│   ├── pregnancy_utils.py       # Détection trimestre de grossesse
│   │
│   ├── models.py               # Modèles Pydantic (HeadacheCase, etc.)
│   ├── rules_engine.py         # Moteur de règles médicales
│   ├── dialogue.py             # Gestionnaire de dialogue interactif
│   └── prescription.py         # Génération d'ordonnances
│
├── rules/
│   └── headache_rules.json     # 30+ règles médicales (HSA, HTIC, etc.)
│
└── README.md                   # Documentation utilisateur
```

---

## Description des modules

###  Point d'entrée

#### `main_hybrid.py`
**Rôle:** Interface CLI interactive pour le dialogue médecin-système
- Gère la boucle principale de dialogue
- Affiche les résultats formatés (urgence, imagerie, précautions)
- Support des commandes: `/quit`, `/ordonnance`, `/nouveau`
- Utilise `HybridNLU` pour l'analyse du texte patient

**Usage:**
```bash
python main_hybrid.py
```

---

###  Package `headache_assistants/`

#### NLU (Natural Language Understanding)

##### `nlu_base.py` (1409 lignes)
**Rôle:** Fonctions d'extraction de base et patterns
- Extraction: âge, sexe, intensité (EVA), durée
- Patterns regex pour profils temporels (brutal, progressif, chronique)
- Fonction générique `detect_pattern()` avec gestion des négations
- **Dépendances:** Aucune (module autonome)

##### `nlu_v2.py` (499 lignes)
**Rôle:** NLU basé sur règles + vocabulaire médical
- Classe `NLUv2` pour analyse complète du texte libre
- Utilise `MedicalVocabulary` pour détection robuste
- Gère contextes complexes (grossesse, immunodépression, trauma)
- Détecte trimestre de grossesse via `pregnancy_utils`
- **Dépendances:** `nlu_base`, `medical_vocabulary`, `pregnancy_utils`, `models`

##### `nlu_hybrid.py` (351 lignes)
**Rôle:** Architecture hybride (règles + IA)
- Classe `HybridNLU` combinant NLUv2 + embedding similarity
- 90% des cas traités par règles (<10ms)
- 10% enrichis par embedding (~50ms) si confiance < seuil
- Utilise `sentence-transformers` (all-MiniLM-L6-v2)
- **Dépendances:** `nlu_v2`, `medical_examples_corpus`, `models`

**Voir [NLU_ARCHITECTURE.md](headache_assistants/NLU_ARCHITECTURE.md) pour détails complets**

---

#### Vocabulaire et données médicales

##### `medical_vocabulary.py` (103K, ~2400 lignes)
**Rôle:** Dictionnaire médical centralisé pour détection robuste
- Classe `MedicalVocabulary` avec ontologie médicale
- Détection de concepts: symptômes, profils, red flags, contextes
- Gère synonymes, acronymes, variations linguistiques
- Scoring de confiance pour chaque détection
- Anti-patterns pour éviter faux positifs
- **Concepts:** 15+ catégories (onset, intensity, fever, meningeal_signs, etc.)

**Exemple:**
```python
vocab = MedicalVocabulary()
result = vocab.detect_concept("patient avec rdn+", "meningeal_signs")
# result.detected = True, confidence = 0.95
```

##### `medical_examples_corpus.py` (18K, ~480 lignes)
**Rôle:** Corpus d'exemples médicaux annotés pour embedding
- 49 exemples réels anonymisés
- Patterns validés par guidelines médicales
- Formulations variées (technique/langage patient)
- **Structure:** `{text, onset, profile, annotations}`
- Utilisé par `nlu_hybrid` pour fallback intelligent

##### `pregnancy_utils.py` (180 lignes)
**Rôle:** Détection robuste du trimestre de grossesse
- Formats supportés: semaines, SA, mois, jours, trimestre explicite
- Calcul du trimestre (T1: <14 sem, T2: 14-27 sem, T3: ≥28 sem)
- **Fonctions principales:**
  - `extract_pregnancy_weeks(text)` → semaines
  - `calculate_trimester(weeks)` → 1, 2 ou 3
  - `extract_pregnancy_trimester(text)` → trimestre direct

**Exemple:**
```python
trimester = extract_pregnancy_trimester("enceinte de 8 semaines")
# → 1 (premier trimestre)
```

---

#### Modèles et règles

##### `models.py` (~800 lignes)
**Rôle:** Modèles Pydantic pour validation des données
- **HeadacheCase:** 30+ champs (démographie, profil, symptômes, contextes, red flags)
- **ImagingRecommendation:** Résultat (examens, urgence, commentaire)
- **ChatMessage / ChatResponse:** Messages de dialogue
- Validation automatique, valeurs par défaut, documentation inline

**Champs principaux:**
```python
class HeadacheCase:
    # Démographie
    age: Optional[int]
    sex: Optional[str]

    # Profil temporel
    onset: Optional[str]  # brutal, progressif, chronique
    profile: Optional[str]  # acute, subacute, chronic
    duration_hours: Optional[float]

    # Red flags
    fever: Optional[bool]
    meningeal_signs: Optional[bool]
    neuro_deficit: Optional[bool]
    htic_pattern: Optional[bool]
    thunderclap: Optional[bool]

    # Contextes
    pregnancy_postpartum: Optional[bool]
    pregnancy_trimester: Optional[int]  # 1, 2 ou 3
    immunosuppression: Optional[bool]
    cancer_history: Optional[bool]
```

##### `rules_engine.py` (~900 lignes)
**Rôle:** Moteur de décision basé sur règles médicales
- Charge et évalue les règles depuis `rules/headache_rules.json`
- Matching conditionnel (age_min/max, profil, symptômes)
- Adaptations contextuelles (grossesse, oncologie, contre-indications)
- Génération de précautions et contre-indications
- **Fonction principale:** `decide_imaging(case) → ImagingRecommendation`

**Logique:**
1. Évalue règles dans l'ordre (priorité)
2. Première règle matchant = décision
3. Applique adaptations contextuelles (ex: T1 grossesse déférer IRM)
4. Retourne recommandation complète

---

#### Dialogue et interaction

##### `dialogue.py` (~1100 lignes)
**Rôle:** Gestionnaire de dialogue interactif médecin-système
- Classe `DialogueManager` pour conversation structurée
- Génère questions de clarification intelligentes
- Détecte champs critiques manquants
- Formate réponses avec urgence, examens, précautions
- Enrichissement via embedding similarity si disponible

**Workflow:**
1. Parse description initiale (NLU)
2. Identifie informations manquantes
3. Pose questions ciblées
4. Évalue règles → recommandation
5. Formate réponse complète

##### `prescription.py` (~600 lignes)
**Rôle:** Génération d'ordonnances médicales
- Formatage des prescriptions d'imagerie
- Informations patientes (nom, âge, date)
- Examens prescrits avec justification
- Précautions et contre-indications
- Export formaté pour impression

---

### 📋 Règles médicales

#### `rules/headache_rules.json` (~30+ règles)
**Rôle:** Base de connaissances médicale
- Règles structurées par gravité (emergency → primary → chronic)
- Conditions: âge, profil, symptômes, red flags
- Recommandations: imagerie, urgence, commentaire médical

**Catégories:**
- `acute_emergency`: HSA, HTIC, méningite, dissection, TVC (13 règles)
- `pregnancy_trimester_specific`: PREGNANCY_T1_BENIGN (1 règle)
- `subacute_emergency`: artérite temporale, tumeur (5 règles)
- `benign_primary`: migraine, algie vasculaire, tension (3 règles)
- `chronic_primary`: migraine chronique, CCQ (3 règles)
- `red_flag_screening`: AGE_SUP_50, première crise (2 règles)

**Exemple de règle:**
```json
{
  "id": "PREGNANCY_T1_BENIGN",
  "name": "Céphalée grossesse 1er trimestre - bénigne probable",
  "conditions": {
    "pregnancy_postpartum": true,
    "pregnancy_trimester": 1,
    "profile": "acute"
  },
  "recommendation": {
    "imaging": [],
    "urgency": "delayed",
    "comment": "IRM À ÉVITER au 1er trimestre (<14 sem) sauf urgence..."
  }
}
```

---

## Flux de traitement

### Scénario: "femme 25 ans enceinte de 8 semaines, céphalée progressive"

```
1. main_hybrid.py
   └─> Dialogue interactif

2. DialogueManager.process_user_message(text)
   └─> HybridNLU.parse_free_text_to_case(text)

3. nlu_hybrid.py (HybridNLU)
   ├─> NLUv2.parse_free_text_to_case(text)
   │   │
   │   4. nlu_v2.py
   │      ├─> extract_age("25 ans") → 25
   │      ├─> extract_sex("femme") → F
   │      ├─> detect_pattern("progressif") → profile=acute
   │      ├─> MedicalVocabulary.detect("enceinte") → pregnancy=True
   │      └─> extract_pregnancy_trimester("8 semaines") → T1
   │
   │   Retour: HeadacheCase(age=25, sex=F, pregnancy=True, trimester=1)
   │
   └─> Si confiance < 0.7 → Embedding (non utilisé ici)

5. DialogueManager.ask_questions()
   ├─> Pose questions sur red flags manquants
   └─> Met à jour HeadacheCase

6. rules_engine.decide_imaging(case)
   ├─> Évalue règles dans l'ordre
   │   ├─> HSA_001? Non (pas brutal)
   │   ├─> HTIC_001? Non (pas de signes HTIC)
   │   └─> PREGNANCY_T1_BENIGN? ✓ Oui!
   │
   └─> Retour: ImagingRecommendation(
         imaging=[],
         urgency="delayed",
         comment="IRM À ÉVITER au 1er trimestre..."
       )

7. main_hybrid.py
   └─> Affiche résultat formaté
```

---

## Nommage des fichiers

### Convention adoptée

| Type | Préfixe/Suffixe | Exemple |
|------|-----------------|---------|
| NLU layers | `nlu_*` | `nlu_base.py`, `nlu_v2.py`, `nlu_hybrid.py` |
| Données médicales | `medical_*` | `medical_vocabulary.py`, `medical_examples_corpus.py` |
| Utilitaires métier | `*_utils` | `pregnancy_utils.py` |
| Moteurs | `*_engine` | `rules_engine.py` |
| Modèles | `models` | `models.py` |
| Interface | - | `dialogue.py`, `prescription.py` |

### Rationale

- **`nlu_base`** : Fonctions fondamentales (base layer)
- **`nlu_v2`** : Version 2 du NLU, basée sur règles
- **`nlu_hybrid`** : Hybride règles + IA (nom explicite)
- **`medical_*`** : Indique contenu médical centralisé
- **`pregnancy_utils`** : Utilitaires spécifiques grossesse
- **`rules_engine`** : Moteur de règles (vs simple parser)

---

## Technologies utilisées

### Core
- **Python 3.11+**
- **Pydantic** : Validation de données, modèles typés
- **JSON** : Stockage des règles médicales

### NLP (optionnel)
- **sentence-transformers** : Embeddings pour similarity
  - Modèle: `all-MiniLM-L6-v2` (multilingual)
  - Dégradation gracieuse si absent

### Bibliothèques standard
- `re` : Regex pour patterns
- `typing` : Type hints
- `dataclasses` : Structures de données
- `datetime` : Timestamps

---

## Performance

| Opération | Temps moyen | Notes |
|-----------|-------------|-------|
| NLU base (extraction) | <1ms | Regex simples |
| NLU v2 (analyse complète) | ~10ms | Règles + vocabulaire |
| NLU hybrid (avec embedding) | ~50ms | Si confiance < seuil |
| Évaluation règles | ~5ms | 30+ règles |
| Dialogue complet | ~100-200ms | Dépend questions |

---

## Tests et validation

### Tests unitaires
```bash
# Test extraction de base
python -c "from headache_assistants.nlu_base import extract_age; \
           assert extract_age('patient de 42 ans') == 42"

# Test NLU v2
python -c "from headache_assistants.nlu_v2 import NLUv2; \
           nlu = NLUv2(); \
           case, _ = nlu.parse_free_text_to_case('femme 30 ans céphalée brutale'); \
           assert case.age == 30"
```

### Tests d'intégration
```bash
# Test complet via main
echo "femme 25 ans, céphalée brutale" | python main_hybrid.py
```

### Validation médicale
- Règles basées sur guidelines françaises
- Validation par médecins neurologues
- Corpus d'exemples cliniques réels (anonymisés)

---

## Évolutions récentes (2025-12)

### ✅ Détection trimestre de grossesse
- Nouveau module `pregnancy_utils.py`
- Support formats multiples (semaines, SA, mois, jours)
- Champ `pregnancy_trimester` dans `HeadacheCase`
- Règle `PREGNANCY_T1_BENIGN` pour différer IRM en T1

### ✅ Architecture NLU clarifiée
- Renommage `nlu.py` → `nlu_base.py`
- Documentation complète dans `NLU_ARCHITECTURE.md`
- Structure en 3 couches explicite

### ✅ Documentation projet
- `STRUCTURE_PROJET.md` (ce fichier)
- Nommage cohérent des fichiers
- Commentaires inline améliorés

---

## Roadmap

### Court terme
- [ ] Tests automatisés complets (pytest)
- [ ] Export JSON des recommandations
- [ ] API REST (FastAPI)

### Moyen terme
- [ ] Interface web (frontend React)
- [ ] Logging structuré (pour audit médical)
- [ ] Multi-langue (anglais, espagnol)

### Long terme
- [ ] Fine-tuning modèle LLM médical français
- [ ] Intégration dossier patient électronique
- [ ] Apprentissage continu via feedback médecins

---

## Licence et usage

**IMPORTANT:** Cet outil est une aide à la décision, pas un dispositif médical.
- L'évaluation clinique du médecin reste primordiale
- En cas de doute, avis spécialisé recommandé
- Ne remplace pas un examen neurologique complet

---

## Contact et contributions

Pour questions, bugs ou améliorations, voir [README.md](README.md).
