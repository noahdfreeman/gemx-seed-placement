# Previous Seed Placement Algorithm — Extracted from Excel Files

## Overview

This document captures the calculation methodology from your previous seed placement algorithm implementation (Keystone/Mix Matters era). The algorithm uses a **G × E × M** scoring approach where:

- **G (Genetics):** Hybrid/variety ratings on a 1-5 scale
- **E (Environment):** Field conditions (drainage, yield potential, disease pressure)
- **M (Management):** Grower practices (tillage, rotation, fungicide, nitrogen)

---

## 1. Algorithm Structure

### 1.1 Input Variables

**Environment & Management Variables (User Inputs):**

| Variable | Example Values | Crop |
|----------|---------------|------|
| Field Average Yield | 250 bu/ac (corn), 75 bu/ac (soy) | Both |
| Previous Crop | Corn, Soybeans, Other | Both |
| Soil Drainage | Very poorly drained → Excessively drained | Both |
| Tile Drainage | No tile, Minimally tiled, Moderate, Highly tiled | Both |
| Tillage | No till, Minimal/reduced, Conventional | Both |
| Fungicide | Never/rarely, Based on scouting, Always | Both |
| Seed Treatment | Untreated → Full package | Both |
| Trait Preference | Conventional, RR, Xtend, E3, etc. | Both |
| Maturity Range | Min/Max RM or MG | Both |
| Nitrogen Timing | All before planting, Before V6, After V6 | Corn |
| Nitrogen Rate | lbs/acre | Corn |
| Row Spacing | 20"+, <20", Drilled | Soy |
| Disease Pressure | High, Medium, Low (per disease) | Both |

---

## 2. Scoring Formula

### 2.1 E × M Score Calculation

For each scoring factor, the formula is:

```
E×M Score = (Raw Value / Max Value) × 10 × Multiplier
```

Where:
- **Raw Value:** Derived from environment/management inputs
- **Max Value:** Maximum possible for that factor
- **Scaling 1-10:** Normalizes to 0-10 scale
- **Multiplier:** Weight for that factor's importance

### 2.2 Corn Scoring Factors

| Factor | Max | Multiplier | Weight Effect |
|--------|-----|------------|---------------|
| High Yield | 3 | 1.0 | Full weight |
| Low Yield | 3 | 1.0 | Full weight |
| Soil Drainage | 5 | 0.75 | 75% weight |
| Nitrogen Management | 10 | 0.75 | 75% weight |
| Previous Crop (Corn on Corn) | 2 | 0.25 | 25% weight |
| Tillage | 2 | 0.25 | 25% weight |
| Positive Fungicide Response | 2 | 0.5 | 50% weight |
| Disease Response | 10.5 | 0.5 | 50% weight |
| Trait Preference | — | 1.0 | Binary (0 or 40 points) |
| Maturity Range | — | — | Binary filter (0 or pass) |

### 2.3 Soybean Scoring Factors

| Factor | Max | Multiplier | Weight Effect |
|--------|-----|------------|---------------|
| High Yield | 3 | 1.0 | Full weight |
| Low Yield | 3 | 1.0 | Full weight |
| Soil Drainage | 7.5 | 0.4 | 40% weight |
| Tillage | 2 | 1.0 | Full weight |
| Soybeans on Soybeans | 2 | 1.0 | Full weight |
| Narrow Row Spacing | 3 | 1.0 | Full weight |
| Wide Row Spacing | 3 | 1.0 | Full weight |
| **Disease Factors (each):** | | **1.5** | **150% weight** |
| - Soybean Cyst Nematode | 2 | 1.5 | High importance |
| - Phytophthora | 5.75 | 0.52 | Scaled |
| - Brown Stem Rot | 2 | 1.5 | High importance |
| - Sclerotinia White Mold | 2 | 1.5 | High importance |
| - Sudden Death Syndrome | 7.75 | 0.39 | Scaled |
| - Frogeye Leaf Spot | 2 | 1.5 | High importance |
| - Charcoal Rot | 2 | 1.5 | High importance |
| - Stem Canker | 2 | 1.5 | High importance |
| Trait Preference | — | 1.0 | Large bonus (80 points) |
| Maturity Range | — | — | Binary filter |

---

## 3. Genetic Variables (Hybrid/Variety Ratings)

### 3.1 Rating Scale

Hybrids/varieties are rated on a **1-5 scale** for each environment:
- **1** = Best fit for this environment
- **2** = Better fit
- **3** = Good fit
- **4** = Below average fit
- **5** = Poor fit / Not recommended

### 3.2 Corn Genetic Variables

| Variable | Description |
|----------|-------------|
| High Yield Environment | Performance in high-yield conditions |
| Low Yield Environment | Performance in stressed/low-yield conditions |
| Poorly Drained Environment | Tolerance to wet soils |
| Low Nitrogen Management | Performance under limited N |
| Corn on Corn Rotation | Tolerance to continuous corn |
| No-Till Environments | Performance in no-till/early planting |
| Yield/Positive Response to Fungicide | Benefit from fungicide application |
| Disease Resistance | Overall disease package |
| Trait | Herbicide/insect trait package |
| Maturity | Relative maturity (days) |

