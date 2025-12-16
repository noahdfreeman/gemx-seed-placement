# GEMx Architecture — Genetics × Environment × Management

## Overview

GEMx is a seed placement recommendation engine that matches **hybrid/variety genetic traits** to **field environments** and **management practices**. The system scores each product against field conditions to produce ranked recommendations.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GENETICS (G)  │    │ ENVIRONMENT (E) │    │ MANAGEMENT (M)  │
│                 │    │                 │    │                 │
│ Hybrid/Variety  │    │ Field-specific  │    │ Grower-reported │
│ trait ratings   │    │ conditions      │    │ practices       │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   SCORING ENGINE      │
                    │                       │
                    │ Match traits to       │
                    │ field requirements    │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   RECOMMENDATIONS     │
                    │                       │
                    │ Ranked products with  │
                    │ fit scores & rationale│
                    └───────────────────────┘
```

---

## Part 1: Data Layer → Trait Rating Mappings

This is the core mapping between field conditions and the genetic ratings that matter for each condition.

### 1.1 Soil-Based Layers

| Data Layer | Source | Corn Hybrid Ratings | Soybean Variety Ratings |
|------------|--------|---------------------|------------------------|
| **Soil Texture** (sand/silt/clay %) | SSURGO/gSSURGO | Drought tolerance, Root strength | Drought tolerance, Emergence |
| **Organic Matter** | SSURGO | N response, Yield potential | Yield potential |
| **pH** | SSURGO, Soil samples | pH tolerance (rare rating) | Iron Deficiency Chlorosis (IDC) |
| **Drainage Class** | SSURGO | Flooding tolerance, Early vigor | Phytophthora tolerance, Emergence |
| **Available Water Capacity** | SSURGO | Drought tolerance | Drought tolerance |
| **CEC** | SSURGO | Nutrient efficiency | Nutrient efficiency |
| **Slope** | DEM/SSURGO | Standability, Root lodging | Standability |

### 1.2 Weather/Climate Layers

| Data Layer | Source | Corn Hybrid Ratings | Soybean Variety Ratings |
|------------|--------|---------------------|------------------------|
| **Growing Degree Days (GDD)** | PRISM, gridMET | Relative Maturity (RM) | Maturity Group (MG) |
| **Frost-free days** | PRISM | RM, Dry-down | MG |
| **Precipitation (growing season)** | PRISM | Drought tolerance | Drought tolerance |
| **Precipitation variability** | PRISM | Drought tolerance, Flex ear | Drought tolerance |
| **Heat stress days (>95°F)** | PRISM | Heat tolerance, Pollen viability | Heat tolerance |
| **Historical drought frequency** | PRISM/PDSI | Drought tolerance | Drought tolerance |

### 1.3 Disease Pressure Layers

| Data Layer | Source | Corn Hybrid Ratings | Soybean Variety Ratings |
|------------|--------|---------------------|------------------------|
| **Gray Leaf Spot risk** | Historical + weather model | GLS tolerance (1-9) | — |
| **Northern Corn Leaf Blight** | Historical + weather model | NCLB tolerance (1-9) | — |
| **Tar Spot risk** | Historical + weather model | Tar Spot tolerance | — |
| **Goss's Wilt risk** | Regional history | Goss's Wilt tolerance | — |
| **Sudden Death Syndrome** | Soil temp + moisture model | — | SDS tolerance (1-9) |
| **White Mold** | Historical + canopy model | — | White Mold tolerance |
| **Phytophthora** | Drainage + history | — | Phytophthora genes (Rps1k, etc.) |
| **Soybean Cyst Nematode** | Soil samples, history | — | SCN resistance (PI 88788, Peking) |
| **Frogeye Leaf Spot** | Historical + weather | — | Frogeye tolerance |
| **Brown Stem Rot** | Rotation history | — | BSR tolerance |

### 1.4 Pest Pressure Layers

| Data Layer | Source | Corn Hybrid Ratings | Soybean Variety Ratings |
|------------|--------|---------------------|------------------------|
| **Corn Rootworm pressure** | Trap data, rotation | CRW traits (Bt, native) | — |
| **European Corn Borer** | Regional history | ECB Bt traits | — |
| **Corn Earworm** | Regional history | Earworm Bt traits | — |
| **Aphid pressure** | Regional monitoring | — | Aphid tolerance |

### 1.5 Management Practice Inputs

| Management Input | Collection Method | Corn Hybrid Ratings | Soybean Variety Ratings |
|------------------|-------------------|---------------------|------------------------|
| **Previous crop** | Questionnaire | CRW traits (corn-on-corn) | SCN, SDS risk |
| **Tillage system** | Questionnaire | Emergence, Early vigor | Emergence, Phytophthora |
| **Planting date (typical)** | Questionnaire | RM selection, Cold tolerance | MG selection |
| **Target population** | Questionnaire | Flex ear vs. fixed ear | Branching habit |
| **Irrigation** | Questionnaire | Drought tolerance (less critical) | Drought tolerance |
| **Fungicide program** | Questionnaire | Disease tolerance (can relax) | Disease tolerance |
| **Seed treatment** | Questionnaire | Early vigor, Emergence | Emergence, Phytophthora |
| **Nitrogen program** | Questionnaire | N efficiency, Stay-green | — |
| **Herbicide program** | Questionnaire | Herbicide traits (RR, LL, etc.) | Herbicide traits (RR, XT, E3) |

---

## Part 2: Genetic Trait Ratings — Data Sources

### 2.1 Corn Hybrid Ratings (Typical Seed Guide Format)

| Trait Category | Specific Traits | Rating Scale | Public Sources |
|----------------|-----------------|--------------|----------------|
| **Agronomics** | Relative Maturity | Days (e.g., 108) | Seed guides, NCGA trials |
| | Yield potential | 1-9 or relative % | Company guides, university trials |
| | Test weight | 1-9 | Seed guides |
| | Dry-down | 1-9 | Seed guides |
| **Standability** | Stalk strength | 1-9 | Seed guides |
| | Root strength | 1-9 | Seed guides |
| | Intactability | 1-9 | Seed guides |
| **Stress Tolerance** | Drought tolerance | 1-9 | Seed guides |
| | Heat tolerance | 1-9 | Seed guides |
| | Cold/emergence | 1-9 | Seed guides |
| **Disease** | GLS, NCLB, Tar Spot, etc. | 1-9 | Seed guides |
| **Traits** | Bt traits (VT2P, SmartStax, etc.) | Present/Absent | Seed guides |
| | Herbicide traits | RR, LL, Enlist | Seed guides |

### 2.2 Soybean Variety Ratings

| Trait Category | Specific Traits | Rating Scale | Public Sources |
|----------------|-----------------|--------------|----------------|
| **Agronomics** | Maturity Group | 0.0 - 5.0+ | Seed guides, university trials |
| | Yield potential | 1-9 or bu/ac | Seed guides, VIPS trials |
| | Plant height | Inches or 1-9 | Seed guides |
| | Lodging resistance | 1-9 | Seed guides |
| **Disease** | SDS, SCN, Phytophthora, etc. | 1-9 or gene | Seed guides |
| | IDC tolerance | 1-9 | Seed guides (critical in MN/ND) |
| **Traits** | Herbicide traits | RR, RR2X, XT, E3, GT27 | Seed guides |

### 2.3 Public Data Sources for Ratings

| Source | URL/Access | Data Available |
|--------|------------|----------------|
| **University Variety Trials** | State extension websites | Yield, standability, disease notes |
| **USDA GRIN** | npgsweb.ars-grin.gov | Germplasm traits |
| **Seed Company Guides** | Company websites (PDF/web) | Full trait ratings |
| **Farmers Business Network** | fbn.com (subscription) | Aggregated performance |
| **FIRST (Soybean)** | firstsoybean.com | Independent soybean trials |
| **NCGA Corn Yield Contest** | ncga.com | Top-performing hybrids |

---

## Part 3: Scoring Algorithm Design

### 3.1 Field Requirement Derivation

For each field, derive **requirement scores** from environmental data:

```python
class FieldRequirements:
    # Derived from E + M layers
    drought_stress_risk: float      # 0-1, from AWC + precip + irrigation
    disease_pressure: dict          # {disease: risk_score}
    pest_pressure: dict             # {pest: risk_score}
    target_rm: tuple                # (min_rm, optimal_rm, max_rm)
    standability_need: float        # 0-1, from wind exposure + soil
    emergence_challenge: float      # 0-1, from tillage + drainage + soil
