# GEMx Scoring Engine — Algorithm Design

## Overview

The scoring engine matches hybrid/variety genetic traits to field requirements derived from environmental and management data. This document details the scoring algorithm, weighting system, and recommendation generation.

---

## 1. Scoring Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCORING PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. FILTER (Hard Constraints)                                   │
│     ├── Maturity range (RM/MG must fit GDD)                    │
│     ├── Required traits (herbicide system)                      │
│     └── Brand whitelist (if specified)                          │
│                                                                 │
│  2. SCORE (Soft Constraints)                                    │
│     ├── Stress tolerance match                                  │
│     ├── Disease tolerance match                                 │
│     ├── Agronomic fit                                          │
│     └── Yield potential baseline                                │
│                                                                 │
│  3. RANK                                                        │
│     ├── Sort by composite score                                 │
│     └── Apply diversity rules (brand spread)                    │
│                                                                 │
│  4. EXPLAIN                                                     │
│     ├── Generate strengths                                      │
│     ├── Generate watch-outs                                     │
│     └── Suggest placement/population                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Hard Constraint Filters

### 2.1 Maturity Filter

```python
def filter_by_maturity(products: list, field_requirements: FieldRequirements, 
                       crop: str) -> list:
    """
    Filter products to those within acceptable maturity range.
    This is a HARD constraint - products outside range are excluded.
    """
    min_rm, optimal_rm, max_rm = field_requirements.target_maturity_range
    
    filtered = []
    for product in products:
        if crop == "corn":
            rm = product.relative_maturity
        else:
            rm = product.maturity_group
        
        if min_rm <= rm <= max_rm:
            filtered.append(product)
    
    return filtered
```

### 2.2 Trait Filter

```python
def filter_by_traits(products: list, management: ManagementInputs) -> list:
    """
    Filter products that have required traits.
    """
    filtered = []
    
    for product in products:
        # Herbicide trait requirement
        if management.herbicide_system:
            required_traits = HERBICIDE_TRAIT_MAP[management.herbicide_system]
            if not any(t in product.herbicide_traits for t in required_traits):
                continue
        
        # Bt trait requirement (corn only)
        if management.bt_requirement and hasattr(product, 'bt_traits'):
            if management.bt_requirement not in product.bt_traits:
                continue
        
        filtered.append(product)
    
    return filtered

HERBICIDE_TRAIT_MAP = {
    "Roundup Ready": ["RR", "RR2", "RR2X", "GT27"],
    "Liberty Link": ["LL", "LibertyLink"],
    "Enlist": ["E3", "Enlist"],
    "XtendFlex": ["XF", "XtendFlex", "RR2X"],
    "Conventional": [],  # No trait required
}
```

### 2.3 Brand Filter

```python
def filter_by_brand(products: list, brand_whitelist: Optional[list]) -> list:
    """
    Filter to only whitelisted brands if specified.
    """
    if not brand_whitelist:
        return products
    
    return [p for p in products if p.brand in brand_whitelist]
```

---

## 3. Soft Constraint Scoring

### 3.1 Score Components

Each product receives scores in multiple categories:

| Category | Weight (Corn) | Weight (Soy) | Components |
|----------|---------------|--------------|------------|
| **Maturity Fit** | 15% | 15% | Distance from optimal RM/MG |
| **Yield Potential** | 20% | 20% | Baseline yield rating |
| **Stress Tolerance** | 20% | 20% | Drought, heat, emergence |
| **Disease Tolerance** | 25% | 30% | Weighted by field risk |
| **Agronomics** | 20% | 15% | Standability, drydown, etc. |

### 3.2 Maturity Fit Score

```python
def score_maturity_fit(product_rm: float, target_range: tuple) -> float:
    """
    Score how well product maturity fits the field.
    Optimal = 1.0, edges of range = 0.7, outside = 0.0
    """
    min_rm, optimal_rm, max_rm = target_range
    
    if product_rm < min_rm or product_rm > max_rm:
        return 0.0  # Should have been filtered, but safety check
    
    # Distance from optimal
    if product_rm <= optimal_rm:
        distance = (optimal_rm - product_rm) / (optimal_rm - min_rm)
    else:
        distance = (product_rm - optimal_rm) / (max_rm - optimal_rm)
    
    # Convert distance to score (0 distance = 1.0, max distance = 0.7)
    return 1.0 - (0.3 * distance)
```

