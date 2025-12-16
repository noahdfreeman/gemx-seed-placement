# Variable Rate Seeding (VRS) — Grid-Based Prescriptions

## Overview

GEMx generates **continuous 10m grid-based** variable rate seeding prescriptions. Rather than discrete zones, each 10m cell receives a population value calculated from a productivity model that integrates multiple GEMx data layers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    GEMx OUTPUT LEVELS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: FIELD PLACEMENT                                       │
│  ├── Which hybrid/variety for this field?                       │
│  └── What base population for this field?                       │
│                                                                 │
│  Level 2: VARIABLE RATE SEEDING (10m Grid)                      │
│  ├── Continuous productivity raster (0-1 scale)                 │
│  ├── Cell-by-cell population from productivity formula          │
│  └── Export to planter (GeoTIFF, Shapefile, AgX)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Difference from Zone-Based Approaches:**
- No discrete zones (Low/Medium/High)
- Every 10m cell has a unique productivity value
- Population varies continuously across the field
- Leverages all GEMx spatial models at native resolution

---

## 1. Productivity Raster Model

The core of VRS is a **continuous productivity raster** at 10m resolution. The **primary driver** is the multi-year yield data layer, supplemented by topographic and weather forecast data.

### 1.1 Primary Data Layers

| Data Layer | Source | Role | Weight |
|------------|--------|------|--------|
| **Multi-Year Yield Layer** | User's yield model | **Primary driver** — productivity level + variation | 0.60-0.70 |
| **Topographic Wetness Index (TWI)** | Derived from DEM | Drainage/ponding risk modifier | 0.15-0.20 |
| **Long-Range Weather Forecast (LRWF)** | User's forecast model | Season-specific adjustment | 0.10-0.20 |

### 1.2 Multi-Year Yield Data Layer

The yield data layer quantifies both **productivity level** and **yield stability/variation** across the field:

```python
@dataclass
class YieldDataLayer:
    """Multi-year yield analysis for VRS."""
    
    # Core rasters (10m resolution)
    mean_yield: Raster           # Average yield across years (bu/ac)
    yield_std: Raster            # Standard deviation of yield
    yield_cv: Raster             # Coefficient of variation (std/mean)
    relative_yield: Raster       # Normalized to field average (0-1 scale)
    
    # Metadata
    years_included: list[int]    # e.g., [2020, 2021, 2022, 2023, 2024]
    num_years: int
    field_avg_yield: float       # Overall field average
    
    # Stability classification
    stability_class: Raster      # "stable_high", "stable_low", "variable"


def create_yield_data_layer(
    yield_rasters: dict[int, Raster],  # year -> yield raster
    min_years: int = 3,
) -> YieldDataLayer:
    """
    Create multi-year yield analysis layer.
    
    Quantifies:
    1. Productivity level (mean yield per cell)
    2. Yield variation (CV per cell)
    3. Stability classification
    """
    years = sorted(yield_rasters.keys())
    stack = np.stack([yield_rasters[y] for y in years], axis=0)
    
    # Calculate statistics per cell
    mean_yield = np.nanmean(stack, axis=0)
    yield_std = np.nanstd(stack, axis=0)
    yield_cv = yield_std / np.where(mean_yield > 0, mean_yield, 1)
    
    # Normalize to field average
    field_avg = np.nanmean(mean_yield)
    relative_yield = mean_yield / field_avg
    
    # Classify stability
    # High CV (>0.20) = variable, Low CV (<0.10) = stable
    stability_class = np.where(
        yield_cv < 0.10,
        np.where(relative_yield > 1.0, "stable_high", "stable_low"),
        "variable"
    )
    
    return YieldDataLayer(
        mean_yield=mean_yield,
        yield_std=yield_std,
        yield_cv=yield_cv,
        relative_yield=relative_yield,
        years_included=years,
        num_years=len(years),
        field_avg_yield=field_avg,
        stability_class=stability_class,
    )
```

### 1.3 Yield Variation Impact on Population

Yield variation (CV) affects population strategy:

| Stability Class | CV Range | Population Strategy |
|-----------------|----------|---------------------|
| **Stable High** | CV < 0.10, yield > avg | Higher populations — consistent high performers |
| **Stable Low** | CV < 0.10, yield < avg | Lower populations — consistent limiters |
| **Variable** | CV > 0.20 | Conservative populations — hedge against bad years |

