# Architecture NLU - Natural Language Understanding

## Vue d'ensemble

Le système NLU (Natural Language Understanding) utilise une **architecture en 3 couches** pour extraire les données médicales depuis le texte libre du patient. Chaque couche a un rôle spécifique et ajoute des capacités supplémentaires.

```
┌─────────────────────────────────────────────────────────────┐
│                       main_hybrid.py                         │
│                  (Interface utilisateur)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 3: nlu_hybrid.py                                     │
│  Rôle: Orchestrateur hybride (règles + IA)                  │
│  - Classe: HybridNLU                                         │
│  - Combine NLUv2 (règles) + embedding similarity            │
│  - 90% traité par règles (<10ms)                            │
│  - 10% enrichi par embedding (~50ms)                        │
│  - Fallback intelligent pour formulations inconnues         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 2: nlu_v2.py                                         │
│  Rôle: NLU basé sur règles + vocabulaire médical            │
│  - Classe: NLUv2                                             │
│  - Utilise MedicalVocabulary (détection robuste)            │
│  - Gère négations, contextes médicaux                       │
│  - Extrait trimestre de grossesse                           │
│  - Détecte red flags et patterns complexes                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 1: nlu_base.py                                       │
│  Rôle: Fonctions de base et patterns                        │
│  - Fonctions: extract_age, extract_sex, detect_pattern      │
│  - Patterns: PROFILE_PATTERNS, HEADACHE_PROFILE_PATTERNS    │
│  - Utilitaires: extract_intensity, extract_duration         │
│  - Pas de dépendances externes                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Description détaillée des couches

### COUCHE 1: `nlu_base.py` (1409 lignes)
**Anciennement:** `nlu.py`

**Responsabilités:**
- Fonctions d'extraction de base (âge, sexe, intensité, durée)
- Patterns regex pour détection de profils (brutal, progressif, chronique)
- Fonction générique `detect_pattern()` pour matching avec négation
- Aucune dépendance sur d'autres modules NLU

**Principales fonctions:**
```python
extract_age(text: str) -> Optional[int]
extract_sex(text: str) -> Optional[str]
extract_intensity_score(text: str) -> Optional[int]
extract_duration_hours(text: str) -> Optional[float]
detect_pattern(text, patterns, check_negation=True) -> Optional[Any]
```

**Patterns définis:**
- `PROFILE_PATTERNS`: brutal, progressif, chronique
- `HEADACHE_PROFILE_PATTERNS`: début brutal, progressif, chronique
- `RECENT_PL_OR_PERIDURAL_PATTERNS`: ponction lombaire récente

**Usage:** Importé par `nlu_v2.py` pour réutiliser les fonctions de base.

---

### COUCHE 2: `nlu_v2.py` (499 lignes)
**Nom actuel:** `nlu_v2.py` (conservé pour compatibilité)

**Responsabilités:**
- Classe `NLUv2` pour analyse complète du texte patient
- Utilise `MedicalVocabulary` pour détection robuste des symptômes
- Gère les contextes médicaux complexes (grossesse, trauma, immunodépression)
- Détecte le trimestre de grossesse via `pregnancy_utils`
- Extrait tous les champs du modèle `HeadacheCase`

**Classe principale:**
```python
class NLUv2:
    def parse(self, text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
        """Parse le texte et retourne un HeadacheCase + métadonnées."""
```

**Modules utilisés:**
- `nlu_base` → fonctions de base et patterns
- `medical_vocabulary` → MedicalVocabulary pour détection symptômes
- `pregnancy_utils` → détection trimestre de grossesse
- `models` → HeadacheCase

**Capacités avancées:**
- Détection de négations contextuelles
- Gestion de l'immunodépression (VIH, chimio, greffe)
- Extraction du trimestre de grossesse (T1/T2/T3)
- Calcul de scores de confiance par champ
- Métadonnées détaillées (champs détectés, sources)

---

### COUCHE 3: `nlu_hybrid.py` (351 lignes)
**Nom actuel:** `nlu_hybrid.py` (conservé)

**Responsabilités:**
- Classe `HybridNLU` combinant règles (NLUv2) + embedding similarity
- Utilise `sentence-transformers` pour enrichir les cas ambigus
- Fallback intelligent quand confiance NLUv2 < seuil
- Matching avec corpus d'exemples médicaux via embeddings

**Classe principale:**
```python
class HybridNLU:
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        use_embedding: bool = True,
        embedding_model: str = 'all-MiniLM-L6-v2'
    ):
        self.rule_nlu = NLUv2()  # Couche règles
        self.embedder = SentenceTransformer(...)  # Couche IA
```

**Architecture hybride:**
1. **Phase 1 (Règles):** NLUv2 analyse le texte (rapide, <10ms)
2. **Phase 2 (Embedding):** Si confiance < seuil, recherche dans corpus via similarité cosinus
3. **Phase 3 (Enrichissement):** Combine résultats règles + embedding

**Avantages:**
- ✅ Rapide (90% des cas traités par règles uniquement)
- ✅ Robuste (gère formulations inconnues via embedding)
- ✅ Amélioration continue (ajout d'exemples au corpus)
- ✅ 100% local, RGPD-compliant
- ✅ Dégradation gracieuse (fonctionne sans sentence-transformers)

**Dépendances optionnelles:**
- `sentence-transformers` (modèle: all-MiniLM-L6-v2)
- Si absent: fonctionne en mode règles uniquement

---

## Flux de traitement

### Exemple: "femme 25 ans enceinte de 8 semaines, céphalée brutale"

```
1. main_hybrid.py
   └─> HybridNLU.parse(text)

