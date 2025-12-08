"""
Module de génération d'ordonnances médicales.

Génère des ordonnances formatées pour les examens d'imagerie
recommandés par le système d'évaluation des céphalées.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import HeadacheCase, ImagingRecommendation


def generate_prescription(
    case: HeadacheCase,
    recommendation: ImagingRecommendation,
    doctor_name: str = "Dr. [NOM]",
    output_dir: Optional[Path] = None
) -> Path:
    """Génère une ordonnance médicale formatée.
    
    Args:
        case: Cas clinique du patient
        recommendation: Recommandation d'imagerie
        doctor_name: Nom du médecin prescripteur
        output_dir: Répertoire de sortie (défaut: ordonnances/)
        
    Returns:
        Path vers le fichier d'ordonnance généré
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "ordonnances"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Nom du fichier avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ordonnance_{timestamp}.txt"
    filepath = output_dir / filename
    
    # Générer le contenu
    content = _format_prescription(case, recommendation, doctor_name)
    
    # Écrire le fichier
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def _format_prescription(
    case: HeadacheCase,
    recommendation: ImagingRecommendation,
    doctor_name: str
) -> str:
    """Formate le contenu de l'ordonnance.
    
    Args:
        case: Cas clinique
        recommendation: Recommandation d'imagerie
        doctor_name: Nom du prescripteur
        
    Returns:
        Contenu formaté de l'ordonnance
    """
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    # En-tête
    lines = [
        "="*70,
        "ORDONNANCE MÉDICALE",
        "="*70,
        "",
        f"Date: {date_str}",
        f"Prescripteur: {doctor_name}",
        "",
        "-"*70,
        "INFORMATIONS PATIENT",
        "-"*70,
        f"Âge: {case.age} ans",
        f"Sexe: {_format_sex(case.sex)}",
        "",
    ]
    
    # Contexte clinique
    if case.pregnancy_postpartum:
        lines.append("CONTEXTE: PATIENTE ENCEINTE OU POST-PARTUM")
        lines.append("")
    
    # Indications cliniques
    lines.extend([
        "-"*70,
        "INDICATION CLINIQUE",
        "-"*70,
        _format_clinical_indication(case),
        "",
    ])
    
    # Examens prescrits
    lines.extend([
        "-"*70,
        "EXAMENS DEMANDÉS",
        "-"*70,
    ])
    
    if recommendation.imaging and "aucun" not in recommendation.imaging:
        for i, exam in enumerate(recommendation.imaging, 1):
            lines.append(f"{i}. {_format_exam_name(exam)}")
    else:
        lines.append("Aucun examen d'imagerie prescrit")
    
    lines.append("")
    
    # Urgence
    urgency_text = {
        "immediate": "URGENCE IMMÉDIATE - À réaliser dans les heures qui suivent",
        "urgent": "URGENCE - À réaliser dans les 24 heures",
        "delayed": "Semi-urgent - À réaliser dans les 7 jours",
        "none": "Non urgent"
    }
    
    lines.extend([
        "-"*70,
        "DEGRÉ D'URGENCE",
        "-"*70,
        urgency_text.get(recommendation.urgency, "Non spécifié"),
        "",
    ])
    
    # Précautions et contre-indications
    if case.pregnancy_postpartum:
        urgency_level = recommendation.urgency
        lines.extend([
            "-"*70,
            "PRÉCAUTIONS IMPORTANTES",
            "-"*70,
            "PATIENTE ENCEINTE:",
        ])
        
        if urgency_level == "immediate":
            lines.extend([
                "- URGENCE VITALE: Scanner acceptable (bénéfice > risque)",
                "- Protection abdominale plombée, dose minimale",
                "- IRM alternative si délai compatible avec urgence",
                "- Scanner éviter si grossesse < 4 semaines (organogenèse)",
            ])
        elif urgency_level == "urgent":
            lines.extend([
                "- IRM acceptable en urgence (risque TVC > risque IRM)",
                "- IRM idéale à partir 2e trimestre (> 13 sem)",
                "- Scanner uniquement si urgence vitale ou IRM impossible",
            ])
        else:
            lines.extend([
                "- Privilégier IRM (éviter radiations scanner)",
                "- IRM éviter 1er trimestre (< 13 sem) sauf urgence",
                "- Scanner uniquement si urgence vitale",
            ])
        
        lines.extend([
            "- Gadolinium contre-indiqué pendant grossesse sauf urgence absolue",
            "- Risque TVC augmenté : vigilance accrue",
            "",
        ])
    elif case.sex == "F" and case.age < 50:
        lines.extend([
            "-"*70,
            "PRÉCAUTIONS IMPORTANTES",
            "-"*70,
            "FEMME EN ÂGE DE PROCRÉER:",
            "- Test de grossesse obligatoire avant scanner",
            "",
        ])
    
    # Renseignements cliniques pour le radiologue
    lines.extend([
        "-"*70,
        "RENSEIGNEMENTS CLINIQUES",
        "-"*70,
        recommendation.comment.split("\n\n")[0],  # Premier paragraphe
        "",
    ])
    
    # Signature
    lines.extend([
        "",
        "-"*70,
        "",
        f"Signature du prescripteur: {doctor_name}",
        "",
        "="*70,
    ])
    
    return "\n".join(lines)