```python
def adjust_population_for_variation(
    base_population: Raster,
    yield_cv: Raster,
    stability_class: Raster,
) -> Raster:
    """
    Adjust population based on yield stability.
    
    - Stable high areas: can push population higher
    - Variable areas: reduce population to hedge risk
    """
    adjustment = np.ones_like(base_population, dtype=float)
    
    # Stable high performers — increase 5%
    adjustment[stability_class == "stable_high"] = 1.05
    
    # Variable areas — reduce 5-10% based on CV
    variable_mask = stability_class == "variable"
    cv_penalty = np.clip((yield_cv - 0.15) * 0.5, 0, 0.10)  # Max 10% reduction
    adjustment[variable_mask] = 1.0 - cv_penalty[variable_mask]
    
    return (base_population * adjustment).astype(int)
```

### 1.4 Topographic Wetness Index (TWI)

TWI modifies productivity based on drainage characteristics:

```python
def calculate_twi_modifier(
    twi_raster: Raster,
    crop: str,
) -> Raster:
    """
    TWI modifier for productivity.
    
    - Very high TWI (wet areas): penalty for ponding/disease risk
    - Very low TWI (dry areas): penalty for drought stress
    - Optimal TWI: no penalty
    """
    twi_normalized = normalize_0_1(twi_raster)
    
    # Optimal TWI is mid-range (0.4-0.6 normalized)
    # Penalty increases as you move away from optimal
    deviation = np.abs(twi_normalized - 0.5)
    
    # Corn more sensitive to wet, soy more sensitive to dry
    if crop == "corn":
        # Penalize high TWI (wet) more
        wet_penalty = np.where(twi_normalized > 0.6, (twi_normalized - 0.6) * 0.3, 0)
        dry_penalty = np.where(twi_normalized < 0.4, (0.4 - twi_normalized) * 0.15, 0)
    else:  # soybean
        # Penalize both wet (SDS, Phyto) and dry equally
        wet_penalty = np.where(twi_normalized > 0.6, (twi_normalized - 0.6) * 0.25, 0)
        dry_penalty = np.where(twi_normalized < 0.4, (0.4 - twi_normalized) * 0.2, 0)
    
    # Modifier: 1.0 = no change, <1.0 = penalty
    modifier = 1.0 - wet_penalty - dry_penalty
    return np.clip(modifier, 0.7, 1.0)  # Max 30% penalty
```

### 1.5 Long-Range Weather Forecast (LRWF) Integration

The LRWF adjusts productivity expectations based on seasonal outlook:

```python
@dataclass
class LRWFAdjustment:
    """Long-range weather forecast adjustment for VRS."""
    
    # Forecast indicators (from user's LRWF model)
    precip_outlook: str          # "above_normal", "normal", "below_normal"
    temp_outlook: str            # "above_normal", "normal", "below_normal"
    drought_probability: float   # 0-1
    excess_moisture_prob: float  # 0-1
    
    # Derived adjustments
    yield_expectation_modifier: float  # Multiplier on expected yield
    population_adjustment: float       # Adjustment to base population


def calculate_lrwf_adjustment(
    lrwf: LRWFAdjustment,
    twi_raster: Raster,
    crop: str,
) -> Raster:
    """
    Apply LRWF to modify productivity spatially.
    
    Key interactions:
    - Dry forecast + high TWI areas = less penalty (moisture buffer)
    - Dry forecast + low TWI areas = more penalty (drought stress)
    - Wet forecast + high TWI areas = more penalty (ponding/disease)
    - Wet forecast + low TWI areas = less penalty (adequate moisture)
    """
    twi_normalized = normalize_0_1(twi_raster)
    adjustment = np.ones_like(twi_raster, dtype=float)
    
    if lrwf.precip_outlook == "below_normal" or lrwf.drought_probability > 0.4:
        # Dry year expected
        # Low TWI (droughty) areas get penalized more
        # High TWI (wet) areas have moisture buffer
        drought_penalty = (1 - twi_normalized) * lrwf.drought_probability * 0.15
        adjustment -= drought_penalty
        
    elif lrwf.precip_outlook == "above_normal" or lrwf.excess_moisture_prob > 0.4:
        # Wet year expected
        # High TWI areas get penalized (ponding, disease)
        # Low TWI areas benefit
        wet_penalty = twi_normalized * lrwf.excess_moisture_prob * 0.12
        adjustment -= wet_penalty
    
    return np.clip(adjustment, 0.85, 1.10)  # -15% to +10% adjustment


def apply_lrwf_to_population(
    base_population: Raster,
    lrwf: LRWFAdjustment,
) -> Raster:
    """
    Adjust population based on seasonal outlook.
    
    - Dry year forecast: reduce populations (less yield potential)
    - Wet year forecast: may reduce in wet areas (disease risk)
    """
    if lrwf.drought_probability > 0.5:
        # Significant drought risk — reduce populations field-wide
        reduction = 0.03 + (lrwf.drought_probability - 0.5) * 0.1  # 3-8% reduction
        return (base_population * (1 - reduction)).astype(int)
    
    return base_population
```

