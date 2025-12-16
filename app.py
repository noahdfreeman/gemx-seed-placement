"""
GEMx - Genetics × Environment × Management Seed Placement Tool
Streamlit MVP Prototype
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

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
    
    field_options = {f["name"]: f for f in sample_fields["fields"]}
    selected_field_name = st.sidebar.selectbox(
        "Select Field",
        options=list(field_options.keys())
    )
    selected_field = field_options[selected_field_name]
    
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
    
    # Main content - Field Environment
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🗺️ Field Environment")
        env = selected_field["environment"]
        
        st.markdown(f"""
        **{selected_field['name']}**  
        {selected_field['county']} County, {selected_field['state']} • {selected_field['acres']} acres
        """)
        
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
        
        # Score all products
        results = []
        
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
        
        # Sort by score
        results.sort(key=lambda x: x["result"]["score"], reverse=True)
        
        if not results:
            st.warning("No products match your criteria. Try adjusting herbicide program.")
        else:
            # Display top recommendations
            for i, item in enumerate(results[:5]):
                product = item["product"]
                result = item["result"]
                
                with st.expander(
                    f"**#{i+1} {product['brand']} {product['name']}** — Score: {result['score']}/100",
                    expanded=(i == 0)
                ):
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
                        # Trait ratings
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
                    
                    # Explanations and warnings
                    if result["explanations"]:
                        st.success("✅ " + " • ".join(result["explanations"]))
                    
                    if result["warnings"]:
                        st.warning("⚠️ " + " • ".join(result["warnings"]))
                    
                    st.caption(product.get("notes", ""))
            
            # Show filtered products
            filtered_count = len(products) - len(results)
            if filtered_count > 0:
                st.caption(f"ℹ️ {filtered_count} products filtered out due to maturity or trait requirements")


if __name__ == "__main__":
    main()