### 3.3 Stress Tolerance Score

```python
def score_stress_tolerance(product: Product, 
                           field_requirements: FieldRequirements) -> float:
    """
    Score stress tolerance match.
    Higher field stress = need higher product tolerance.
    """
    scores = []
    weights = []
    
    # Drought tolerance
    if field_requirements.drought_risk > 0.2:  # Only score if meaningful risk
        drought_score = match_tolerance_to_risk(
            product.drought_tolerance,
            field_requirements.drought_risk
        )
        scores.append(drought_score)
        weights.append(field_requirements.drought_risk)  # Weight by risk level
    
    # Heat tolerance (if available)
    if hasattr(product, 'heat_tolerance') and product.heat_tolerance:
        if field_requirements.heat_stress_risk > 0.2:
            heat_score = match_tolerance_to_risk(
                product.heat_tolerance,
                field_requirements.heat_stress_risk
            )
            scores.append(heat_score)
            weights.append(field_requirements.heat_stress_risk * 0.5)
    
    # Emergence vigor
    if field_requirements.emergence_challenge > 0.3:
        emergence_score = match_tolerance_to_risk(
            product.emergence_vigor,
            field_requirements.emergence_challenge
        )
        scores.append(emergence_score)
        weights.append(field_requirements.emergence_challenge * 0.7)
    
    if not scores:
        return 0.8  # Default good score if no stress concerns
    
    return weighted_average(scores, weights)


def match_tolerance_to_risk(tolerance_rating: int, risk_level: float) -> float:
    """
    Match a 1-9 tolerance rating to a 0-1 risk level.
    
    Logic:
    - High risk (>0.7) needs high tolerance (7+) for good score
    - Low risk (<0.3) doesn't penalize low tolerance much
    - Excess tolerance is slightly rewarded but not required
    """
    normalized_tolerance = tolerance_rating / 9.0
    
    if risk_level < 0.3:
        # Low risk: tolerance doesn't matter much
        # Even low tolerance gets decent score
        return 0.7 + (0.3 * normalized_tolerance)
    
    elif risk_level < 0.7:
        # Moderate risk: tolerance should roughly match
        tolerance_needed = risk_level
        if normalized_tolerance >= tolerance_needed:
            return 0.85 + (0.15 * (normalized_tolerance - tolerance_needed))
        else:
            gap = tolerance_needed - normalized_tolerance
            return max(0.3, 0.85 - (gap * 1.5))
    
    else:
        # High risk: need high tolerance
        if normalized_tolerance >= 0.7:
            return 0.9 + (0.1 * (normalized_tolerance - 0.7) / 0.3)
        else:
            gap = 0.7 - normalized_tolerance
            return max(0.2, 0.9 - (gap * 2.0))
```

### 3.4 Disease Tolerance Score

```python
def score_disease_tolerance(product: Product, 
                            field_requirements: FieldRequirements,
                            crop: str) -> float:
    """
    Score disease tolerance weighted by field-specific disease risks.
    """
    if crop == "corn":
        disease_ratings = {
            "gls": (product.gray_leaf_spot, field_requirements.gls_risk),
            "nclb": (product.northern_leaf_blight, field_requirements.nclb_risk),
            "tar_spot": (product.tar_spot, field_requirements.tar_spot_risk),
            "gosss_wilt": (product.gosss_wilt, field_requirements.gosss_wilt_risk),
        }
    else:  # soybean
        disease_ratings = {
            "sds": (product.sds_rating, field_requirements.sds_risk),
            "phytophthora": (product.phytophthora_field, field_requirements.phytophthora_risk),
            "white_mold": (product.white_mold, field_requirements.white_mold_risk),
            "frogeye": (product.frogeye_leaf_spot, field_requirements.frogeye_risk),
        }
        
        # Special handling for SCN (gene-based)
        if field_requirements.scn_risk > 0.3:
            scn_score = score_scn_resistance(
                product.scn_source, 
                field_requirements.scn_risk,
                field_requirements.scn_source_history  # What's been planted before
            )
            disease_ratings["scn"] = (scn_score * 9, field_requirements.scn_risk)
    
    scores = []
    weights = []
    
    for disease, (rating, risk) in disease_ratings.items():
        if rating is None:
            continue  # Skip if no rating available
        
        if risk > 0.1:  # Only score if meaningful risk
            score = match_tolerance_to_risk(rating, risk)
            scores.append(score)
            weights.append(risk)  # Weight by risk level
    
    if not scores:
        return 0.8  # Default if no disease concerns
    
    return weighted_average(scores, weights)


def score_scn_resistance(scn_source: str, risk: float, 
                         source_history: Optional[list] = None) -> float:
    """
    Score SCN resistance considering source rotation.
    PI 88788 overuse has led to adapted populations.
    """
    base_scores = {
        "PI 88788": 0.7,
        "Peking": 0.85,
        "PI 89772": 0.8,
        "PI 437654": 0.9,
        "Hartwig": 0.85,
        "None": 0.1,
    }
    
    score = base_scores.get(scn_source, 0.5)
    
    # Penalize if same source used repeatedly
    if source_history and scn_source in source_history[-3:]:
        consecutive = sum(1 for s in source_history[-3:] if s == scn_source)
        score *= (1 - 0.1 * consecutive)
    
    # Bonus for rotating sources
    if source_history and scn_source not in source_history[-2:]:
        score *= 1.1
    
    return min(1.0, score)
```