```

### 3.2 Product Scoring

For each hybrid/variety, compute **fit score** against field requirements:

```python
def score_product(product: HybridRatings, field: FieldRequirements) -> float:
    scores = []
    
    # Maturity fit (hard constraint)
    rm_score = maturity_fit(product.rm, field.target_rm)
    if rm_score < 0.5:
        return 0  # Disqualify if maturity doesn't fit
    
    # Stress tolerance match
    drought_score = match_rating(product.drought_tolerance, field.drought_stress_risk)
    
    # Disease tolerance match
    disease_scores = [
        match_rating(product.disease_ratings[d], field.disease_pressure[d])
        for d in field.disease_pressure
    ]
    
    # Agronomic fit
    standability_score = match_rating(product.stalk_strength, field.standability_need)
    emergence_score = match_rating(product.emergence_vigor, field.emergence_challenge)
    
    # Weighted combination
    return weighted_average([
        (rm_score, 0.20),
        (drought_score, 0.15),
        (mean(disease_scores), 0.25),
        (standability_score, 0.15),
        (emergence_score, 0.10),
        (product.yield_potential, 0.15),  # Baseline yield matters
    ])
```

### 3.3 Recommendation Output

```python
class Recommendation:
    product: str                    # Hybrid/variety name
    fit_score: float               # 0-100
    strengths: list[str]           # Why this product fits
    watch_outs: list[str]          # Potential concerns
    suggested_population: int      # Based on field + product
    suggested_placement: str       # "Best fields", "Average fields", etc.