### 3.3 Soybean Genetic Variables

| Variable | Description |
|----------|-------------|
| High Yield Environment | Performance in high-yield conditions |
| Low Yield Environment | Performance in stressed conditions |
| Poorly Drained Environment | Tolerance to wet soils |
| Soybean on Soybean Environment | Tolerance to continuous soy |
| No-Till/Early Planting | Performance in no-till |
| Narrow Row Spacing | Suitability for narrow rows |
| Wide Row Spacing | Suitability for wide rows |
| Soybean Cyst Nematode | SCN resistance rating |
| Phytophthora | Phytophthora tolerance |
| Brown Stem Rot | BSR tolerance |
| Sclerotinia White Mold | White mold tolerance |
| Sudden Death Syndrome | SDS tolerance |
| Frogeye Leaf Spot | Frogeye tolerance |
| Charcoal Rot | Charcoal rot tolerance |
| Stem Canker | Stem canker tolerance |
| Trait | Herbicide trait package |
| Maturity | Maturity group |

---

## 4. G × E × M Calculation

### 4.1 Final Score Formula

```python
def calculate_gxexm_score(hybrid, field_requirements):
    """
    Calculate G × E × M score for a hybrid in a field.
    
    Lower score = Better fit (because genetic ratings are 1-5 where 1 is best)
    """
    total_score = 0
    
    for factor in scoring_factors:
        # Get E×M score for this factor (0-10 scale, weighted)
        exm_score = field_requirements[factor].multiplier_result
        
        # Get genetic rating for this factor (1-5 scale)
        genetic_rating = hybrid[factor]
        
        # Multiply E×M importance by genetic rating
        # Higher E×M score × Higher genetic rating = Higher total (worse fit)
        factor_score = exm_score * genetic_rating
        
        total_score += factor_score
    
    # Add trait preference bonus (if trait matches)
    if hybrid.trait == field_requirements.trait_preference:
        total_score += TRAIT_BONUS  # 40 for corn, 80 for soy
    
    # Check maturity range (filter, not score)
    if not (min_maturity <= hybrid.maturity <= max_maturity):
        return DISQUALIFIED
    
    return total_score
```

### 4.2 Example Calculation (Soybean)

**Field Requirements:**
- Field Average Yield: 75 bu/ac
- Previous Crop: Soybeans
- Soil Drainage: Very poorly drained
- Tillage: No till
- Row Spacing: Drilled
- SCN Pressure: High
- All diseases: High
- Trait Preference: Xtend
- Maturity Range: 1.0 - 4.0

**E×M Scores Calculated:**

| Factor | E×M | Max | Scaled | Multiplier | Result |
|--------|-----|-----|--------|------------|--------|
| High Yield | 1 | 3 | 3.33 | 1.0 | 3.33 |
| Soil Drainage | 2.75 | 7.5 | 3.67 | 0.4 | 1.47 |
| Tillage | 2 | 2 | 10 | 1.0 | 10 |
| Soy on Soy | 2 | 2 | 10 | 1.0 | 10 |
| Narrow Row | 3 | 3 | 10 | 1.0 | 10 |
| SCN | 2 | 2 | 10 | 1.5 | 15 |
| Phytophthora | 3.375 | 5.75 | 5.87 | 0.52 | 3.06 |
| BSR | 2 | 2 | 10 | 1.5 | 15 |
| White Mold | 2 | 2 | 10 | 1.5 | 15 |
| SDS | 4.04 | 7.75 | 5.22 | 0.39 | 2.02 |
| Frogeye | 2 | 2 | 10 | 1.5 | 15 |
| Charcoal Rot | 2 | 2 | 10 | 1.5 | 15 |
| Stem Canker | 2 | 2 | 10 | 1.5 | 15 |

**Variety A Ratings (all 1s = best):**
- All genetic ratings = 1
- Trait = Xtend (matches)
- Maturity = 3.0 (in range)

**Variety A Score:**
```
= (3.33×1) + (1.47×1) + (10×1) + (10×1) + (10×1) + (15×1) + (3.06×1) + 
  (15×1) + (15×1) + (2.02×1) + (15×1) + (15×1) + (15×1) + 80 (trait) + 1 (maturity)
= 210.88
```

**Variety B Ratings (mixed, some 5s = worst):**
- High Yield = 5, Low Yield = 5, etc.
- Same trait and maturity

**Variety B Score:**
```
= (3.33×5) + (1.47×1) + (10×2) + (10×5) + ... + 80 + 1
= 531.31
```

**Result:** Variety A (210.88) ranks better than Variety B (531.31)

---

## 5. Population Recommendations

### 5.1 Population Curve

Population is calculated using a polynomial regression based on yield potential:

```python
# Cubic polynomial for population
population = x3 * yield^3 + x2 * yield^2 + x * yield + b

# Example coefficients (varies by hybrid):
x3 = -0.000148
x2 = 0.106349
x = 2.830688
b = 22666.67
r2 = 0.992  # High fit
```

