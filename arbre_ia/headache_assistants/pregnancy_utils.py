# fichier qui gère la détection de grossesse

import re
from typing import Optional


def extract_pregnancy_weeks(text: str) -> Optional[float]:
    """Extrait la durée de grossesse en semaines depuis le texte.

    Formats supportés:
    - "8 semaines" / "8 sem" / "8s"
    - "8 SA" / "8SA" (Semaines d'Aménorrhée)
    - "2 mois" (converti en semaines: mois * 4.33)
    - "56 jours" (converti en semaines: jours / 7)
    - "1er trimestre" / "T1" / "premier trimestre" → 6.5 sem (milieu T1)
    - "2ème trimestre" / "T2" / "deuxième trimestre" → 21 sem (milieu T2)
    - "3ème trimestre" / "T3" / "troisième trimestre" → 35 sem (milieu T3)

    Args:
        text: Texte à analyser

    Returns:
        Nombre de semaines de grossesse, ou None si non trouvé
    """
    text_lower = text.lower()

    # Pattern 1: Trimestre explicite (priorité haute)
    # 1er trimestre: 0-13 sem → moyenne 6.5
    # 2ème trimestre: 14-27 sem → moyenne 20.5
    # 3ème trimestre: 28-40 sem → moyenne 34
    trimester_match = re.search(
        r'(?:1er|premier|t1|trimestre\s*1)\s*trimestre',
        text_lower
    )
    if trimester_match:
        return 6.5  # Milieu du 1er trimestre

    trimester_match = re.search(
        r'(?:2[èe]me|deuxi[èe]me|t2|trimestre\s*2)\s*trimestre',
        text_lower
    )
    if trimester_match:
        return 20.5  # Milieu du 2ème trimestre

    trimester_match = re.search(
        r'(?:3[èe]me|troisi[èe]me|t3|trimestre\s*3)\s*trimestre',
        text_lower
    )
    if trimester_match:
        return 34.0  # Milieu du 3ème trimestre

    # Pattern 2: Semaines d'Aménorrhée (SA)
    sa_match = re.search(r'(\d+(?:\.\d+)?)\s*sa\b', text_lower)
    if sa_match:
        return float(sa_match.group(1))

    # Pattern 3: Semaines explicites
    sem_match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:semaines?|sem)\b',
        text_lower
    )
    if sem_match:
        return float(sem_match.group(1))

    # Pattern 4: Mois (conversion: 1 mois ≈ 4.33 semaines)
    mois_match = re.search(r'(\d+(?:\.\d+)?)\s*mois', text_lower)
    if mois_match:
        mois = float(mois_match.group(1))
        return mois * 4.33

    # Pattern 5: Jours (conversion: jours / 7)
    jours_match = re.search(r'(\d+)\s*jours?', text_lower)
    if jours_match:
        jours = int(jours_match.group(1))
        # Seulement si contexte grossesse (sinon "3 jours" = durée céphalée)
        if any(term in text_lower for term in ['enceinte', 'grossesse', 'gravid']):
            return jours / 7.0

    return None


def calculate_trimester(weeks: Optional[float]) -> Optional[int]:
    """Calcule le trimestre de grossesse à partir du nombre de semaines.

    Règles médicales:
    - 1er trimestre: 0-13 semaines (< 14)
    - 2ème trimestre: 14-27 semaines (14 ≤ x < 28)
    - 3ème trimestre: 28-40 semaines (≥ 28)

    Args:
        weeks: Nombre de semaines de grossesse

    Returns:
        Trimestre (1, 2 ou 3), ou None si weeks est None ou invalide
    """
    if weeks is None:
        return None

    # Validation: grossesse normale = 0-42 semaines
    if weeks < 0 or weeks > 42:
        return None

    if weeks < 14:
        return 1
    elif weeks < 28:
        return 2
    else:
        return 3


def extract_pregnancy_trimester(text: str) -> Optional[int]:
    """Extrait le trimestre de grossesse depuis le texte.

    Fonction principale combinant extraction de durée et calcul de trimestre.

    Args:
        text: Texte à analyser

    Returns:
        Trimestre (1, 2 ou 3), ou None si non détecté
    """
    weeks = extract_pregnancy_weeks(text)
    return calculate_trimester(weeks)
