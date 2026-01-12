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

### Local Development

```bash
cd C:\Users\noahd\Projects\04_experiments\GEMX

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

App runs at http://localhost:8501

---

## Field Boundary Mapping (MVP)

The Streamlit MVP supports selecting fields from mock data, uploading field boundaries, or drawing field boundaries directly in the app. Boundaries render on a map (satellite hybrid basemap) on each individual field tab.

### Dependencies

Field boundary mapping relies on:

- `geopandas` + `fiona` (read GeoPackage)
- `folium` + `streamlit-folium` (interactive maps)

Install via:

```bash
pip install -r requirements.txt
```

### Field Sources

In the sidebar under **Field Selection**, choose **Field Source**:

1) **Sample fields**

- Uses `data/reference/sample_fields.json` (no geometry)

2) **Upload GPKG**

- Upload a GeoPackage (`.gpkg`) containing one or more field polygons.
- Select:
  - the **layer**
  - an optional **field name column** (or use the base name)
  - one or more **features** from the file
- Optionally override field names for each selected feature.

3) **Draw on map**

- Draw one or more polygons/rectangles on the map.
- Select one or more drawn shapes to use as fields.
- Optionally override field names.

### Map Basemap (Satellite “Hybrid”)

Maps default to a satellite basemap with labels overlay:

- **Satellite** (Esri imagery)
- **Labels** (roads/place names overlay)
- **Streets** (OpenStreetMap) as an option

Use the map layer control to toggle basemaps/labels.

### Per-field Management Lock

Multi-field workflows can use different management assumptions per field.

On each field tab under **🚜 Management (per-field)**:

- Enable **Use field-specific management**
- Set management values
- Click **Lock for this field** to save the option set per field
- Click **Unlock** to edit again

Scoring and LLM reasons for that field use the saved values when per-field management is enabled.

### Zoom to Field Boundary

On each field tab, click **Zoom to field boundary** to re-fit the map view to the field polygon.

### Notes / Known Limitations

- Uploaded/drawn fields currently use placeholder environment + disease risk values so the scoring UI works. Next step would be wiring soil/weather extraction from the polygon.
- Streamlit map widgets require unique keys per tab; the app sets unique keys so boundaries render correctly across multiple field tabs.

### Troubleshooting

- If **Upload GPKG** shows an error about missing dependencies, re-run:
  ```bash
  pip install -r requirements.txt
  ```
- If map changes don’t appear after edits, hard refresh the page or restart Streamlit.
- If port `8501` is already in use, stop the existing process and re-run `streamlit run app.py`.

### Live Deployment

**URL:** https://gemx-seed-placement.streamlit.app

**GitHub Repo:** https://github.com/noahdfreeman/gemx-seed-placement (public)

**Deployment Platform:** Streamlit Community Cloud

To redeploy after changes:
```bash
git add -A
git commit -m "Your commit message"
git push
```
Streamlit Cloud auto-deploys on push to `main`.

---

## MVP Status (December 2024)

### What's Built

| Component | Status | Notes |
|-----------|--------|-------|
| Streamlit app | ✅ Complete | `app.py` (~400 lines) |
| Corn hybrid catalog | ✅ Mock data | 10 hybrids with trait ratings |
| Soybean variety catalog | ✅ Mock data | 10 varieties with trait ratings |
| Sample fields | ✅ Mock data | 5 fields with soil/climate/disease |
| Scoring engine | ✅ Basic | Maturity filter + weighted trait scoring |
| Recommendations UI | ✅ Complete | Top-5 ranked with explanations |
| Streamlit Cloud deployment | ✅ Live | Auto-deploys on push |

### Data Files

| File | Description |
|------|-------------|
| `data/products/corn_hybrids.json` | 10 mock corn hybrids (DeKalb, Pioneer, Asgrow, NK, LG, Wyffels, Beck's) |
| `data/products/soybean_varieties.json` | 10 mock soybean varieties with SCN source, Phyto genes |
| `data/reference/sample_fields.json` | 5 sample fields (Clinton IL, Vermillion IN, Iroquois IL, Tippecanoe IN, Champaign IL) |

### Scoring Algorithm Summary

**Corn:**
- Hard filter: RM must fit GDD zone
- Hard filter: Herbicide traits must match program
- Soft scoring: Drought (20%), Disease (35%), Standability (25%), Maturity fit (20%)
- Disease weight increases on high-risk fields
- Population adjusted by AWC and drainage

**Soybeans:**
- Hard filter: MG must fit zone
- Hard filter: Herbicide traits (XtendFlex/Enlist E3)
- Soft scoring: Disease (40%), Maturity (20%), Drought (15%), IDC (10%), Standability (15%)
- SCN source (Peking vs PI88788) noted in explanations
- IDC scoring triggered by pH > 7.5

### Next Steps (Phase 2)

- [ ] Replace mock data with real hybrid catalogs
- [ ] Integrate SSURGO for real soil extraction
- [ ] Integrate PRISM for real climate data
- [ ] Add disease risk models
- [ ] Convert to FastAPI + React for production
