"""Corpus d'exemples médicaux annotés pour le NLU hybride.

Ce corpus sert de base de connaissances pour le système d'embedding,
permettant de gérer les formulations non couvertes par les règles.

Organisation:
    - Exemples réels anonymisés
    - Patterns validés par médecins
    - Formulations variées 
"""

from typing import List, Dict, Any

# Corpus d'exemples médicaux annotés
MEDICAL_EXAMPLES: List[Dict[str, Any]] = [
    # ========================================================================
    # ONSET - Début de la céphalée
    # ========================================================================
    {
        "text": "Céphalée brutale pire douleur de ma vie",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "HSA classique",
            "keywords": ["brutale", "pire douleur"]
        }
    },
    {
        "text": "Mal de tête soudain très violent comme un coup de marteau",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["soudain", "violent", "coup de marteau"]
        }
    },
    {
        "text": "Douleur crânienne installation progressive sur plusieurs jours",
        "onset": "progressive",
        "profile": "acute",
        "annotations": {
            "source": "Formulation médicale",
            "keywords": ["progressive", "plusieurs jours"]
        }
    },
    {
        "text": "Céphalée qui s'aggrave petit à petit depuis une semaine",
        "onset": "progressive",
        "profile": "subacute",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["aggrave petit à petit", "depuis une semaine"]
        }
    },
    {
        "text": "Mal de tête tous les jours depuis des mois",
        "onset": "chronic",
        "profile": "chronic",
        "annotations": {
            "source": "Céphalée chronique",
            "keywords": ["tous les jours", "depuis des mois"]
        }
    },
    {
        "text": "Douleur permanente au niveau du crâne depuis longtemps",
        "onset": "chronic",
        "profile": "chronic",
        "annotations": {
            "source": "Langage patient",
            "keywords": ["permanente", "depuis longtemps"]
        }
    },

    # ========================================================================
    # FIÈVRE
    # ========================================================================
    {
        "text": "Patient fébrile à 39 degrés",
        "fever": True,
        "annotations": {
            "source": "Formulation médicale classique",
            "keywords": ["fébrile", "39"]
        }
    },
    {
        "text": "Il a chaud et transpire beaucoup",
        "fever": True,
        "annotations": {
            "source": "Langage patient - signes indirects",
            "keywords": ["chaud", "transpire"]
        }
    },
    {
        "text": "Température normale, pas de fièvre",
        "fever": False,
        "annotations": {
            "source": "Négation explicite",
            "keywords": ["normale", "pas de fièvre"]
        }
    },
    {
        "text": "Apyrétique depuis consultation",
        "fever": False,
        "annotations": {
            "source": "Terme médical",
            "keywords": ["apyrétique"]
        }
    },

    # ========================================================================
    # SYNDROME MÉNINGÉ
    # ========================================================================
    {
        "text": "Raideur de nuque importante avec impossibilité de fléchir",
        "meningeal_signs": True,
        "annotations": {
            "source": "Signe méningé classique",
            "keywords": ["raideur nuque", "impossibilité fléchir"]
        }
    },
    {
        "text": "Le patient ne peut plus bouger le cou tellement c'est raide",
        "meningeal_signs": True,
        "annotations": {
            "source": "Langage patient",
            "keywords": ["ne peut plus bouger cou", "raide"]
        }
    },
    {
        "text": "Kernig et Brudzinski positifs",
        "meningeal_signs": True,
        "annotations": {
            "source": "Signes cliniques",
            "keywords": ["Kernig", "Brudzinski"]
        }
    },
    {
        "text": "Position en chien de fusil au lit",
        "meningeal_signs": True,
        "annotations": {
            "source": "Posture méningée",
            "keywords": ["chien de fusil"]
        }
    },
    {
        "text": "Nuque souple, pas de signes méningés",
        "meningeal_signs": False,
        "annotations": {
            "source": "Examen négatif",
            "keywords": ["nuque souple", "pas de signes"]
        }
    },

    # ========================================================================
    # HTIC - Hypertension IntraCrânienne
    # ========================================================================
    {
        "text": "Céphalée avec vomissements en jet et aggravation par la toux",
        "htic_pattern": True,
        "annotations": {
            "source": "HTIC classique - signes FORTS",
            "keywords": ["vomissements en jet", "aggravation", "toux"]
        }
    },
    {
        "text": "Douleur qui empire quand il tousse ou fait un effort",
        "htic_pattern": True,
        "annotations": {
            "source": "Déclencheurs HTIC",
            "keywords": ["empire", "tousse", "effort"]
        }
    },
    {
        "text": "Céphalée matutinale avec œdème papillaire au fond d'œil",
        "htic_pattern": True,
        "annotations": {
            "source": "HTIC avec signe ophtalmo",
            "keywords": ["matutinale", "œdème papillaire"]
        }
    },

    # ========================================================================
    # DÉFICIT NEUROLOGIQUE
    # ========================================================================
    {
        "text": "Faiblesse du bras droit avec difficulté à lever",
        "neuro_deficit": True,
        "annotations": {
            "source": "Déficit moteur",
            "keywords": ["faiblesse bras", "difficulté lever"]
        }
    },
    {
        "text": "Le patient n'arrive plus à parler correctement",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble langage",
            "keywords": ["n'arrive plus parler"]
        }
    },
    {
        "text": "Vision double depuis ce matin",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble visuel",
            "keywords": ["vision double"]
        }
    },
    {
        "text": "Patient confus, désorienté dans le temps",
        "neuro_deficit": True,
        "annotations": {
            "source": "Trouble conscience",
            "keywords": ["confus", "désorienté"]
        }
    },
    {
        "text": "Examen neurologique strictement normal",
        "neuro_deficit": False,
        "annotations": {
            "source": "Examen négatif",
            "keywords": ["normal"]
        }
    },

    # ========================================================================
    # TRAUMATISME
    # ========================================================================
    {
        "text": "Chute avec choc à la tête hier",
        "trauma": True,
        "annotations": {
            "source": "Traumatisme récent",
            "keywords": ["chute", "choc tête"]
        }
    },
    {
        "text": "Accident de voiture il y a 2 jours",
        "trauma": True,
        "annotations": {
            "source": "AVP",
            "keywords": ["accident voiture"]
        }
    },
    {
        "text": "Pas de notion de traumatisme crânien",
        "trauma": False,
        "annotations": {
            "source": "Négation explicite",
            "keywords": ["pas de traumatisme"]
        }
    },

    # ========================================================================
    # CRISES / CONVULSIONS
    # ========================================================================
    {
        "text": "Épisode de convulsions ce matin",
        "seizure": True,
        "annotations": {
            "source": "Crise convulsive",
            "keywords": ["convulsions"]
        }
    },
    {
        "text": "Perte de connaissance avec mouvements anormaux",
        "seizure": True,
        "annotations": {
            "source": "Description patient",
            "keywords": ["perte connaissance", "mouvements anormaux"]
        }
    },

    # ========================================================================
    # GROSSESSE / POST-PARTUM
    # ========================================================================
    {
        "text": "Patiente enceinte de 7 mois",
        "pregnancy_postpartum": True,
        "annotations": {
            "source": "Grossesse en cours",
            "keywords": ["enceinte"]
        }
    },
    {
        "text": "Accouchement il y a 2 semaines",
        "pregnancy_postpartum": True,
        "annotations": {
            "source": "Post-partum",
            "keywords": ["accouchement", "2 semaines"]
        }
    },

    # ========================================================================
    # IMMUNODÉPRESSION
    # ========================================================================
    {
        "text": "Patient VIH positif sous traitement",
        "immunosuppression": True,
        "annotations": {
            "source": "VIH",
            "keywords": ["VIH positif"]
        }
    },
    {
        "text": "Antécédent de chimiothérapie pour cancer du sein",
        "immunosuppression": True,
        "annotations": {
            "source": "Traitement immunosuppresseur",
            "keywords": ["chimiothérapie"]
        }
    },

    # ========================================================================
    # PROFILS CLINIQUES - Caractéristiques céphalée
    # ========================================================================
    {
        "text": "Douleur d'un seul côté qui bat avec gêne à la lumière",
        "headache_profile": "migraine_like",
        "annotations": {
            "source": "Migraine classique",
            "keywords": ["un seul côté", "bat", "gêne lumière"]
        }
    },
    {
        "text": "Céphalée pulsatile temporale gauche avec nausées",
        "headache_profile": "migraine_like",
        "annotations": {
            "source": "Migraine médicale",
            "keywords": ["pulsatile", "temporale", "nausées"]
        }
    },
    {
        "text": "Mal de tête des deux côtés comme un bandeau serré",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Céphalée tension",
            "keywords": ["deux côtés", "bandeau serré"]
        }
    },
    {
        "text": "Douleur en étau bilatérale sans nausées",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Tension type",
            "keywords": ["étau", "bilatérale"]
        }
    },
    {
        "text": "Douleur atroce derrière l'œil gauche avec larmoiement",
        "headache_profile": "cluster_like",
        "annotations": {
            "source": "Algie vasculaire face",
            "keywords": ["derrière œil", "larmoiement"]
        }
    },

    # ========================================================================
    # CAS COMPLEXES - Formulations inhabituelles
    # ========================================================================
    {
        "text": "Sensation d'explosion dans la tête en plein effort",
        "onset": "thunderclap",
        "htic_pattern": True,
        "annotations": {
            "source": "HSA à l'effort",
            "keywords": ["explosion", "plein effort"]
        }
    },
    {
        "text": "Douleur crânienne maximale d'emblée pendant rapport sexuel",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Céphalée coïtale",
            "keywords": ["maximale d'emblée", "rapport sexuel"]
        }
    },
    {
        "text": "Tête qui serre fort quand je travaille devant l'ordinateur",
        "headache_profile": "tension_like",
        "annotations": {
            "source": "Céphalée tension contexte",
            "keywords": ["serre fort", "travaille ordinateur"]
        }
    },
    # ========================================================================
    # NÉVRALGIES ET NEUROPATHIES CRÂNIENNES
    # ========================================================================
    {
        "text": "Douleur faciale comme une décharge électrique quand je parle",
        "facial_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie du trijumeau typique",
            "keywords": ["décharge électrique", "quand je parle", "faciale"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Éclairs douloureux dans la joue déclenchés par la mastication",
        "facial_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie trijumeau V2/V3",
            "keywords": ["éclairs", "joue", "mastication"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Douleur en coup de poignard côté droit du visage quelques secondes",
        "facial_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie trijumeau (durée brève)",
            "keywords": ["coup de poignard", "visage", "quelques secondes"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Douleur faciale fulgurante déclenchée par le contact de la peau",
        "facial_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie trijumeau (zone gâchette)",
            "keywords": ["fulgurante", "déclenchée", "contact peau"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Brûlure continue sur la moitié du visage depuis zona",
        "facial_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie post-zostérienne",
            "keywords": ["brûlure continue", "zona"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Douleur derrière l'oreille irradiant vers la mâchoire",
        "cranial_nerve_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie du nerf glossopharyngien (IX)",
            "keywords": ["derrière oreille", "mâchoire"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Douleur à l'arrière du crâne comme des coups de couteau",
        "cranial_nerve_pain": True,
        "neuropathic_pattern": True,
        "profile": "chronic",
        "annotations": {
            "source": "Névralgie du grand nerf occipital",
            "keywords": ["arrière crâne", "coups de couteau"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Céphalée tous les jours depuis 6 mois intensité modérée",
        "profile": "chronic",
        "frequency_high": True,
        "annotations": {
            "source": "Céphalée chronique quotidienne (CCQ)",
            "keywords": ["tous les jours", "6 mois"],
            "imaging": "irm_cerebrale",
            "note": "IRM systématique pour CCQ ≥15j/mois depuis >3 mois"
        }
    },
    {
        "text": "Mal de tête présent plus de 15 jours par mois depuis 4 mois",
        "profile": "chronic",
        "frequency_high": True,
        "annotations": {
            "source": "CCQ - critères diagnostiques",
            "keywords": ["15 jours par mois", "4 mois"],
            "imaging": "irm_cerebrale"
        }
    },

    # ========================================================================
    # CÉPHALÉE POST-PONCTION LOMBAIRE / PÉRIDURALE
    # ========================================================================
    {
        "text": "Céphalée depuis ponction lombaire il y a 2 jours aggravée en position debout",
        "recent_pl_or_peridural": True,
        "profile": "acute",
        "annotations": {
            "source": "Syndrome post-PL classique",
            "keywords": ["ponction lombaire", "aggravée debout"],
            "diagnosis": "Hypotension intracrânienne post-PL"
        }
    },
    {
        "text": "Mal de tête apparu après la péridurale soulagé quand je m'allonge",
        "recent_pl_or_peridural": True,
        "profile": "acute",
        "annotations": {
            "source": "Céphalée post-péridurale (langage patient)",
            "keywords": ["après péridurale", "soulagé allongé"],
            "diagnosis": "Hypotension intracrânienne"
        }
    },
    {
        "text": "Céphalée orthostatique depuis rachianesthésie disparaît en décubitus",
        "recent_pl_or_peridural": True,
        "profile": "acute",
        "annotations": {
            "source": "Céphalée positionnelle post-brèche durale",
            "keywords": ["orthostatique", "rachianesthésie", "décubitus"],
            "diagnosis": "Hypotension intracrânienne"
        }
    },
    {
        "text": "Douleur de tête majeure quand je me lève depuis la ponction lombaire hier",
        "recent_pl_or_peridural": True,
        "profile": "acute",
        "annotations": {
            "source": "Post-PL avec pattern postural typique",
            "keywords": ["quand je me lève", "depuis ponction"],
            "note": "Blood-patch si persistance"
        }
    },

    # ========================================================================
    # CONTEXTE ONCOLOGIQUE / CANCER
    # ========================================================================
    {
        "text": "Patient avec antécédent de cancer du poumon nouvelle céphalée",
        "cancer_history": True,
        "profile": "acute",
        "annotations": {
            "source": "Contexte oncologique = red flag",
            "keywords": ["cancer", "nouvelle céphalée"],
            "imaging": "irm_cerebrale_avec_injection",
            "note": "Rechercher métastases cérébrales"
        }
    },
    {
        "text": "Patiente traitée pour cancer du sein céphalée progressive depuis 2 semaines",
        "cancer_history": True,
        "profile": "subacute",
        "onset": "progressive",
        "annotations": {
            "source": "Cancer + céphalée progressive",
            "keywords": ["cancer du sein", "progressive", "2 semaines"],
            "imaging": "irm_cerebrale_avec_injection"
        }
    },
    {
        "text": "Antécédent de mélanome mal de tête qui empire depuis quelques jours",
        "cancer_history": True,
        "profile": "acute",
        "onset": "progressive",
        "annotations": {
            "source": "Mélanome à haut risque métastatique",
            "keywords": ["mélanome", "empire"],
            "imaging": "irm_cerebrale_avec_injection"
        }
    },

    # ========================================================================
    # CHANGEMENT RÉCENT DE PATTERN (CHRONIQUE AGGRAVÉ)
    # ========================================================================
    {
        "text": "Mes migraines habituelles ont changé depuis un mois plus intenses",
        "recent_pattern_change": True,
        "profile": "chronic",
        "annotations": {
            "source": "Modification céphalée connue = red flag",
            "keywords": ["ont changé", "plus intenses"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Céphalée chronique mais là c'est différent plus violent que d'habitude",
        "recent_pattern_change": True,
        "profile": "chronic",
        "annotations": {
            "source": "Changement de pattern (langage patient)",
            "keywords": ["différent", "plus violent que d'habitude"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "J'ai mal à la tête depuis des années mais depuis 2 semaines c'est pire",
        "recent_pattern_change": True,
        "profile": "chronic",
        "annotations": {
            "source": "Aggravation récente céphalée chronique",
            "keywords": ["depuis des années", "depuis 2 semaines c'est pire"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Mes céphalées de tension habituelles mais maintenant avec vomissements",
        "recent_pattern_change": True,
        "profile": "chronic",
        "annotations": {
            "source": "Nouveaux symptômes sur céphalée connue",
            "keywords": ["habituelles", "maintenant avec vomissements"],
            "note": "Nouveaux symptômes = nécessite réévaluation"
        }
    },
    {
        "text": "Céphalée chronique stable aucun changement depuis des mois",
        "recent_pattern_change": False,
        "profile": "chronic",
        "annotations": {
            "source": "Chronique stable (pas d'urgence)",
            "keywords": ["stable", "aucun changement"]
        }
    },

    # ========================================================================
    # PROFIL SUBAIGU (SOUS-REPRÉSENTÉ)
    # ========================================================================
    {
        "text": "Céphalée qui s'installe progressivement depuis 10 jours",
        "profile": "subacute",
        "onset": "progressive",
        "annotations": {
            "source": "Subaigu typique (1-3 semaines)",
            "keywords": ["progressivement", "10 jours"]
        }
    },
    {
        "text": "Mal de tête apparu il y a 2 semaines qui empire petit à petit",
        "profile": "subacute",
        "onset": "progressive",
        "annotations": {
            "source": "Subaigu progressif",
            "keywords": ["2 semaines", "empire petit à petit"]
        }
    },
    {
        "text": "Douleur crânienne installée sur 3 semaines",
        "profile": "subacute",
        "onset": "progressive",
        "annotations": {
            "source": "Subaigu (formulation médicale)",
            "keywords": ["installée", "3 semaines"]
        }
    },

    # ========================================================================
    # INTENSITÉ EXPLICITE
    # ========================================================================
    {
        "text": "Douleur insupportable intensité 10 sur 10",
        "intensity": 10,
        "annotations": {
            "source": "Intensité maximale (HSA typique)",
            "keywords": ["10 sur 10", "insupportable"]
        }
    },
    {
        "text": "Céphalée sévère je dirais 8 ou 9 sur 10",
        "intensity": 8,
        "annotations": {
            "source": "Intensité élevée",
            "keywords": ["8 ou 9 sur 10", "sévère"]
        }
    },
    {
        "text": "Mal de tête modéré environ 5 sur l'échelle",
        "intensity": 5,
        "annotations": {
            "source": "Intensité modérée",
            "keywords": ["5 sur l'échelle", "modéré"]
        }
    },
    {
        "text": "Douleur légère intensité 3 sur 10",
        "intensity": 3,
        "annotations": {
            "source": "Intensité faible",
            "keywords": ["3 sur 10", "légère"]
        }
    },

    # ========================================================================
    # DURÉE ÉPISODE ACTUEL (avec heures explicites)
    # ========================================================================
    {
        "text": "Céphalée depuis 6 heures",
        "duration_current_episode_hours": 6,
        "profile": "acute",
        "annotations": {
            "source": "Durée courte (hyperaigu)",
            "keywords": ["depuis 6 heures"]
        }
    },
    {
        "text": "Mal de tête depuis 3 jours",
        "duration_current_episode_hours": 72,
        "profile": "acute",
        "annotations": {
            "source": "Durée en jours (3j = 72h)",
            "keywords": ["3 jours"]
        }
    },
    {
        "text": "Douleur présente depuis une semaine",
        "duration_current_episode_hours": 168,
        "profile": "acute",
        "annotations": {
            "source": "1 semaine = limite aigu/subaigu",
            "keywords": ["une semaine"]
        }
    },
    {
        "text": "Céphalée depuis 3 semaines",
        "duration_current_episode_hours": 504,
        "profile": "subacute",
        "annotations": {
            "source": "3 semaines = subaigu",
            "keywords": ["3 semaines"]
        }
    },

    # ========================================================================
    # COMBINAISONS CLINIQUES RÉALISTES
    # ========================================================================
    {
        "text": "Patiente enceinte de 8 mois céphalée progressive sans fièvre ni déficit",
        "pregnancy_postpartum": True,
        "profile": "acute",
        "onset": "progressive",
        "fever": False,
        "neuro_deficit": False,
        "annotations": {
            "source": "Grossesse = red flag même sans autres signes",
            "keywords": ["enceinte", "progressive", "sans fièvre"],
            "diagnosis": "TVC, PRES, éclampsie à éliminer",
            "imaging": "irm_cerebrale_angio_veineuse"
        }
    },
    {
        "text": "Post-partum 10 jours céphalée qui empire progressivement",
        "pregnancy_postpartum": True,
        "profile": "acute",
        "onset": "progressive",
        "annotations": {
            "source": "Post-partum = TVC jusqu'à preuve du contraire",
            "keywords": ["post-partum", "empire progressivement"],
            "imaging": "irm_angio_veineuse"
        }
    },
    {
        "text": "Homme 65 ans première céphalée de sa vie temporale gauche",
        "age": 65,
        "new_onset_after_50": True,
        "profile": "acute",
        "annotations": {
            "source": "Nouveau onset >50 ans = Horton à éliminer",
            "keywords": ["65 ans", "première céphalée", "temporale"],
            "diagnosis": "Artérite temporale (Horton)",
            "imaging": "Doppler artères temporales + CRP + biopsie"
        }
    },
    {
        "text": "Céphalée explosive pendant rapport sexuel",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Céphalée coïtale = SVCR ou HSA",
            "keywords": ["explosive", "rapport sexuel"],
            "imaging": "scanner_cerebral_angioscanner",
            "note": "SVCR fréquent dans ce contexte"
        }
    },
    {
        "text": "Douleur maximale d'emblée pendant effort physique intense",
        "onset": "thunderclap",
        "profile": "acute",
        "annotations": {
            "source": "Thunderclap à l'effort = HSA ou SVCR",
            "keywords": ["maximale d'emblée", "effort physique"],
            "imaging": "scanner_cerebral"
        }
    },

    # ========================================================================
    # CRISES CONVULSIVES (ENRICHIR)
    # ========================================================================
    {
        "text": "Crise généralisée tonico-clonique ce matin suivie de céphalée",
        "seizure": True,
        "profile": "acute",
        "annotations": {
            "source": "Épilepsie + céphalée",
            "keywords": ["crise généralisée", "tonico-clonique"],
            "imaging": "irm_cerebrale"
        }
    },
    {
        "text": "Mouvements anormaux du bras droit puis mal de tête intense",
        "seizure": True,
        "neuro_deficit": True,
        "profile": "acute",
        "annotations": {
            "source": "Crise focale avec déficit post-critique",
            "keywords": ["mouvements anormaux", "bras droit"],
            "imaging": "irm_cerebrale_urgence"
        }
    },
    {
        "text": "Aucune crise d'épilepsie jamais convulsé",
        "seizure": False,
        "annotations": {
            "source": "Négation explicite crises",
            "keywords": ["aucune crise", "jamais convulsé"]
        }
    },

    # ========================================================================
    # AGGRAVATION DÉCUBITUS (HTIC)
    # ========================================================================
    {
        "text": "Céphalée pire quand je suis allongé soulagée debout",
        "htic_pattern": True,
        "annotations": {
            "source": "HTIC - aggravation décubitus typique",
            "keywords": ["pire allongé", "soulagée debout"],
            "note": "Signe cardinal HTIC"
        }
    },
    {
        "text": "Mal de tête au réveil qui s'améliore dans la journée",
        "htic_pattern": True,
        "annotations": {
            "source": "Céphalée matutinale HTIC",
            "keywords": ["au réveil", "s'améliore dans la journée"]
        }
    },
    {
        "text": "Douleur augmente quand je me penche en avant",
        "htic_pattern": True,
        "annotations": {
            "source": "Aggravation posturale HTIC",
            "keywords": ["augmente", "penche en avant"]
        }
    },

    # ========================================================================
    # VARIANTES LINGUISTIQUES IMPORTANTES
    # ========================================================================
    {
        "text": "Grosse migraine comme d'habitude rien de nouveau",
        "profile": "chronic",
        "recent_pattern_change": False,
        "headache_profile": "migraine_like",
        "annotations": {
            "source": "Migraine habituelle stable",
            "keywords": ["comme d'habitude", "rien de nouveau"],
            "note": "Pas d'urgence si migraine connue identique"
        }
    },
    {
        "text": "C'est pas ma migraine habituelle c'est autre chose",
        "recent_pattern_change": True,
        "annotations": {
            "source": "Patient identifie différence = red flag",
            "keywords": ["pas habituelle", "autre chose"],
            "note": "Toujours prendre au sérieux"
        }
    },
    {
        "text": "Première fois de ma vie que j'ai aussi mal à la tête",
        "profile": "acute",
        "new_headache": True,
        "annotations": {
            "source": "Première céphalée = à explorer",
            "keywords": ["première fois", "de ma vie"],
            "imaging": "selon contexte clinique"
        }
    },
]


def get_examples_by_field(field: str, value: Any = True) -> List[Dict[str, Any]]:
    """Récupère tous les exemples annotés pour un champ donné.

    Args:
        field: Nom du champ (fever, onset, meningeal_signs, etc.)
        value: Valeur recherchée (par défaut True)

    Returns:
        Liste d'exemples correspondants
    """
    return [ex for ex in MEDICAL_EXAMPLES if ex.get(field) == value]


def get_all_texts() -> List[str]:
    """Retourne tous les textes du corpus."""
    return [ex["text"] for ex in MEDICAL_EXAMPLES]


def get_corpus_statistics() -> Dict[str, int]:
    """Statistiques du corpus."""
    stats = {
        "total_examples": len(MEDICAL_EXAMPLES),
        "with_onset": len([ex for ex in MEDICAL_EXAMPLES if "onset" in ex]),
        "with_fever": len([ex for ex in MEDICAL_EXAMPLES if "fever" in ex]),
        "with_meningeal": len([ex for ex in MEDICAL_EXAMPLES if "meningeal_signs" in ex]),
        "with_htic": len([ex for ex in MEDICAL_EXAMPLES if "htic_pattern" in ex]),
        "with_neuro_deficit": len([ex for ex in MEDICAL_EXAMPLES if "neuro_deficit" in ex]),
        "with_trauma": len([ex for ex in MEDICAL_EXAMPLES if "trauma" in ex]),
        "with_profile": len([ex for ex in MEDICAL_EXAMPLES if "headache_profile" in ex]),
    }
    return stats


if __name__ == "__main__":
    # Afficher statistiques du corpus
    stats = get_corpus_statistics()
    print("=" * 60)
    print("CORPUS MÉDICAL - Statistiques")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key:25s}: {value:3d}")
    print("=" * 60)

    # Exemples par catégorie
    print("\nExemples ONSET thunderclap:")
    for ex in get_examples_by_field("onset", "thunderclap")[:3]:
        print(f"  • {ex['text']}")

    print("\nExemples FIÈVRE (positifs):")
    for ex in get_examples_by_field("fever", True)[:3]:
        print(f"  • {ex['text']}")
