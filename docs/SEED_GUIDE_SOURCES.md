# GEMx Seed Guide Data Sources

## Overview

This document catalogs public and semi-public sources for hybrid/variety trait ratings. Most ratings will need to be manually entered or scraped from seed company guides.

---

## 1. Seed Company Guides (Primary Source)

### Major Corn Seed Brands

| Brand | Guide Access | Rating Format | Notes |
|-------|--------------|---------------|-------|
| **Pioneer** | pioneer.com/seed-guide | 1-9 scale | Comprehensive, PDF + web |
| **DeKalb (Bayer)** | dekalb.com | 1-9 scale | Good disease ratings |
| **Channel** | channel.com | 1-9 scale | Regional focus |
| **Golden Harvest** | goldenharvestseeds.com | 1-9 scale | Syngenta brand |
| **NK (Syngenta)** | nk-us.com | 1-9 scale | |
| **Wyffels** | wyffels.com | 1-9 scale | Independent, Midwest focus |
| **Beck's** | beckshybrids.com | 1-9 scale | Large independent |
| **LG Seeds** | lgseeds.com | 1-9 scale | |
| **Dyna-Gro** | dynagroseed.com | 1-9 scale | |
| **AgriGold** | agrigold.com | 1-9 scale | |
| **Hoegemeyer** | hoegemeyer.com | 1-9 scale | Regional |
| **Latham** | lathamseeds.com | 1-9 scale | Upper Midwest |
| **Hefty Seed** | heftyseed.com | 1-9 scale | |

### Major Soybean Seed Brands

| Brand | Guide Access | Rating Format | Notes |
|-------|--------------|---------------|-------|
| **Pioneer** | pioneer.com | 1-9 scale | Comprehensive |
| **Asgrow (Bayer)** | asgrow.com | 1-9 scale | Market leader |
| **Channel** | channel.com | 1-9 scale | |
| **Golden Harvest** | goldenharvestseeds.com | 1-9 scale | |
| **NK (Syngenta)** | nk-us.com | 1-9 scale | |
| **Beck's** | beckshybrids.com | 1-9 scale | |
| **Stine** | stineseed.com | 1-9 scale | Large soybean focus |
| **Credenz** | credenzsoybeans.com | 1-9 scale | BASF brand |
| **LG Seeds** | lgseeds.com | 1-9 scale | |
| **Dyna-Gro** | dynagroseed.com | 1-9 scale | |

---

## 2. University Variety Trials (Validation Source)

### Corn Hybrid Trials

| State | Institution | URL | Data Available |
|-------|-------------|-----|----------------|
| **Iowa** | Iowa State | crops.extension.iastate.edu | Yield, moisture, lodging |
| **Illinois** | U of I | vt.cropsci.illinois.edu | Yield, moisture, test weight |
| **Indiana** | Purdue | ag.purdue.edu/agry/pcpp | Yield, moisture |
| **Nebraska** | UNL | cropwatch.unl.edu | Yield, moisture, test weight |
| **Minnesota** | UMN | varietytrials.umn.edu | Yield, moisture, lodging |
| **Wisconsin** | UW | coolbean.info | Yield, moisture |
| **Ohio** | OSU | oardc.ohio-state.edu | Yield, moisture |
| **Kansas** | KSU | agronomy.k-state.edu | Yield, dryland vs irrigated |
| **Missouri** | Mizzou | varietytesting.missouri.edu | Yield, moisture |
| **South Dakota** | SDSU | igrow.org | Yield, moisture |
| **North Dakota** | NDSU | ag.ndsu.edu | Yield, moisture |

### Soybean Variety Trials

| State | Institution | URL | Data Available |
|-------|-------------|-----|----------------|
| **Iowa** | Iowa State | crops.extension.iastate.edu | Yield, maturity, lodging |
| **Illinois** | U of I | vt.cropsci.illinois.edu | Yield, maturity, height |
| **Indiana** | Purdue | ag.purdue.edu/agry/pcpp | Yield, maturity |
| **Minnesota** | UMN | varietytrials.umn.edu | Yield, IDC, lodging |
| **Wisconsin** | UW | coolbean.info | Yield, maturity |
| **Nebraska** | UNL | cropwatch.unl.edu | Yield, maturity |
| **Ohio** | OSU | oardc.ohio-state.edu | Yield, maturity |
| **Kansas** | KSU | agronomy.k-state.edu | Yield, maturity |
| **Missouri** | Mizzou | varietytesting.missouri.edu | Yield, maturity |
| **South Dakota** | SDSU | igrow.org | Yield, IDC |
| **North Dakota** | NDSU | ag.ndsu.edu | Yield, IDC |

---

## 3. Independent Testing Organizations

### FIRST (Soybean)
- **URL:** firstsoybean.com
- **Coverage:** Multi-state soybean trials
- **Data:** Yield, maturity, disease notes
- **Access:** Subscription + some public data

### National Corn Growers Association (NCGA)
- **URL:** ncga.com/yield-contest
- **Data:** Winning hybrids by state/category
- **Use:** Identify top performers

### Farmers Business Network (FBN)
- **URL:** fbn.com
- **Data:** Aggregated farmer-reported yields
- **Access:** Subscription required
- **Note:** Large dataset, real-world performance

---

## 4. Trait Rating Definitions

### Standard 1-9 Scale Interpretation

