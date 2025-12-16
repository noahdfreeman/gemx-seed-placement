"""
Field and field feature models.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date


class SoilFeatures(BaseModel):
    """Soil properties extracted from SSURGO."""
    texture_class: Optional[str] = None
    sand_pct: Optional[float] = None
    silt_pct: Optional[float] = None
    clay_pct: Optional[float] = None
    om_pct: Optional[float] = None
    ph: Optional[float] = None
    cec: Optional[float] = None
    drainage_class: Optional[str] = None
    hydro_group: Optional[str] = None
    aws_0_100: Optional[float] = Field(None, description="Available water storage 0-100cm")
    slope_pct: Optional[float] = None
    flood_freq: Optional[str] = None


class WeatherFeatures(BaseModel):
    """Weather/climate features extracted from PRISM."""
    gdd_mean: Optional[float] = Field(None, description="Mean GDD accumulation (base 50F)")
    gdd_std: Optional[float] = None
    growing_season_precip_mm: Optional[float] = None
    precip_cv: Optional[float] = Field(None, description="Precipitation coefficient of variation")
    heat_stress_days: Optional[float] = Field(None, description="Days >95F in July-Aug")
    frost_free_days: Optional[int] = None
    last_spring_frost: Optional[date] = None
    first_fall_frost: Optional[date] = None


class FieldFeatures(BaseModel):
    """Combined field features from all data sources."""
    soil: SoilFeatures
    weather: WeatherFeatures
    state: str
    county: Optional[str] = None


class FieldRequirements(BaseModel):
    """Derived requirements for a field based on features + management."""
    
    # Maturity
    target_maturity_range: tuple[float, float, float] = Field(
        ..., description="(min, optimal, max) RM or MG"
    )
    
    # Stress risks (0-1 scale)
    drought_risk: float = Field(0.0, ge=0, le=1)
    heat_stress_risk: float = Field(0.0, ge=0, le=1)
    emergence_challenge: float = Field(0.0, ge=0, le=1)
    
    # Disease risks (0-1 scale)
    gls_risk: float = Field(0.0, ge=0, le=1)
    nclb_risk: float = Field(0.0, ge=0, le=1)
    tar_spot_risk: float = Field(0.0, ge=0, le=1)
    gosss_wilt_risk: float = Field(0.0, ge=0, le=1)
    sds_risk: float = Field(0.0, ge=0, le=1)
    scn_risk: float = Field(0.0, ge=0, le=1)
    phytophthora_risk: float = Field(0.0, ge=0, le=1)
    white_mold_risk: float = Field(0.0, ge=0, le=1)
    idc_risk: float = Field(0.0, ge=0, le=1)
    frogeye_risk: float = Field(0.0, ge=0, le=1)
    
    # Agronomic needs
    standability_need: float = Field(0.0, ge=0, le=1)
    lodging_risk: float = Field(0.0, ge=0, le=1)
    late_harvest_risk: float = Field(0.0, ge=0, le=1)
    
    # Yield environment
    yield_environment: str = Field("medium", description="high, medium, or low")
    
    # SCN history (for source rotation)
    scn_source_history: list[str] = Field(default_factory=list)


class Field(BaseModel):
    """Field definition with boundary and features."""
    id: str
    name: str
    grower_id: Optional[str] = None
    acres: float
    state: str
    county: Optional[str] = None
    # boundary: GeoJSON would go here
    features: Optional[FieldFeatures] = None
    requirements: Optional[FieldRequirements] = None
