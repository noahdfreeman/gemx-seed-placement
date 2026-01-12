"""
GEMx - Genetics × Environment × Management Seed Placement Tool
Streamlit MVP Prototype
"""

import streamlit as st
import json
import os
import tempfile
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

from gemx_llm import (
    LLMConfig,
    generate_farm_summary,
    generate_field_reasons,
    get_llm_provider,
    load_llm_config,
)

PURDUE_CENTER = (40.4237, -86.9212)

# Page config
st.set_page_config(
    page_title="GEMx - Seed Placement Tool",
    page_icon="🌽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data
@st.cache_data
def load_data():
    base_path = Path(__file__).parent / "data"
    
    with open(base_path / "products" / "corn_hybrids.json") as f:
        corn_data = json.load(f)
    
    with open(base_path / "products" / "soybean_varieties.json") as f:
        soy_data = json.load(f)
    
    with open(base_path / "reference" / "sample_fields.json") as f:
        fields_data = json.load(f)
    
    return corn_data, soy_data, fields_data

corn_hybrids, soy_varieties, sample_fields = load_data()


def _safe_import_gis_libs() -> tuple[Any, Any, Any, Any]:
    try:
        import geopandas as gpd  # type: ignore
        import shapely  # type: ignore
        import folium  # type: ignore
        from streamlit_folium import st_folium  # type: ignore

        return gpd, shapely, folium, st_folium
    except Exception:
        return None, None, None, None


def _to_feature_collection(geojson_features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": geojson_features,
    }


def _add_hybrid_basemap(m: Any) -> None:
    _, _, folium, _ = _safe_import_gis_libs()
    if not folium:
        return

    # Satellite imagery (base)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    # Labels overlay (roads/place names)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Labels",
        overlay=True,
        control=True,
        opacity=0.95,
    ).add_to(m)

    # Optional street basemap for comparison
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Streets",
        overlay=False,
        control=True,
    ).add_to(m)


def _keyify(val: Any) -> str:
    s = str(val or "")
    out = []
    for ch in s:
        if ch.isalnum() or ch in {"_", "-"}:
            out.append(ch)
        else:
            out.append("_")
    res = "".join(out).strip("_")
    return res or "key"


def _get_field_key(field: Dict[str, Any]) -> str:
    return _keyify(field.get("id") or field.get("name"))


def _get_management_for_field(field: Dict[str, Any], default_management: Dict[str, Any]) -> Dict[str, Any]:
    fk = _get_field_key(field)
    override = bool(st.session_state.get(f"mgmt_override_{fk}", False))
    saved = st.session_state.get(f"mgmt_saved_{fk}")
    if override and isinstance(saved, dict):
        return saved
    return default_management


def _render_boundary_map(geometry_geojson: dict, *, height: int = 320, key: str | None = None) -> None:
    gpd, _, folium, st_folium = _safe_import_gis_libs()
    if not (folium and st_folium):
        st.caption("Map preview requires geopandas + folium + streamlit-folium.")
        return

    m = folium.Map(location=PURDUE_CENTER, zoom_start=14, tiles=None)
    _add_hybrid_basemap(m)

    try:
        folium.GeoJson(
            geometry_geojson,
            name="Field boundary",
            style_function=lambda _: {
                "color": "#2563eb",
                "weight": 3,
                "fillColor": "#60a5fa",
                "fillOpacity": 0.2,
            },
        ).add_to(m)
    except Exception:
        pass

    try:
        if gpd:
            gdf = gpd.GeoDataFrame.from_features([geometry_geojson], crs="EPSG:4326")
            bounds = gdf.total_bounds  # minx, miny, maxx, maxy
            sw = (bounds[1], bounds[0])
            ne = (bounds[3], bounds[2])
            m.fit_bounds([sw, ne])
    except Exception:
        pass

    try:
        folium.LayerControl(collapsed=True).add_to(m)
    except Exception:
        pass

    st_folium(m, height=height, width="100%", key=key)


def _normalize_drawings_to_features(drawings: list[dict]) -> list[dict]:
    features: list[dict] = []
    for d in drawings or []:
        geom = d.get("geometry")
        if not geom:
            continue
        features.append({
            "type": "Feature",
            "properties": {},
            "geometry": geom,
        })
    return features


