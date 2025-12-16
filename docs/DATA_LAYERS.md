# GEMx Data Layers — Detailed Specifications

## Overview

This document details each data layer, its source, extraction method, and how it maps to genetic trait requirements.

---

## 1. Environmental Layers (E)

### 1.1 Soil Properties (SSURGO/gSSURGO)

**Source:** USDA NRCS Soil Survey  
**Format:** Shapefile/GeoPackage with tabular joins  
**Update Frequency:** Annual (minor updates)

| Property | SSURGO Column | Unit | Extraction Method |
|----------|---------------|------|-------------------|
| Texture Class | `texcl` | Category | Area-weighted mode |
| Sand % | `sandtotal_r` | % | Area-weighted mean |
| Silt % | `silttotal_r` | % | Area-weighted mean |
| Clay % | `claytotal_r` | % | Area-weighted mean |
| Organic Matter | `om_r` | % | Area-weighted mean |
| pH | `ph1to1h2o_r` | pH units | Area-weighted mean |
| CEC | `cec7_r` | meq/100g | Area-weighted mean |
| Drainage Class | `drclassdcd` | Category | Area-weighted mode |
| Hydrologic Group | `hydgrpdcd` | A/B/C/D | Area-weighted mode |
| AWS 0-100cm | `aws0100` | cm | Area-weighted mean |
| Flooding Frequency | `flodfreqdcd` | Category | Worst-case |
| Ponding Frequency | `pondfreqdcd` | Category | Worst-case |
| Slope | `slope_r` | % | Area-weighted mean |

**Derived Metrics:**
```python
def derive_soil_metrics(soil_props: dict) -> dict:
    return {
        "drought_risk": calculate_drought_risk(
            soil_props["aws0100"],
            soil_props["sand_pct"],
            soil_props["om_pct"]
        ),
        "compaction_risk": calculate_compaction_risk(
            soil_props["clay_pct"],
            soil_props["drainage_class"]
        ),
        "emergence_challenge": calculate_emergence_challenge(
            soil_props["texture_class"],
            soil_props["drainage_class"],
            soil_props["om_pct"]
        ),
        "idc_risk": calculate_idc_risk(  # Soybeans only
            soil_props["ph"],
            soil_props["caco3_pct"]  # If available
        )
    }
```

---

### 1.2 Weather/Climate (PRISM)

**Source:** PRISM Climate Group, Oregon State University  
**Format:** BIL raster (4km resolution)  
**Update Frequency:** Monthly (provisional), Annual (stable)

| Variable | PRISM Code | Unit | Temporal Resolution |
|----------|------------|------|---------------------|
| Precipitation | `ppt` | mm | Daily, Monthly, Annual |
| Max Temperature | `tmax` | °C | Daily, Monthly |
| Min Temperature | `tmin` | °C | Daily, Monthly |
| Mean Temperature | `tmean` | °C | Daily, Monthly |
| Dew Point | `tdmean` | °C | Daily, Monthly |
| VPD Min | `vpdmin` | hPa | Daily, Monthly |
| VPD Max | `vpdmax` | hPa | Daily, Monthly |

**Derived Metrics:**
```python
def derive_weather_metrics(weather_data: pd.DataFrame, 
                           years: list = range(2015, 2025)) -> dict:
    return {
        # Growing Degree Days (base 50°F / 10°C)
        "gdd_mean": calculate_gdd_mean(weather_data, base=10),
        "gdd_std": calculate_gdd_std(weather_data, base=10),
        
        # Precipitation
        "growing_season_precip_mean": calc_precip(weather_data, months=[4,5,6,7,8,9]),
        "growing_season_precip_cv": calc_precip_cv(weather_data, months=[4,5,6,7,8,9]),
        "july_precip_mean": calc_precip(weather_data, months=[7]),
        
        # Heat Stress
        "heat_stress_days": count_days_above(weather_data, threshold_f=95),
        "extreme_heat_days": count_days_above(weather_data, threshold_f=100),
        
        # Frost
        "last_spring_frost_median": calc_last_frost(weather_data, threshold_f=32),
        "first_fall_frost_median": calc_first_frost(weather_data, threshold_f=32),
        "frost_free_days": calc_frost_free_period(weather_data),
        
        # Drought indicators
        "drought_frequency": calc_drought_frequency(weather_data),  # % of years
    }
```