```

---

## Part 4: Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   SSURGO     │  │    PRISM     │  │  Seed Guides │              │
│  │  (Soil)      │  │  (Weather)   │  │  (Genetics)  │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         ▼                 ▼                 ▼                       │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │              PostGIS / Parquet Cache                      │      │
│  │  - Soil properties by geometry                            │      │
│  │  - Weather normals + recent years                         │      │
│  │  - Product catalog with ratings                           │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FEATURE EXTRACTION                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Field Boundary → Extract:                                          │
│    - Soil properties (weighted by area)                             │
│    - Weather normals (centroid or area-weighted)                    │
│    - Disease risk models                                            │
│    - Derived requirements                                           │
│                                                                     │
│  Management Questionnaire → Extract:                                │
│    - Adjusted disease/pest risk                                     │
│    - Trait requirements (herbicide, Bt)                             │
│    - Maturity constraints                                           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SCORING ENGINE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  For each product in filtered catalog:                              │
│    1. Check hard constraints (maturity, traits)                     │
│    2. Score against field requirements                              │
│    3. Generate strengths/watch-outs                                 │
│    4. Rank and return Top-N                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       OUTPUT                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  - Interactive dashboard (field map + recommendations)              │
│  - PDF report per grower/field                                      │
│  - CSV export for seed ordering                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Output Levels

GEMx provides three levels of output, from simple field-level recommendations to advanced variable rate prescriptions:

```
┌─────────────────────────────────────────────────────────────────┐
│                    GEMx OUTPUT LEVELS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: FIELD PLACEMENT                                       │
│  ├── Which hybrid/variety for this field?                       │
│  └── What base population for this field?                       │
│                                                                 │
│  Level 2: VARIABLE RATE SEEDING (VRS)                           │
│  ├── Continuous 10m productivity raster                         │
│  ├── Cell-by-cell population prescription                       │
│  └── Export to planter (GeoTIFF, Shapefile, AgX)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Variable Rate Seeding — Grid-Based Approach

VRS prescriptions are generated as **continuous 10m rasters**, not discrete zones. Each cell receives a population value calculated from a productivity model.

**Input Data Layers (10m Grid):**

| Data Source | Resolution | VRS Role |
|-------------|------------|----------|
| **SSURGO NCCPI** | Rasterized to 10m | Base soil productivity |
| **SSURGO AWC** | Rasterized to 10m | Drought stress component |
| **DEM Derivatives** | 10m native | TWI, slope, relative elevation |
| **Yield History** | Resampled to 10m | Best productivity indicator (if available) |
| **Satellite NDVI** | 10m native | Crop vigor (optional) |
| **Disease Risk Rasters** | 10m | GLS, SDS, Phyto penalties |

**Note:** EC mapping is NOT used.

### 5.2 Productivity → Population Formula

```python
# Step 1: Calculate productivity raster (0-1 per cell)
productivity = weighted_combination(
    nccpi, awc, twi, slope, yield_history, disease_penalties
)

# Step 2: Convert productivity to yield potential per cell
yield_multiplier = 0.7 + (productivity * 0.6)  # Range: 0.7x to 1.3x
cell_yield = field_avg_yield * yield_multiplier

# Step 3: Apply population formula
population = base_pop + (productivity - 0.5) * 2 * pop_range
# OR use hybrid-specific polynomial curve
```

### 5.3 Prescription Export Formats

| Format | Use Case |
|--------|----------|
| **GeoTIFF** | Native raster, preserves cell values |
| **Shapefile** | Vectorized for planter import |
| **AgX/ADAPT** | Industry standard |
| **John Deere Ops Center** | JD equipment integration |
| **Climate FieldView** | Climate platform integration |

---

## Part 6: Implementation Phases

### Phase 1: MVP (Streamlit + Local Data)
- [ ] Field boundary input (draw, upload, CLU)
- [ ] Basic soil extraction (SSURGO)
- [ ] Weather normals (PRISM)
- [ ] Management questionnaire
- [ ] Mock hybrid catalog (10-20 products)
- [ ] Simple scoring algorithm
- [ ] Basic recommendation display
- [ ] Field-level population recommendation