def _render_draw_map(*, height: int = 420, key: str | None = None) -> list[dict]:
    gpd, _, folium, st_folium = _safe_import_gis_libs()
    if not (folium and st_folium):
        st.error("Draw tool requires folium + streamlit-folium installed.")
        return []

    from folium.plugins import Draw  # type: ignore

    m = folium.Map(location=PURDUE_CENTER, zoom_start=15, tiles=None)
    _add_hybrid_basemap(m)
    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "circle": False,
            "circlemarker": False,
            "marker": False,
            "polygon": True,
            "rectangle": True,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)

    try:
        folium.LayerControl(collapsed=True).add_to(m)
    except Exception:
        pass

    out = st_folium(m, height=height, width="100%", key=key)
    drawings = out.get("all_drawings") or []

    # Optionally fit to last drawn geometry
    try:
        if drawings and gpd:
            last = drawings[-1]
            geom = last.get("geometry")
            if geom:
                feat = {"type": "Feature", "properties": {}, "geometry": geom}
                gdf = gpd.GeoDataFrame.from_features([feat], crs="EPSG:4326")
                bounds = gdf.total_bounds
                sw = (bounds[1], bounds[0])
                ne = (bounds[3], bounds[2])
                m.fit_bounds([sw, ne])
    except Exception:
        pass

    return drawings


def _fields_from_drawn_features(
    features: list[dict],
    selected_indices: list[int],
    *,
    name_overrides: dict[int, str],
    base_name: str,
) -> list[dict]:
    gpd, _, _, _ = _safe_import_gis_libs()

    gdf_area = None
    if gpd and features:
        try:
            gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
            gdf_area = gdf.to_crs("EPSG:5070")
        except Exception:
            gdf_area = None

    fields: list[dict] = []
    for n, idx in enumerate(selected_indices, start=1):
        if idx < 0 or idx >= len(features):
            continue

        nm = (name_overrides.get(idx) or "").strip()
        if not nm:
            nm = f"{base_name} {n}".strip()

        acres = None
        try:
            if gdf_area is not None:
                area_m2 = float(gdf_area.iloc[idx].geometry.area)
                acres = area_m2 / 4046.8564224
        except Exception:
            acres = None

        geom_feature = {
            "type": "Feature",
            "properties": {"name": nm},
            "geometry": features[idx]["geometry"],
        }

        fields.append({
            "id": f"drawn_{idx}",
            "name": nm,
            "county": "",
            "state": "",
            "acres": round(acres, 1) if acres is not None else None,
            "geometry": geom_feature,
            "environment": {
                "soil_texture": "",
                "drainage_class": "",
                "awc": 0.2,
                "ph": 6.8,
                "organic_matter": 3.5,
                "cec": 18.0,
                "slope": 2.0,
                "gdd_normal": 2850,
                "precip_normal": 38.0,
                "heat_stress_days": 8,
            },
            "disease_risk": {
                "gray_leaf_spot": 5,
                "northern_corn_leaf_blight": 5,
                "tar_spot": 4,
                "goss_wilt": 3,
                "sds": 5,
                "scn": 6,
                "phytophthora": 4,
                "white_mold": 3,
            },
        })

    return fields


def _load_fields_from_gpks_upload(uploaded_file, *, name_column: str | None, base_name: str) -> list[dict]:
    gpd, _, _, _ = _safe_import_gis_libs()
    if not gpd:
        raise RuntimeError("geopandas is required to read .gpkg files")

    gdf = gpd.read_file(uploaded_file)
    if gdf.empty:
        return []

    if gdf.crs is None:
        # Assume WGS84 if missing CRS; common issue in ad-hoc exports
        gdf = gdf.set_crs("EPSG:4326")

    gdf = gdf.to_crs("EPSG:4326")

    fields: list[dict] = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        if name_column and name_column in gdf.columns:
            nm = str(row.get(name_column) or "").strip()
        else:
            nm = ""

        if not nm:
            nm = f"{base_name} {len(fields) + 1}".strip()

        # GeoJSON feature
        geom_geojson = {
            "type": "Feature",
            "properties": {"name": nm},
            "geometry": geom.__geo_interface__,
        }

        # Minimal placeholders for environment/disease until you wire real extraction
        fields.append({
            "id": f"uploaded_{idx}",
            "name": nm,
            "county": "",
            "state": "",
            "acres": None,
            "geometry": geom_geojson,
            "environment": {
                "soil_texture": "",
                "drainage_class": "",
                "awc": 0.2,
                "ph": 6.8,
                "organic_matter": 3.5,
                "cec": 18.0,
                "slope": 2.0,
                "gdd_normal": 2850,
                "precip_normal": 38.0,
                "heat_stress_days": 8,
            },
            "disease_risk": {
                "gray_leaf_spot": 5,
                "northern_corn_leaf_blight": 5,
                "tar_spot": 4,
                "goss_wilt": 3,
                "sds": 5,
                "scn": 6,
                "phytophthora": 4,
                "white_mold": 3,
            },
        })

    return fields