**GDD to Relative Maturity Conversion:**
```python
# Approximate GDD requirements by RM (corn)
GDD_BY_RM = {
    85: 2100,
    90: 2200,
    95: 2350,
    100: 2500,
    105: 2650,
    108: 2750,
    110: 2850,
    112: 2950,
    115: 3100,
}

def gdd_to_rm(available_gdd: int) -> int:
    """Convert available GDD to recommended RM."""
    for rm, required_gdd in sorted(GDD_BY_RM.items(), reverse=True):
        if available_gdd >= required_gdd:
            return rm
    return 85  # Minimum RM if very short season
```

---

### 1.3 Topography (DEM-derived)

**Source:** USGS 3DEP (1/3 arc-second DEM)  
**Format:** GeoTIFF  
**Resolution:** ~10m

| Metric | Derivation | Relevance |
|--------|------------|-----------|
| Slope | DEM gradient | Erosion risk, equipment access |
| Aspect | DEM direction | Microclimate, snow melt |
| TWI | Topographic Wetness Index | Drainage, ponding risk |
| Curvature | Profile/plan curvature | Water accumulation |

---

### 1.4 Disease Pressure Models

Disease risk is modeled from environmental conditions + regional history.

#### Gray Leaf Spot (Corn)
```python
def gls_risk(field: Field, weather: Weather, management: Management) -> float:
    """
    GLS favored by:
    - Corn-on-corn rotation
    - No-till (residue)
    - High humidity, moderate temps
    - History of GLS in region
    """
    base_risk = REGIONAL_GLS_PREVALENCE.get(field.state, 0.3)
    
    # Rotation modifier
    if management.previous_crop == "corn":
        base_risk *= 1.5
    
    # Tillage modifier
    if management.tillage == "no-till":
        base_risk *= 1.3
    elif management.tillage == "conventional":
        base_risk *= 0.7
    
    # Weather modifier (humid growing season)
    humidity_factor = weather.july_aug_humidity / 70  # Normalize to 70% baseline
    base_risk *= humidity_factor
    
    return min(1.0, base_risk)
```

#### Sudden Death Syndrome (Soybean)
```python
def sds_risk(field: Field, weather: Weather, management: Management) -> float:
    """
    SDS favored by:
    - Cool, wet conditions at planting
    - Soil compaction
    - Early planting into cold soils
    - SCN presence (vector)
    """
    base_risk = REGIONAL_SDS_PREVALENCE.get(field.state, 0.2)
    
    # Soil temperature at planting
    if management.planting_date < date(2024, 4, 20):
        base_risk *= 1.4  # Early planting risk
    
    # Drainage modifier
    drainage_multiplier = {
        "very poorly drained": 1.5,
        "poorly drained": 1.3,
        "somewhat poorly drained": 1.1,
        "moderately well drained": 1.0,
        "well drained": 0.8,
        "excessively drained": 0.7,
    }
    base_risk *= drainage_multiplier.get(field.drainage_class, 1.0)
    
    # Compaction risk (clay + traffic)
    if field.clay_pct > 35:
        base_risk *= 1.2
    
    return min(1.0, base_risk)
```

#### Soybean Cyst Nematode (SCN)
```python
def scn_risk(field: Field, management: Management, 
             scn_egg_count: Optional[int] = None) -> float:
    """
    SCN risk based on:
    - Known egg counts (if sampled)
    - Rotation history
    - Regional prevalence
    - Variety resistance history
    """
    if scn_egg_count is not None:
        # Direct measurement available
        if scn_egg_count < 200:
            return 0.2
        elif scn_egg_count < 2000:
            return 0.5
        elif scn_egg_count < 10000:
            return 0.7
        else:
            return 0.9
    
    # Estimate from rotation
    base_risk = REGIONAL_SCN_PREVALENCE.get(field.state, 0.5)
    
    soy_years_in_last_5 = management.soy_frequency_5yr
    if soy_years_in_last_5 >= 4:
        base_risk *= 1.5
    elif soy_years_in_last_5 >= 3:
        base_risk *= 1.2
    elif soy_years_in_last_5 <= 1:
        base_risk *= 0.7
    
    return min(1.0, base_risk)
```