### 5.2 Population by Yield Potential (Example)

| Yield Potential | Hybrid A | Hybrid B | Hybrid C |
|-----------------|----------|----------|----------|
| 300 bu/ac | 29,000 | 32,000 | 35,500 |
| 250 bu/ac | 28,000 | 30,000 | 33,500 |
| 200 bu/ac | 26,000 | 28,000 | 30,000 |
| 150 bu/ac | 25,000 | 26,000 | 28,000 |
| 100 bu/ac | 24,000 | 24,000 | 26,000 |
| 50 bu/ac | 23,000 | 22,000 | 18,000 |

---

## 6. Placement Text Generation

The algorithm generates natural language recommendations using lookup tables:

### 6.1 Text Templates

| Fit Level | Template Options |
|-----------|-----------------|
| Best (1) | "is a best choice for", "is best suited for", "is best positioned in" |
| Better (2) | "is a better choice for", "is better suited for", "is better positioned in" |
| Good (3) | "is a good choice for", "is suited for", "is adequately positioned in" |
| Poor (4-5) | "is not a good choice for", "is not suited for", "should be avoided in" |

### 6.2 Environment Descriptions

| Factor | Description |
|--------|-------------|
| Soil Drainage | "soils with drainage challenges" |
| Disease | "favorable disease conditions" / "conditions where disease is likely" |
| Nitrogen | "low nitrogen environments" |
| Previous Crop | "corn on corn rotation" |
| Tillage | "no-till and minimal tillage practices" |

### 6.3 Example Output

> "Variety A **is a best choice for** soils with drainage challenges, **is best suited for** conditions where disease is likely, and **is effectively used in** no-till and minimal tillage practices."

---

## 7. Key Observations & Improvement Opportunities

### 7.1 What Works Well

1. **G × E × M framework** — Solid conceptual foundation
2. **Weighted multipliers** — Allows tuning factor importance
3. **Disease-heavy weighting for soybeans** — Reflects reality (1.5× multiplier)
4. **Trait matching** — Large bonus ensures trait requirements are met
5. **Population curves** — Hybrid-specific recommendations

### 7.2 Improvement Opportunities for GEMx

| Current Approach | Improvement |
|------------------|-------------|
| **1-5 genetic ratings** | Use actual 1-9 seed guide ratings |
| **Manual E×M derivation** | Derive from SSURGO + PRISM automatically |
| **Fixed multipliers** | Learn optimal weights from outcomes |
| **Binary disease pressure** | Model disease risk from weather + rotation |
| **No weather data** | Integrate PRISM for GDD, drought risk |
| **Single score output** | Show component scores for transparency |
| **Text templates** | Generate dynamic explanations |

### 7.3 Specific Enhancements

1. **Environment Derivation:**
   - Current: User selects "Very poorly drained"
   - GEMx: Auto-detect from SSURGO drainage class

2. **Disease Risk:**
   - Current: User selects "High" for each disease
   - GEMx: Model from weather history + rotation + drainage

3. **Scoring Transparency:**
   - Current: Single total score
   - GEMx: Show breakdown (yield fit: 85, disease fit: 72, etc.)

4. **Rating Scale:**
   - Current: 1-5 (1=best, 5=worst)
   - GEMx: Use 1-9 seed guide scale (higher=better), invert for scoring

5. **Maturity Selection:**
   - Current: User specifies range
   - GEMx: Derive from GDD accumulation + planting date

---

## 8. Data Model Translation

### 8.1 Current → GEMx Mapping

| Current Variable | GEMx Source | Derivation |
|------------------|-------------|------------|
| Field Average Yield | SSURGO + History | Soil productivity + county average |
| Soil Drainage | SSURGO | `drclassdcd` field |
| Tile Drainage | User input | Keep as questionnaire |
| Tillage | User input | Keep as questionnaire |
| Previous Crop | User input | Keep as questionnaire |
| Disease Pressure | Modeled | Weather + rotation + drainage |
| GDD/Maturity | PRISM | Calculate from weather data |

### 8.2 Genetic Rating Translation

| Current (1-5, 1=best) | Seed Guide (1-9, 9=best) | GEMx Internal |
|-----------------------|--------------------------|---------------|
| 1 | 8-9 | 0.9-1.0 |
| 2 | 6-7 | 0.7-0.8 |
| 3 | 5 | 0.5-0.6 |
| 4 | 3-4 | 0.3-0.4 |
| 5 | 1-2 | 0.1-0.2 |

---

## 9. Summary

Your previous algorithm is a solid foundation with:
- Clear G × E × M structure
- Weighted scoring by factor importance
- Trait and maturity filtering
- Population recommendations
- Natural language output

GEMx improvements:
- **Automate environment derivation** from spatial data
- **Model disease risk** instead of user input
- **Use standard 1-9 ratings** from seed guides
- **Add transparency** with component scores
- **Integrate weather** for maturity and stress risk
