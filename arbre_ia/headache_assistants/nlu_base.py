"""
Base NLU Module - Clinical Pattern Recognition for Headache Assessment.

This module provides rule-based Natural Language Understanding (NLU) for extracting
structured clinical data from free-text medical descriptions of headache cases.

Clinical Architecture
---------------------
The NLU system follows a hierarchical approach aligned with emergency medicine
triage protocols:

1. **Red Flags Detection (Highest Priority)**
   - Thunderclap onset → HSA until proven otherwise (SAUCI-FVS mnemonic)
   - Meningeal signs → Meningitis/encephalitis pathway
   - HTIC pattern → Mass lesion/hydrocephalus workup
   - Neurological deficit → Stroke/structural lesion

2. **Risk Context Identification**
   - Pregnancy/postpartum → Eclampsia, PRES, CVT risk
   - Immunosuppression → Opportunistic infections
   - Recent LP/epidural → Post-dural puncture headache
   - Trauma history → Subdural/epidural hematoma

3. **Clinical Profiling**
   - Temporal profile (acute/subacute/chronic)
   - Headache type (migraine-like, tension-like, HTIC-like)
   - Intensity scoring (EVA/numeric scale)

Pattern Dictionaries
--------------------
Each dictionary maps clinical concepts to regex patterns covering:
- Standard French medical terminology
- Common medical abbreviations (RDN, HTIC, AVP, etc.)
- Patient vernacular expressions
- Numeric values with units (temperature, pain scores)

Clinical Validation
-------------------
Patterns are designed with high sensitivity for red flags to avoid
false negatives in emergency scenarios. Specificity is optimized
through negation handling (checking False patterns before True).

References
----------
- SAUCI-FVS mnemonic for thunderclap headache workup
- IHS Classification (ICHD-3) for headache profiling
- French emergency medicine guidelines (SFMU)

Example Usage
-------------
>>> from headache_assistants.nlu_base import parse_free_text_to_case
>>> case, metadata = parse_free_text_to_case("H 45a, céphalée brutale fébrile avec RDN")
>>> print(case.onset)  # thunderclap
>>> print(case.fever)  # True
>>> print(case.meningeal_signs)  # True

Author: Medical NLU Team
Version: 2.0 (Clinical-grade refactoring)
"""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .models import HeadacheCase


# ============================================================================
# DICTIONNAIRES DE PATTERNS - Basés sur headache_rules.txt
# ============================================================================
#
# CLINICAL NOTE: Pattern dictionaries follow emergency medicine priorities.
# For boolean patterns (True/False keys), negation patterns (False) are
# always checked BEFORE affirmation patterns (True) to prevent false positives.
# Example: "pas de fièvre" should return False, not True.
#
# SENSITIVITY vs SPECIFICITY TRADE-OFF:
# - Red flags (fever, meningeal signs, HTIC): HIGH SENSITIVITY prioritized
# - Clinical profiling (headache type): BALANCED approach
# - Demographics (age, sex): HIGH SPECIFICITY for accuracy
# ============================================================================

# -----------------------------------------------------------------------------
# ONSET PATTERNS - Mode de début de la céphalée
# -----------------------------------------------------------------------------
# Clinical significance:
# - thunderclap: HSA (hémorragie sous-arachnoïdienne) until proven otherwise
#   Also: SVCR (syndrome vasoconstriction cérébrale réversible), CVT (thrombose veineuse)
# - progressive: Mass lesion, HTIC, infection
# - chronic: Primary headache disorders, medication overuse
# -----------------------------------------------------------------------------
ONSET_PATTERNS = {
    "thunderclap": [
        r"coup de tonnerre",
        r"brutale?",
        r"soudaine?",
        r"instantanée?",
        r"thunderclap",
        r"en quelques secondes",
        r"d'emblée maximale?",
        r"violence maximale d'emblée",
        r"maximale? d'emblée",
        r"installation brutale",
        r"d'installation brutale",
        r"début (?:brutal|soudain)",
        r"ictus céphalalgique",
        r"HSA",
        # Langage familier
        r"d'un coup",
        r"d'un seul coup",
        r"tout d'un coup",
        r"commencé d'un coup",
        r"du jour au lendemain",
        r"jamais eu aussi mal",
        r"jamais ressenti",
        r"pire (?:douleur|mal|céphalée) de (?:ma|sa) vie"
    ],
    "progressive": [
        r"progressive?",
        r"progressivement",
        r"qui augmente",
        r"en quelques heures",
        r"en quelques jours",
        r"installation progressive",
        r"progressivement installée?",
        r"depuis \d+ heures?"
    ],
    "chronic": [
        r"chronique",
        r"depuis des mois",
        r"depuis des années",
        r"permanente?",
        r"quotidienne?",
        r"tous les jours"
    ]
}

# -----------------------------------------------------------------------------
# PROFILE PATTERNS - Profil temporel de la céphalée
# -----------------------------------------------------------------------------
# Clinical thresholds (IHS criteria):
# - acute: < 7 days (urgent workup needed)
# - subacute: 7 days - 3 months (intermediate concern)
# - chronic: > 3 months (primary headache more likely, but exclude secondary)
#
# IMPORTANT: acute + sudden onset = immediate imaging (CT ± LP)
# -----------------------------------------------------------------------------
PROFILE_PATTERNS = {
    "acute": [
        r"aigu[eë]?",
        r"depuis (?:quelques )?heures?",
        r"depuis \d+\s*heures?",  # "depuis 2 heures", "depuis 12h"
        r"dep\s+\d+\s*h",  # "dep 48h", "dep 24h"
        r"depuis (?:quelques )?jours?",
        r"depuis [1-6]\s*(?:jours?|j)\b",  # "depuis 2 jours", "depuis 2j"
        r"dep\s+[1-6]\s*j",  # "dep 2j", "dep 3j"
        r"il y a [1-6]\s*(?:jours?|j)",  # "il y a 3 jours"
        r"il y a \d+\s*(?:heures?|h)",  # "il y a 2h"
        r"j-\d+",  # "J-1", "J-2"
        r"récente?",
        r"soudaine?",
        # Durées implicites
        r"(?:depuis )?ce matin",
        r"(?:depuis )?cet après-midi",
        r"(?:depuis )?ce soir",
        r"(?:depuis )?aujourd'hui",
        r"(?:depuis )?hier",
        r"(?:depuis )?la nuit dernière",
        r"(?:depuis )?cette nuit"
    ],
    "subacute": [
        r"subaigu[eë]?",
        r"depuis (?:quelques )?semaines?",
        r"depuis \d+\s*sem(?:aines?)?",  # "depuis 2 sem", "depuis 2 semaines"
        r"dep\s+\d+\s*sem",  # "dep 2 sem"
        r"depuis [1-2]\s*mois",
        r"depuis (?:[7-9]|[1-9]\d)\s*(?:jours?|j)\b"  # "depuis 7-99 jours", "depuis 10j"
    ],
    "chronic": [
        r"chronique",
        r"depuis (?:plusieurs|des) (?:mois|années?|ans)",
        r"de longue date",
        r"permanente?",
        r"céphalée chronique quotidienne",
        r"depuis (?:\d+|de nombreux) mois",
        r"depuis (?:\d+|de nombreuses?) (?:années?|ans)",
        r"depuis \d+\s*ans?",  # "depuis 15 ans", "depuis 10 an"
        r">3\s*mois",  # >3mois (notation médicale)
        r"quotid(?:iennes?)?",  # quotid (abréviation)
        r"(?:tous les|chaque) jours?",
        r"cch (?:chroniques?|quotid)",  # CCH chroniques
        r"fond (?:douloureux|migraineux)",  # Fond douloureux permanent
        r"migraineuse? (?:connue?|depuis)",  # "migraineuse connue", "migraineux depuis"
        r"(?:migraines?|céphalées?) (?:connues?|habituelles?)"  # "migraines connues"
    ]
}