---

## 2. Management Layers (M)

### 2.1 Management Questionnaire

| Question | Options | Impact on Recommendations |
|----------|---------|---------------------------|
| **Previous crop** | Corn, Soybean, Wheat, Other | Disease/pest carryover |
| **Crop 2 years ago** | Same options | Rotation pattern |
| **Tillage system** | No-till, Strip-till, Minimum till, Conventional | Emergence, disease residue |
| **Typical planting date** | Date range | Maturity selection |
| **Target harvest date** | Date or "Before X" | Maturity selection |
| **Irrigation** | None, Pivot, Drip, Flood | Drought tolerance need |
| **Target population** | seeds/acre | Ear type, branching |
| **Row spacing** | 15", 20", 30", 36"+ | White mold risk (soy) |
| **Fungicide program** | None, As-needed, Routine | Disease tolerance need |
| **Seed treatment** | None, Basic, Premium | Emergence support |
| **Herbicide system** | Conventional, RR, LL, Enlist, XtendFlex | Trait requirements |
| **Known pest issues** | Multi-select | Specific trait needs |
| **Known disease issues** | Multi-select | Specific tolerance needs |

### 2.2 Management Impact Matrix

```python
MANAGEMENT_IMPACTS = {
    "tillage": {
        "no-till": {
            "emergence_challenge": +0.2,
            "gls_risk": +0.15,
            "nclb_risk": +0.15,
            "tar_spot_risk": +0.1,
        },
        "conventional": {
            "emergence_challenge": -0.1,
            "gls_risk": -0.2,
            "nclb_risk": -0.2,
            "erosion_risk": +0.2,
        }
    },
    "irrigation": {
        "pivot": {
            "drought_tolerance_need": -0.5,
            "white_mold_risk": +0.1,  # Soy
        },
        "none": {
            "drought_tolerance_need": +0.0,  # Use environmental baseline
        }
    },
    "fungicide_program": {
        "routine": {
            "disease_tolerance_need": -0.3,  # Can relax disease requirements
        },
        "none": {
            "disease_tolerance_need": +0.2,  # Need more tolerant varieties
        }
    }
}
```

---

## 3. Genetic Layers (G)

### 3.1 Hybrid/Variety Catalog Schema

```python
@dataclass
class CornHybrid:
    # Identification
    brand: str
    hybrid_name: str
    
    # Agronomics
    relative_maturity: float  # e.g., 108.0
    yield_potential: int      # 1-9 scale
    test_weight: int          # 1-9 scale
    drydown: int              # 1-9 scale
    
    # Standability
    stalk_strength: int       # 1-9 scale
    root_strength: int        # 1-9 scale
    intactability: int        # 1-9 scale
    
    # Stress tolerance
    drought_tolerance: int    # 1-9 scale
    heat_tolerance: int       # 1-9 scale (if available)
    emergence_vigor: int      # 1-9 scale
    
    # Disease ratings
    gray_leaf_spot: int       # 1-9 scale
    northern_leaf_blight: int # 1-9 scale
    tar_spot: int             # 1-9 scale (newer rating)
    gosss_wilt: int           # 1-9 scale
    anthracnose_stalk: int    # 1-9 scale
    
    # Traits
    bt_traits: list[str]      # e.g., ["VT2P", "RIB"]
    herbicide_traits: list[str]  # e.g., ["RR", "LL"]
    
    # Ear type
    ear_type: str             # "Flex", "Semi-flex", "Fixed"
    kernel_type: str          # "Dent", "Semi-dent", "Flint"
    
    # Metadata
    year_introduced: int
    data_source: str
    confidence: float         # Data completeness score


@dataclass
class SoybeanVariety:
    # Identification
    brand: str
    variety_name: str
    
    # Agronomics
    maturity_group: float     # e.g., 2.8
    yield_potential: int      # 1-9 scale
    plant_height: int         # 1-9 or inches
    lodging_resistance: int   # 1-9 scale
    
    # Stress tolerance
    drought_tolerance: int    # 1-9 scale
    emergence_vigor: int      # 1-9 scale
    idc_tolerance: int        # 1-9 scale (critical in MN/ND/SD)
    
    # Disease ratings
    sds_tolerance: int        # 1-9 scale
    scn_resistance: str       # "PI 88788", "Peking", "None", etc.
    phytophthora_genes: list[str]  # e.g., ["Rps1c", "Rps1k"]
    phytophthora_field: int   # 1-9 field tolerance
    white_mold: int           # 1-9 scale
    brown_stem_rot: int       # 1-9 scale
    frogeye_leaf_spot: int    # 1-9 scale
    
    # Traits
    herbicide_traits: list[str]  # e.g., ["RR2X", "STS"]
    
    # Plant architecture
    growth_habit: str         # "Determinate", "Indeterminate"
    branching: str            # "Bushy", "Moderate", "Erect"
    canopy_closure: str       # "Fast", "Medium", "Slow"
    
    # Metadata
    year_introduced: int
    data_source: str
    confidence: float
```