### 1.6 Combined Productivity Model

```python
def calculate_productivity_raster(
    yield_layer: YieldDataLayer,
    twi_raster: Raster,
    lrwf: Optional[LRWFAdjustment],
    crop: str,
) -> Raster:
    """
    Calculate final productivity raster from primary drivers.
    
    Primary driver: Multi-year yield layer (60-70%)
    Modifiers: TWI (15-20%), LRWF (10-20%)
    """
    # Start with yield-based productivity (normalized 0-1)
    productivity = normalize_0_1(yield_layer.relative_yield)
    
    # Apply TWI modifier
    twi_modifier = calculate_twi_modifier(twi_raster, crop)
    productivity = productivity * twi_modifier
    
    # Apply LRWF adjustment if available
    if lrwf is not None:
        lrwf_adjustment = calculate_lrwf_adjustment(lrwf, twi_raster, crop)
        productivity = productivity * lrwf_adjustment
    
    # Re-normalize to 0-1
    return normalize_0_1(productivity)
```

---

## 2. Fallback: SSURGO-Based Productivity

When yield data is not available, fall back to SSURGO NCCPI + TWI:

```python
def calculate_fallback_productivity(
    ssurgo_raster: dict[str, Raster],
    twi_raster: Raster,
    lrwf: Optional[LRWFAdjustment],
    crop: str,
) -> Raster:
    """
    Fallback productivity when no yield data available.
    
    Uses SSURGO NCCPI as primary, TWI and LRWF as modifiers.
    """
    # NCCPI as base (already 0-1 scale)
    nccpi_key = 'nccpi3corn' if crop == 'corn' else 'nccpi3soy'
    productivity = ssurgo_raster[nccpi_key]
    
    # Apply TWI modifier
    twi_modifier = calculate_twi_modifier(twi_raster, crop)
    productivity = productivity * twi_modifier
    
    # Apply LRWF if available
    if lrwf is not None:
        lrwf_adjustment = calculate_lrwf_adjustment(lrwf, twi_raster, crop)
        productivity = productivity * lrwf_adjustment
    
    return normalize_0_1(productivity)
```

---

## 3. Population Calculation (Cell-by-Cell)

### 3.1 Productivity to Population Formula

Each 10m cell's population is calculated directly from its productivity index:

```python
def productivity_to_population(
    productivity_raster: Raster,
    field_avg_yield: float,
    hybrid: CornHybrid,
    min_population: int = 24000,
    max_population: int = 38000,
) -> Raster:
    """
    Convert productivity raster (0-1) to population raster (seeds/acre).
    
    Formula:
    1. Convert productivity index to estimated yield potential per cell
    2. Apply hybrid-specific population curve
    3. Clip to min/max bounds
    
    Args:
        productivity_raster: 0-1 productivity index per cell
        field_avg_yield: Field average yield potential (bu/ac)
        hybrid: Selected hybrid with population curve
        min_population: Minimum population (seeds/acre)
        max_population: Maximum population (seeds/acre)
    """
    # Step 1: Convert productivity (0-1) to yield potential
    # Productivity of 0.5 = field average
    # Productivity of 1.0 = ~130% of field average
    # Productivity of 0.0 = ~70% of field average
    yield_multiplier = 0.7 + (productivity_raster * 0.6)  # Range: 0.7 to 1.3
    cell_yield_potential = field_avg_yield * yield_multiplier
    
    # Step 2: Apply hybrid population curve
    population_raster = hybrid.population_curve.calculate(cell_yield_potential)
    
    # Step 3: Clip to bounds
    population_raster = np.clip(population_raster, min_population, max_population)
    
    # Step 4: Round to nearest 100 (practical for planter)
    population_raster = np.round(population_raster / 100) * 100
    
    return population_raster.astype(int)
```

