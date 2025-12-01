"""Moteur de règles médicales pour l'évaluation des céphalées.

Ce module implémente le moteur de décision basé sur les règles extraites
de headache_rules.txt et stockées dans headache_rules.json.

Fonctions principales:
- load_rules() : Charge les règles depuis le JSON
- match_rule(case, rule) : Vérifie si un cas correspond à une règle
- decide_imaging(case) : Décide de l'imagerie à prescrire
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import HeadacheCase, ImagingRecommendation


def load_rules(rules_path: Optional[Path] = None) -> Dict[str, Any]:
    """Charge les règles médicales depuis le fichier JSON.
    
    Args:
        rules_path: Chemin vers le fichier de règles (optionnel).
                   Si None, utilise le chemin par défaut.
        
    Returns:
        Dictionnaire contenant toutes les règles médicales
        
    Raises:
        FileNotFoundError: Si le fichier de règles n'existe pas
        json.JSONDecodeError: Si le fichier JSON est invalide
        
    Example:
        >>> rules = load_rules()
        >>> print(rules["metadata"]["version"])
        '1.0'
        >>> print(len(rules["rules"]))
        17
    """
    if rules_path is None:
        # Chemin par défaut vers le fichier de règles
        rules_path = Path(__file__).parent.parent / "rules" / "headache_rules.json"
    
    rules_path = Path(rules_path)
    
    if not rules_path.exists():
        raise FileNotFoundError(f"Fichier de règles introuvable: {rules_path}")
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def match_rule(case: HeadacheCase, rule: Dict[str, Any]) -> bool:
    """Vérifie si un cas de céphalée correspond aux conditions d'une règle.
    
    Cette fonction évalue toutes les conditions définies dans la règle
    et applique la logique spécifiée ("all" ou "any").
    
    Args:
        case: Cas de céphalée à évaluer (modèle Pydantic HeadacheCase)
        rule: Règle médicale (dictionnaire avec "conditions" et "logic")
        
    Returns:
        True si le cas correspond à la règle, False sinon
        
    Logique d'évaluation:
        - "all": Toutes les conditions doivent être satisfaites (ET logique)
        - "any": Au moins une condition doit être satisfaite (OU logique)
        
    Gestion des conditions spéciales:
        - Champs avec "_min" : Valeur >= seuil minimum
        - Champs avec "_max" : Valeur <= seuil maximum
        - Listes : Vérification d'appartenance
        - Booléens : Comparaison directe
        - Autres : Égalité stricte
        
    Example:
        >>> case = HeadacheCase(age=55, onset="thunderclap", profile="acute")
        >>> rule = {
        ...     "logic": "all",
        ...     "conditions": {"onset": "thunderclap", "profile": "acute"}
        ... }
        >>> match_rule(case, rule)
        True
    """
    conditions = rule.get("conditions", {})
    logic = rule.get("logic", "all")
    
    # Si pas de conditions, la règle ne match pas
    if not conditions:
        return False
    
    matches = []
    
    for key, expected_value in conditions.items():
        # Gérer les champs avec suffixes spéciaux
        if key.endswith("_min"):
            # Comparaison >= pour les minimums
            field_name = key[:-4]  # Retire "_min"
            actual_value = getattr(case, field_name, None)
            
            if actual_value is None:
                matches.append(False)
            else:
                matches.append(actual_value >= expected_value)
        
        elif key.endswith("_max"):
            # Comparaison <= pour les maximums
            field_name = key[:-4]  # Retire "_max"
            actual_value = getattr(case, field_name, None)
            
            if actual_value is None:
                matches.append(False)
            else:
                matches.append(actual_value <= expected_value)
        
        elif key.endswith("_count_min"):
            # Compte d'éléments dans une liste >= minimum
            field_name = key[:-10]  # Retire "_count_min"
            actual_list = getattr(case, field_name, None)
            
            if actual_list is None:
                matches.append(False)
            elif isinstance(actual_list, list):
                matches.append(len(actual_list) >= expected_value)
            else:
                matches.append(False)
        
        else:
            # Récupérer la valeur actuelle du cas
            actual_value = getattr(case, key, None)
            
            # Cas spécial : expected_value est une liste vide
            if isinstance(expected_value, list) and len(expected_value) == 0:
                # Vérifier que le champ est vide ou None
                if actual_value is None:
                    matches.append(True)
                elif isinstance(actual_value, list):
                    matches.append(len(actual_value) == 0)
                else:
                    matches.append(False)
            
            elif isinstance(expected_value, list):
                # expected_value est une liste non-vide
                # Vérifier si actual_value est dedans OU si intersection
                if isinstance(actual_value, list):
                    # Vérifier si au moins un élément de actual_value est dans expected_value
                    matches.append(any(item in expected_value for item in actual_value))
                else:
                    # Vérifier si actual_value est dans la liste expected_value
                    matches.append(actual_value in expected_value)
            
            elif isinstance(expected_value, bool):
                # Comparaison booléenne stricte
                matches.append(actual_value is expected_value)
            
            else:
                # Comparaison d'égalité standard
                matches.append(actual_value == expected_value)
    
    # Appliquer la logique spécifiée dans la règle
    if logic == "all":
        # Toutes les conditions doivent être vraies
        return all(matches) if matches else False
    elif logic == "any":
        # Au moins une condition doit être vraie
        return any(matches) if matches else False
    else:
        # Logique non reconnue, considérer comme "all" par défaut
        return all(matches) if matches else False


def decide_imaging(
    case: HeadacheCase, 
    rules_path: Optional[Path] = None
) -> ImagingRecommendation:
    """Décide de l'imagerie à prescrire en fonction du cas de céphalée.
    
    Cette fonction applique le moteur de décision basé sur les règles médicales:
    1. Charge les règles depuis le JSON
    2. Parcourt les règles dans l'ordre
    3. Applique la PREMIÈRE règle qui match
    4. Retourne une recommandation fallback si aucune règle ne match
    
    Args:
        case: Cas de céphalée à évaluer (modèle Pydantic HeadacheCase)
        rules_path: Chemin optionnel vers le fichier de règles
        
    Returns:
        ImagingRecommendation avec l'imagerie recommandée, l'urgence et un commentaire
        
    Stratégie de décision:
        - Première règle matchée = règle appliquée (pas de recherche exhaustive)
        - Priorisation implicite par l'ordre des règles dans le JSON
        - Fallback: Scanner cérébral en urgence si aucune règle ne match
        
    Example:
        >>> case = HeadacheCase(
        ...     age=55, sex="F", profile="acute", onset="thunderclap"
        ... )
        >>> recommendation = decide_imaging(case)
        >>> print(recommendation.urgency)
        'immediate'
        >>> print(recommendation.imaging)
        ['scanner_cerebral_sans_injection', 'ponction_lombaire']
    """
    # 1. Charger les règles
    rules_data = load_rules(rules_path)
    rules_list = rules_data.get("rules", [])
    
    # 2. Parcourir les règles dans l'ordre
    for rule in rules_list:
        # 3. Vérifier si la règle match le cas
        if match_rule(case, rule):
            # 4. Première règle matchée = appliquer immédiatement
            recommendation_data = rule.get("recommendation", {})
            
            recommendation = ImagingRecommendation(
                imaging=recommendation_data.get("imaging", []),
                urgency=recommendation_data.get("urgency", "none"),
                comment=recommendation_data.get("comment", ""),
                applied_rule_id=rule.get("id")
            )
            
            # 5. Appliquer les adaptations contextuelles (grossesse, etc.)
            recommendation = _apply_contextual_adaptations(case, recommendation)
            
            return recommendation
    
    # 6. Aucune règle ne match : retourner recommandation fallback
    fallback = _get_fallback_recommendation(case)
    return _apply_contextual_adaptations(case, fallback)


def _apply_contextual_adaptations(
    case: HeadacheCase, 
    recommendation: ImagingRecommendation
) -> ImagingRecommendation:
    """Applique des adaptations contextuelles à la recommandation d'imagerie.
    
    Règles transversales PRIORITAIRES appliquées APRÈS sélection de la règle principale:
    
    PROTOCOLE SCANNER:
    - Contre-indication absolue si grossesse < 2-4 semaines
    - Femme < 50 ans : nécessite test de grossesse
    - Scanner injecté : créatinine si > 60 ans ou ATCD rénaux
    - Scanner injecté : vérifier allergie produit de contraste iodé
    
    PROTOCOLE IRM:
    - Grossesse < 3 mois : contre-indication, privilégier scanner
    - Chirurgie récente < 6 semaines avec matériel : attendre ou urgence seulement
    - Pace-maker, valve cardiaque : vérifier compatibilité centre imagerie
    - Claustrophobie : vérifier avec centre imagerie
    - IRM injectée : vérifier allergie si ATCD IRM injectée
    
    RÈGLES CÉPHALÉES:
    - Contexte oncologique : Scanner en 1ère intention
    - Brutale/fébrile/déficit : Urgences
    - Reste : IRM 1ère intention, scanner si contre-indication
    
    Args:
        case: Cas de céphalée avec contexte
        recommendation: Recommandation initiale à adapter
        
    Returns:
        Recommandation adaptée avec précautions/contre-indications
    """
    adapted_imaging = list(recommendation.imaging)
    adapted_comment = recommendation.comment
    precautions = []
    contraindications = []
    
    # ========================================================================
    # RÈGLE 1: GROSSESSE - Gestion complexe selon trimestre
    # ========================================================================
    if case.pregnancy_postpartum is True:
        scanner_found = False
        irm_found = False
        new_imaging = []
        
        for exam in adapted_imaging:
            if "scanner" in exam.lower():
                scanner_found = True
                # Remplacer scanner par IRM (sauf contexte oncologique)
                if "injection" in exam.lower() and "sans" not in exam.lower():
                    new_imaging.append("IRM_cerebrale_avec_gadolinium")
                else:
                    new_imaging.append("irm_cerebrale")
            elif "irm" in exam.lower():
                irm_found = True
                new_imaging.append(exam)
            else:
                new_imaging.append(exam)
        
        # Ajouter angio-IRM veineuse si pas déjà présente (risque TVC)
        if "angio_irm_veineuse" not in new_imaging:
            new_imaging.append("angio_irm_veineuse")
        
        adapted_imaging = new_imaging
        
        # Ajouter précautions grossesse
        precautions.append("PATIENTE ENCEINTE:")
        if scanner_found:
            precautions.append("- Scanner remplacé par IRM (éviter radiations)")
            contraindications.append("- Scanner contre-indiqué si grossesse < 2-4 semaines")
        if irm_found or scanner_found:
            contraindications.append("- IRM contre-indiquée si grossesse < 3 mois (privilégier scanner si urgence)")
        precautions.append("- Risque TVC augmenté en grossesse/post-partum")
    
    # ========================================================================
    # RÈGLE 2: CONTEXTE ONCOLOGIQUE - Scanner en priorité
    # ========================================================================
    # TODO: Ajouter champ cancer/oncologique dans HeadacheCase
    # Si contexte oncologique détecté, privilégier scanner
    
    # ========================================================================
    # RÈGLE 3: FEMME < 50 ANS - Test grossesse avant scanner
    # ========================================================================
    if case.sex == "F" and case.age < 50:
        for exam in adapted_imaging:
            if "scanner" in exam.lower():
                precautions.append("FEMME < 50 ANS:")
                precautions.append("- Test de grossesse urinaire OBLIGATOIRE avant scanner")
                precautions.append("- Sauf si ménopause précoce confirmée")
                break
    
    # ========================================================================
    # RÈGLE 4: SCANNER INJECTÉ - Créatinine et allergie
    # ========================================================================
    for exam in adapted_imaging:
        exam_lower = exam.lower()
        # Vérifier scanner AVEC injection (pas "sans_injection")
        if "scanner" in exam_lower and ("avec_injection" in exam_lower or ("injection" in exam_lower and "sans" not in exam_lower)):
            precautions.append("SCANNER INJECTÉ:")
            if case.age > 60:
                precautions.append("- Dosage créatinine OBLIGATOIRE (patient > 60 ans)")
            precautions.append("- Vérifier absence allergie produit de contraste iodé")
            precautions.append("- Allergie crustacés/Bétadine à préciser mais ne contre-indique pas")
            break
    
    # ========================================================================
    # RÈGLE 5: IRM - Contre-indications matériel et claustrophobie
    # ========================================================================
    for exam in adapted_imaging:
        if "irm" in exam.lower():
            precautions.append("IRM - VÉRIFICATIONS NÉCESSAIRES:")
            precautions.append("- Chirurgie récente < 6 semaines avec matériel? Attendre ou urgence seulement")
            precautions.append("- Pace-maker? Contacter centre imagerie (compatibilité spécifique)")
            precautions.append("- Valve cardiaque/prothèse aortique? Envoyer références matériel au centre")
            precautions.append("- Prothèse articulaire/ostéosynthèse > 6 sem: OK")
            precautions.append("- Claustrophobie? Contacter centre imagerie")
            if "injection" in exam.lower():
                precautions.append("- IRM injectée: vérifier allergie si ATCD IRM injectée")
            break
    
    # ========================================================================
    # Construire commentaire final
    # ========================================================================
    if precautions or contraindications:
        full_comment = adapted_comment + "\n\n"
        
        if contraindications:
            full_comment += "CONTRE-INDICATIONS:\n" + "\n".join(contraindications) + "\n\n"
        
        if precautions:
            full_comment += "PRÉCAUTIONS ET VÉRIFICATIONS:\n" + "\n".join(precautions)
        
        return ImagingRecommendation(
            imaging=adapted_imaging,
            urgency=recommendation.urgency,
            comment=full_comment,
            applied_rule_id=recommendation.applied_rule_id
        )
    
    return recommendation


def _get_fallback_recommendation(case: HeadacheCase) -> ImagingRecommendation:
    """Génère une recommandation fallback si aucune règle ne correspond.
    
    Stratégie fallback basée sur le profil:
    - Aigu : Scanner cérébral en urgence (éliminer cause secondaire)
    - Subaïgu : Scanner ou IRM en semi-urgence
    - Chronique : Pas d'imagerie systématique (consulter neurologue)
    
    Args:
        case: Cas de céphalée
        
    Returns:
        ImagingRecommendation fallback adaptée au profil
    """
    if case.profile == "acute":
        # Céphalée aiguë sans règle spécifique : bilan étiologique
        return ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection"],
            urgency="urgent",
            comment=(
                "Céphalée aiguë inhabituelle sans correspondance règle spécifique. "
                "Scanner cérébral recommandé pour éliminer cause secondaire grave "
                "(HSA, méningite, processus expansif). Examen neurologique complet requis."
            ),
            applied_rule_id="FALLBACK_ACUTE"
        )
    
    elif case.profile == "subacute":
        # Céphalée subaiguë : IRM préférée au scanner
        return ImagingRecommendation(
            imaging=["irm_cerebrale"],
            urgency="delayed",
            comment=(
                "Céphalée subaiguë d'aggravation progressive. IRM cérébrale recommandée "
                "pour recherche processus expansif, HTIC, TVC. Consultation neurologique "
                "dans les 7 jours."
            ),
            applied_rule_id="FALLBACK_SUBACUTE"
        )
    
    elif case.profile == "chronic":
        # Céphalée chronique : pas d'imagerie systématique sauf red flags
        if case.has_red_flags():
            return ImagingRecommendation(
                imaging=["irm_cerebrale"],
                urgency="urgent",
                comment=(
                    "Céphalée chronique avec signes d'alarme. IRM cérébrale recommandée "
                    "pour éliminer processus secondaire. Consultation neurologique urgente."
                ),
                applied_rule_id="FALLBACK_CHRONIC_RED_FLAGS"
            )
        else:
            return ImagingRecommendation(
                imaging=[],
                urgency="none",
                comment=(
                    "Céphalée chronique sans signe d'alarme. Pas d'imagerie systématique "
                    "si examen neurologique normal. Traitement symptomatique et consultation "
                    "neurologique programmée si nécessaire."
                ),
                applied_rule_id="FALLBACK_CHRONIC_NO_FLAGS"
            )
    
    else:
        # Profil non reconnu : approche conservatrice
        return ImagingRecommendation(
            imaging=["scanner_cerebral_sans_injection"],
            urgency="urgent",
            comment=(
                "Profil de céphalée non classifiable. Par prudence, bilan étiologique "
                "recommandé. Consultation neurologique pour évaluation approfondie."
            ),
            applied_rule_id="FALLBACK_UNKNOWN"
        )


# ==============================================================================
# Classe RulesEngine (interface orientée objet alternative)
# ==============================================================================

class RulesEngine:
    """Moteur de règles pour l'évaluation diagnostique des céphalées.
    
    Cette classe fournit une interface orientée objet pour le moteur de décision.
    Elle charge les règles au moment de l'initialisation et les garde en cache.
    
    Utilisation recommandée pour des évaluations multiples (évite de recharger
    le JSON à chaque fois).
    
    Example:
        >>> engine = RulesEngine()
        >>> case = HeadacheCase(age=55, onset="thunderclap", profile="acute")
        >>> recommendation = engine.decide_imaging(case)
        >>> print(recommendation.urgency)
        'immediate'
    """
    
    def __init__(self, rules_path: Optional[Path] = None):
        """Initialise le moteur de règles.
        
        Args:
            rules_path: Chemin vers le fichier JSON des règles.
                       Si None, utilise le chemin par défaut.
        """
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "rules" / "headache_rules.json"
        
        self.rules_path = Path(rules_path)
        self.rules_data: Dict[str, Any] = {}
        self.rules: List[Dict[str, Any]] = []
        self.red_flags_catalog: Dict[str, Any] = {}
        self.imaging_catalog: Dict[str, Any] = {}
        self.urgency_levels: Dict[str, Any] = {}
        
        self._load_rules()
    
    def _load_rules(self) -> None:
        """Charge les règles depuis le fichier JSON (méthode interne)."""
        self.rules_data = load_rules(self.rules_path)
        self.rules = self.rules_data.get("rules", [])
        self.red_flags_catalog = self.rules_data.get("red_flags_catalog", {})
        self.imaging_catalog = self.rules_data.get("imaging_catalog", {})
        self.urgency_levels = self.rules_data.get("urgency_levels", {})
    
    def reload_rules(self) -> None:
        """Recharge les règles depuis le fichier (utile pour le développement)."""
        self._load_rules()
    
    def match_rule(self, case: HeadacheCase, rule: Dict[str, Any]) -> bool:
        """Vérifie si un cas correspond aux conditions d'une règle.
        
        Wrapper autour de la fonction match_rule() pour compatibilité OO.
        
        Args:
            case: Cas de céphalée
            rule: Règle médicale
            
        Returns:
            True si le cas correspond à la règle
        """
        return match_rule(case, rule)
    
    def decide_imaging(self, case: HeadacheCase) -> ImagingRecommendation:
        """Décide de l'imagerie à prescrire.
        
        Version orientée objet de decide_imaging() qui utilise les règles
        déjà chargées en mémoire.
        
        Args:
            case: Cas de céphalée à évaluer
            
        Returns:
            ImagingRecommendation avec l'imagerie recommandée
        """
        # Parcourir les règles dans l'ordre
        for rule in self.rules:
            if self.match_rule(case, rule):
                # Première règle matchée = appliquée
                recommendation_data = rule.get("recommendation", {})
                
                return ImagingRecommendation(
                    imaging=recommendation_data.get("imaging", []),
                    urgency=recommendation_data.get("urgency", "none"),
                    comment=recommendation_data.get("comment", ""),
                    applied_rule_id=rule.get("id")
                )
        
        # Aucune règle ne match : fallback
        return _get_fallback_recommendation(case)
    
    def find_matching_rules(self, case: HeadacheCase) -> List[Dict[str, Any]]:
        """Trouve TOUTES les règles qui correspondent au cas.
        
        Contrairement à decide_imaging() qui s'arrête à la première règle,
        cette méthode retourne toutes les règles qui matchent.
        Utile pour le debugging et l'analyse.
        
        Args:
            case: Cas de céphalée
            
        Returns:
            Liste des règles correspondantes (peut être vide)
        """
        matching_rules = []
        
        for rule in self.rules:
            if self.match_rule(case, rule):
                matching_rules.append(rule)
        
        return matching_rules
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une règle par son ID.
        
        Args:
            rule_id: Identifiant de la règle
            
        Returns:
            Dictionnaire de la règle ou None si non trouvée
        """
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return rule
        return None
    
    def get_rules_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Récupère les règles par catégorie.
        
        Args:
            category: Catégorie de règles (ex: 'acute_emergency', 'chronic_primary')
            
        Returns:
            Liste des règles de la catégorie
        """
        return [rule for rule in self.rules if rule.get("category") == category]
    
    def get_red_flag_info(self, red_flag_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations sur un red flag.
        
        Args:
            red_flag_id: Identifiant du red flag
            
        Returns:
            Dictionnaire d'informations ou None
        """
        flags = self.red_flags_catalog.get("flags", [])
        for flag in flags:
            if flag.get("id") == red_flag_id:
                return flag
        return None
    
    def get_imaging_info(self, imaging_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations sur une modalité d'imagerie.
        
        Args:
            imaging_id: Identifiant de la modalité
            
        Returns:
            Dictionnaire d'informations ou None
        """
        modalities = self.imaging_catalog.get("modalities", [])
        for modality in modalities:
            if modality.get("id") == imaging_id:
                return modality
        return None
    
    def explain_decision(self, case: HeadacheCase) -> Dict[str, Any]:
        """Explique la décision prise pour un cas donné.
        
        Retourne des informations détaillées sur le processus de décision:
        - Règles qui matchent
        - Règle appliquée
        - Conditions évaluées
        
        Args:
            case: Cas de céphalée
            
        Returns:
            Dictionnaire avec l'explication de la décision
        """
        all_matching = self.find_matching_rules(case)
        recommendation = self.decide_imaging(case)
        
        return {
            "case_summary": {
                "age": case.age,
                "sex": case.sex,
                "profile": case.profile,
                "onset": case.onset,
                "has_red_flags": case.has_red_flags(),
                "is_emergency": case.is_emergency()
            },
            "matching_rules_count": len(all_matching),
            "all_matching_rule_ids": [r.get("id") for r in all_matching],
            "applied_rule_id": recommendation.applied_rule_id,
            "recommendation": {
                "imaging": recommendation.imaging,
                "urgency": recommendation.urgency,
                "comment": recommendation.comment
            }
        }
