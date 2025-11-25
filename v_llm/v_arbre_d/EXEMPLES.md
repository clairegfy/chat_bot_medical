# Exemples d'utilisation

## Exemple 1 : Thorax - Patiente avec toux et fièvre

### Entrée
```
Choix : 2
Médecin : patiente 45 ans avec toux chronique et fièvre depuis 3 jours
```

### Questions posées (filtrées, ~38 au total)
- BPCO ? n
- bruits respiratoires anormaux ? n
- crépitants ? n
- détresse respiratoire ? n
- douleur thoracique aiguë ? n
- dyspnée aiguë ? n
- fièvre ? **o** *(pré-rempli automatiquement)*
- infections récidivantes ? n
- pneumopathie récidivante ? n
- toux chronique >1 mois ? **o** *(pré-rempli automatiquement)*
- etc.

### Sortie
```
SYNTHÈSE CLINIQUE
  Sexe : femme
  Âge : 45 ans
  Symptômes/Éléments identifiés :
    • fièvre
    • toux chronique >1 mois

RECOMMANDATION FINALE
radiographie thoracique de face (1ère intention) — Indiquée chez tout patient 
avec toux chronique (>1 mois). En cas d'anomalie radiographique, un scanner 
doit être réalisé.

Remarques complémentaires :
• Chez les femmes de moins de 50 ans, un test de grossesse est recommandé 
  avant tout examen radiologique.
• Chez les patients de plus de 60 ans ou ayant des antécédents rénaux, un 
  dosage de la créatinine est nécessaire avant injection de produit de contraste.
```

---

## Exemple 2 : Digestif - Homme avec douleur FID

### Entrée
```
Choix : 3
Médecin : homme 60 ans douleur fosse iliaque droite depuis ce matin fièvre 38.5
```

### Questions posées (filtrées, ~39 au total)
- abcès hépatique ? n
- cholécystite ? n
- constipation ? n
- douleur FID ? **o** *(pré-rempli)*
- douleur épigastrique ? n
- fièvre ? **o** *(pré-rempli)*
- hépatite aiguë ? n
- infection digestive ? o
- mal au ventre ? o
- syndrome inflammatoire ? o
- etc.

### Sortie
```
SYNTHÈSE CLINIQUE
  Sexe : homme
  Âge : 60 ans
  Symptômes/Éléments identifiés :
    • douleur FID
    • fièvre
    • infection digestive
    • mal au ventre
    • syndrome inflammatoire

RECOMMANDATION FINALE
échographie-Doppler abdominopelvienne — Chez un adulte présentant une douleur 
de la fosse iliaque droite évoquant une appendicite, l'échographie-Doppler 
abdominopelvienne est recommandée en première intention. Si non concluante ou 
chez le patient âgé, un scanner abdominopelvien avec injection est indiqué.

Remarques complémentaires :
• Chez les patients de plus de 60 ans ou ayant des antécédents rénaux, un 
  dosage de la créatinine est nécessaire avant injection de produit de contraste.
• En cas d'allergie, signaler toute réaction préalable.

EXAMENS BIOLOGIQUES À PRÉVOIR :

☐ Créatininémie + calcul de la clairance (DFG)
    (Avant injection de produit de contraste)
```

---

## Exemple 3 : Thorax - Enfant avec dyspnée

### Entrée
```
Choix : 2
Médecin : enfant 8 ans dyspnée aiguë suspicion corps étranger
```

### Questions posées
- BPCO ? n
- détresse respiratoire ? o
- douleur respiro-dépendante ? n
- dyspnée aiguë ? **o** *(pré-rempli)*
- dyspnée expiratoire aiguë ? o
- fièvre ? n
- signes de gravité ? o
- suspicion corps étranger ? **o** *(pré-rempli)*
- syndrome de pénétration ? o
- toux paroxystique ? o
- etc.

### Sortie
```
SYNTHÈSE CLINIQUE
  Sexe : (non détecté)
  Âge : 8 ans
  Symptômes/Éléments identifiés :
    • détresse respiratoire
    • dyspnée aiguë
    • dyspnée expiratoire aiguë
    • signes de gravité
    • suspicion corps étranger
    • syndrome de pénétration
    • toux paroxystique

RECOMMANDATION FINALE
radiographie thoracique face inspiration/expiration (1ère intention) — En 
dyspnée expiratoire aiguë, radio de face indiquée seulement si suspicion de 
corps étranger, fièvre associée ou signes de gravité pour rechercher 
atélectasie, pneumothorax ou pneumomédiastin.
```

---

## Exemple 4 : Digestif - Femme enceinte avec douleur abdominale

### Entrée
```
Choix : 3
Médecin : femme 28 ans enceinte 20 semaines douleur FID
```

### Questions posées
- douleur FID ? **o** *(pré-rempli)*
- grossesse ? **o** *(pré-rempli)*
- fièvre ? n
- mal au ventre ? o
- etc.

Puis :
```
Durée de la grossesse :
Nombre de semaines (laisser vide si inconnu) : 20
```

### Sortie
```
SYNTHÈSE CLINIQUE
  Sexe : femme
  Âge : 28 ans
  Grossesse : 20 semaines
  Symptômes/Éléments identifiés :
    • douleur FID
    • grossesse
    • mal au ventre

RECOMMANDATION FINALE
IRM abdominopelvienne — Chez une femme enceinte présentant une douleur 
abdominale droite évoquant une appendicite, l'IRM abdominopelvienne est 
recommandée. L'échographie peut être réalisée en première intention, mais 
le scanner est contre-indiqué.

Remarques complémentaires :
• Grossesse confirmée (20 SA) : précautions d'irradiation à respecter.
• En cas d'allergie, signaler toute réaction préalable.
```

---

## Points clés

1. **Pré-remplissage automatique** : Les symptômes mentionnés dans le texte libre sont automatiquement détectés
2. **Questions filtrées** : Seules les questions cliniques pertinentes sont posées (~38-40 au lieu de 150+)
3. **Retour arrière** : Possibilité de revenir à la question précédente avec `←`
4. **Contextualisation** : Prise en compte de l'âge, sexe, grossesse pour affiner la recommandation
5. **Contre-indications** : Rappels automatiques des précautions (grossesse, créatinine, allergies)
