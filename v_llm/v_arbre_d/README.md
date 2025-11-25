# Assistant Médical - Arbre Décisionnel d'Imagerie

## Vue d'ensemble

Ce système d'aide à la décision médicale permet de guider la prescription d'examens d'imagerie pour trois domaines :
- **Céphalées** (logique codée en dur)
- **Thorax** (basé sur `data/thorax.json`)
- **Système digestif** (basé sur `data/digestif.json`)

## Utilisation

### Lancement
```bash
python3 source/main.py
```

### Sélection du système
Au démarrage, choisissez le système à évaluer :
```
1) Céphalées
2) Thorax
3) Système digestif
```

### Questionnaire interactif
- Entrez le texte libre décrivant le cas clinique
- Répondez aux questions avec `o` (oui) ou `n` (non)
- Utilisez la touche `←` (flèche gauche) pour revenir à la question précédente
- Le système pré-remplit automatiquement les réponses détectées dans le texte libre

### Recommandation
Le système :
1. Analyse les symptômes et le contexte patient (âge, sexe, grossesse)
2. Sélectionne l'examen d'imagerie le plus approprié
3. Affiche les contre-indications et précautions
4. Propose d'enregistrer le rapport et l'ordonnance

## Nouveautés (version 2.1)

### ✅ Questionnaire dirigé avec discrimination intelligente

**Problème résolu** : Plusieurs entrées JSON peuvent partager les mêmes symptômes mais avoir des indications différentes.

**Solution** : Le système pose maintenant des questions sur les `indications_positives` pour discriminer entre les options.

**Exemple concret** :
- Symptôme : "bruits respiratoires anormaux"
- 2 options possibles :
  1. Radiographie thoracique (1ère intention)
  2. Scanner thoracique (2e intention)
  
Le système pose automatiquement :
- "bilan initial des bruits respiratoires anormaux ?"
- "suspicion pneumopathie infectieuse ?"
- "clarification lésionnelle ?"
- "radiographie non contributive ?"

Selon les réponses → recommandation adaptée !

### ✅ Prise en compte des indications négatives

- Pénalité de score si une indication négative est présente
- Évite de recommander un examen contre-indiqué

### ✅ Questions basées sur `symptomes` ET `indications_positives`

- Phase 1 : Questions sur les symptômes
- Phase 2 (si ambiguïté) : Questions sur les indications
- Arrêt dès qu'une seule entrée domine

### ✅ Détection améliorée depuis texte libre

- Matching intelligent avec seuil de 50%
- "toux chronique" détecte "toux", "chronique", "toux chronique"
- "fièvre" (avec accent) détecté même si normalisé en "fievre"

## Nouveautés (version 2.0)

### ✅ Multi-systèmes
- Ajout des arbres décisionnels pour **thorax** et **digestif**
- Chargement dynamique depuis fichiers JSON
- Menu de sélection au démarrage

### ✅ Filtrage intelligent des questions
Les questions posées sont filtrées pour exclure :
- Noms d'examens techniques (scanner, IRM, CXR, etc.)
- Termes génériques (bilan, évaluation, recherche, etc.)
- Acronymes médicaux non pertinents (Wells, Genève, PERC, etc.)
- Résultats d'examens (anomalie CXR, radio non contributive, etc.)

**Exemple** : 
- ❌ Avant : 150+ questions incluant "CT thorax", "angioscanner", "bilan initial"
- ✅ Après : ~38-40 questions cliniques pertinentes uniquement

### ✅ Déduplication
Les symptômes redondants sont fusionnés :
- "toux" + "toux chronique" + "toux chronique >1 mois" → seuls les plus spécifiques sont gardés
- "suspicion corps étranger" + "suspicion CE" → dédupliqués

### ✅ Matching amélioré
Le système de correspondance (scoring) prend en compte :
- Symptômes et indications positives
- Population cible (enfant/adulte/personne âgée)
- Sexe et grossesse
- Bonus de score pour les correspondances de population

### ✅ Détection intelligente dans texte libre
- Analyse par mots-clés avec seuil de 60% de correspondance
- Ignore les mots courts (<3 lettres)
- Normalisation des accents et casse

### ✅ Affichage amélioré
- Synthèse avec labels originaux (plus lisibles que les clés normalisées)
- Recommandation détaillée incluant modalité et résumé
- Gestion des contre-indications (grossesse, ionisant, contraste)

## Structure des données JSON

Chaque entrée JSON contient :
- `id` : identifiant unique
- `systeme` : thorax / digestif / cardio / etc.
- `pathologie` : nom de la pathologie
- `modalite` : examen d'imagerie recommandé
- `resume` : description de l'indication
- `urgence_enum` : immédiate / rapide / standard
- `populations` : ["adulte", "enfant", "personne_agee", "femme", "enceinte"]
- `symptomes` : liste de symptômes cliniques
- `indications_positives` : indications pour cet examen
- `indications_negatives` : contre-indications
- `ionisant` : true/false
- `requires_contrast` : true/false/depends
- `contre_indications` : liste textuelle

## Fichiers du projet

```
v_arbre_d/
├── source/
│   └── main.py              # Code principal
├── data/
│   ├── thorax.json          # Arbre thorax (24 entrées)
│   ├── digestif.json        # Arbre digestif (32 entrées)
│   └── keywords.json        # (optionnel, non utilisé actuellement)
├── ordonnances/             # Ordonnances générées
├── reports/                 # Rapports générés
├── ORDONNANCE_README.md     # Documentation ordonnances
├── README.md                # Ce fichier
└── run.sh                   # Script de lancement (optionnel)
```

## Exemple d'utilisation

### Cas thorax
```
Choix : 2
Médecin : patiente 45 ans avec toux chronique et fièvre depuis 3 jours
Âge détecté : 45 ans
Sexe détecté : femme

Questions (pré-remplies automatiquement : fièvre, toux chronique)
...

RECOMMANDATION FINALE
radiographie thoracique de face (1ère intention) — Radio quasi systématique; 
passer au scanner si la radiographie ne répond pas à la question.
```

### Cas digestif
```
Choix : 3
Médecin : homme 60 ans douleur FID suspicion appendicite
Âge détecté : 60 ans
Sexe détecté : homme

Questions (pré-remplies : douleur FID)
...

RECOMMANDATION FINALE
échographie-Doppler abdominopelvienne — Recommandée en première intention.
Si non concluante, scanner abdominopelvien avec injection.
```

## Statistiques

- **Thorax** : 24 entrées JSON → 38 questions cliniques filtrées
- **Digestif** : 32 entrées JSON → 39 questions cliniques filtrées
- **Céphalées** : 8 questions codées manuellement

## Limitations connues

- Le matching est basé sur un score simple (nombre de symptômes correspondants)
- Pas de validation médicale formelle des recommandations
- Les ordonnances générées nécessitent validation par un médecin
- Certains acronymes médicaux peuvent encore apparaître (ex: BPCO, OAP)

## Améliorations futures possibles

- Pondération des symptômes par importance clinique
- Règles d'exclusion strictes (symptômes incompatibles)
- Export PDF des ordonnances
- Interface graphique (GUI)
- Base de données SQLite pour historique
- API REST pour intégration externe

## Important

⚠️ **Les ordonnances et recommandations générées doivent être validées par le médecin prescripteur avant utilisation.**

Ce système est une aide à la décision et ne remplace en aucun cas le jugement clinique médical.