### 3.2 Alternative: Linear Productivity-to-Population

Simpler approach without hybrid-specific curves:

```python
def simple_productivity_to_population(
    productivity_raster: Raster,
    base_population: int,
    population_range: int = 8000,
) -> Raster:
    """
    Simple linear mapping from productivity to population.
    
    Args:
        productivity_raster: 0-1 productivity index per cell
        base_population: Target population at average productivity (e.g., 32000)
        population_range: Total range (+/- from base, e.g., 8000 = 24k to 40k)
    
    Formula:
        population = base + (productivity - 0.5) * 2 * range
        
    Example (base=32000, range=8000):
        productivity=0.0 → 24,000
        productivity=0.5 → 32,000  
        productivity=1.0 → 40,000
    """
    # Center productivity around 0.5, scale to -1 to +1
    centered = (productivity_raster - 0.5) * 2
    
    # Apply to population range
    population = base_population + (centered * population_range)
    
    # Round to nearest 500 for practical planter use
    return (np.round(population / 500) * 500).astype(int)
```

### 3.3 Hybrid-Specific Population Curves (Optional Enhancement)

For advanced users, hybrid-specific curves can be applied:

```python
@dataclass
class PopulationCurve:
    """Polynomial coefficients for population by yield potential."""
    hybrid_name: str
    ear_type: str  # "flex", "semi-flex", "fixed"
    
    # Cubic polynomial: pop = x3*yield^3 + x2*yield^2 + x*yield + b
    x3: float  # Cubic term (usually small, ~-0.0001)
    x2: float  # Quadratic term (~0.1)
    x: float   # Linear term (~3-25)
    b: float   # Intercept (~22,000-23,000)
    r2: float  # Fit quality
    
    def calculate_population(self, yield_potential: float) -> int:
        """Calculate optimal population for given yield potential."""
        pop = (
            self.x3 * yield_potential**3 +
            self.x2 * yield_potential**2 +
            self.x * yield_potential +
            self.b
        )
        return int(round(pop, -2))  # Round to nearest 100


# Example curves from your Excel data
POPULATION_CURVES = {
    "Hybrid_A": PopulationCurve(
        hybrid_name="Hybrid_A",
        x3=-0.000148,
        x2=0.106349,
        x=2.830688,
        b=22666.67,
        r2=0.992
    ),
    "Hybrid_B": PopulationCurve(
        hybrid_name="Hybrid_B",
        x3=-0.0,
        x2=0.028571,
        x=14.571429,
        b=22200,
        r2=0.991
    ),
}
```


---

## 3. Complete VRS Pipeline

### 3.1 End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│              GRID-BASED VRS PRESCRIPTION PIPELINE               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DATA LAYER ASSEMBLY (10m grid)                              │
│     ├── Rasterize SSURGO (NCCPI, AWC, drainage)                 │
│     ├── Calculate DEM derivatives (TWI, slope, rel. elevation)  │
│     ├── Import yield history (if available)                     │
│     └── Fetch satellite NDVI (if available)                     │
│                                                                 │
│  2. PRODUCTIVITY RASTER CALCULATION                             │
│     ├── Combine layers with weights                             │
│     ├── Apply disease risk penalties (GLS, SDS, etc.)           │
│     ├── Apply drought/ponding penalties                         │
│     └── Output: 0-1 productivity per cell                       │
│                                                                 │
│  3. HYBRID SELECTION (from GEMx placement)                      │
│     └── Single hybrid for field                                 │
│                                                                 │
│  4. POPULATION CALCULATION (cell-by-cell)                       │
│     ├── Convert productivity to yield potential per cell        │
│     ├── Apply population formula (linear or curve)              │
│     └── Round to practical increments (500 seeds)               │
│                                                                 │
│  5. PRESCRIPTION EXPORT                                         │
│     ├── GeoTIFF (native raster)                                 │
│     ├── Shapefile (vectorized for planters)                     │
│     ├── AgX/ADAPT format                                        │
│     ├── John Deere Operations Center                            │
│     └── Climate FieldView                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Grid-Based Prescription Data Model