### 3.5 Agronomic Score

```python
def score_agronomics(product: Product, 
                     field_requirements: FieldRequirements,
                     crop: str) -> float:
    """
    Score agronomic characteristics.
    """
    scores = []
    weights = []
    
    if crop == "corn":
        # Standability (stalk + root)
        if field_requirements.standability_need > 0.3:
            stalk_score = product.stalk_strength / 9.0
            root_score = product.root_strength / 9.0
            standability = (stalk_score + root_score) / 2
            scores.append(standability)
            weights.append(field_requirements.standability_need)
        
        # Drydown (important for late harvest)
        if field_requirements.late_harvest_risk > 0.3:
            drydown_score = product.drydown / 9.0
            scores.append(drydown_score)
            weights.append(field_requirements.late_harvest_risk * 0.8)
        
        # Test weight
        if product.test_weight:
            scores.append(product.test_weight / 9.0)
            weights.append(0.3)  # Always somewhat important
    
    else:  # soybean
        # Lodging resistance
        if field_requirements.lodging_risk > 0.3:
            lodging_score = product.lodging_resistance / 9.0
            scores.append(lodging_score)
            weights.append(field_requirements.lodging_risk)
        
        # IDC tolerance (critical in certain regions)
        if field_requirements.idc_risk > 0.3:
            idc_score = product.idc_tolerance / 9.0
            scores.append(idc_score)
            weights.append(field_requirements.idc_risk * 1.5)  # High weight
    
    if not scores:
        return 0.8
    
    return weighted_average(scores, weights)
```

### 3.6 Composite Score

```python
def calculate_composite_score(product: Product,
                              field_requirements: FieldRequirements,
                              management: ManagementInputs,
                              crop: str) -> float:
    """
    Calculate final composite score for a product.
    """
    # Individual component scores
    maturity_score = score_maturity_fit(
        product.relative_maturity if crop == "corn" else product.maturity_group,
        field_requirements.target_maturity_range
    )
    
    yield_score = product.yield_potential / 9.0
    
    stress_score = score_stress_tolerance(product, field_requirements)
    
    disease_score = score_disease_tolerance(product, field_requirements, crop)
    
    agronomic_score = score_agronomics(product, field_requirements, crop)
    
    # Weights by crop
    if crop == "corn":
        weights = {
            "maturity": 0.15,
            "yield": 0.20,
            "stress": 0.20,
            "disease": 0.25,
            "agronomic": 0.20,
        }
    else:
        weights = {
            "maturity": 0.15,
            "yield": 0.20,
            "stress": 0.20,
            "disease": 0.30,
            "agronomic": 0.15,
        }
    
    composite = (
        weights["maturity"] * maturity_score +
        weights["yield"] * yield_score +
        weights["stress"] * stress_score +
        weights["disease"] * disease_score +
        weights["agronomic"] * agronomic_score
    )
    
    # Apply data confidence modifier
    confidence = calculate_data_confidence(product)
    if confidence < 0.7:
        # Penalize products with incomplete data
        composite *= (0.8 + 0.2 * confidence)
    
    return composite * 100  # Return as 0-100 score
```

---

## 4. Ranking & Diversity

### 4.1 Ranking with Diversity

