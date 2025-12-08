# Tests Automatisés - Chatbot Médical

## 📋 Vue d'ensemble

Suite de **76 tests automatisés** couvrant tous les aspects critiques du chatbot médical d'aide à la prescription d'imagerie.

### 🎯 Résultat : **100% RÉUSSITE** ✅

```
Total tests : 76
Réussis     : 76 (100%)
Échoués     : 0
Temps       : ~0.012s
```

## 🚀 Lancement rapide

```bash
# Exécuter tous les tests
./run_tests.sh

# Ou directement
python3 tests/test_chatbot.py
```

## 📊 Couverture des tests

### 1️⃣ **Tests Unitaires** (43 tests)

#### Analyse du texte médical (8 tests)
- ✅ Détection âge (enfant, adulte, personne âgée)
- ✅ Détection sexe (homme/femme)
- ✅ Détection grossesse et trimestre
- ✅ Détection fièvre
- ✅ Détection signes urgents (brutale, déficit neurologique)

#### Expansion des acronymes (4 tests)
- ✅ FID → fosse iliaque droite
- ✅ FIG → fosse iliaque gauche
- ✅ EP → embolie pulmonaire
- ✅ Robustesse générale

#### Matching fuzzy de symptômes (5 tests)
- ✅ Matching exact
- ✅ Qualificateurs critiques présents (aigu, chronique)
- ✅ Rejet si qualificateur absent
- ✅ Prévention des faux positifs

#### Filtrage questions redondantes (10 tests)
- ✅ Auto-réponse critères d'âge (≥18 ans, ≥65 ans)
- ✅ Filtrage questions pédiatriques pour adultes
- ✅ Filtrage questions techniques (GCS, NEXUS, etc.)
- ✅ Filtrage questions vagues (tumorale?, infection?)
- ✅ Filtrage questions hors contexte (ORL en neuro)
- ✅ Non-filtrage questions pertinentes

#### Intégrité des données JSON (4 tests)
- ✅ Validité syntaxe JSON (thorax, digestif, cephalees)
- ✅ Présence champs requis
- ✅ Absence entrées rachis dans cephalees.json
- ✅ Cohérence système (neuro/ORL, pas rachis)

#### Tests d'intégration (8 tests)
- ✅ Scénarios céphalées (adulte, âgé, urgences)
- ✅ Scénarios thorax (douleur aiguë vs chronique)
- ✅ Détection automatique urgences
- ✅ Workflow complet

#### Tests métier critiques (4 tests)
- ✅ Pas d'entrées rachis dans cephalees.json
- ✅ Pas de radiculalgie dans symptômes céphalées
- ✅ Pas d'IRM cervicale rachis mélangée avec neuro
- ✅ Uniquement entrées neuro/ORL dans cephalees

---

### 2️⃣ **Tests Scénarios Cliniques** (33 tests)

#### Céphalées (5 tests)
- ✅ Céphalée urgente avec fièvre → Urgence immédiate
- ✅ Céphalée brutale → Urgence sans imagerie
- ✅ Céphalée + déficit neurologique → Urgence
- ✅ Traumatisme crânien adulte → Scanner cérébral
- ✅ Enfant HTIC → IRM cérébrale prioritaire

#### Thorax (3 tests)
- ✅ Douleur thoracique aiguë → Imagerie appropriée
- ✅ Suspicion EP (acronyme) → Matching correct
- ✅ Pneumothorax → Radiographie 1ère intention

#### Digestif (4 tests)
- ✅ Douleur FID + fièvre → Imagerie abdo (appendicite)
- ✅ Douleur FIG → Imagerie abdo gauche
- ✅ Douleur épigastrique → Imagerie haute
- ✅ Traumatisme abdominal → Scanner si nécessaire

#### Grossesse (3 tests)
- ✅ Grossesse T1 (< 12 sem) → Bonus scoring +2.0
- ✅ Grossesse T2 (12-26 sem) → Bonus +1.5
- ✅ Grossesse T3 (> 26 sem) → Bonus +1.0

#### Populations spécifiques (3 tests)
- ✅ Nourrisson < 4 mois → Écho transfontanellaire
- ✅ Personne âgée ≥ 65 ans → Protocole adapté
- ✅ Enfant 8 ans → IRM privilégiée (pas radiation)

#### Contre-indications (3 tests)
- ✅ Pacemaker → Pas d'IRM
- ✅ Claustrophobie → Scanner préféré
- ✅ Patient > 60 ans → Créatinine avant injection