```python
@dataclass
class VRSPrescription:
    """Variable rate seeding prescription for a field (grid-based)."""
    
    field_id: str
    field_name: str
    crop: str  # "corn" or "soybean"
    hybrid: str
    
    # Raster data
    productivity_raster: Raster  # 0-1 productivity index
    population_raster: Raster    # seeds/acre per cell
    
    # Grid metadata
    resolution_m: float = 10.0
    crs: str = "EPSG:4326"
    bounds: tuple  # (minx, miny, maxx, maxy)
    
    # Summary stats
    total_acres: float
    total_seeds: int
    avg_population: int
    min_population: int
    max_population: int
    population_std: float
    
    # Metadata
    created_at: datetime
    created_by: str
    notes: str
    
    # Input layers used
    layers_used: list[str]  # e.g., ["nccpi", "awc", "twi", "yield_history"]


def generate_prescription_geotiff(
    prescription: VRSPrescription,
    output_path: str
) -> None:
    """
    Export prescription as GeoTIFF raster.
    
    Native format preserves cell-by-cell values.
    """
    import rasterio
    from rasterio.transform import from_bounds
    
    height, width = prescription.population_raster.shape
    transform = from_bounds(
        *prescription.bounds, width, height
    )
    
    with rasterio.open(
        output_path, 'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=prescription.population_raster.dtype,
        crs=prescription.crs,
        transform=transform,
    ) as dst:
        dst.write(prescription.population_raster, 1)


def generate_prescription_shapefile(
    prescription: VRSPrescription,
    output_path: str,
    simplify_tolerance: float = 5.0,  # meters
) -> None:
    """
    Export prescription as vectorized shapefile for planter import.
    
    Converts raster to polygons, grouping adjacent cells with same population.
    Simplifies geometry for smaller file size.
    """
    import rasterio
    from rasterio.features import shapes
    import geopandas as gpd
    from shapely.geometry import shape
    
    # Vectorize raster
    features = []
    for geom, value in shapes(
        prescription.population_raster, 
        transform=prescription.transform
    ):
        features.append({
            "geometry": shape(geom).simplify(simplify_tolerance),
            "POPULATION": int(value),
        })
    
    gdf = gpd.GeoDataFrame(features, crs=prescription.crs)
    
    # Dissolve adjacent polygons with same population
    gdf = gdf.dissolve(by='POPULATION', as_index=False)
    
    # Add metadata columns
    gdf['HYBRID'] = prescription.hybrid
    gdf['FIELD'] = prescription.field_name
    gdf['ACRES'] = gdf.geometry.area / 4046.86  # sq meters to acres
    
    gdf.to_file(output_path)
```

---

## 4. GEMx Model Integration Summary

The VRS productivity raster leverages all GEMx spatial models:

| GEMx Model | VRS Integration | Spatial Variation |
|------------|-----------------|-------------------|
| **Soil Productivity** | NCCPI as base productivity | Varies by soil map unit |
| **Drought Risk** | AWC + sand% + TWI | Varies by soil + topography |
| **Disease Risk (GLS)** | Penalty in low areas (humidity) | Varies by TWI |
| **Disease Risk (SDS)** | Penalty in poorly drained areas | Varies by drainage + TWI |
| **Disease Risk (Phyto)** | Penalty in wet areas | Varies by drainage + TWI |
| **Ponding Risk** | Penalty in depressions | Varies by TWI + drainage |
| **Erosion Risk** | Penalty on steep slopes | Varies by slope |
| **Yield History** | Direct productivity indicator | Varies by historical performance |

### 4.1 Layer Weights by Data Availability

| Scenario | NCCPI | AWC | TWI | Slope | Yield History | NDVI |
|----------|-------|-----|-----|-------|---------------|------|
| **Minimum (SSURGO + DEM only)** | 0.45 | 0.25 | 0.15 | 0.10 | — | — |
| **With Yield History** | 0.20 | 0.15 | 0.10 | 0.05 | 0.45 | — |
| **With NDVI** | 0.35 | 0.20 | 0.15 | 0.10 | — | 0.20 |
| **Full Data** | 0.15 | 0.10 | 0.08 | 0.05 | 0.40 | 0.12 |

---

## 5. Data Sources

### 5.1 SSURGO Productivity Indices

| Property | Description | Scale |
|----------|-------------|-------|
| `nccpi3corn` | National Commodity Crop Productivity Index - Corn | 0-1 |
| `nccpi3soy` | NCCPI - Soybeans | 0-1 |
| `nccpi3sg` | NCCPI - Small Grains | 0-1 |
| `nccpi3cot` | NCCPI - Cotton | 0-1 |
| `nirrcapcl` | Non-irrigated capability class | 1-8 |
| `aws0100` | Available water storage 0-100cm | cm |