### Phase 2: Production Backend
- [ ] FastAPI backend
- [ ] PostGIS for spatial queries
- [ ] Real hybrid catalog (scraped/entered)
- [ ] Disease risk models
- [ ] User authentication
- [ ] Grower/field management
- [ ] Hybrid-specific population curves

### Phase 3: Variable Rate Seeding
- [ ] Productivity raster from SSURGO/DEM/yield history
- [ ] Cell-by-cell population prescriptions
- [ ] GeoTIFF and Shapefile export for planters
- [ ] Satellite imagery integration

### Phase 4: Advanced Features
- [ ] Historical performance tracking
- [ ] Brand whitelist/preferences
- [ ] Multi-year weather analysis
- [ ] PDF report generation
- [ ] Integration with seed ordering systems
- [ ] Machine learning zone optimization

---

## Part 7: Key Design Decisions

### 6.1 Rating Scale Normalization
Different seed companies use different scales (1-9, 1-5, descriptive). Need a normalization layer:

```python
SCALE_MAPPINGS = {
    "1-9": lambda x: x / 9,
    "1-5": lambda x: x / 5,
    "descriptive": {
        "Excellent": 0.9,
        "Very Good": 0.8,
        "Good": 0.7,
        "Average": 0.5,
        "Below Average": 0.3,
        "Poor": 0.1,
    }
}
```

### 6.2 Missing Data Handling
Not all products have all ratings. Strategy:
- Use category averages for missing ratings
- Flag recommendations with incomplete data
- Weight known ratings higher

### 6.3 Maturity Selection Logic
```python
def select_target_rm(gdd_accumulation: int, planting_date: date, 
                     harvest_target: date, safety_margin: int = 100) -> tuple:
    """
    Returns (min_rm, optimal_rm, max_rm) based on:
    - Available GDD from planting to target harvest
    - Safety margin for dry-down
    - Regional frost risk
    """
    available_gdd = gdd_accumulation - safety_margin
    optimal_rm = gdd_to_rm(available_gdd)
    return (optimal_rm - 3, optimal_rm, optimal_rm + 2)
```

### 6.4 Disease Risk Modeling
Simple initial approach:
```python
def disease_risk(disease: str, field: Field, weather: WeatherData) -> float:
    """
    Combine:
    - Regional historical prevalence
    - Field-specific factors (drainage, rotation)
    - Recent weather favorability
    """
    base_risk = REGIONAL_DISEASE_PREVALENCE[disease][field.region]
    field_modifier = FIELD_RISK_FACTORS[disease](field)
    weather_modifier = WEATHER_RISK_FACTORS[disease](weather)
    return min(1.0, base_risk * field_modifier * weather_modifier)
```

---

## Appendix A: Trait Rating Crosswalk

### Corn Disease Ratings → Field Conditions

| Disease | Favoring Conditions | Key Field Indicators |
|---------|--------------------|--------------------|
| Gray Leaf Spot | Humid, corn-on-corn, no-till | Rotation, tillage, humidity |
| NCLB | Cool, wet, susceptible residue | Rotation, weather |
| Tar Spot | Cool nights, high humidity | Regional spread, weather |
| Goss's Wilt | Hail damage, warm/wet | Regional presence, storm history |

### Soybean Disease Ratings → Field Conditions

| Disease | Favoring Conditions | Key Field Indicators |
|---------|--------------------|--------------------|
| SDS | Cool, wet early; compaction | Drainage, planting date, soil temp |
| SCN | Continuous soy, susceptible varieties | Rotation, egg counts |
| Phytophthora | Saturated soils, poor drainage | Drainage class, flooding history |
| White Mold | Dense canopy, cool/wet flowering | Row spacing, population, weather |
| IDC | High pH, wet, calcareous soils | Soil pH, carbonates |

---

## Appendix B: Data Source Details

### SSURGO Properties to Extract
- `texcl` - Texture class
- `om_r` - Organic matter (representative)
- `ph1to1h2o_r` - pH
- `drclassdcd` - Drainage class (dominant)
- `aws0100` - Available water storage 0-100cm
- `cec7_r` - CEC at pH 7

### PRISM Variables
- `ppt` - Precipitation (monthly/annual)
- `tmax`, `tmin`, `tmean` - Temperature
- Derived: GDD (base 50°F for corn, 50°F for soy)

### Weather-Derived Metrics
- Growing season precipitation (Apr-Sep)
- Heat stress days (days > 95°F in July-Aug)
- GDD accumulation (May 1 - Oct 1)
- Frost-free period