```python
def rank_recommendations(scored_products: list[tuple[Product, float]],
                         top_n: int = 5,
                         brand_diversity: bool = True) -> list[Recommendation]:
    """
    Rank products and apply diversity rules.
    """
    # Sort by score descending
    sorted_products = sorted(scored_products, key=lambda x: x[1], reverse=True)
    
    if not brand_diversity:
        return [create_recommendation(p, s) for p, s in sorted_products[:top_n]]
    
    # Apply brand diversity (max 2 per brand in top 5)
    recommendations = []
    brand_counts = {}
    
    for product, score in sorted_products:
        brand = product.brand
        if brand_counts.get(brand, 0) < 2:
            recommendations.append(create_recommendation(product, score))
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        
        if len(recommendations) >= top_n:
            break
    
    return recommendations
```

---

## 5. Explanation Generation

### 5.1 Strengths & Watch-Outs

```python
def generate_explanations(product: Product, 
                          field_requirements: FieldRequirements,
                          crop: str) -> tuple[list[str], list[str]]:
    """
    Generate human-readable strengths and watch-outs.
    """
    strengths = []
    watch_outs = []
    
    # Yield potential
    if product.yield_potential >= 8:
        strengths.append("Excellent yield potential")
    elif product.yield_potential >= 7:
        strengths.append("Strong yield potential")
    
    # Drought tolerance vs risk
    if field_requirements.drought_risk > 0.5:
        if product.drought_tolerance >= 7:
            strengths.append("Strong drought tolerance for this water-limited environment")
        elif product.drought_tolerance <= 4:
            watch_outs.append("Below-average drought tolerance in a drought-prone field")
    
    # Disease matches
    if crop == "corn":
        if field_requirements.gls_risk > 0.5 and product.gray_leaf_spot >= 7:
            strengths.append("Excellent Gray Leaf Spot tolerance")
        if field_requirements.tar_spot_risk > 0.5 and product.tar_spot >= 7:
            strengths.append("Strong Tar Spot tolerance")
        if field_requirements.gls_risk > 0.5 and product.gray_leaf_spot <= 4:
            watch_outs.append("Consider fungicide program for Gray Leaf Spot")
    
    else:  # soybean
        if field_requirements.sds_risk > 0.5 and product.sds_rating >= 7:
            strengths.append("Excellent SDS tolerance")
        if field_requirements.scn_risk > 0.5:
            if product.scn_source == "Peking":
                strengths.append("Peking SCN resistance (less common, broader spectrum)")
            elif product.scn_source == "PI 88788":
                strengths.append("PI 88788 SCN resistance")
            elif product.scn_source == "None":
                watch_outs.append("No SCN resistance in a field with SCN pressure")
        
        if field_requirements.idc_risk > 0.5:
            if product.idc_tolerance >= 7:
                strengths.append("Strong IDC tolerance for high-pH soils")
            elif product.idc_tolerance <= 4:
                watch_outs.append("IDC risk on calcareous soils")
    
    # Standability
    if crop == "corn" and field_requirements.standability_need > 0.5:
        avg_stand = (product.stalk_strength + product.root_strength) / 2
        if avg_stand >= 7:
            strengths.append("Excellent standability")
        elif avg_stand <= 4:
            watch_outs.append("Monitor for stalk/root issues late season")
    
    # Maturity fit
    min_rm, optimal_rm, max_rm = field_requirements.target_maturity_range
    rm = product.relative_maturity if crop == "corn" else product.maturity_group
    
    if abs(rm - optimal_rm) <= 1:
        strengths.append(f"Optimal maturity ({rm}) for this location")
    elif rm > optimal_rm:
        watch_outs.append(f"Slightly full-season ({rm}) - monitor dry-down")
    
    return strengths, watch_outs
```

### 5.2 Placement Suggestions