def _fields_from_gdf_selection(
    gdf: Any,
    selected_indices: list[int],
    *,
    name_column: str | None,
    name_overrides: dict[int, str],
    base_name: str,
) -> list[dict]:
    fields: list[dict] = []
    if not selected_indices:
        return fields

    # Area calc in a projected CRS (CONUS Albers)
    try:
        gdf_area = gdf.to_crs("EPSG:5070")
    except Exception:
        gdf_area = None

    for n, idx in enumerate(selected_indices, start=1):
        row = gdf.iloc[idx]
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        nm = (name_overrides.get(idx) or "").strip()
        if not nm and name_column and name_column in gdf.columns:
            nm = str(row.get(name_column) or "").strip()
        if not nm:
            nm = f"{base_name} {n}".strip()

        acres = None
        try:
            if gdf_area is not None:
                area_m2 = float(gdf_area.iloc[idx].geometry.area)
                acres = area_m2 / 4046.8564224
        except Exception:
            acres = None

        geom_geojson = {
            "type": "Feature",
            "properties": {"name": nm},
            "geometry": geom.__geo_interface__,
        }

        fields.append({
            "id": f"uploaded_{idx}",
            "name": nm,
            "county": "",
            "state": "",
            "acres": round(acres, 1) if acres is not None else None,
            "geometry": geom_geojson,
            "environment": {
                "soil_texture": "",
                "drainage_class": "",
                "awc": 0.2,
                "ph": 6.8,
                "organic_matter": 3.5,
                "cec": 18.0,
                "slope": 2.0,
                "gdd_normal": 2850,
                "precip_normal": 38.0,
                "heat_stress_days": 8,
            },
            "disease_risk": {
                "gray_leaf_spot": 5,
                "northern_corn_leaf_blight": 5,
                "tar_spot": 4,
                "goss_wilt": 3,
                "sds": 5,
                "scn": 6,
                "phytophthora": 4,
                "white_mold": 3,
            },
        })

    return fields


def score_products_for_field(crop: str, selected_field: Dict, management: Dict) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    if crop == "Corn":
        products = corn_hybrids["hybrids"]
        score_func = calculate_corn_score
    else:
        products = soy_varieties["varieties"]
        score_func = calculate_soy_score

    for product in products:
        result = score_func(product, selected_field, management)
        if not result.get("filtered"):
            results.append({
                "product": product,
                "result": result
            })

    results.sort(key=lambda x: x["result"]["score"], reverse=True)
    return results


def calculate_corn_score(hybrid: Dict, field: Dict, management: Dict) -> Dict:
    """Calculate fit score for a corn hybrid on a given field."""
    env = field["environment"]
    disease = field["disease_risk"]
    
    scores = {}
    explanations = []
    warnings = []
    
    # Maturity check (hard filter)
    rm = hybrid["relative_maturity"]
    gdd = env["gdd_normal"]
    
    # Rough GDD requirement: RM * 25 + 100
    gdd_required = rm * 25 + 100
    gdd_margin = gdd - gdd_required
    
    if gdd_margin < -100:
        return {"score": 0, "filtered": True, "reason": f"RM {rm} too long for {gdd} GDD zone"}
    elif gdd_margin < 0:
        scores["maturity"] = 60
        warnings.append(f"RM {rm} is borderline for this zone")
    elif gdd_margin < 100:
        scores["maturity"] = 85
        explanations.append(f"RM {rm} fits well")
    else:
        scores["maturity"] = 100
        explanations.append(f"RM {rm} has good safety margin")
    
    # Drought tolerance vs AWC
    awc = env["awc"]
    drought_trait = hybrid["traits"]["drought_tolerance"]
    
    if awc < 0.15:  # Low water holding
        drought_weight = 2.0
        if drought_trait >= 7:
            explanations.append("Strong drought tolerance for sandy soil")
        elif drought_trait <= 4:
            warnings.append("Low drought tolerance on droughty soil")
    else:
        drought_weight = 1.0
    
    scores["drought"] = drought_trait * 10 * drought_weight
    
    # Disease scoring
    disease_scores = []
    
    # Gray Leaf Spot
    gls_risk = disease["gray_leaf_spot"]
    gls_trait = hybrid["traits"]["gray_leaf_spot"]
    gls_score = min(100, (gls_trait / max(gls_risk, 1)) * 50 + 30)
    disease_scores.append(gls_score)
    if gls_risk >= 7 and gls_trait >= 7:
        explanations.append("Good GLS tolerance for high-risk field")
    elif gls_risk >= 7 and gls_trait <= 5:
        warnings.append("GLS risk - consider fungicide")
    
    # NCLB
    nclb_risk = disease["northern_corn_leaf_blight"]
    nclb_trait = hybrid["traits"]["northern_corn_leaf_blight"]
    nclb_score = min(100, (nclb_trait / max(nclb_risk, 1)) * 50 + 30)
    disease_scores.append(nclb_score)
    
    # Tar Spot
    tar_risk = disease["tar_spot"]
    tar_trait = hybrid["traits"]["tar_spot"]
    tar_score = min(100, (tar_trait / max(tar_risk, 1)) * 50 + 30)
    disease_scores.append(tar_score)
    if tar_risk >= 6 and tar_trait <= 4:
        warnings.append("Tar spot risk - scout closely")
    
    scores["disease"] = sum(disease_scores) / len(disease_scores)
    
    # Stalk/root strength
    stalk = hybrid["traits"]["stalk_strength"]
    root = hybrid["traits"]["root_strength"]
    scores["standability"] = (stalk + root) * 5
    
    if stalk >= 8 and root >= 8:
        explanations.append("Excellent standability")
    
    # Management fit
    if management.get("previous_crop") == "Corn":
        # Corn-on-corn: disease pressure higher
        scores["disease"] *= 0.9
        if hybrid["traits"]["gray_leaf_spot"] >= 7:
            explanations.append("Good for corn-on-corn (GLS tolerant)")
    
    if management.get("tillage") == "No-Till":
        # More residue = more disease pressure
        scores["disease"] *= 0.95
    
    # Herbicide trait check
    if management.get("herbicide_program"):
        required_traits = []
        if "Roundup" in management["herbicide_program"]:
            required_traits.append("RR2")
        if "Liberty" in management["herbicide_program"]:
            required_traits.append("LL")
        
        for trait in required_traits:
            if trait not in hybrid.get("herbicide_traits", []):
                return {"score": 0, "filtered": True, "reason": f"Missing {trait} trait for herbicide program"}
    
    # Calculate composite score
    weights = {
        "maturity": 0.20,
        "drought": 0.20,
        "disease": 0.35,
        "standability": 0.25
    }
    
    composite = sum(scores.get(k, 70) * w for k, w in weights.items())
    composite = min(100, max(0, composite))
    
    # Population recommendation
    pop_range = hybrid["population_range"]
    if awc < 0.15:
        pop = pop_range[0]  # Lower pop on droughty
    elif env["drainage_class"] in ["Poorly Drained", "Somewhat Poorly Drained"]:
        pop = int((pop_range[0] + pop_range[1]) / 2)  # Medium
    else:
        pop = pop_range[1]  # Higher pop on good ground
    
    return {
        "score": round(composite, 1),
        "filtered": False,
        "scores": scores,
        "explanations": explanations,
        "warnings": warnings,
        "population": pop
    }