#### Acronymes médicaux (3 tests)
- ✅ FID → fosse iliaque droite
- ✅ EP → embolie pulmonaire
- ✅ Multiples acronymes simultanés

#### Edge Cases (5 tests)
- ✅ Âge limite 18 ans → Adulte
- ✅ Âge limite 65 ans → Personne âgée
- ✅ Grossesse limite 12 sem → T1/T2
- ✅ Texte vide → Pas de crash
- ✅ Texte non-médical → Robustesse

#### Radiation ionisante (4 tests)
- ✅ IRM → ionisant=false (100%)
- ✅ Scanner → ionisant=true (100%)
- ✅ Radiographie → ionisant=true (100%)
- ✅ Échographie → ionisant=false (100%)

## 📈 Résultats

```
Total : 76 tests
  • Tests unitaires : 43
  • Tests scénarios : 33

Ran 76 tests in 0.012s

OK - 100% RÉUSSITE ✅
```

## 📁 Fichiers de tests

```
tests/
├── test_chatbot.py              # 43 tests unitaires
├── test_scenarios_cliniques.py  # 33 tests scénarios
├── README.md                    # Ce fichier
└── RAPPORT_TESTS_SCENARIOS.md   # Rapport détaillé
```

## 🔍 Tests clés par fonctionnalité

### Qualificateurs critiques (aigu/chronique)
```python
# ✅ DOIT PASSER
"douleur thoracique aiguë" → match "douleur thoracique aiguë"

# ❌ DOIT ÉCHOUER  
"douleur thoracique" → match "douleur thoracique aiguë"
```

### Filtrage pédiatrique pour adultes
```python
# Patient 67 ans → auto-filtre
- "âge < 4 mois ?" → FILTRÉ
- "exploration craniosténose ?" → FILTRÉ
- "bombement fontanelle ?" → FILTRÉ
```

### Filtrage questions techniques
```python
# Filtrage automatique
- "GCS < 13 ?" → FILTRÉ
- "règles NEXUS négatives ?" → FILTRÉ
- "bilan préopératoire ?" → FILTRÉ
```

### Filtrage questions vagues
```python
# Questions trop vagues → filtrées
- "tumorale ?" → FILTRÉ
- "infection ?" → FILTRÉ
- "récentes/inhabituelles ?" → FILTRÉ
```

## 🛠️ Structure des tests

```
tests/
├── test_chatbot.py       # Suite complète de tests
└── __init__.py           # (optionnel)

run_tests.sh              # Script de lancement automatisé
```

## ⚙️ Configuration

Tests configurés pour :
- Python 3.11+
- RapidFuzz pour matching fuzzy
- JSON valide (thorax.json, digestif.json, cephalees.json)
- Encodage UTF-8

## 📝 Ajout de nouveaux tests

```python
class TestNouvelleFeature(unittest.TestCase):
    def test_ma_feature(self):
        """Description du test"""
        result = ma_fonction(input)
        self.assertEqual(result, expected)
```

## 🔧 Dépannage

### Test échoue : "import main"
→ Vérifier sys.path dans test_chatbot.py

### Test échoue : JSON invalide
→ Valider JSON avec `python3 -m json.tool data/FILE.json`

### Test échoue : Mauvais matching
→ Vérifier seuils FUZZY_THRESHOLD dans main.py

## ✅ Bonnes pratiques

1. **Lancer les tests après chaque modification**
   ```bash
   ./run_tests.sh
   ```

2. **Tests en continu pendant développement**
   ```bash
   watch -n 2 python3 tests/test_chatbot.py
   ```

3. **Tests avant commit Git**
   ```bash
   ./run_tests.sh && git commit
   ```

## 📊 Métriques de qualité

- **76 tests** automatisés (43 unitaires + 33 scénarios)
- **0.012s** temps d'exécution total
- **100%** taux de réussite
- **9 catégories** de tests scénarios
- **32 entrées** cephalees.json (neuro/ORL uniquement)
- **0 entrée** rachis dans cephalees.json ✅
- **100%** cohérence radiation (IRM non-ionisant, Scanner ionisant)

## 🎯 Objectifs atteints

✅ Validation syntaxe Python  
✅ Validation intégrité JSON  
✅ Tests unitaires fonctions critiques  
✅ Tests d'intégration workflows complets  
✅ Tests métier spécifiques (rachis supprimé)  
✅ Tests filtrage intelligent questions  
✅ Tests matching avec qualificateurs critiques  
✅ Tests robustesse NLP  

---

**Dernière mise à jour :** 27 novembre 2025  
**Version :** 1.0  
**Status :** ✅ Tous tests passent
