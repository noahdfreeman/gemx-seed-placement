"""
Feature extraction from environmental data sources.
"""
from typing import Optional
import json
from pathlib import Path
from ..models.fields import SoilFeatures, WeatherFeatures, FieldFeatures, FieldRequirements
from ..models.management import ManagementInputs


class FeatureExtractor:
    """Extract and derive field features from data sources."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent.parent.parent / "data"
        self._load_reference_data()
    
    def _load_reference_data(self):
        """Load reference data files."""
        ref_dir = self.data_dir / "reference"
        
        try:
            with open(ref_dir / "disease_risk_baselines.json") as f:
                self.disease_baselines = json.load(f)
        except FileNotFoundError:
            self.disease_baselines = {}
        
        try:
            with open(ref_dir / "management_modifiers.json") as f:
                self.management_modifiers = json.load(f)
        except FileNotFoundError:
            self.management_modifiers = {}
        
        try:
            with open(ref_dir / "gdd_rm_conversion.json") as f:
                self.gdd_conversion = json.load(f)
        except FileNotFoundError:
            self.gdd_conversion = {}
    
    def extract_soil_features(self, boundary_geojson: dict) -> SoilFeatures:
        """
        Extract soil features from SSURGO for a field boundary.
        
        TODO: Implement actual SSURGO extraction using geopandas/postgis
        """
        # Placeholder - would query SSURGO data
        return SoilFeatures(
            texture_class="Silt loam",
            sand_pct=20.0,
            silt_pct=55.0,
            clay_pct=25.0,
            om_pct=3.5,
            ph=6.8,
            cec=18.0,
            drainage_class="Moderately well drained",
            hydro_group="B",
            aws_0_100=20.0,
            slope_pct=2.0,
        )
    
    def extract_weather_features(self, centroid: tuple[float, float], 
                                  state: str) -> WeatherFeatures:
        """
        Extract weather features from PRISM for a field centroid.
        
        TODO: Implement actual PRISM extraction using rasterio
        """
        # Placeholder - would query PRISM data
        return WeatherFeatures(
            gdd_mean=2800.0,
            gdd_std=150.0,
            growing_season_precip_mm=550.0,
            precip_cv=0.25,
            heat_stress_days=5.0,
            frost_free_days=165,
        )
    
    def derive_drought_risk(self, soil: SoilFeatures, weather: WeatherFeatures,
                            irrigation: str) -> float:
        """Derive drought risk from soil and weather."""
        base_risk = 0.3
        
        # Soil factors
        if soil.aws_0_100 and soil.aws_0_100 < 15:
            base_risk += 0.2
        elif soil.aws_0_100 and soil.aws_0_100 > 25:
            base_risk -= 0.1
        
        if soil.sand_pct and soil.sand_pct > 50:
            base_risk += 0.15
        
        # Weather factors
        if weather.growing_season_precip_mm and weather.growing_season_precip_mm < 450:
            base_risk += 0.2
        
        if weather.precip_cv and weather.precip_cv > 0.3:
            base_risk += 0.1
        
        # Irrigation modifier
        if irrigation == "pivot":
            base_risk *= 0.3
        elif irrigation == "drip":
            base_risk *= 0.4
        
        return min(1.0, max(0.0, base_risk))
    
    def derive_disease_risks(self, soil: SoilFeatures, weather: WeatherFeatures,
                             management: ManagementInputs, state: str,
                             crop: str) -> dict[str, float]:
        """Derive disease risks from field conditions and management."""
        risks = {}
        
        if crop == "corn":
            # Gray Leaf Spot
            base_gls = self.disease_baselines.get("corn", {}).get(
                "gray_leaf_spot", {}).get("by_state", {}).get(state, 0.3)
            
            if management.previous_crop == "corn":
                base_gls *= 1.5
            if management.tillage.value == "no-till":
                base_gls *= 1.3
            elif management.tillage.value == "conventional":
                base_gls *= 0.7
            
            risks["gls"] = min(1.0, base_gls)
            
            # Northern Leaf Blight
            base_nclb = self.disease_baselines.get("corn", {}).get(
                "northern_leaf_blight", {}).get("by_state", {}).get(state, 0.3)
            risks["nclb"] = min(1.0, base_nclb)
            
            # Tar Spot
            base_tar = self.disease_baselines.get("corn", {}).get(
                "tar_spot", {}).get("by_state", {}).get(state, 0.2)
            risks["tar_spot"] = min(1.0, base_tar)
            
            # Goss's Wilt
            base_goss = self.disease_baselines.get("corn", {}).get(
                "gosss_wilt", {}).get("by_state", {}).get(state, 0.2)
            risks["gosss_wilt"] = min(1.0, base_goss)
        
        else:  # soybean
            # SDS
            base_sds = self.disease_baselines.get("soybean", {}).get(
                "sudden_death_syndrome", {}).get("by_state", {}).get(state, 0.3)
            
            if soil.drainage_class in ["Poorly drained", "Very poorly drained"]:
                base_sds *= 1.4
            
            risks["sds"] = min(1.0, base_sds)
            
            # SCN
            base_scn = self.disease_baselines.get("soybean", {}).get(
                "soybean_cyst_nematode", {}).get("by_state", {}).get(state, 0.5)
            
            if management.soy_frequency_5yr and management.soy_frequency_5yr >= 3:
                base_scn *= 1.3
            
            risks["scn"] = min(1.0, base_scn)
            
            # Phytophthora
            base_phyto = self.disease_baselines.get("soybean", {}).get(
                "phytophthora", {}).get("by_state", {}).get(state, 0.3)
            
            if soil.drainage_class in ["Poorly drained", "Very poorly drained"]:
                base_phyto *= 1.5
            
            risks["phytophthora"] = min(1.0, base_phyto)
            
            # White Mold
            base_wm = self.disease_baselines.get("soybean", {}).get(
                "white_mold", {}).get("by_state", {}).get(state, 0.3)
            
            if management.row_spacing <= 15:
                base_wm *= 1.2
            
            risks["white_mold"] = min(1.0, base_wm)
            
            # IDC
            base_idc = self.disease_baselines.get("soybean", {}).get(
                "iron_deficiency_chlorosis", {}).get("by_state", {}).get(state, 0.2)
            
            if soil.ph and soil.ph > 7.5:
                base_idc *= 1.5
            
            risks["idc"] = min(1.0, base_idc)
        
        return risks
    
    def derive_target_maturity(self, weather: WeatherFeatures, 
                               management: ManagementInputs,
                               crop: str) -> tuple[float, float, float]:
        """Derive target maturity range from GDD and management."""
        
        if not weather.gdd_mean:
            # Default ranges if no weather data
            if crop == "corn":
                return (105, 110, 115)
            else:
                return (2.5, 3.0, 3.5)
        
        available_gdd = weather.gdd_mean
        
        # Safety margin
        if crop == "corn":
            safety = self.gdd_conversion.get("corn", {}).get("safety_margin_gdd", 100)
            available_gdd -= safety
            
            # Find optimal RM
            gdd_by_rm = self.gdd_conversion.get("corn", {}).get("gdd_by_rm", {})
            optimal_rm = 100  # default
            
            for rm_str, required_gdd in sorted(gdd_by_rm.items(), 
                                                key=lambda x: int(x[0]), reverse=True):
                if available_gdd >= required_gdd:
                    optimal_rm = int(rm_str)
                    break
            
            return (optimal_rm - 3, optimal_rm, optimal_rm + 2)
        
        else:  # soybean
            safety = self.gdd_conversion.get("soybean", {}).get("safety_margin_gdd", 150)
            available_gdd -= safety
            
            gdd_by_mg = self.gdd_conversion.get("soybean", {}).get("gdd_by_mg", {})
            optimal_mg = 3.0  # default
            
            for mg_str, required_gdd in sorted(gdd_by_mg.items(),
                                                key=lambda x: float(x[0]), reverse=True):
                if available_gdd >= required_gdd:
                    optimal_mg = float(mg_str)
                    break
            
            return (optimal_mg - 0.5, optimal_mg, optimal_mg + 0.3)
    
    def derive_field_requirements(self, features: FieldFeatures,
                                   management: ManagementInputs,
                                   crop: str) -> FieldRequirements:
        """Derive complete field requirements from features and management."""
        
        drought_risk = self.derive_drought_risk(
            features.soil, features.weather, management.irrigation
        )
        
        disease_risks = self.derive_disease_risks(
            features.soil, features.weather, management, features.state, crop
        )
        
        target_maturity = self.derive_target_maturity(
            features.weather, management, crop
        )
        
        # Emergence challenge
        emergence = 0.3
        if management.tillage.value == "no-till":
            emergence += 0.2
        if features.soil.clay_pct and features.soil.clay_pct > 35:
            emergence += 0.15
        
        # Standability need (corn)
        standability = 0.3
        if features.soil.slope_pct and features.soil.slope_pct > 5:
            standability += 0.1
        
        # Yield environment
        if features.soil.om_pct and features.soil.om_pct > 4:
            yield_env = "high"
        elif features.soil.om_pct and features.soil.om_pct < 2:
            yield_env = "low"
        else:
            yield_env = "medium"
        
        return FieldRequirements(
            target_maturity_range=target_maturity,
            drought_risk=drought_risk,
            heat_stress_risk=0.3 if features.weather.heat_stress_days and 
                             features.weather.heat_stress_days > 7 else 0.1,
            emergence_challenge=min(1.0, emergence),
            gls_risk=disease_risks.get("gls", 0.0),
            nclb_risk=disease_risks.get("nclb", 0.0),
            tar_spot_risk=disease_risks.get("tar_spot", 0.0),
            gosss_wilt_risk=disease_risks.get("gosss_wilt", 0.0),
            sds_risk=disease_risks.get("sds", 0.0),
            scn_risk=disease_risks.get("scn", 0.0),
            phytophthora_risk=disease_risks.get("phytophthora", 0.0),
            white_mold_risk=disease_risks.get("white_mold", 0.0),
            idc_risk=disease_risks.get("idc", 0.0),
            frogeye_risk=0.2,  # Default
            standability_need=min(1.0, standability),
            lodging_risk=0.3,  # Default
            late_harvest_risk=0.3,  # Default
            yield_environment=yield_env,
            scn_source_history=management.scn_source_history,
        )