def calculate_soy_score(variety: Dict, field: Dict, management: Dict) -> Dict:
    """Calculate fit score for a soybean variety on a given field."""
    env = field["environment"]
    disease = field["disease_risk"]
    
    scores = {}
    explanations = []
    warnings = []
    
    # Maturity check
    mg = variety["maturity_group"]
    gdd = env["gdd_normal"]
    
    # Rough MG fit: 2800 GDD = MG 3.0, +100 GDD per 0.3 MG
    ideal_mg = 3.0 + (gdd - 2800) / 333
    mg_diff = abs(mg - ideal_mg)
    
    if mg_diff > 0.8:
        return {"score": 0, "filtered": True, "reason": f"MG {mg} too {'long' if mg > ideal_mg else 'short'} for this zone"}
    elif mg_diff > 0.5:
        scores["maturity"] = 65
        warnings.append(f"MG {mg} is borderline")
    elif mg_diff > 0.3:
        scores["maturity"] = 80
    else:
        scores["maturity"] = 95
        explanations.append(f"MG {mg} fits zone well")
    
    # Drought tolerance
    awc = env["awc"]
    drought_trait = variety["traits"]["drought_tolerance"]
    
    if awc < 0.15:
        drought_weight = 2.0
        if drought_trait >= 7:
            explanations.append("Good drought tolerance for light soil")
        elif drought_trait <= 4:
            warnings.append("Low drought tolerance risk")
    else:
        drought_weight = 1.0
    
    scores["drought"] = drought_trait * 10 * drought_weight
    
    # Disease scoring
    disease_scores = []
    
    # SDS
    sds_risk = disease["sds"]
    sds_trait = variety["traits"]["sds"]
    sds_score = min(100, (sds_trait / max(sds_risk, 1)) * 50 + 30)
    disease_scores.append(sds_score)
    if sds_risk >= 7 and sds_trait >= 7:
        explanations.append("Strong SDS tolerance")
    elif sds_risk >= 7 and sds_trait <= 5:
        warnings.append("SDS risk - avoid early planting")
    
    # SCN
    scn_risk = disease["scn"]
    scn_trait = variety["traits"]["scn"]
    scn_score = min(100, (scn_trait / max(scn_risk, 1)) * 50 + 30)
    disease_scores.append(scn_score)
    if scn_risk >= 7:
        if variety.get("scn_source") == "Peking":
            explanations.append("Peking SCN source - good for resistant populations")
            scn_score += 10
        elif scn_trait >= 8:
            explanations.append("Strong SCN package")
    
    # Phytophthora
    phyto_risk = disease["phytophthora"]
    phyto_trait = variety["traits"]["phytophthora"]
    phyto_score = min(100, (phyto_trait / max(phyto_risk, 1)) * 50 + 30)
    disease_scores.append(phyto_score)
    if phyto_risk >= 7:
        genes = variety.get("phytophthora_genes", [])
        if len(genes) >= 3:
            explanations.append(f"Strong Phyto package: {', '.join(genes)}")
        elif phyto_trait <= 5:
            warnings.append("Phytophthora risk on poorly drained soil")
    
    # White Mold
    wm_risk = disease["white_mold"]
    wm_trait = variety["traits"]["white_mold"]
    wm_score = min(100, (wm_trait / max(wm_risk, 1)) * 50 + 30)
    disease_scores.append(wm_score)
    
    scores["disease"] = sum(disease_scores) / len(disease_scores)
    
    # IDC (Iron Deficiency Chlorosis) - pH related
    ph = env["ph"]
    idc_trait = variety["traits"]["idc"]
    if ph >= 7.5:
        if idc_trait >= 7:
            scores["idc"] = 90
            explanations.append("Good IDC tolerance for high pH")
        else:
            scores["idc"] = 50
            warnings.append("IDC risk on high pH soil")
    else:
        scores["idc"] = 80
    
    # Standability
    scores["standability"] = variety["traits"]["standability"] * 10
    
    # Management fit
    if management.get("previous_crop") == "Soybeans":
        scores["disease"] *= 0.85
        warnings.append("Soy-on-soy increases disease pressure")
    
    # Herbicide trait check
    if management.get("herbicide_program"):
        herb_prog = management["herbicide_program"]
        variety_traits = variety.get("herbicide_traits", [])
        
        if "Dicamba" in herb_prog and "XtendFlex" not in variety_traits:
            return {"score": 0, "filtered": True, "reason": "Missing XtendFlex for dicamba program"}
        if "Enlist" in herb_prog and "Enlist E3" not in variety_traits:
            return {"score": 0, "filtered": True, "reason": "Missing Enlist E3 for 2,4-D program"}
    
    # Calculate composite score
    weights = {
        "maturity": 0.20,
        "drought": 0.15,
        "disease": 0.40,
        "idc": 0.10,
        "standability": 0.15
    }
    
    composite = sum(scores.get(k, 70) * w for k, w in weights.items())
    composite = min(100, max(0, composite))
    
    # Population recommendation
    pop_range = variety["population_range"]
    if awc < 0.15:
        pop = pop_range[0]
    elif env["drainage_class"] in ["Poorly Drained", "Somewhat Poorly Drained"]:
        pop = pop_range[1]  # Higher pop on heavy ground
    else:
        pop = int((pop_range[0] + pop_range[1]) / 2)
    
    return {
        "score": round(composite, 1),
        "filtered": False,
        "scores": scores,
        "explanations": explanations,
        "warnings": warnings,
        "population": pop
    }