# -----------------------------------------------------------------------------
# INTENSITY PATTERNS - Intensité de la douleur (EVA 0-10)
# -----------------------------------------------------------------------------
# Clinical mapping:
# - maximum (10/10): "pire douleur de ma vie" → highly suggestive of HSA
# - severe (8-9/10): Requires urgent evaluation
# - moderate (5-7/10): Standard workup
# - mild (1-4/10): Lower acuity, but don't dismiss new-onset
#
# NOTE: EVA maximum + thunderclap onset = HSA until proven otherwise
# -----------------------------------------------------------------------------
INTENSITY_PATTERNS = {
    "maximum": [
        r"maximale? (?:et |, )?insupportable",
        r"insupportable (?:et |, )?maximale?",
        r"atroce (?:et |, )?insupportable",
        r"insupportable (?:et |, )?atroce",
        r"brutale? (?:et |, )?explosive?",
        r"explosive? (?:et |, )?brutale?",
        r"intensité maximale",
        r"douleur maximale",
        r"10/10",
        r"eva\s*(?:=\s*)?10",  # EVA 10, EVA= 10
        r"en\s*(?:=\s*)?10",  # EN 10, EN= 10
        r"pire (?:douleur|mal|céphalée) de (?:ma|sa) vie",
        r"jamais (?:eu|ressenti) aussi mal",
        r"douleur (?:la plus )?intense de (?:ma|sa) vie",
        r"épouvantable"
    ],
    "severe": [
        r"intense",
        r"sévère",
        r"atroce",
        r"insupportable",  # Seul = 10 dans extract_intensity_score
        r"terrible",  # = 9
        r"maximale?",
        r"9/10",
        r"eva\s*(?:=\s*)?9",  # EVA 9, EVA= 9
        r"en\s*(?:=\s*)?9",  # EN 9
        r"eva\s*(?:=\s*)?[89]",  # EVA 8-9
        r"en\s*(?:=\s*)?[89]",  # EN 8-9
        r"horrible"
    ],
    "moderate": [
        r"modérée?",  # = 5 dans extract_intensity_score
        r"moyenne",
        r"gênante?",
        r"[5-8]/10",
        r"eva\s*(?:=\s*)?[5-7]",  # EVA 5-7
        r"en\s*(?:=\s*)?[5-7]"  # EN 5-7
    ],
    "mild": [
        r"légère?",
        r"faible",
        r"peu intense",
        r"[1-4]/10",
        r"eva\s*(?:=\s*)?[1-4]",  # EVA 1-4
        r"en\s*(?:=\s*)?[1-4]"  # EN 1-4
    ]
}

# -----------------------------------------------------------------------------
# FEVER PATTERNS - Fièvre (RED FLAG)
# -----------------------------------------------------------------------------
# Clinical significance:
# - Fever + headache = meningitis/encephalitis until proven otherwise
# - Threshold: ≥38.0°C (validated numerically when available)
#
# Common abbreviations:
# - féb: fébrile
# - apyr: apyrétique (no fever)
# - T° or T: température
#
# PRIORITY: Check False patterns (apyrétique, sans fièvre) BEFORE True
# -----------------------------------------------------------------------------
FEVER_PATTERNS = {
    True: [
        r"fièvre",
        r"fébrile",
        r"féb",  # Abréviation
        r"température",
        r"temp(?:érature)?",
        r"\bt°?\s*\d+",  # T 39, T° 39 (avec word boundary)
        r"\bt=\s*\d+",  # T=39
        r"\d+°\d+",  # 38°5
        r"(?:38|39|40)(?:°|°C)\b",  # 38°, 38°C (requires degree symbol, avoids age like "40a")
        r"\d+\.\d+\s*°c?",  # 38.5°c, 38.5°C
        r"féb(?:rile)?\s*(?:à|=)\s*\d+",  # féb à 39
        r"hyperthermie",
        r"avec de la fièvre"
    ],
    False: [
        r"sans fièvre",
        r"apyrétique",
        r"apyr",  # Abréviation
        r"pas de fièvre",
        r"afébril",
        r"afébrile"
    ]
}

# -----------------------------------------------------------------------------
# MENINGEAL SIGNS PATTERNS - Syndrome méningé (CRITICAL RED FLAG)
# -----------------------------------------------------------------------------
# Clinical significance:
# - Meningeal signs = LP mandatory (unless contraindicated)
# - Classic triad: headache + fever + neck stiffness
#
# Clinical signs detected:
# - RDN (Raideur De Nuque): Neck stiffness
# - Kernig sign: Hip/knee flexion resistance
# - Brudzinski sign: Neck flexion → hip flexion
# - "Chien de fusil": Fetal position (meningeal irritation)
#
# CRITICAL: High sensitivity prioritized - never miss meningitis
# -----------------------------------------------------------------------------
MENINGEAL_SIGNS_PATTERNS = {
    True: [
        r"syndrome méningé",
        r"sdm méningé",  # Syndrome méningé (abréviation)
        r"sg(?:s)? méningés?",  # Signes méningés
        r"raideur(?: de(?: la)?)? nuque",
        r"rdn",  # Raideur De Nuque
        r"rdn\s*\+",  # RDN +, RDN ++
        r"raideur méningée",
        r"signe de kernig",
        r"kernig\s*\+",  # Kernig +
        r"kernig pos(?:itif)?",  # Kernig positif, Kernig pos
        r"signe de brudzinski",
        r"brudzinski\s*\+",  # Brudzinski +
        r"brudzinski pos(?:itif)?",  # Brudzinski pos
        r"kernig positif",
        r"brudzinski positif",
        r"chien de fusil",
        r"nuque raide",
        r"méningé",
        # Langage familier
        r"ne peut pas (?:bouger|tourner|plier) (?:le|la) (?:cou|nuque)",
        r"impossible de (?:bouger|plier|tourner) (?:le|la|sa) (?:tête|nuque|cou)",
        r"cou (?:bloqué|raide)",
        r"nuque (?:douloureuse|tendue|bloquée)"
    ],
    False: [
        r"sans (?:signe )?méningé",
        r"pas de raideur",
        r"pas de rdn",  # "pas de RDN"
        r"pas de kernig",  # "pas de Kernig"
        r"pas de brudzinski",  # "pas de Brudzinski"
        r"nuque souple",
        r"rdn\s*-",  # RDN -, RDN nég
        r"kernig\s*-",  # Kernig -
        r"kernig nég(?:atif)?",  # Kernig négatif, Kernig nég
        r"brudzinski\s*-",  # Brudzinski -
        r"brudzinski nég(?:atif)?"  # Brudzinski négatif
    ]
}

# -----------------------------------------------------------------------------
# HTIC PATTERNS - Hypertension Intracrânienne (RED FLAG)
# -----------------------------------------------------------------------------
# Clinical significance:
# - HTIC suggests mass lesion, hydrocephalus, or venous thrombosis
# - Classic features: morning headache, vomiting, papilledema
#
# Key indicators:
# - Vomissements en jet: Projectile vomiting (cardinal sign)
# - Céphalée matutinale: Morning headache (ICP rises during sleep)
# - Aggravation par toux/effort: Increased with Valsalva
# - Œdème papillaire: Papilledema (requires fundoscopy)
#
# IMPORTANT: Scotomes/aura alone = migraine, NOT HTIC (anti-pattern)
# Confidence threshold applied to avoid false positives
# -----------------------------------------------------------------------------
HTIC_PATTERNS = {
    False: [
        r"scotomes?",  # Scotomes = aura migraineuse, pas HTIC
        r"aura",
        r"(?:pas|sans) (?:de |d')?(?:signes? )?htic",
        r"htic (?:négatif|absent|écart)"
    ],
    True: [
        r"hypertension intracrânienne",
        r"htic",
        r"sdm htic",  # Syndrome HTIC
        r"signes? (?:d')?htic",
        r"céphalée matutinale",
        r"céph(?:alée)?.{0,10}matin",  # Céphalée ... matin
        r"vomissements? en jet",
        r"vom(?:issements)? en jet",  # Abréviation
        r"aggrav(?:ée?|ation) (?:par (?:la |l')?)?(?:toux|effort)",
        r"œdème papillaire",
        r"op\+\+",  # Œdème Papillaire ++ (abrégé avec intensité)
        r"flou visuel",
        r"éclipses? visuelles?",
        # Formulations variées
        r"(?:plus )?forte? le matin",
        r"pire le matin",
        r"aggravée? (?:le|au) matin",
        r"aggravée? au réveil",
        r"douleur matutinale"
    ]
}