2. nlu_hybrid.py (HybridNLU)
   ├─> NLUv2.parse(text)  [Couche règles]
   │
   │   3. nlu_v2.py (NLUv2)
   │      ├─> extract_age(text)           → 25 ans
   │      ├─> extract_sex(text)           → femme
   │      ├─> detect_pattern(text, ...)   → brutal
   │      ├─> MedicalVocabulary.detect()  → pregnancy=True
   │      └─> extract_pregnancy_trimester() → T1 (8 semaines)
   │
   │   Retour: HeadacheCase + metadata (confiance: 0.9)
   │
   └─> Si confiance < 0.7 → Embedding similarity
       (Non utilisé ici car confiance élevée)

4. Retour final: HeadacheCase complet
```

---

## Modules complémentaires

### `medical_vocabulary.py`
- Classe `MedicalVocabulary` pour détection robuste des symptômes
- Patterns médicaux avec synonymes (fièvre, température, fébrile)
- Gestion des négations contextuelles
- Retourne `DetectionResult(value, confidence, matched_text)`

### `pregnancy_utils.py`
- Extraction robuste de la durée de grossesse
- Formats supportés: semaines, SA, mois, jours, trimestre explicite
- Calcul du trimestre (T1: <14 sem, T2: 14-27 sem, T3: ≥28 sem)

### `medical_examples_corpus.py`
- Corpus de 49 exemples médicaux pour embedding similarity
- Structure: `{text, profile, expected_fields}`
- Utilisé par `nlu_hybrid.py` pour enrichissement

### `models.py`
- Modèle Pydantic `HeadacheCase` (30+ champs)
- Validation automatique des données
- Champs: démographie, profil temporel, symptômes, contextes, red flags

---

## Schéma de nommage proposé

Pour clarifier les rôles, renommage suggéré:

```
nlu.py          → nlu_base.py       (fonctions de base)
nlu_v2.py       → nlu_rules.py      (NLU basé sur règles)
nlu_hybrid.py   → nlu_hybrid.py     (conservé, nom clair)
```

**Rationale:**
- `nlu_base`: indique clairement les fonctions fondamentales
- `nlu_rules`: met en évidence l'approche par règles (vs IA)
- `nlu_hybrid`: déjà explicite (hybride règles + IA)

---

## Utilisation

### Import recommandé (utilisateur final):
```python
from headache_assistants.nlu_hybrid import HybridNLU

nlu = HybridNLU(
    confidence_threshold=0.7,
    use_embedding=True
)
case, metadata = nlu.parse(text)
```

### Import direct NLU v2 (règles uniquement):
```python
from headache_assistants.nlu_v2 import NLUv2

nlu = NLUv2()
case, metadata = nlu.parse(text)
```

### Import fonctions de base:
```python
from headache_assistants.nlu_base import (
    extract_age,
    extract_sex,
    detect_pattern
)
```

---

## Performance

| Couche | Temps moyen | Cas d'usage |
|--------|-------------|-------------|
| nlu_base | <1ms | Extraction simple (âge, sexe) |
| nlu_v2 (NLUv2) | ~10ms | Analyse complète par règles |
| nlu_hybrid (HybridNLU) | ~50ms | Analyse + enrichissement IA |

**Recommandation:** Utiliser `nlu_hybrid` par défaut pour robustesse maximale.

---

## Tests

### Test de la couche base:
```python
from headache_assistants.nlu_base import extract_age
assert extract_age("patient de 45 ans") == 45
```

### Test NLU v2:
```python
from headache_assistants.nlu_v2 import NLUv2
nlu = NLUv2()
case, meta = nlu.parse("femme 30 ans, céphalée brutale")
assert case.age == 30
assert case.profile == "brutal"
```

### Test NLU hybride:
```python
from headache_assistants.nlu_hybrid import HybridNLU
nlu = HybridNLU()
case, meta = nlu.parse("mal de tête très fort depuis ce matin")
assert case.profile in ["brutal", "acute"]
```

---

## Maintenance

### Ajouter un nouveau pattern:
→ Modifier `nlu_base.py` (si pattern générique)
→ Modifier `nlu_v2.py` (si pattern spécifique)

### Ajouter un nouveau symptôme:
→ Modifier `medical_vocabulary.py` (MedicalVocabulary)

### Améliorer l'embedding:
→ Ajouter exemples dans `medical_examples_corpus.py`

### Ajouter un champ au modèle:
→ Modifier `models.py` (HeadacheCase)
→ Ajouter extraction dans `nlu_v2.py`

---

## Historique

- **v1 (nlu.py):** NLU original basé sur regex simples
- **v2 (nlu_v2.py):** Ajout MedicalVocabulary + gestion négations
- **v3 (nlu_hybrid.py):** Architecture hybride règles + embedding
- **2025-12:** Ajout détection trimestre grossesse (pregnancy_utils)