### 4.2 Topographic Derivatives (from DEM)

| Metric | Calculation | Use |
|--------|-------------|-----|
| **Slope** | Gradient of elevation | Erosion risk, equipment access |
| **Aspect** | Direction of slope | Microclimate |
| **TWI** | Topographic Wetness Index | Drainage, ponding |
| **Curvature** | Profile/plan curvature | Water accumulation |
| **Relative Elevation** | Elevation vs field mean | Drainage position |

```python
def calculate_twi(dem: Raster) -> Raster:
    """
    Calculate Topographic Wetness Index.
    
    TWI = ln(a / tan(b))
    where:
    - a = upslope contributing area
    - b = local slope
    
    Higher TWI = wetter, lower landscape position
    """
    slope = calculate_slope(dem)
    flow_acc = calculate_flow_accumulation(dem)
    
    # Avoid division by zero
    slope_rad = np.maximum(np.radians(slope), 0.001)
    
    twi = np.log(flow_acc / np.tan(slope_rad))
    return twi
```

### 4.3 Satellite Imagery

| Source | Resolution | Bands | Use |
|--------|------------|-------|-----|
| **Sentinel-2** | 10m | NDVI, NDRE | Crop vigor |
| **Landsat** | 30m | NDVI | Historical archive |
| **Planet** | 3m | NDVI | High resolution |

```python
def calculate_ndvi(nir: Raster, red: Raster) -> Raster:
    """Calculate Normalized Difference Vegetation Index."""
    return (nir - red) / (nir + red)

def calculate_ndre(nir: Raster, red_edge: Raster) -> Raster:
    """Calculate Normalized Difference Red Edge Index."""
    return (nir - red_edge) / (nir + red_edge)
```

---

## 5. Soybean Population Considerations

### 5.1 Soybean Population Strategy

Soybeans are less responsive to population than corn:

| Factor | Impact on Population |
|--------|---------------------|
| Row spacing | Narrow rows → higher pop |
| Planting date | Late planting → higher pop |
| Yield environment | Less responsive than corn |
| Branching habit | Bushy → lower pop |

### 5.2 Soybean Population Ranges