# Patterns pour traumatisme crânien récent
TRAUMA_PATTERNS = {
    False: [
        r"pas de (?:trauma|traumatisme|choc|chute)",
        r"sans (?:trauma|traumatisme|choc|chute)",
        r"nie (?:tout )?(?:trauma|traumatisme|choc|chute)"
    ],
    True: [
        r"tcc",  # Traumatisme Crânio-Cérébral
        r"traumatisme cr[aâ]nien",
        r"trauma cr[aâ]nien",
        r"trauma crânio-cérébral",
        r"avp",  # Accident Voie Publique
        r"accident de (?:la )?voie publique",
        r"chute",
        r"choc (?:à la |au )?(?:tête|crâne)",
        r"pdc",  # Perte De Connaissance
        r"perte de connaissance",
        r"(?:coup|choc) (?:à|sur) la tête",
        r"(?:depuis|dep|j-|j )(?:traumatisme|trauma|chute|avp)",
        r"contexte (?:de )?trauma"
    ]
}

# Patterns pour traumatisme crânien récent
TRAUMA_PATTERNS = {
    False: [
        r"pas de (?:trauma|traumatisme|choc|chute)",
        r"sans (?:trauma|traumatisme|choc|chute)",
        r"nie (?:tout )?(?:trauma|traumatisme|choc|chute)"
    ],
    True: [
        r"tcc",  # Traumatisme Crânio-Cérébral
        r"traumatisme crânien",
        r"trauma crânien",
        r"avp",  # Accident Voie Publique
        r"accident (?:de )?(?:la )?voie publique",
        r"chute",
        r"choc (?:à la |au )?(?:tête|crâne)",
        r"pdc",  # Perte De Connaissance
        r"perte de connaissance",
        r"(?:coup|choc) (?:à|sur) la tête",
        r"j-\d+",  # J-3, J-15
        r"contexte (?:de )?trauma"
    ]
}

# -----------------------------------------------------------------------------
# SEIZURE PATTERNS - Crises d'épilepsie (RED FLAG)
# -----------------------------------------------------------------------------
# Clinical significance:
# - New-onset seizure + headache → structural lesion, hemorrhage, infection
# - Post-ictal headache is common, but exclude secondary causes
#
# Terms detected:
# - CGT: Crise Généralisée Tonico-Clonique
# - Crise comitiale: Medical term for epileptic seizure
# - TC: Tonico-Clonique
#
# IMPORTANT: "crise" alone is ambiguous - context needed
# -----------------------------------------------------------------------------
SEIZURE_PATTERNS = {
    False: [
        r"pas de (?:crise|convulsion)",
        r"sans (?:crise|convulsion)",
        r"nie (?:toute )?(?:crise|convulsion)"
    ],
    True: [
        # Patterns spécifiques en premier (avant les génériques)
        r"cgt",  # Crise Généralisée Tonico-Clonique
        r"crise tc",  # Crise Tonico-Clonique (abrégé)
        r"crise comitiale",  # Terme médical pour crise d'épilepsie
        r"crise d'épilepsie",
        r"crise (?:généralisée )?(?:tonico-clonique|tonique|clonique)",
        r"crises? épileptiques?",
        r"crise convulsive",
        r"crises? convulsives?",
        r"crise (?:ce matin|hier|ce soir)",  # Crise avec temporalité
        r"mouvements? anormaux",
        r"secousses?",
        r"perte (?:de )?connaissance.{0,20}secousses",  # Perte connaissance + secousses
        # Patterns génériques
        r"convulsions?",
        r"épilepsie",
        r"a convulsé",
        r"fait une crise",
        r"suivie? d'une crise",
        r"puis convulsions?",
        r"avec convulsions?",
        r"a fait une crise"
    ]
}

# -----------------------------------------------------------------------------
# NEURO DEFICIT PATTERNS - Déficit neurologique (CRITICAL RED FLAG)
# -----------------------------------------------------------------------------
# Clinical significance:
# - Focal deficit + headache → stroke, mass lesion, abscess
# - New deficit = URGENT imaging (CT then MRI if needed)
#
# Deficit types detected:
# - Motor: hemiparesis, hemiplegia, PF (facial paralysis)
# - Sensory: DSM (déficit sensitivo-moteur), paresthesias
# - Language: aphasia, dysarthria
# - Visual: diplopia, hemianopsia, visual field defects
# - Consciousness: confusion, GCS alterations
#
# IMPORTANT: Scotomes/visual aura are NOT deficits (migraine aura)
# This distinction is clinically critical to avoid over-investigation
# -----------------------------------------------------------------------------
NEURO_DEFICIT_PATTERNS = {
    False: [
        r"pas de déficit",
        r"sans déficit",
        r"aucun déficit",
        r"pas de trouble (?:neurologique|moteur|sensitif)",
        r"sans trouble (?:neurologique|moteur|sensitif)",
        r"examen neurologique normal"
        # Note: scotome/aura RETIRÉS - peuvent coexister avec déficit réel (migraine compliquée)
    ],
    True: [
        r"déficit",
        r"dsm",  # Déficit Sensitivomoteur
        r"hémiparésie",
        r"hémipar\s*[dg]",  # hémipar D, hémipar G
        r"hémipar\s+[dg]\s+transitoire",  # hémipar G transitoire
        r"hémiplégie",
        r"aphasie",
        r"trouble du langage",
        r"hémianopsie",
        r"parésie",
        r"pf",  # Paralysie Faciale
        r"paralysie faciale",
        r"diplopie",  # Vision double
        r"vision double",
        r"flou visuel",
        # r"scotomes?" RETIRÉ - scotomes = aura migraineuse, pas déficit
        r"confusion",
        r"désorientation",
        r"troubles? mnésiques?",  # Troubles de la mémoire
        r"faiblesse mb",  # Faiblesse membre
        r"faiblesse membre",
        r"altération (?:de (?:la|l'))?conscience",
        r"glasgow",  # Score de Glasgow
        r"gcs",  # Glasgow Coma Scale
        r"faiblesse (?:d')?un (?:bras|membre)",
        r"ne peut plus bouger",
        # Symptômes spécifiques
        r"faiblesse (?:du|de la|des|d'un) (?:bras|jambe|membre)",
        r"faiblesse bras",
        r"faiblesse jambe",
        r"ne peut (?:plus )?(?:bouger|lever) (?:le|la|son|sa)",
        r"difficultés? (?:à|pour) parler",
        r"troubles? de (?:la )?parole",
        r"troubles? du langage",
        r"vision (?:floue|trouble|double)",
        r"perte de (?:la )?vision",
        r"troubles? visuels?",
        r"hémi(?:parésie|plégie)",
        r"paralysie"
    ]
}