| Rating | Interpretation | Percentile |
|--------|----------------|------------|
| 9 | Excellent | Top 5% |
| 8 | Very Good | Top 15% |
| 7 | Good | Top 30% |
| 6 | Above Average | Top 45% |
| 5 | Average | Middle |
| 4 | Below Average | Bottom 45% |
| 3 | Fair | Bottom 30% |
| 2 | Poor | Bottom 15% |
| 1 | Very Poor | Bottom 5% |

### Corn Trait Definitions

| Trait | Definition | Measurement Method |
|-------|------------|-------------------|
| **Relative Maturity (RM)** | Days to physiological maturity relative to check | GDD accumulation |
| **Yield Potential** | Genetic yield capacity under optimal conditions | Multi-location trials |
| **Test Weight** | Grain density (lb/bu) | Lab measurement |
| **Drydown** | Rate of moisture loss post-maturity | Harvest moisture tracking |
| **Stalk Strength** | Resistance to stalk breakage | Push/pinch tests, lodging % |
| **Root Strength** | Resistance to root lodging | Post-storm assessments |
| **Drought Tolerance** | Yield stability under water stress | Dryland vs irrigated trials |
| **GLS Tolerance** | Resistance to Gray Leaf Spot | Inoculated trials, field ratings |
| **NCLB Tolerance** | Resistance to Northern Corn Leaf Blight | Inoculated trials |
| **Tar Spot Tolerance** | Resistance to Tar Spot | Field ratings in endemic areas |

### Soybean Trait Definitions

| Trait | Definition | Measurement Method |
|-------|------------|-------------------|
| **Maturity Group (MG)** | Relative maturity (0.0 - 5.0+) | Days to maturity |
| **Yield Potential** | Genetic yield capacity | Multi-location trials |
| **Lodging Resistance** | Standability at harvest | Visual ratings |
| **Plant Height** | Mature plant height | Measurement (inches) |
| **SDS Tolerance** | Resistance to Sudden Death Syndrome | Inoculated trials |
| **SCN Resistance** | Resistance to Soybean Cyst Nematode | Gene source + field trials |
| **Phytophthora Tolerance** | Resistance to Phytophthora root rot | Gene + field tolerance |
| **White Mold Tolerance** | Resistance to Sclerotinia | Field ratings |
| **IDC Tolerance** | Resistance to Iron Deficiency Chlorosis | High-pH field trials |
| **Frogeye Tolerance** | Resistance to Frogeye Leaf Spot | Field ratings |

---

## 5. Data Collection Strategy

### Phase 1: Manual Entry (MVP)
1. Select 3-5 major brands per crop
2. Enter 10-20 products per brand
3. Focus on ratings that match our data layers:
   - Maturity
   - Yield potential
   - Drought tolerance
   - Key disease ratings (GLS, NCLB for corn; SDS, SCN, Phyto for soy)
   - Standability

### Phase 2: Structured Scraping
1. Build scrapers for seed guide PDFs
2. Parse tabular data from web guides
3. Normalize across brands

### Phase 3: Crowdsourced/API
1. Allow dealers to enter products
2. Integrate with seed company APIs (if available)
3. Connect to FBN or similar aggregators

---

## 6. Sample Data Entry Template

### Corn Hybrid Entry

```json
{
  "brand": "Pioneer",
  "hybrid_name": "P1185AM",
  "relative_maturity": 111,
  "yield_potential": 8,
  "test_weight": 7,
  "drydown": 7,
  "stalk_strength": 7,
  "root_strength": 8,
  "drought_tolerance": 7,
  "emergence_vigor": 7,
  "gray_leaf_spot": 6,
  "northern_leaf_blight": 7,
  "tar_spot": 5,
  "gosss_wilt": 6,
  "anthracnose_stalk": 7,
  "bt_traits": ["Qrome", "AM"],
  "herbicide_traits": ["RR", "LL"],
  "ear_type": "Semi-flex",
  "data_source": "Pioneer 2024 Seed Guide",
  "year_introduced": 2022
}
```

### Soybean Variety Entry

```json
{
  "brand": "Asgrow",
  "variety_name": "AG27XF2",
  "maturity_group": 2.7,
  "yield_potential": 8,
  "lodging_resistance": 7,
  "plant_height": 6,
  "drought_tolerance": 7,
  "emergence_vigor": 7,
  "idc_tolerance": 5,
  "sds_rating": 7,
  "scn_source": "PI 88788",
  "phytophthora_genes": ["Rps1c"],
  "phytophthora_field": 6,
  "white_mold": 5,
  "brown_stem_rot": 6,
  "frogeye_leaf_spot": 7,
  "herbicide_traits": ["XtendFlex"],
  "growth_habit": "Indeterminate",
  "branching": "Moderate",
  "data_source": "Asgrow 2024 Seed Guide",
  "year_introduced": 2023
}
```

---

## 7. Data Quality Notes

### Cross-Brand Calibration
- Different companies may calibrate 1-9 scales differently
- Use university trial data to validate/calibrate
- Consider relative rankings within brand more reliable than absolute scores

### Missing Data Handling
- Tar Spot ratings: Many older hybrids lack ratings (disease is new)
- Heat tolerance: Rarely published explicitly
- IDC: Only relevant in MN/ND/SD, not always rated elsewhere

### Rating Inflation
- Some brands rate more generously
- Use multi-year trial data to ground-truth
- Weight university trial data higher for validation