def main():
    st.title("🌽 GEMx - Seed Placement Tool")
    st.markdown("**Genetics × Environment × Management**")
    
    # Sidebar - Field Selection
    st.sidebar.header("📍 Field Selection")

    field_source = st.sidebar.radio(
        "Field Source",
        ["Sample fields", "Upload GPKG", "Draw on map"],
        horizontal=False,
    )

    selected_fields: List[Dict[str, Any]] = []

    if field_source == "Sample fields":
        field_options = {f["name"]: f for f in sample_fields["fields"]}
        selected_field_names = st.sidebar.multiselect(
            "Select Field(s)",
            options=list(field_options.keys()),
            default=[list(field_options.keys())[0]] if field_options else [],
        )
        selected_fields = [field_options[n] for n in selected_field_names if n in field_options]
    elif field_source == "Upload GPKG":
        gpd, _, _, _ = _safe_import_gis_libs()
        if not gpd:
            st.sidebar.error("GPKG upload requires geopandas + fiona installed.")
        else:
            uploaded = st.sidebar.file_uploader("Upload field boundaries (.gpkg)", type=["gpkg"])
            if uploaded is not None:
                try:
                    import fiona  # type: ignore

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".gpkg") as tmp:
                        tmp.write(uploaded.getbuffer())
                        gpkg_path = tmp.name

                    layers = list(fiona.listlayers(gpkg_path))
                    if not layers:
                        st.sidebar.error("No layers found in the uploaded GeoPackage.")
                    else:
                        selected_layer = st.sidebar.selectbox("Layer", options=layers)
                        gdf = gpd.read_file(gpkg_path, layer=selected_layer)
                        if gdf.crs is None:
                            gdf = gdf.set_crs("EPSG:4326")
                        gdf = gdf.to_crs("EPSG:4326")

                        non_geom_cols = [c for c in gdf.columns if c != "geometry"]
                        name_column = st.sidebar.selectbox(
                            "Field name column (optional)",
                            options=["(none)"] + non_geom_cols,
                        )
                        chosen_name_col = None if name_column == "(none)" else name_column
                        base_name = st.sidebar.text_input("Base name (if no column)", value="Uploaded Field")

                        total_features = len(gdf)
                        st.sidebar.caption(f"{total_features} feature(s) found")

                        def _format_feature(i: int) -> str:
                            try:
                                if chosen_name_col and chosen_name_col in gdf.columns:
                                    val = str(gdf.iloc[i].get(chosen_name_col) or "").strip()
                                    if val:
                                        return val
                            except Exception:
                                pass
                            return f"Feature {i}"

                        selected_indices = st.sidebar.multiselect(
                            "Select field(s) from file",
                            options=list(range(total_features)),
                            format_func=_format_feature,
                        )

                        name_overrides: dict[int, str] = {}
                        if selected_indices:
                            with st.sidebar.expander("Optional: override names", expanded=False):
                                for idx in selected_indices:
                                    default_nm = _format_feature(idx)
                                    name_overrides[idx] = st.text_input(
                                        f"Name for {default_nm}",
                                        value=default_nm,
                                        key=f"field_name_override_{idx}",
                                    )

                        selected_fields = _fields_from_gdf_selection(
                            gdf,
                            selected_indices,
                            name_column=chosen_name_col,
                            name_overrides=name_overrides,
                            base_name=base_name,
                        )
                except Exception as e:
                    st.sidebar.error(f"Failed to load GPKG: {e}")
                finally:
                    try:
                        if "gpkg_path" in locals() and gpkg_path and os.path.exists(gpkg_path):
                            os.unlink(gpkg_path)
                    except Exception:
                        pass

    elif field_source == "Draw on map":
        st.subheader("✏️ Draw Field Boundaries")
        drawings = _render_draw_map(height=520, key="draw_map")
        features = _normalize_drawings_to_features(drawings)
        total_drawings = len(features)

        st.sidebar.caption(f"{total_drawings} drawing(s) on map")
        base_name = st.sidebar.text_input("Base name", value="Drawn Field")

        def _fmt_drawing(i: int) -> str:
            return f"Drawing {i + 1}"

        selected_indices = st.sidebar.multiselect(
            "Select drawn field(s)",
            options=list(range(total_drawings)),
            format_func=_fmt_drawing,
        )

        name_overrides: dict[int, str] = {}
        if selected_indices:
            with st.sidebar.expander("Optional: override names", expanded=False):
                for idx in selected_indices:
                    default_nm = f"{base_name} {idx + 1}".strip()
                    name_overrides[idx] = st.text_input(
                        f"Name for Drawing {idx + 1}",
                        value=default_nm,
                        key=f"drawn_name_override_{idx}",
                    )

        selected_fields = _fields_from_drawn_features(
            features,
            selected_indices,
            name_overrides=name_overrides,
            base_name=base_name,
        )
    
    # Sidebar - Crop Selection
    st.sidebar.header("🌱 Crop")
    crop = st.sidebar.radio("Select Crop", ["Corn", "Soybeans"])
    
    # Sidebar - Management Inputs
    st.sidebar.header("🚜 Management")
    
    previous_crop = st.sidebar.selectbox(
        "Previous Crop",
        ["Soybeans", "Corn", "Wheat", "Other"]
    )
    
    tillage = st.sidebar.selectbox(
        "Tillage System",
        ["Conventional", "Reduced", "Strip-Till", "No-Till"]
    )
    
    if crop == "Corn":
        herbicide = st.sidebar.multiselect(
            "Herbicide Program",
            ["Roundup", "Liberty", "Atrazine", "Other"],
            default=["Roundup", "Liberty"]
        )
    else:
        herbicide = st.sidebar.multiselect(
            "Herbicide Program",
            ["Dicamba", "Enlist", "Roundup", "Other"],
            default=["Dicamba", "Roundup"]
        )
    
    fungicide = st.sidebar.checkbox("Planned Fungicide Application", value=False)
    
    management = {
        "previous_crop": previous_crop,
        "tillage": tillage,
        "herbicide_program": herbicide,
        "fungicide": fungicide
    }

    # Sidebar - LLM Explanations
    st.sidebar.header("🧠 LLM Explanations")
    llm_cfg = load_llm_config()
    llm_toggle = st.sidebar.checkbox(
        "Enable LLM-generated reasons",
        value=llm_cfg.enabled,
        help="If disabled or no provider/API key is configured, GEMx will use deterministic template reasons.",
    )
    provider = get_llm_provider(
        LLMConfig(
            provider=llm_cfg.provider,
            model=llm_cfg.model,
            openai_api_key=llm_cfg.openai_api_key,
            openai_base_url=llm_cfg.openai_base_url,
            ollama_base_url=llm_cfg.ollama_base_url,
            enabled=llm_toggle,
        )
    )

    if llm_toggle and provider is None:
        st.sidebar.warning(
            "LLM is enabled, but no provider is available. If using OpenAI, set OPENAI_API_KEY."
        )
    elif provider is None:
        st.sidebar.caption("LLM disabled (using deterministic fallback reasons).")
    else:
        st.sidebar.success(f"LLM active: {llm_cfg.provider} / {llm_cfg.model}")

    if not selected_fields:
        st.warning("Select at least one field to view recommendations.")
        return

    if len(selected_fields) > 1:
        field_summaries_for_llm: List[Dict[str, Any]] = []
        for f in selected_fields:
            mgmt_for_f = _get_management_for_field(f, management)
            results_for_field = score_products_for_field(crop, f, mgmt_for_f)
            top = results_for_field[0]["product"] if results_for_field else None
            field_summaries_for_llm.append({
                "field_name": f.get("name"),
                "county": f.get("county"),
                "state": f.get("state"),
                "top_product": (f"{top.get('brand', '')} {top.get('name', '')}".strip() if top else None),
            })

        farm_summary = generate_farm_summary(
            crop=crop,
            field_recommendations=field_summaries_for_llm,
            provider=provider,
        )
        if farm_summary:
            st.subheader("🏠 Farm Summary")
            st.write(farm_summary)
            st.markdown("---")

    tabs = st.tabs([f["name"] for f in selected_fields])
    for tab, selected_field in zip(tabs, selected_fields):
        with tab:
            fk = _get_field_key(selected_field)
            locked_key = f"mgmt_locked_{fk}"
            if locked_key not in st.session_state:
                st.session_state[locked_key] = False

            override_key = f"mgmt_override_{fk}"
            if override_key not in st.session_state:
                st.session_state[override_key] = False

            saved_key = f"mgmt_saved_{fk}"
            locked = bool(st.session_state.get(locked_key, False))
            saved = st.session_state.get(saved_key)
            base_mgmt = saved if isinstance(saved, dict) else management

            col1, col2 = st.columns([1, 2])

            with col1:
                st.subheader("🗺️ Field Environment")
                env = selected_field["environment"]

                st.markdown(f"""
                **{selected_field['name']}**  
                {selected_field['county']} County, {selected_field['state']} • {selected_field['acres']} acres
                """)

                if selected_field.get("geometry"):
                    nonce_key = f"zoom_nonce_{fk}"
                    if nonce_key not in st.session_state:
                        st.session_state[nonce_key] = 0
                    if st.button("Zoom to field boundary", key=f"zoom_btn_{fk}"):
                        st.session_state[nonce_key] = int(st.session_state[nonce_key]) + 1
                    map_key = f"boundary_{fk}_{st.session_state[nonce_key]}"
                    _render_boundary_map(selected_field["geometry"], height=320, key=map_key)

                with st.expander("🚜 Management (per-field)", expanded=False):
                    use_override = st.checkbox(
                        "Use field-specific management",
                        key=override_key,
                        disabled=locked,
                    )

                    if f"mgmt_prev_crop_{fk}" not in st.session_state:
                        st.session_state[f"mgmt_prev_crop_{fk}"] = base_mgmt.get("previous_crop", "Soybeans")
                    if f"mgmt_tillage_{fk}" not in st.session_state:
                        st.session_state[f"mgmt_tillage_{fk}"] = base_mgmt.get("tillage", "Conventional")
                    if f"mgmt_fungicide_{fk}" not in st.session_state:
                        st.session_state[f"mgmt_fungicide_{fk}"] = bool(base_mgmt.get("fungicide", False))
                    if f"mgmt_herbicide_{fk}" not in st.session_state:
                        st.session_state[f"mgmt_herbicide_{fk}"] = list(base_mgmt.get("herbicide_program", []))

                    prev_crop_f = st.selectbox(
                        "Previous Crop",
                        ["Soybeans", "Corn", "Wheat", "Other"],
                        key=f"mgmt_prev_crop_{fk}",
                        disabled=locked,
                    )
                    tillage_f = st.selectbox(
                        "Tillage System",
                        ["Conventional", "Reduced", "Strip-Till", "No-Till"],
                        key=f"mgmt_tillage_{fk}",
                        disabled=locked,
                    )

                    if crop == "Corn":
                        herb_options = ["Roundup", "Liberty", "Atrazine", "Other"]
                    else:
                        herb_options = ["Dicamba", "Enlist", "Roundup", "Other"]

                    herb_f = st.multiselect(
                        "Herbicide Program",
                        options=herb_options,
                        key=f"mgmt_herbicide_{fk}",
                        disabled=locked,
                    )
                    fungicide_f = st.checkbox(
                        "Planned Fungicide Application",
                        key=f"mgmt_fungicide_{fk}",
                        disabled=locked,
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Lock for this field", key=f"lock_btn_{fk}", disabled=locked):
                            st.session_state[saved_key] = {
                                "previous_crop": prev_crop_f,
                                "tillage": tillage_f,
                                "herbicide_program": list(herb_f),
                                "fungicide": bool(fungicide_f),
                            }
                            st.session_state[override_key] = True
                            st.session_state[locked_key] = True
                    with c2:
                        if st.button("Unlock", key=f"unlock_btn_{fk}", disabled=not locked):
                            st.session_state[locked_key] = False

                st.markdown("---")
                st.markdown("**Soil Properties**")

                env_df = pd.DataFrame({
                    "Property": ["Texture", "Drainage", "AWC", "pH", "OM%", "CEC", "Slope"],
                    "Value": [
                        env["soil_texture"],
                        env["drainage_class"],
                        f"{env['awc']:.2f} in/in",
                        f"{env['ph']:.1f}",
                        f"{env['organic_matter']:.1f}%",
                        f"{env['cec']:.1f}",
                        f"{env['slope']:.1f}%"
                    ]
                })
                st.dataframe(env_df, hide_index=True, use_container_width=True)

                st.markdown("**Climate**")
                climate_df = pd.DataFrame({
                    "Property": ["GDD (Normal)", "Precip (Normal)", "Heat Stress Days"],
                    "Value": [
                        f"{env['gdd_normal']}",
                        f"{env['precip_normal']:.1f}\"",
                        f"{env['heat_stress_days']}"
                    ]
                })
                st.dataframe(climate_df, hide_index=True, use_container_width=True)

                st.markdown("**Disease Risk (1-9)**")
                disease = selected_field["disease_risk"]

                if crop == "Corn":
                    disease_items = [
                        ("Gray Leaf Spot", disease["gray_leaf_spot"]),
                        ("NCLB", disease["northern_corn_leaf_blight"]),
                        ("Tar Spot", disease["tar_spot"]),
                        ("Goss's Wilt", disease["goss_wilt"])
                    ]
                else:
                    disease_items = [
                        ("SDS", disease["sds"]),
                        ("SCN", disease["scn"]),
                        ("Phytophthora", disease["phytophthora"]),
                        ("White Mold", disease["white_mold"])
                    ]

                for name, risk in disease_items:
                    color = "🟢" if risk <= 3 else "🟡" if risk <= 6 else "🔴"
                    st.markdown(f"{color} **{name}**: {risk}")

            with col2:
                st.subheader(f"🏆 Top {crop} Recommendations")

                management_for_field = _get_management_for_field(selected_field, management)
                results = score_products_for_field(crop, selected_field, management_for_field)
                llm_reasons = generate_field_reasons(
                    field=selected_field,
                    crop=crop,
                    management=management_for_field,
                    ranked_results=results[:5],
                    provider=provider,
                )

                if not results:
                    st.warning("No products match your criteria. Try adjusting herbicide program.")
                    continue

                for i, item in enumerate(results[:5]):
                    product = item["product"]
                    result = item["result"]
                    rec_id = f"{product.get('brand', '')} {product.get('name', '')}".strip()

                    with st.expander(
                        f"**#{i+1} {product['brand']} {product['name']}** — Score: {result['score']}/100",
                        expanded=(i == 0)
                    ):
                        reason = llm_reasons.get(rec_id, "")
                        if reason:
                            st.info(reason)

                        col_a, col_b = st.columns(2)

                        with col_a:
                            if crop == "Corn":
                                st.markdown(f"**RM:** {product['relative_maturity']}")
                            else:
                                st.markdown(f"**MG:** {product['maturity_group']}")

                            st.markdown(f"**Technology:** {', '.join(product.get('technology', []))}")
                            st.markdown(f"**Herbicide Traits:** {', '.join(product.get('herbicide_traits', []))}")
                            st.markdown(f"**Recommended Population:** {result['population']:,}/acre")

                        with col_b:
                            st.markdown("**Key Traits (1-9):**")
                            traits = product["traits"]
                            if crop == "Corn":
                                trait_display = ["drought_tolerance", "gray_leaf_spot", "stalk_strength", "drydown"]
                            else:
                                trait_display = ["drought_tolerance", "sds", "scn", "phytophthora"]

                            for trait in trait_display:
                                val = traits.get(trait, 5)
                                label = trait.replace("_", " ").title()
                                bar = "█" * val + "░" * (9 - val)
                                st.markdown(f"`{bar}` {label}: {val}")

                        if result["explanations"]:
                            st.success("✅ " + " • ".join(result["explanations"]))

                        if result["warnings"]:
                            st.warning("⚠️ " + " • ".join(result["warnings"]))

                        st.caption(product.get("notes", ""))

                filtered_count = (
                    (len(corn_hybrids["hybrids"]) if crop == "Corn" else len(soy_varieties["varieties"]))
                    - len(results)
                )
                if filtered_count > 0:
                    st.caption(f"ℹ️ {filtered_count} products filtered out due to maturity or trait requirements")


if __name__ == "__main__":
    main()