# -----------------------------------------------------------------------------
# PREGNANCY/POSTPARTUM PATTERNS - Contexte obstétrical (HIGH RISK)
# -----------------------------------------------------------------------------
# Clinical significance:
# - Pregnancy headache: eclampsia, PRES, CVT must be excluded
# - Postpartum: CVT peak incidence in first 2 weeks
# - Epidural/spinal → post-dural puncture headache
#
# Terms detected:
# - G1P0, G2P1: Gravidity/Parity notation
# - SA: Semaines d'Aménorrhée (weeks of amenorrhea)
# - T1/T2/T3: Trimester
# - Post-partum: Up to 6 weeks after delivery
#
# CRITICAL: Any new severe headache in pregnancy/postpartum = emergency
# -----------------------------------------------------------------------------
PREGNANCY_POSTPARTUM_PATTERNS = {
    True: [
        r"enceinte",
        r"grossesse",
        r"gestante?",
        r"en gestation",
        r"femme enceinte",
        r"patiente enceinte",
        r"femme gestante",
        r"patiente gestante",
        r"patiente en gestation",
        r"g\d+p\d+",  # g1p0, g2p1, etc. (Grossesse/Parité)
        r"\d+\s*sa",  # 8 sa, 12sa (Semaines d'Aménorrhée)
        r"gravidique",  # Ex: céphalée gravidique
        r"t[123]",  # t1, t2, t3 (trimestres)
        r"(?:1er|2ème|3ème) trimestre",
        r"post[- ]partum",
        r"accouchement",
        r"a accouché",
        r"vient d'accoucher",
        r"J[0-9]+\s*(?:post[- ]partum)?",  # J5 post-partum
        # Formulations variées
        r"accouch(?:é|ée|ement) (?:il y a|depuis)",
        r"(?:jeune )?mère",
        r"suite à (?:un )?accouchement",
        r"après (?:l')?accouchement",
        r"période (?:du|de) post[- ]partum"
    ]
}

TRAUMA_PATTERNS = {
    False: [
        r"pas de traumatisme",
        r"sans traumatisme",
        r"aucun traumatisme",
        r"pas de choc",
        r"sans choc",
        r"nie (?:tout )?traumatisme",
        r"sans trauma\b",  # "sans trauma" (abréviation)
        r"nie trauma\b"  # "nie trauma" (abréviation)
    ],
    True: [
        r"traumatisme",
        r"choc (?:à|sur) la tête",
        r"coup (?:à|sur) la tête",
        r"chute",
        r"accident",
        r"avp",  # Accident Voie Publique
        r"accident (?:de (?:la )?)?voie publique",
        r"contusion (?:crânienne|cérébrale)",
        r"choc (?:à la |au |sur le |)(?:crâne|tête)",
        r"coup (?:à la |au |sur le |)(?:crâne|tête)",
        r"trauma crânien",
        r"trauma cérébral",
        r"j-?\d+",  # j-1, j-2, j3, etc.
        # Acronymes médicaux (en minuscules car text_lower)
        r"tce",
        r"tcc",  # Traumatisme Cranio-Cérébral
        r"traumatisme (?:crânien|cranio|cérébral)"
    ]
}

# Patterns pour ponction lombaire ou péridurale récente (<2 semaines)
RECENT_PL_OR_PERIDURAL_PATTERNS = {
    False: [
        r"pas de (?:ponction|pl|péridurale)",
        r"sans (?:ponction|pl|péridurale)",
        r"nie (?:ponction|pl|péridurale)"
    ],
    True: [
        r"ponction lombaire",
        r"pl\s+(?:il y a|depuis|j-?\d+)",  # PL il y a 3j, PL depuis, PL J-2
        r"pl\s+récente?",
        r"après pl",
        r"post[- ]pl",
        r"suite à (?:une )?pl",
        r"péridurale?\s+(?:il y a|depuis|récente?)",
        r"anesthésie péridurale",
        r"après (?:la )?péridurale",
        r"post[- ]péridurale",
        r"rachianesthésie",
        r"rachi\s+(?:il y a|depuis)",
        r"ponction\s+(?:il y a|depuis)",
        r"après (?:la )?ponction",
        # Formulations avec durée
        r"pl\s+il y a\s+\d+\s*j",  # PL il y a 3j
        r"pl\s+j-?\d+",  # PL J-3, PL J3
        r"péridurale\s+il y a\s+\d+\s*j",
        r"ponction\s+il y a\s+\d+\s*j",
        # Nouvelles formulations
        r"pl\s+faite",  # PL faite il y a...
        r"depuis\s+(?:la\s+)?pl",  # depuis PL, depuis la PL
        r"depuis\s+(?:la\s+)?ponction",  # depuis ponction
        r"\bpl\b.*\bil y a\b",  # PL ... il y a (plus flexible)
        # Contexte clinique typique
        r"céphalée.*(?:position debout|orthostatique)",
        r"amélioration (?:en )?décubitus",
        r"am[ée]lioration.*d[ée]cubitus",  # sans accent
        r"céphalée positionnelle"
    ]
}

# -----------------------------------------------------------------------------
# IMMUNOSUPPRESSION PATTERNS - Immunodépression (HIGH RISK)
# -----------------------------------------------------------------------------
# Clinical significance:
# - Opportunistic CNS infections (toxoplasmosis, cryptococcus, PML)
# - Atypical presentations of common infections
# - Malignancy-related (brain metastases, carcinomatous meningitis)
#
# Risk factors detected:
# - VIH/SIDA: AIDS with low CD4 count
# - Cancer + chemotherapy: Immunosuppressive
# - Organ transplant + immunosuppressants
# - Corticotherapy: Long-term steroids
#
# CLINICAL: Lower threshold for LP and advanced imaging
# -----------------------------------------------------------------------------
IMMUNOSUPPRESSION_PATTERNS = {
    True: [
        r"immunodéprim(?:é|ée?|és)",
        r"vih",
        r"sida",
        r"chimiothérapie",
        r"corticoïde",
        r"corticothérapie",
        r"immunosuppresseur",
        r"greffe",
        r"greffé(?:e)?",  # Patient greffé
        r"cd4",  # Taux de CD4 (VIH)
        r"k\s+(?:poumon|sein|colon|prostate|ovaire)",  # k = cancer
        r"cancer",
        r"ttt immunosup",  # Traitement immunosuppresseur
        r"cortico",  # Corticothérapie (abrégé)
        # Variantes (en minuscules car text_lower)
        r"vih\+",
        r"vih positif",
        r"séropositif",
        r"sous chimiothérapie",
        r"sous corticothérapie",
        r"corticothérapie au long cours",
        r"chimio"
    ]
}

# -----------------------------------------------------------------------------
# HEADACHE PROFILE PATTERNS - Profil clinique de la céphalée
# -----------------------------------------------------------------------------
# Clinical significance:
# - Helps differentiate primary headache types
# - Guides symptomatic treatment decisions
#
# Profile types:
# - migraine_like: Unilateral, pulsatile, photo/phonophobia, N/V, aura
# - tension_like: Bilateral, pressure/band-like, no N/V
# - htic_like: Morning worse, projectile vomiting, positional
#
# NOTE: Profile is for CHARACTERIZATION, not for excluding secondary causes
# Red flags take precedence regardless of profile
# -----------------------------------------------------------------------------
HEADACHE_PROFILE_PATTERNS = {
    "migraine_like": [
        r"migraine",
        r"unilatéral(?:e)?",
        r"hémicrân(?:ie|ien)",
        r"pulsatile",
        r"battante?",
        r"lancinante?",  # Synonyme médical français
        r"photophobie",
        r"phonophobie",
        r"photo\+",  # photo+ (notation médicale)
        r"phono\+",  # phono+ (notation médicale)
        r"nausées?",
        r"n\+",  # N+ (abréviation)
        r"vomissement(?:s)?",
        r"v\+",  # V+ (abréviation)
        r"aura",
        r"scotome",
        r"pulsations?",
        r"intolérance (?:à la )?lumière",
        r"intolérance (?:au )?bruit"
    ],
    "tension_like": [
        r"céphalée de tension",
        r"tension",
        r"pression",
        r"pesanteur",
        r"en casque",
        r"bilatérale?s?",
        r"bilat\b",  # bilat (abréviation)
        r"serrement",
        r"étau",
        r"diffuses?",
        r"non pulsatile",
        r"type serrement",
        r"occipito-frontal",
        r"cervico-dorsal",
        r"contractures? (?:cervicales?|trapèzes)",
        r"Ø\s*(?:n/?v|photo|phono)",  # Ø = absence (notation française)
        r"sans\s+n/?v",
        r"pas\s+de\s+n/?v",
        r"aucun s associé"  # Aucun S associé (signe)
    ],
    "htic_like": [
        r"HTIC",
        r"hypertension intracrânienne",
        r"en casque",
        r"matutinale?",
        r"vomissements? en jet"
    ]
}


