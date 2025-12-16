"""
GEMx Scoring Engine - Core recommendation logic.
"""
from typing import Union, Optional
from ..models.products import CornHybrid, SoybeanVariety
from ..models.fields import FieldRequirements
from ..models.management import ManagementInputs
from ..models.recommendations import Recommendation, ComponentScores, RecommendationSet


def weighted_average(values: list[float], weights: list[float]) -> float:
    """Calculate weighted average."""
    if not values or not weights:
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_weight


class ScoringEngine:
    """Main scoring engine for product recommendations."""
    
    def __init__(self):
        self.default_weights = {
            "corn": {
                "maturity": 0.15,
                "yield": 0.20,
                "stress": 0.20,
                "disease": 0.25,
                "agronomic": 0.20,
            },
            "soybean": {
                "maturity": 0.15,
                "yield": 0.20,
                "stress": 0.20,
                "disease": 0.30,
                "agronomic": 0.15,
            }
        }
    
    def score_maturity_fit(self, product_maturity: float, 
                          target_range: tuple[float, float, float]) -> float:
        """Score how well product maturity fits the field."""
        min_rm, optimal_rm, max_rm = target_range
        
        if product_maturity < min_rm or product_maturity > max_rm:
            return 0.0
        
        if product_maturity <= optimal_rm:
            distance = (optimal_rm - product_maturity) / max(optimal_rm - min_rm, 1)
        else:
            distance = (product_maturity - optimal_rm) / max(max_rm - optimal_rm, 1)
        
        return 1.0 - (0.3 * distance)
    
    def match_tolerance_to_risk(self, tolerance_rating: Optional[int], 
                                risk_level: float) -> float:
        """Match a 1-9 tolerance rating to a 0-1 risk level."""
        if tolerance_rating is None:
            return 0.5  # Unknown = average
        
        normalized_tolerance = tolerance_rating / 9.0
        
        if risk_level < 0.3:
            return 0.7 + (0.3 * normalized_tolerance)
        elif risk_level < 0.7:
            tolerance_needed = risk_level
            if normalized_tolerance >= tolerance_needed:
                return 0.85 + (0.15 * (normalized_tolerance - tolerance_needed))
            else:
                gap = tolerance_needed - normalized_tolerance
                return max(0.3, 0.85 - (gap * 1.5))
        else:
            if normalized_tolerance >= 0.7:
                return 0.9 + (0.1 * (normalized_tolerance - 0.7) / 0.3)
            else:
                gap = 0.7 - normalized_tolerance
                return max(0.2, 0.9 - (gap * 2.0))
    
    def score_stress_tolerance(self, product: Union[CornHybrid, SoybeanVariety],
                               requirements: FieldRequirements) -> float:
        """Score stress tolerance match."""
        scores = []
        weights = []
        
        if requirements.drought_risk > 0.2:
            drought_score = self.match_tolerance_to_risk(
                product.drought_tolerance, requirements.drought_risk
            )
            scores.append(drought_score)
            weights.append(requirements.drought_risk)
        
        if requirements.emergence_challenge > 0.3:
            emergence_score = self.match_tolerance_to_risk(
                product.emergence_vigor, requirements.emergence_challenge
            )
            scores.append(emergence_score)
            weights.append(requirements.emergence_challenge * 0.7)
        
        if not scores:
            return 0.8
        
        return weighted_average(scores, weights)
    
    def score_disease_tolerance_corn(self, product: CornHybrid,
                                     requirements: FieldRequirements) -> float:
        """Score disease tolerance for corn."""
        disease_ratings = [
            (product.gray_leaf_spot, requirements.gls_risk),
            (product.northern_leaf_blight, requirements.nclb_risk),
            (product.tar_spot, requirements.tar_spot_risk),
            (product.gosss_wilt, requirements.gosss_wilt_risk),
        ]
        
        scores = []
        weights = []
        
        for rating, risk in disease_ratings:
            if rating is not None and risk > 0.1:
                score = self.match_tolerance_to_risk(rating, risk)
                scores.append(score)
                weights.append(risk)
        
        if not scores:
            return 0.8
        
        return weighted_average(scores, weights)
    
    def score_disease_tolerance_soybean(self, product: SoybeanVariety,
                                        requirements: FieldRequirements) -> float:
        """Score disease tolerance for soybean."""
        disease_ratings = [
            (product.sds_rating, requirements.sds_risk),
            (product.phytophthora_field, requirements.phytophthora_risk),
            (product.white_mold, requirements.white_mold_risk),
            (product.frogeye_leaf_spot, requirements.frogeye_risk),
        ]
        
        scores = []
        weights = []
        
        for rating, risk in disease_ratings:
            if rating is not None and risk > 0.1:
                score = self.match_tolerance_to_risk(rating, risk)
                scores.append(score)
                weights.append(risk)
        
        # SCN special handling
        if requirements.scn_risk > 0.3:
            scn_score = self.score_scn_resistance(
                product.scn_source, 
                requirements.scn_risk,
                requirements.scn_source_history
            )
            scores.append(scn_score)
            weights.append(requirements.scn_risk * 1.5)  # Higher weight for SCN
        
        # IDC special handling
        if requirements.idc_risk > 0.3 and product.idc_tolerance:
            idc_score = self.match_tolerance_to_risk(product.idc_tolerance, requirements.idc_risk)
            scores.append(idc_score)
            weights.append(requirements.idc_risk * 1.5)
        
        if not scores:
            return 0.8
        
        return weighted_average(scores, weights)
    
    def score_scn_resistance(self, scn_source: Optional[str], risk: float,
                             source_history: list[str]) -> float:
        """Score SCN resistance considering source rotation."""
        base_scores = {
            "PI 88788": 0.7,
            "Peking": 0.85,
            "PI 89772": 0.8,
            "PI 437654": 0.9,
            "Hartwig": 0.85,
            "None": 0.1,
            None: 0.1,
        }
        
        score = base_scores.get(scn_source, 0.5)
        
        if source_history and scn_source in source_history[-3:]:
            consecutive = sum(1 for s in source_history[-3:] if s == scn_source)
            score *= (1 - 0.1 * consecutive)
        
        if source_history and scn_source not in source_history[-2:]:
            score = min(1.0, score * 1.1)
        
        return score
    
    def score_agronomics_corn(self, product: CornHybrid,
                              requirements: FieldRequirements) -> float:
        """Score agronomic characteristics for corn."""
        scores = []
        weights = []
        
        if requirements.standability_need > 0.3:
            stalk = (product.stalk_strength or 5) / 9.0
            root = (product.root_strength or 5) / 9.0
            standability = (stalk + root) / 2
            scores.append(standability)
            weights.append(requirements.standability_need)
        
        if requirements.late_harvest_risk > 0.3 and product.drydown:
            drydown_score = product.drydown / 9.0
            scores.append(drydown_score)
            weights.append(requirements.late_harvest_risk * 0.8)
        
        if product.test_weight:
            scores.append(product.test_weight / 9.0)
            weights.append(0.3)
        
        if not scores:
            return 0.8
        
        return weighted_average(scores, weights)
    
    def score_agronomics_soybean(self, product: SoybeanVariety,
                                 requirements: FieldRequirements) -> float:
        """Score agronomic characteristics for soybean."""
        scores = []
        weights = []
        
        if requirements.lodging_risk > 0.3 and product.lodging_resistance:
            lodging_score = product.lodging_resistance / 9.0
            scores.append(lodging_score)
            weights.append(requirements.lodging_risk)
        
        if not scores:
            return 0.8
        
        return weighted_average(scores, weights)
    
    def calculate_composite_score(self, product: Union[CornHybrid, SoybeanVariety],
                                  requirements: FieldRequirements,
                                  crop: str) -> tuple[float, ComponentScores]:
        """Calculate final composite score for a product."""
        
        if crop == "corn":
            maturity = product.relative_maturity
        else:
            maturity = product.maturity_group
        
        maturity_score = self.score_maturity_fit(maturity, requirements.target_maturity_range)
        yield_score = product.yield_potential / 9.0
        stress_score = self.score_stress_tolerance(product, requirements)
        
        if crop == "corn":
            disease_score = self.score_disease_tolerance_corn(product, requirements)
            agronomic_score = self.score_agronomics_corn(product, requirements)
        else:
            disease_score = self.score_disease_tolerance_soybean(product, requirements)
            agronomic_score = self.score_agronomics_soybean(product, requirements)
        
        weights = self.default_weights[crop]
        
        composite = (
            weights["maturity"] * maturity_score +
            weights["yield"] * yield_score +
            weights["stress"] * stress_score +
            weights["disease"] * disease_score +
            weights["agronomic"] * agronomic_score
        )
        
        component_scores = ComponentScores(
            maturity_fit=maturity_score * 100,
            yield_potential=yield_score * 100,
            stress_tolerance=stress_score * 100,
            disease_tolerance=disease_score * 100,
            agronomics=agronomic_score * 100,
        )
        
        return composite * 100, component_scores