| Row Spacing | Low Yield | Medium Yield | High Yield |
|-------------|-----------|--------------|------------|
| 30" rows | 100,000 | 120,000 | 130,000 |
| 20" rows | 110,000 | 130,000 | 140,000 |
| 15" rows | 120,000 | 140,000 | 150,000 |
| Drilled (7.5") | 130,000 | 150,000 | 160,000 |

### 5.3 Soybean VRS Approach

```python
def calculate_soybean_population(
    row_spacing: int,  # inches
    yield_environment: str,  # "low", "medium", "high"
    planting_date: str,  # "early", "normal", "late"
    variety_branching: str,  # "bushy", "moderate", "erect"
) -> int:
    """
    Calculate soybean population based on management factors.
    
    Less zone-based variation than corn because:
    1. Soybeans compensate with branching
    2. Population response curve is flatter
    """
    # Base population by row spacing
    base_pop = {
        30: 115000,
        20: 125000,
        15: 135000,
        7.5: 145000,
    }.get(row_spacing, 120000)
    
    # Yield environment adjustment (smaller than corn)
    yield_adj = {
        "low": -10000,
        "medium": 0,
        "high": 10000,
    }.get(yield_environment, 0)
    
    # Late planting adjustment
    date_adj = {
        "early": -5000,
        "normal": 0,
        "late": 10000,
    }.get(planting_date, 0)
    
    # Branching adjustment
    branch_adj = {
        "bushy": -10000,
        "moderate": 0,
        "erect": 5000,
    }.get(variety_branching, 0)
    
    return base_pop + yield_adj + date_adj + branch_adj
```

---

## 6. Integration with GEMx

### 6.1 User Workflow

```
1. SELECT FIELD
   └── Import boundary, CLU lookup, or draw

2. HYBRID PLACEMENT (Level 1)
   └── GEMx recommends top hybrids for field

3. ZONE CREATION (Optional)
   ├── Auto-generate from SSURGO/topo
   ├── Import yield history
   └── Manual zone drawing

4. VRS PRESCRIPTION (Optional)
   ├── Select hybrid(s) for zones
   ├── Review population recommendations
   └── Adjust as needed

5. EXPORT
   ├── PDF report with recommendations
   ├── Shapefile prescription for planter
   └── CSV seed order summary
```

### 6.2 API Endpoints

```python
# Zone creation
POST /api/fields/{field_id}/zones
Body: {
    "method": "ssurgo" | "yield_history" | "composite",
    "num_zones": 3,
    "yield_history_ids": [...]  # Optional
}
Response: {
    "zones": [
        {"zone_id": "...", "name": "High", "acres": 45.2, "geometry": {...}},
        ...
    ]
}

# VRS prescription
POST /api/fields/{field_id}/vrs-prescription
Body: {
    "hybrid": "Pioneer P1185AM",
    "zones": [
        {"zone_id": "...", "population": 34000},
        ...
    ]
}
Response: {
    "prescription_id": "...",
    "total_seeds": 1250000,
    "download_url": "/api/prescriptions/{id}/shapefile"
}
```

---

## 7. Marketing Positioning

From the Seed Channel Management Platform presentation:

### 7.1 Value Propositions

**For Seed Dealers:**
- Maximize Performance with G×E×M Based Recs at the Field-Level
- Save Time with Simplified Information Entry
- Stronger Seed Placement Versus Traditional Approaches
- Control Costs by Expanding the List of Potential Product Choices

**For Seed Companies:**
- Overall Improvement to Sales Efficiency and Effectiveness
- Improved Customer Retention by Placing Multiple Seed Products
- Increased Share of Farm with Easy to Create Full-Farm Seed Plans
- Quickly Transitions Plans to Customer Orders

**For Farmers:**
- Optimized seed choices by field
- Variable rate prescriptions for within-field optimization
- Customizable reports with agronomic detail
- Easy transition from plan to order

### 7.2 Key Differentiators

| Feature | Traditional Approach | GEMx Approach |
|---------|---------------------|---------------|
| Hybrid selection | Plot winners, gut feel | G×E×M systematic matching |
| Population | Flat rate or simple high/low | Hybrid-specific curves by zone |
| Zone creation | Manual or expensive services | Auto-generate from public data |
| Prescription export | Separate tools | Integrated workflow |
| Multi-hybrid | Rarely done | Built-in support |

### 7.3 Platform Objectives (from presentation)

1. **Tailor a platform specifically for seed companies and large dealerships**
2. **Align the entire channel** from seed company to dealer to farmer
3. **Create a simplified, intuitive system** to access and enter key information
4. **Infuse product supply and lifecycle priorities** into conversations naturally
5. **Cover recommendation agronomics** to each farmer's level of interest

---

## 8. Implementation Phases

### Phase 1: Basic VRS
- [ ] Zone creation from SSURGO productivity
- [ ] Default population curves (not hybrid-specific)
- [ ] Shapefile export

### Phase 2: Enhanced VRS
- [ ] Hybrid-specific population curves
- [ ] Multi-year yield history import
- [ ] Composite zone creation (SSURGO + topo)
- [ ] Multiple export formats

### Phase 3: Advanced VRS
- [ ] Multi-hybrid prescriptions
- [ ] Satellite imagery integration
- [ ] Machine learning zone optimization
- [ ] Integration with planter monitors

---

## 9. Data Requirements Summary

### Required Data Layers

| Layer | Source | Resolution | Required? |
|-------|--------|------------|-----------|
| Field boundary | User input | Vector | Yes |
| SSURGO soils | USDA NRCS | ~10-30m | Yes |
| Elevation (DEM) | USGS 3DEP | 10m | Recommended |
| Weather/GDD | PRISM | 4km | Yes (for maturity) |

### Optional Data Layers

| Layer | Source | Resolution | Benefit |
|-------|--------|------------|---------|
| Yield history | User upload | Variable | Best zone accuracy |
| Satellite NDVI | Sentinel-2 | 10m | Vigor mapping |
| EC mapping | User upload | Variable | Texture variability |
| Soil samples | User upload | Point | Actual vs estimated |

### Hybrid Data Requirements

| Data | Source | Required? |
|------|--------|-----------|
| Population curve coefficients | Seed company or derived | Recommended |
| Ear type (flex/fixed) | Seed guide | Recommended |
| Optimal population range | Seed guide | Yes |