# ============================================================================
# FONCTIONS D'EXTRACTION PAR RÈGLES
# ============================================================================
#
# These functions implement the core NLU logic for clinical text analysis.
# Design principles:
# 1. High sensitivity for red flags (false negatives are dangerous)
# 2. Negation-aware processing (check "pas de X" before "X")
# 3. Graceful degradation (return None if uncertain, not wrong values)
# ============================================================================

def detect_pattern(text: str, patterns: Dict[Any, list], check_negation: bool = True) -> Optional[Any]:
    """
    Detect clinical patterns in free-text using regex matching.

    This is the core pattern-matching function used throughout the NLU system.
    For boolean patterns (True/False keys), it implements negation-first logic
    to prevent false positives (e.g., "pas de fièvre" should return False, not True).

    Clinical Design Decision:
        Negations are checked BEFORE affirmations because in medical contexts,
        explicit negation of a symptom is critical information. Missing a negation
        could lead to unnecessary investigations.

    Args:
        text: Clinical text to analyze (automatically lowercased).
        patterns: Dictionary mapping values to lists of regex patterns.
                  For boolean patterns, use True/False as keys.
                  For categorical patterns (onset, profile), use string keys.
        check_negation: If True and patterns has both True/False keys,
                       check False patterns first. Default True.

    Returns:
        The matched key (str, bool, or other) or None if no match.

    Examples:
        >>> detect_pattern("patient apyrétique", FEVER_PATTERNS)
        False
        >>> detect_pattern("fièvre à 39°C", FEVER_PATTERNS)
        True
        >>> detect_pattern("céphalée brutale", ONSET_PATTERNS)
        'thunderclap'

    Clinical Safety Note:
        When patterns dict contains both True and False keys, the function
        ensures that explicit negations are detected before affirmations.
        This is critical for red flag assessment.
    """
    text_lower = text.lower()
    
    # Pour les patterns booléens, vérifier False en premier
    if check_negation and False in patterns and True in patterns:
        # Vérifier négations d'abord
        for pattern in patterns[False]:
            if re.search(pattern, text_lower):
                return False
        # Puis affirmations
        for pattern in patterns[True]:
            if re.search(pattern, text_lower):
                return True
        return None
    
    # Pour les autres patterns, ordre normal
    for value, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                return value
    
    return None