### 3.2 Rating Normalization

```python
def normalize_rating(value: Any, scale: str, trait: str) -> float:
    """
    Normalize various rating scales to 0-1 range.
    Higher = better for the trait.
    """
    if scale == "1-9":
        return value / 9.0
    
    elif scale == "1-5":
        return value / 5.0
    
    elif scale == "descriptive":
        mapping = {
            "Excellent": 0.95,
            "Very Good": 0.85,
            "Good": 0.70,
            "Average": 0.50,
            "Fair": 0.35,
            "Below Average": 0.25,
            "Poor": 0.10,
        }
        return mapping.get(value, 0.5)
    
    elif scale == "present_absent":
        return 1.0 if value else 0.0
    
    elif scale == "scn_source":
        # SCN resistance sources have different effectiveness
        mapping = {
            "PI 88788": 0.7,  # Most common, some populations adapted
            "Peking": 0.85,   # Less common, broader resistance
            "PI 89772": 0.8,
            "PI 437654": 0.9,
            "Hartwig": 0.85,
            "None": 0.0,
        }
        return mapping.get(value, 0.5)
    
    else:
        return value  # Assume already normalized
```

---

## 4. Feature Cache Design

### 4.1 PostGIS Schema

```sql
-- Fields table
CREATE TABLE fields (
    id UUID PRIMARY KEY,
    grower_id UUID REFERENCES growers(id),
    name VARCHAR(255),
    boundary GEOMETRY(POLYGON, 4326),
    acres NUMERIC(10, 2),
    centroid GEOMETRY(POINT, 4326),
    state VARCHAR(2),
    county VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Soil features (extracted from SSURGO)
CREATE TABLE field_soil_features (
    field_id UUID PRIMARY KEY REFERENCES fields(id),
    texture_class VARCHAR(50),
    sand_pct NUMERIC(5, 2),
    silt_pct NUMERIC(5, 2),
    clay_pct NUMERIC(5, 2),
    om_pct NUMERIC(5, 2),
    ph NUMERIC(4, 2),
    cec NUMERIC(6, 2),
    drainage_class VARCHAR(50),
    hydro_group VARCHAR(2),
    aws_0_100 NUMERIC(6, 2),
    slope_pct NUMERIC(5, 2),
    flood_freq VARCHAR(50),
    extracted_at TIMESTAMP DEFAULT NOW()
);

-- Weather features (extracted from PRISM)
CREATE TABLE field_weather_features (
    field_id UUID PRIMARY KEY REFERENCES fields(id),
    gdd_mean NUMERIC(8, 2),
    gdd_std NUMERIC(6, 2),
    growing_season_precip_mm NUMERIC(8, 2),
    precip_cv NUMERIC(5, 3),
    heat_stress_days NUMERIC(5, 2),
    frost_free_days INTEGER,
    last_spring_frost DATE,
    first_fall_frost DATE,
    extracted_at TIMESTAMP DEFAULT NOW()
);

-- Derived risk scores
CREATE TABLE field_risk_scores (
    field_id UUID PRIMARY KEY REFERENCES fields(id),
    drought_risk NUMERIC(4, 3),
    gls_risk NUMERIC(4, 3),
    nclb_risk NUMERIC(4, 3),
    tar_spot_risk NUMERIC(4, 3),
    sds_risk NUMERIC(4, 3),
    scn_risk NUMERIC(4, 3),
    phytophthora_risk NUMERIC(4, 3),
    white_mold_risk NUMERIC(4, 3),
    idc_risk NUMERIC(4, 3),
    calculated_at TIMESTAMP DEFAULT NOW()
);

-- Product catalog
CREATE TABLE corn_hybrids (
    id UUID PRIMARY KEY,
    brand VARCHAR(100),
    hybrid_name VARCHAR(100),
    relative_maturity NUMERIC(5, 1),
    yield_potential INTEGER,
    drought_tolerance INTEGER,
    stalk_strength INTEGER,
    root_strength INTEGER,
    gls_rating INTEGER,
    nclb_rating INTEGER,
    tar_spot_rating INTEGER,
    bt_traits TEXT[],
    herbicide_traits TEXT[],
    ear_type VARCHAR(20),
    data_source VARCHAR(100),
    confidence NUMERIC(3, 2),
    UNIQUE(brand, hybrid_name)
);

CREATE TABLE soybean_varieties (
    id UUID PRIMARY KEY,
    brand VARCHAR(100),
    variety_name VARCHAR(100),
    maturity_group NUMERIC(3, 1),
    yield_potential INTEGER,
    drought_tolerance INTEGER,
    idc_tolerance INTEGER,
    sds_rating INTEGER,
    scn_source VARCHAR(50),
    phytophthora_genes TEXT[],
    phytophthora_field INTEGER,
    white_mold_rating INTEGER,
    herbicide_traits TEXT[],
    growth_habit VARCHAR(20),
    data_source VARCHAR(100),
    confidence NUMERIC(3, 2),
    UNIQUE(brand, variety_name)
);
```