def _format_sex(sex: str) -> str:
    """Formate le sexe pour l'affichage."""
    mapping = {"M": "Masculin", "F": "Féminin", "Other": "Autre"}
    return mapping.get(sex, sex)


def _format_clinical_indication(case: HeadacheCase) -> str:
    """Génère l'indication clinique."""
    indications = []
    
    # Profil
    if case.profile == "acute":
        indications.append("Céphalée aiguë")
    elif case.profile == "subacute":
        indications.append("Céphalée subaiguë")
    elif case.profile == "chronic":
        indications.append("Céphalée chronique")
    
    # Onset
    if case.onset == "thunderclap":
        indications.append("Début brutal en coup de tonnerre")
    elif case.onset == "progressive":
        indications.append("Début progressif")
    
    # Red flags
    if case.fever:
        indications.append("Fièvre associée")
    if case.meningeal_signs:
        indications.append("Signes méningés")
    if case.neuro_deficit:
        indications.append("Déficit neurologique")
    if case.seizure:
        indications.append("Crise comitiale")
    if case.htic_pattern:
        indications.append("Signes d'HTIC")
    
    # Contextes
    if case.trauma:
        indications.append("Contexte traumatique")
    if case.immunosuppression:
        indications.append("Patient immunodéprimé")
    
    if indications:
        return "Céphalée. " + ". ".join(indications) + "."
    return "Céphalée à explorer."


def _format_exam_name(exam: str) -> str:
    """Formate le nom de l'examen pour l'ordonnance."""
    exam_names = {
        "scanner_cerebral_sans_injection": "Scanner cérébral sans injection",
        "scanner_cerebral_avec_injection": "Scanner cérébral avec injection",
        "irm_cerebrale": "IRM cérébrale",
        "IRM_cerebrale": "IRM cérébrale",
        "IRM_cerebrale_avec_gadolinium": "IRM cérébrale avec gadolinium",
        "angio_irm_veineuse": "Angio-IRM veineuse",
        "angio_irm": "Angio-IRM",
        "ARM_cerebrale": "Angio-IRM artérielle cérébrale",
        "venographie_IRM": "Vénographie IRM",
        "angioscanner_cerebral": "Angioscanner cérébral",
        "angioscanner": "Angioscanner",
        "ponction_lombaire": "Ponction lombaire",
        "irm_rachis": "IRM du rachis",
        "doppler_TSA": "Doppler des troncs supra-aortiques",
        "angioscanner_TSA": "Angioscanner des troncs supra-aortiques",
        "echographie_arteres_temporales": "Échographie des artères temporales",
        "biopsie_artere_temporale": "Biopsie de l'artère temporale",
        "fond_oeil": "Fond d'œil",
    }
    
    return exam_names.get(exam, exam.replace("_", " ").title())