```python
def suggest_placement(product: Product, score: float, 
                      field_requirements: FieldRequirements) -> str:
    """
    Suggest where this product fits in the operation.
    """
    if score >= 85:
        return "Best fit - prioritize for this field"
    elif score >= 75:
        return "Strong fit - good primary choice"
    elif score >= 65:
        return "Moderate fit - consider for average acres"
    elif score >= 55:
        return "Marginal fit - use only if preferred traits needed"
    else:
        return "Poor fit - consider alternatives"


def suggest_population(product: Product, field_requirements: FieldRequirements,
                       management: ManagementInputs, crop: str) -> int:
    """
    Suggest target population based on product and field.
    """
    if crop == "corn":
        # Base population by yield environment
        if field_requirements.yield_environment == "high":
            base_pop = 34000
        elif field_requirements.yield_environment == "medium":
            base_pop = 32000
        else:
            base_pop = 30000
        
        # Adjust by ear type
        if product.ear_type == "Flex":
            base_pop -= 1000  # Flex ears can compensate
        elif product.ear_type == "Fixed":
            base_pop += 1000  # Fixed ears need more plants
        
        # Adjust by drought risk
        if field_requirements.drought_risk > 0.6 and not management.irrigation:
            base_pop -= 2000
        
        return base_pop
    
    else:  # soybean
        # Base by row spacing
        if management.row_spacing <= 15:
            base_pop = 140000
        elif management.row_spacing <= 20:
            base_pop = 130000
        else:
            base_pop = 120000
        
        # Adjust by branching habit
        if product.branching == "Bushy":
            base_pop -= 10000
        elif product.branching == "Erect":
            base_pop += 10000
        
        return base_pop
```

---

## 6. Full Recommendation Object

```python
@dataclass
class Recommendation:
    # Product info
    brand: str
    product_name: str
    maturity: float
    
    # Scores
    composite_score: float
    component_scores: dict[str, float]
    
    # Explanations
    strengths: list[str]
    watch_outs: list[str]
    
    # Suggestions
    placement: str
    suggested_population: int
    
    # Metadata
    data_confidence: float
    
    def to_dict(self) -> dict:
        return {
            "brand": self.brand,
            "product": self.product_name,
            "maturity": self.maturity,
            "score": round(self.composite_score, 1),
            "strengths": self.strengths,
            "watch_outs": self.watch_outs,
            "placement": self.placement,
            "population": self.suggested_population,
            "confidence": round(self.data_confidence, 2),
        }


def create_recommendation(product: Product, score: float,
                          field_requirements: FieldRequirements,
                          management: ManagementInputs,
                          crop: str) -> Recommendation:
    """
    Create a full recommendation object.
    """
    strengths, watch_outs = generate_explanations(product, field_requirements, crop)
    
    return Recommendation(
        brand=product.brand,
        product_name=product.hybrid_name if crop == "corn" else product.variety_name,
        maturity=product.relative_maturity if crop == "corn" else product.maturity_group,
        composite_score=score,
        component_scores={
            "maturity_fit": score_maturity_fit(...),
            "yield": product.yield_potential / 9.0 * 100,
            "stress": score_stress_tolerance(...) * 100,
            "disease": score_disease_tolerance(...) * 100,
            "agronomic": score_agronomics(...) * 100,
        },
        strengths=strengths,
        watch_outs=watch_outs,
        placement=suggest_placement(product, score, field_requirements),
        suggested_population=suggest_population(product, field_requirements, management, crop),
        data_confidence=calculate_data_confidence(product),
    )
```

---

## 7. API Interface

```python
def get_recommendations(
    field_id: str,
    crop: str,
    management: ManagementInputs,
    brand_whitelist: Optional[list[str]] = None,
    top_n: int = 5,
) -> list[Recommendation]:
    """
    Main entry point for recommendation engine.
    
    Args:
        field_id: UUID of the field
        crop: "corn" or "soybean"
        management: Management practice inputs
        brand_whitelist: Optional list of brands to consider
        top_n: Number of recommendations to return
    
    Returns:
        List of Recommendation objects, ranked by fit score
    """
    # 1. Load field features
    field_features = load_field_features(field_id)
    
    # 2. Derive field requirements
    field_requirements = derive_field_requirements(field_features, management, crop)
    
    # 3. Load product catalog
    if crop == "corn":
        products = load_corn_hybrids()
    else:
        products = load_soybean_varieties()
    
    # 4. Apply hard filters
    products = filter_by_maturity(products, field_requirements, crop)
    products = filter_by_traits(products, management)
    products = filter_by_brand(products, brand_whitelist)
    
    # 5. Score remaining products
    scored = [
        (p, calculate_composite_score(p, field_requirements, management, crop))
        for p in products
    ]
    
    # 6. Rank and create recommendations
    recommendations = rank_recommendations(scored, top_n)
    
    return recommendations
```