def extract_age(text: str) -> Optional[int]:
    """Extrait l'âge depuis le texte.
    
    Cherche des patterns comme:
    - "45 ans"
    - "45a" (abréviation médicale)
    - "âgé de 30 ans"
    - "patient de 55 ans"
    
    Args:
        text: Texte à analyser
        
    Returns:
        L'âge détecté ou None
    """
    # Pattern: nombre suivi de "a" (abréviation médicale: 45a, 60a)
    match = re.search(r'(\d{1,3})a\b', text, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 0 <= age <= 120:
            return age
    
    # Pattern: nombre suivi de "ans"
    match = re.search(r'(\d{1,3})\s*ans?', text, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 0 <= age <= 120:
            return age
    
    # Pattern: "âgé(e) de X ans"
    match = re.search(r'âgée? de (\d{1,3})', text, re.IGNORECASE)
    if match:
        age = int(match.group(1))
        if 0 <= age <= 120:
            return age
    
    return None


def extract_sex(text: str) -> Optional[str]:
    """Extrait le sexe depuis le texte.
    
    Args:
        text: Texte à analyser
        
    Returns:
        "M", "F", ou None
    """
    text_lower = text.lower()
    
    # Indicateurs obstétricaux (priorité haute - override tout)
    # G1P0, SA, trimestre → forcément femme
    if re.search(r'\bg\d+p\d+', text_lower):  # Grossesse/parité
        return "F"
    if re.search(r'\b\d+\s*sa\b', text_lower):  # Semaines d'aménorrhée
        return "F"
    if re.search(r'\bt[123]\b', text_lower):  # Trimestre
        return "F"
    if re.search(r'\b(?:enceinte|gravidique|gestante|post-partum)\b', text_lower):
        return "F"
    
    # Abréviations médicales en début de ligne (F 45a, H 28a, Pt 60a)
    # Chercher au début du texte ou après virgule/point
    if re.search(r'(?:^|[,.])\s*f\s+\d+a', text_lower):
        return "F"
    if re.search(r'(?:^|[,.])\s*h\s+\d+a', text_lower):
        return "M"
    
    # Recherche de marqueurs féminins
    if re.search(r'\b(?:femme|patiente|elle|madame|mme|mère)\b', text_lower):
        return "F"
    
    # Recherche de marqueurs masculins
    if re.search(r'\b(?:homme|patient|il|monsieur|mr?\.)\b', text_lower):
        return "M"
    
    return None


def extract_intensity_score(text: str) -> Optional[int]:
    """Extrait un score d'intensité numérique (0-10).
    
    Prend le MAXIMUM de toutes les valeurs EVA détectées (cliniquement pertinent).
    
    Args:
        text: Texte à analyser
        
    Returns:
        Score 0-10 ou None
    """
    text_lower = text.lower()
    
    # Pattern: "X/10" ou "X-Y/10" - chercher TOUTES les occurrences
    all_evas = []
    for match in re.finditer(r'(\d{1,2})(?:-(\d{1,2}))?\s*/\s*10', text):
        score = int(match.group(1))
        if match.group(2):  # Si range, prendre valeur maximale du range
            score2 = int(match.group(2))
            score = max(score, score2)
        if 0 <= score <= 10:
            all_evas.append(score)
    
    # Si plusieurs EVA trouvées, retourner le maximum
    if all_evas:
        return max(all_evas)
    
    # Pattern: "EVA max" ou "EVA maximum" (fréquent en français)
    if re.search(r'eva\s*(?:max(?:imum|imale?)?|10/10)', text_lower):
        return 10
    
    # Pattern: "EVA X" ou "EN X" (échelles médicales)
    match = re.search(r'(?:eva|en)\s*(?:=\s*)?(\d{1,2})', text_lower)
    if match:
        score = int(match.group(1))
        if 0 <= score <= 10:
            return score
    
    # Cas spéciaux pour mots simples (sans combinaison)
    # insupportable seul = 10
    if re.search(r'\binsupportable\b', text_lower) and not re.search(r'(?:maximale?|atroce)', text_lower):
        return 10
    
    # terrible = 9
    if re.search(r'\bterrible\b', text_lower):
        return 9
    
    # modérée = 5
    if re.search(r'\bmodérée?\b', text_lower):
        return 5
    
    # Vérifier intensité maximale (patterns combinés)
    for pattern in INTENSITY_PATTERNS.get("maximum", []):
        if re.search(pattern, text_lower):
            return 10
    
    # Cas spécial : atroce ET insupportable (même séparés)
    if 'atroce' in text_lower and 'insupportable' in text_lower:
        return 10
    
    # Mapping qualitatif vers numérique (autres cas)
    intensity_level = detect_pattern(text, INTENSITY_PATTERNS)
    if intensity_level == "severe":
        return 9
    elif intensity_level == "moderate":
        return 6
    elif intensity_level == "mild":
        return 3
    
    return None


def extract_duration_hours(text: str) -> Optional[float]:
    """Extrait la durée de l'épisode actuel en heures.
    
    Priorité donnée aux durées de crise plutôt qu'aux durées "depuis".
    Pour AVF typiques: cherche "45min", "30-60min" avant "depuis 10j".
    
    Args:
        text: Texte à analyser
        
    Returns:
        Durée en heures ou None
    """
    text_lower = text.lower()
    
    # PRIORITÉ 1: "durée totale Xh" ou "durée Xh" (explicite)
    match = re.search(r'durée\s+(?:totale\s+)?(\d+(?:\.\d+)?)\s*h(?:eures?)?', text_lower)
    if match:
        return float(match.group(1))
    
    # PRIORITÉ 2: Durée de crise en minutes avec contexte
    # "crises 45min", "durée 30-60min", "épisode 50min"
    match = re.search(r'(?:crises?|durée|épisode)\s*(\d+)(?:-(\d+))?\s*min(?:utes?)?', text_lower)
    if match:
        if match.group(2):  # Range: prendre moyenne
            min_val = float(match.group(1))
            max_val = float(match.group(2))
            return (min_val + max_val) / (2 * 60)
        return float(match.group(1)) / 60
    
    # PRIORITÉ 3: Minutes seules avec virgule (contexte crise)
    # ", 45min," ou ", 50min." ou "EVA 10/10, 45min,"
    match = re.search(r',\s*(\d+)\s*min(?:utes?)?\s*[,\.]', text_lower)
    if match:
        return float(match.group(1)) / 60
    
    # PRIORITÉ 4: Range de minutes seul "30-60min"
    match = re.search(r'\b(\d+)-(\d+)\s*min(?:utes?)?\b', text_lower)
    if match:
        min_val = float(match.group(1))
        max_val = float(match.group(2))
        return (min_val + max_val) / (2 * 60)
    
    # PRIORITÉ 5: Minutes seules en fin de phrase ou isolées
    # "45min" mais pas "20min puis" (qui serait une aura)
    match = re.search(r'\b(\d+)\s*min(?:utes?)?\s*(?:[,\.]|$)', text_lower)
    if match and not re.search(r'(\d+)\s*min(?:utes?)?\s+puis', text_lower):
        return float(match.group(1)) / 60
    
    # PRIORITÉ 6: "Xh" isolé sans "depuis" (ex: "céphalée 8h")
    # Chercher Xh mais PAS précédé de "depuis" dans les 10 caractères précédents
    for match in re.finditer(r'\b(\d+(?:\.\d+)?)\s*h(?:eures?)?\b', text_lower):
        pos = match.start()
        # Vérifier contexte avant (au moins 10 caractères)
        before = text_lower[max(0, pos-10):pos]
        # Exclure si "depuis" dans les 10 caractères précédents
        if 'depuis' not in before and 'dep' not in before:
            return float(match.group(1))
    
    # PRIORITÉ 7: Range d'heures "12-24h" -> moyenne
    match = re.search(r'(\d+)-(\d+)\s*h(?:eures?)?', text_lower)
    if match:
        min_hours = float(match.group(1))
        max_hours = float(match.group(2))
        return (min_hours + max_hours) / 2
    
    # PRIORITÉ 8: "depuis Xh" ou "dep Xh" (format français médical)
    match = re.search(r'(?:depuis|dep)\s+(\d+(?:\.\d+)?)\s*h(?:eures?)?', text_lower)
    if match:
        return float(match.group(1))
    
    # PRIORITÉ 9: "depuis Xj" ou "dep Xj" - convertir jours en heures
    match = re.search(r'(?:depuis|dep)\s+(\d+)\s*j(?:ours?)?(?:\b|\s)', text_lower)
    if match:
        days = int(match.group(1))
        return float(days) * 24  # Convertir en heures
    
    # PRIORITÉ 10: "depuis X semaines" ou "X sem" isolé - convertir en heures
    # Chercher d'abord avec "depuis/dep" (priorité haute)
    match = re.search(r'(?:depuis|dep)\s+(\d+)\s*sem(?:aines?)?', text_lower)
    if match:
        weeks = int(match.group(1))
        return float(weeks) * 7 * 24  # Convertir en heures

    # Sinon chercher "X sem" ou "X semaines" isolé (ex: "progressive 3 sem")
    match = re.search(r'\b(\d+)\s*sem(?:aines?)?\b', text_lower)
    if match:
        weeks = int(match.group(1))
        return float(weeks) * 7 * 24  # Convertir en heures

    # PRIORITÉ 11: "depuis X mois" - convertir en heures (approximation 30j/mois)
    match = re.search(r'(?:depuis|dep)\s+(\d+)\s*mois', text_lower)
    if match:
        months = int(match.group(1))
        return float(months) * 30 * 24  # Approximation 30 jours par mois
    
    # PRIORITÉ 12: "il y a X temps" (tournure temporelle courante)
    match = re.search(r'il y a (\d+)\s*(h(?:eures?)?|j(?:ours?)?|sem(?:aines?)?|mois)', text_lower)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if 'h' in unit:
            return float(value)
        elif 'j' in unit:
            return float(value) * 24
        elif 'sem' in unit:
            return float(value) * 7 * 24
        elif 'mois' in unit:
            return float(value) * 30 * 24
    
    # PRIORITÉ 13: "ça/cela fait X que" (langage familier)
    match = re.search(r'(?:ça|cela) fait (\d+)\s*(h(?:eures?)?|j(?:ours?)?|sem(?:aines?)?|mois)', text_lower)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if 'h' in unit:
            return float(value)
        elif 'j' in unit:
            return float(value) * 24
        elif 'sem' in unit:
            return float(value) * 7 * 24
        elif 'mois' in unit:
            return float(value) * 30 * 24
    
    return None


# ============================================================================
# FONCTION PRINCIPALE NLU
# ============================================================================

def parse_free_text_to_case(text: str) -> Tuple[HeadacheCase, Dict[str, Any]]:
    """
    Parse free-text clinical description into a structured HeadacheCase.

    This is the main entry point for rule-based NLU extraction. It processes
    a free-text description and extracts all relevant clinical information
    into a validated HeadacheCase model with confidence scores.

    Clinical Workflow:
        1. Demographics: age, sex (with obstetric override for G1P0, SA, etc.)
        2. Temporal profile: onset type, duration, profile classification
        3. Red flags: fever, meningeal signs, HTIC, neurological deficit
        4. Risk contexts: pregnancy, immunosuppression, trauma, recent LP
        5. Headache characterization: migraine-like, tension-like, etc.

    Confidence Scoring:
        Each extracted field receives a confidence score (0.0-1.0):
        - 0.9+: Numeric values or specific medical terms
        - 0.8-0.9: Clear pattern matches
        - 0.6-0.8: Inferred values or less specific patterns
        - <0.6: Low confidence, may need clarification

    Args:
        text: Free-text clinical description in French.
              Supports both formal medical notation ("H 45a, féb à 39°C, RDN+")
              and patient vernacular ("j'ai super mal à la tête depuis ce matin").

    Returns:
        Tuple[HeadacheCase, Dict[str, Any]]:
            - HeadacheCase: Validated Pydantic model with extracted fields.
                           Fields not detected remain None or "unknown".
            - metadata: Extraction details including:
                - detected_fields: List of successfully extracted field names
                - confidence_scores: Dict mapping field names to scores
                - overall_confidence: Weighted average confidence
                - extraction_method: Always "rule_based" for this function
                - timestamp: ISO format extraction timestamp
                - original_text: Input text for traceability
                - contradictions: List of detected inconsistencies

    Examples:
        >>> case, meta = parse_free_text_to_case(
        ...     "F 28a, céphalée brutale fébrile avec RDN, depuis 2h"
        ... )
        >>> case.onset
        'thunderclap'
        >>> case.fever
        True
        >>> case.meningeal_signs
        True
        >>> meta["detected_fields"]
        ['age', 'sex', 'onset', 'fever', 'meningeal_signs', 'duration_current_episode_hours']

    Clinical Safety Notes:
        - Age defaults to None if not detected (will trigger dialogue question)
        - Sex defaults to "Other" if not detected
        - Red flags (fever, meningeal, HTIC) prioritize sensitivity over specificity
        - Thunderclap onset automatically implies acute profile (urgency)

    See Also:
        - NLUv2.parse_free_text_to_case: Vocabulary-based version
        - HybridNLU.parse_free_text_to_case: Combined rules + embedding
    """
    
    # ========================================================================
    # ÉTAPE 1: Extraction par règles
    # ========================================================================
    
    extracted_data = {}
    detected_fields = []
    confidence_scores = {}
    
    # Données démographiques (OBLIGATOIRES)
    age = extract_age(text)
    sex = extract_sex(text)
    
    # Validation âge: doit être entre 1 et 120 (rejeter valeurs aberrantes)
    if age is not None:
        if 1 <= age <= 120:
            extracted_data["age"] = age
            detected_fields.append("age")
            confidence_scores["age"] = 0.9  # Haute confiance pour pattern numérique
        # Si âge aberrant, on ne met rien (reste None)
    # Si âge non détecté, on ne met pas de valeur par défaut - le dialogue posera la question si nécessaire
    
    if sex is not None:
        extracted_data["sex"] = sex
        detected_fields.append("sex")
        confidence_scores["sex"] = 0.8
    else:
        # Valeur par défaut
        extracted_data["sex"] = "Other"
        confidence_scores["sex"] = 0.0
    
    # Profil temporel
    onset = detect_pattern(text, ONSET_PATTERNS)
    if onset:
        extracted_data["onset"] = onset
        detected_fields.append("onset")
        confidence_scores["onset"] = 0.85
    else:
        extracted_data["onset"] = "unknown"
    
    profile = detect_pattern(text, PROFILE_PATTERNS)
    if profile:
        extracted_data["profile"] = profile
        detected_fields.append("profile")
        confidence_scores["profile"] = 0.8
    else:
        extracted_data["profile"] = "unknown"
    
    # Durée et intensité
    duration = extract_duration_hours(text)
    if duration is not None:
        extracted_data["duration_current_episode_hours"] = duration
        detected_fields.append("duration_current_episode_hours")
        confidence_scores["duration_current_episode_hours"] = 0.9
    
    intensity = extract_intensity_score(text)
    if intensity is not None:
        extracted_data["intensity"] = intensity
        detected_fields.append("intensity")
        confidence_scores["intensity"] = 0.85
    
    
    # Signes cliniques majeurs (RED FLAGS)
    
    # 1. Fièvre (avec validation température ≥38°C)
    fever = detect_pattern(text, FEVER_PATTERNS)
    
    # Validation numérique stricte: température ≥38°C
    text_for_temp = text.lower()
    if 't°' in text_for_temp or 'température' in text_for_temp or 'temp' in text_for_temp:
        temp_match = re.search(r'(\d+(?:\.\d+)?)\s*°', text_for_temp)
        if temp_match:
            temp = float(temp_match.group(1))
            # Critère médical strict: fièvre si ≥38°C
            if temp >= 38.0:
                fever = True
            elif temp < 38.0 and fever is not True:  # Éviter d'écraser un "fièvre" explicite
                fever = False
    
    if fever is not None:
        extracted_data["fever"] = fever
        detected_fields.append("fever")
        confidence_scores["fever"] = 0.9
    
    # 2. Syndrome méningé (CRITIQUE)
    meningeal_signs = detect_pattern(text, MENINGEAL_SIGNS_PATTERNS)
    if meningeal_signs is not None:
        extracted_data["meningeal_signs"] = meningeal_signs
        detected_fields.append("meningeal_signs")
        confidence_scores["meningeal_signs"] = 0.95  # Haute confiance car critique
    
    # 3. Pattern HTIC - Utiliser vocabulaire médical avec seuil de confiance
    # "pire le matin" seul ne devrait PAS déclencher HTIC (faux positif)
    from headache_assistants.medical_vocabulary import MedicalVocabulary
    vocab = MedicalVocabulary()  # Instance réutilisée pour autres détections
    HTIC_CONFIDENCE_THRESHOLD = 0.70  # Seuil pour valider HTIC

    htic_result = vocab.detect_htic(text)
    if htic_result.detected and htic_result.value is True and htic_result.confidence >= HTIC_CONFIDENCE_THRESHOLD:
        extracted_data["htic_pattern"] = True
        detected_fields.append("htic_pattern")
        confidence_scores["htic_pattern"] = htic_result.confidence
    
    # 4. Déficit neurologique
    neuro_deficit = detect_pattern(text, NEURO_DEFICIT_PATTERNS)
    if neuro_deficit is True:
        extracted_data["neuro_deficit"] = True
        detected_fields.append("neuro_deficit")
        confidence_scores["neuro_deficit"] = 0.9
    
    # 5. Crises d'épilepsie
    seizure = detect_pattern(text, SEIZURE_PATTERNS)
    if seizure is True:
        extracted_data["seizure"] = True
        detected_fields.append("seizure")
        confidence_scores["seizure"] = 0.9
    
    # Contextes à risque
    
    pregnancy_postpartum = detect_pattern(text, PREGNANCY_POSTPARTUM_PATTERNS)
    if pregnancy_postpartum is not None:
        extracted_data["pregnancy_postpartum"] = pregnancy_postpartum
        detected_fields.append("pregnancy_postpartum")
        confidence_scores["pregnancy_postpartum"] = 0.9
    
    trauma = detect_pattern(text, TRAUMA_PATTERNS)
    if trauma is not None:
        extracted_data["trauma"] = trauma
        detected_fields.append("trauma")
        confidence_scores["trauma"] = 0.85
    
    # Changement récent de pattern (pour céphalées chroniques)
    recent_pattern_change_result = vocab.detect_pattern_change(text)
    if recent_pattern_change_result.detected:
        extracted_data["recent_pattern_change"] = recent_pattern_change_result.value
        detected_fields.append("recent_pattern_change")
        confidence_scores["recent_pattern_change"] = recent_pattern_change_result.confidence

    recent_pl_or_peridural = detect_pattern(text, RECENT_PL_OR_PERIDURAL_PATTERNS)
    if recent_pl_or_peridural is not None:
        extracted_data["recent_pl_or_peridural"] = recent_pl_or_peridural
        detected_fields.append("recent_pl_or_peridural")
        confidence_scores["recent_pl_or_peridural"] = 0.9
    
    immunosuppression = detect_pattern(text, IMMUNOSUPPRESSION_PATTERNS)
    if immunosuppression is not None:
        extracted_data["immunosuppression"] = immunosuppression
        detected_fields.append("immunosuppression")
        confidence_scores["immunosuppression"] = 0.9
    
    # Profil clinique de la céphalée
    # Logique améliorée : compter les matches pour chaque profil
    headache_profile_scores = {}
    text_lower = text.lower()
    
    for profile_type, pattern_list in HEADACHE_PROFILE_PATTERNS.items():
        score = 0
        for pattern in pattern_list:
            if re.search(pattern, text_lower):
                score += 1
        if score > 0:
            headache_profile_scores[profile_type] = score
    
    # Bonus pour tension_like si absence explicite de signes migraineux
    if any(re.search(pattern, text_lower) for pattern in [r"Ø\s*(?:n/?v|photo|phono)", r"sans\s+n/?v", r"pas\s+de\s+n/?v", r"aucun s associé"]):
        headache_profile_scores["tension_like"] = headache_profile_scores.get("tension_like", 0) + 3
    
    # Sélectionner le profil avec le meilleur score
    if headache_profile_scores:
        headache_profile = max(headache_profile_scores, key=headache_profile_scores.get)
        extracted_data["headache_profile"] = headache_profile
        detected_fields.append("headache_profile")
        confidence_scores["headache_profile"] = 0.75
    else:
        extracted_data["headache_profile"] = "unknown"
    
 
    # ========================================================================
    # ÉTAPE 2: Construction du HeadacheCase
    # ========================================================================
    
    try:
        case = HeadacheCase(**extracted_data)
    except Exception as e:
        # En cas d'erreur de validation, créer un cas minimal valide
        # On ne met plus de valeur par défaut pour l'âge - il reste None
        case = HeadacheCase(
            age=extracted_data.get("age"),  # None si non détecté
            sex=extracted_data.get("sex", "Other")
        )
        confidence_scores["validation_error"] = str(e)
    
    # ========================================================================
    # ÉTAPE 2.5: Inférence automatique du profil temporel
    # ========================================================================
    # Si onset est détecté mais profile reste "unknown", on infère automatiquement
    # Critère médical: coup de tonnerre = TOUJOURS aigu (urgence vitale)
    
    if case.onset != "unknown" and case.profile == "unknown":
        if case.onset == "thunderclap":
            # HSA suspectée → Toujours aigu
            case = case.model_copy(update={"profile": "acute"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.95  # Haute confiance
        elif case.onset == "progressive":
            # Progressif sans durée → aigu par défaut (principe de précaution)
            if case.duration_current_episode_hours:
                if case.duration_current_episode_hours < 168:  # < 7 jours (1 semaine)
                    case = case.model_copy(update={"profile": "acute"})
                elif case.duration_current_episode_hours < 2160:  # < 90 jours (3 mois)
                    case = case.model_copy(update={"profile": "subacute"})
                else:
                    case = case.model_copy(update={"profile": "chronic"})
                detected_fields.append("profile")
                confidence_scores["profile"] = 0.9
            else:
                # Sans durée précise mais progressive → on vérifie le pattern textuel
                # Si 'semaines' détecté, probablement subaigu
                if 'semaine' in text.lower():
                    case = case.model_copy(update={"profile": "subacute"})
                    detected_fields.append("profile")
                    confidence_scores["profile"] = 0.75
                else:
                    # Sinon aigu par défaut pour maximiser sensibilité
                    case = case.model_copy(update={"profile": "acute"})
                    detected_fields.append("profile")
                    confidence_scores["profile"] = 0.6
        elif case.onset == "chronic":
            case = case.model_copy(update={"profile": "chronic"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.9
    
    # ÉTAPE 2.6: Inférence du profile depuis la durée (si profile toujours unknown)
    # ============================================================================
    # Si aucun pattern temporel n'a matché mais qu'on a extrait une durée,
    # on infère le profile automatiquement
    
    if case.profile == "unknown" and case.duration_current_episode_hours is not None:
        if case.duration_current_episode_hours < 168:  # < 7 jours (1 semaine)
            case = case.model_copy(update={"profile": "acute"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.85
        elif case.duration_current_episode_hours < 2160:  # < 90 jours (3 mois)
            case = case.model_copy(update={"profile": "subacute"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.85
        else:
            case = case.model_copy(update={"profile": "chronic"})
            detected_fields.append("profile")
            confidence_scores["profile"] = 0.85
    
    # ========================================================================
    # ÉTAPE 3: Métadonnées d'extraction
    # ========================================================================
    
    # Détection de contradictions dans le texte
    contradictions = []
    
    # Contradiction onset
    if case.onset in ['thunderclap', 'progressive']:
        if 'progressive' in text_lower and ('brutal' in text_lower or 'thunderclap' in text_lower):
            contradictions.append('onset_conflicting')
    
    # Contradiction fièvre
    if case.fever is True and any(word in text_lower for word in ['apyrétique', 'apyr', 'sans fièvre']):
        contradictions.append('fever_conflicting')
    
    # Contradiction durée vs profile
    if case.duration_current_episode_hours and case.profile != "unknown":
        if case.duration_current_episode_hours < 168 and case.profile == "chronic":
            contradictions.append('duration_profile_mismatch')
        elif case.duration_current_episode_hours >= 2160 and case.profile == "acute":
            contradictions.append('duration_profile_mismatch')
    
    metadata = {
        "detected_fields": detected_fields,
        "confidence_scores": confidence_scores,
        "overall_confidence": sum(confidence_scores.values()) / max(len(confidence_scores), 1),
        "extraction_method": "rule_based",
        "timestamp": datetime.now().isoformat(),
        "original_text": text,
        "contradictions": contradictions,  # Nouvelle métadonnée
        
    }
    
    return case, metadata


# ============================================================================
# FONCTIONS UTILITAIRES POUR DIALOGUE
# ============================================================================

def suggest_clarification_questions(case: HeadacheCase, metadata: Dict[str, Any]) -> list[str]:
    """Génère des questions de clarification basées sur les champs manquants.
    
    Analyse le cas et les métadonnées pour identifier les informations critiques
    manquantes et propose des questions ciblées.
    
    Args:
        case: Le cas HeadacheCase extrait
        metadata: Métadonnées d'extraction
        
    Returns:
        Liste de questions de clarification
    """
    questions = []
    
    # Champs critiques pour le diagnostic
    if case.onset == "unknown":
        questions.append("Comment la douleur a-t-elle débuté ? (brutalement, progressivement, depuis longtemps)")
    
    if case.profile == "unknown":
        questions.append("Depuis combien de temps avez-vous cette douleur ?")
    
    # Red flags critiques
    if case.fever is None:
        questions.append("Avez-vous de la fièvre ?")
    
    if case.meningeal_signs is None:
        questions.append("Avez-vous une raideur de la nuque ?")
    
    if case.htic_pattern is None:
        questions.append("La douleur est-elle pire le matin ? Y a-t-il des vomissements en jet ?")
    
    if case.neuro_deficit is None:
        questions.append("Avez-vous des faiblesses, troubles de la parole ou de la vision ?")
    
    if case.intensity is None:
        questions.append("Sur une échelle de 0 à 10, comment évalueriez-vous l'intensité de la douleur ?")
    
    return questions


def get_missing_critical_fields(case: HeadacheCase) -> list[str]:
    """Identifie les champs critiques manquants pour l'arbre décisionnel.

    Args:
        case: Le cas HeadacheCase

    Returns:
        Liste des noms de champs critiques non renseignés
    """
    critical_fields = []

    # Champs utilisés par les règles HSA/méningite/HTIC
    if case.onset == "unknown":
        critical_fields.append("onset")

    if case.fever is None:
        critical_fields.append("fever")

    if case.meningeal_signs is None:
        critical_fields.append("meningeal_signs")

    if case.intensity is None:
        critical_fields.append("intensity")

    if case.htic_pattern is None:
        critical_fields.append("htic_pattern")

    # CRITIQUE: Déficit neurologique - red flag majeur pour AVC, tumeur, etc.
    if case.neuro_deficit is None:
        critical_fields.append("neuro_deficit")

    # Crise d'épilepsie - red flag majeur
    if case.seizure is None:
        critical_fields.append("seizure")

    if case.recent_pl_or_peridural is None:
        critical_fields.append("recent_pl_or_peridural")

    # CRITIQUE pour cas chronic : demander si changement récent
    # Permet de différencier chronic stable (pas d'urgence) vs chronic aggravé (urgence)
    if (case.profile == "chronic" or case.onset == "chronic") and case.recent_pattern_change is None:
        critical_fields.append("recent_pattern_change")

    return critical_fields