---

## 5. Data Quality & Gaps

### 5.1 Known Data Gaps

| Data Type | Gap | Mitigation |
|-----------|-----|------------|
| Tar Spot ratings | New disease, many hybrids unrated | Use regional average, flag uncertainty |
| Heat tolerance | Rarely published | Infer from drought tolerance + RM |
| SCN egg counts | Requires soil sampling | Use rotation-based estimate |
| Actual yield history | Proprietary | Use relative yield potential |
| Subfield variability | Requires zone maps | Start with field-level averages |

### 5.2 Data Confidence Scoring

```python
def calculate_data_confidence(product: Union[CornHybrid, SoybeanVariety]) -> float:
    """
    Score 0-1 based on data completeness and source quality.
    """
    # Count non-null critical ratings
    critical_fields = [
        "yield_potential", "drought_tolerance", 
        "stalk_strength" if isinstance(product, CornHybrid) else "lodging_resistance",
    ]
    
    disease_fields = [
        "gls_rating", "nclb_rating"
    ] if isinstance(product, CornHybrid) else [
        "sds_rating", "scn_source", "phytophthora_field"
    ]
    
    critical_score = sum(1 for f in critical_fields if getattr(product, f) is not None) / len(critical_fields)
    disease_score = sum(1 for f in disease_fields if getattr(product, f) is not None) / len(disease_fields)
    
    # Source quality multiplier
    source_multiplier = {
        "seed_guide_official": 1.0,
        "university_trial": 0.9,
        "aggregated_farmer": 0.8,
        "estimated": 0.5,
    }.get(product.data_source, 0.7)
    
    return (0.6 * critical_score + 0.4 * disease_score) * source_multiplier
```
