# GEMx — Genetics × Environment × Management Seed Placement Tool

## Overview

GEMx is a seed placement recommendation engine that matches **hybrid/variety genetic traits** to **field environments** and **management practices**. The system scores each product against field-specific conditions to produce ranked recommendations with explanations.

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
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   RECOMMENDATIONS     │
                    │   Top-N with scores   │
                    │   & explanations      │
                    └───────────────────────┘
```

## Target Users

- **Seed Dealers/Agronomists** — Place products on the right fields
- **Growers** — Select hybrids/varieties for their operation
- **Landowners/Purchasers** — Understand field potential

## Supported Crops

- **Corn** — Hybrids with RM, disease ratings, Bt traits
- **Soybeans** — Varieties with MG, SCN resistance, disease ratings
- *(Future: Wheat, other small grains)*

## Key Features

### Field Environment Analysis
- **Soil properties** — Texture, drainage, pH, organic matter (SSURGO)
- **Weather/climate** — GDD, precipitation, heat stress days (PRISM)
- **Disease risk models** — GLS, NCLB, Tar Spot, SDS, SCN, Phytophthora
- **Topography** — Slope, drainage patterns

### Management Practice Capture
- Previous crop / rotation history
- Tillage system
- Planting/harvest timing
- Irrigation status
- Herbicide program (trait requirements)
- Fungicide program

### Genetic Trait Matching
- **Hard constraints** — Maturity range, required traits
- **Soft scoring** — Stress tolerance, disease tolerance, agronomics
- **Weighted by field risk** — Higher disease pressure = higher weight on tolerance

### Recommendation Output
- Top-N ranked products per field
- Composite fit score (0-100)
- Strengths & watch-outs for each product
- Suggested population and placement

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, scoring overview |
| [DATA_LAYERS.md](docs/DATA_LAYERS.md) | Detailed data layer specifications |
| [SCORING_ENGINE.md](docs/SCORING_ENGINE.md) | Scoring algorithm design |
| [SEED_GUIDE_SOURCES.md](docs/SEED_GUIDE_SOURCES.md) | Data sources for hybrid/variety ratings |
| [VARIABLE_RATE_SEEDING.md](docs/VARIABLE_RATE_SEEDING.md) | VRS prescription generation (yield layer + TWI + LRWF) |
| [COMPETITIVE_ANALYSIS.md](docs/COMPETITIVE_ANALYSIS.md) | Review of existing seed placement tools |
| [PREVIOUS_ALGORITHM.md](docs/PREVIOUS_ALGORITHM.md) | Documentation of Mix Matters era algorithm |

## Project Structure

```
GEMX/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md      # System architecture
│   ├── DATA_LAYERS.md       # Data layer specifications
│   ├── SCORING_ENGINE.md    # Scoring algorithm
│   └── SEED_GUIDE_SOURCES.md # Seed data sources
├── backend/                  # FastAPI backend (future)
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   └── requirements.txt
├── frontend/                 # React frontend (future)
├── data/
│   ├── products/            # Hybrid/variety catalogs
│   └── reference/           # Disease risk baselines, etc.
└── notebooks/               # Analysis and prototyping
```

## Implementation Phases

### Phase 1: MVP (Streamlit)
- [ ] Field boundary input (draw, upload, CLU lookup)
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
- [ ] Productivity raster from yield layer + TWI + LRWF
- [ ] Cell-by-cell population prescriptions (10m grid)
- [ ] GeoTIFF and Shapefile export for planters
- [ ] Satellite imagery integration

### Phase 4: Advanced Features
- [ ] Historical performance tracking
- [ ] Brand whitelist/preferences
- [ ] Multi-year weather analysis
- [ ] PDF report generation
- [ ] Integration with seed ordering systems

## Data Sources

### Environmental Data
- **SSURGO/gSSURGO** — Soil properties
- **PRISM** — Weather/climate (user has 2015+ on E: drive)
- **USGS 3DEP** — Elevation/topography

### Genetic Data
- **Seed company guides** — Primary source for trait ratings
- **University variety trials** — Validation data
- **FIRST, FBN** — Independent performance data

## Tech Stack (Planned)

- **Backend:** FastAPI + Python
- **Frontend:** React + TypeScript + TailwindCSS
- **Database:** PostgreSQL + PostGIS
- **Spatial:** GDAL, Rasterio, GeoPandas
- **MVP:** Streamlit for rapid prototyping

## Related Projects

- **Field Summary Report** — Annual field reports with historical data
- **Ag Retail Fertility Tax Credit** — Similar FastAPI + React stack

---

## Getting Started

*Implementation pending. See docs/ for architecture and design.*
