"""
Product models for corn hybrids and soybean varieties.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CornHybrid(BaseModel):
    """Corn hybrid with trait ratings."""
    
    # Identification
    brand: str
    hybrid_name: str
    
    # Agronomics
    relative_maturity: float = Field(..., ge=75, le=130, description="Relative maturity (days)")
    yield_potential: int = Field(..., ge=1, le=9, description="Yield potential (1-9)")
    test_weight: Optional[int] = Field(None, ge=1, le=9)
    drydown: Optional[int] = Field(None, ge=1, le=9)
    
    # Standability
    stalk_strength: Optional[int] = Field(None, ge=1, le=9)
    root_strength: Optional[int] = Field(None, ge=1, le=9)
    intactability: Optional[int] = Field(None, ge=1, le=9)
    
    # Stress tolerance
    drought_tolerance: Optional[int] = Field(None, ge=1, le=9)
    heat_tolerance: Optional[int] = Field(None, ge=1, le=9)
    emergence_vigor: Optional[int] = Field(None, ge=1, le=9)
    
    # Disease ratings
    gray_leaf_spot: Optional[int] = Field(None, ge=1, le=9)
    northern_leaf_blight: Optional[int] = Field(None, ge=1, le=9)
    tar_spot: Optional[int] = Field(None, ge=1, le=9)
    gosss_wilt: Optional[int] = Field(None, ge=1, le=9)
    anthracnose_stalk: Optional[int] = Field(None, ge=1, le=9)
    
    # Traits
    bt_traits: list[str] = Field(default_factory=list)
    herbicide_traits: list[str] = Field(default_factory=list)
    
    # Ear type
    ear_type: Optional[str] = Field(None, description="Flex, Semi-flex, or Fixed")
    kernel_type: Optional[str] = Field(None, description="Dent, Semi-dent, or Flint")
    
    # Metadata
    year_introduced: Optional[int] = None
    data_source: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand": "Pioneer",
                "hybrid_name": "P1185AM",
                "relative_maturity": 111,
                "yield_potential": 8,
                "drought_tolerance": 7,
                "gray_leaf_spot": 6,
                "bt_traits": ["Qrome", "AM"],
                "herbicide_traits": ["RR", "LL"],
            }
        }


class SoybeanVariety(BaseModel):
    """Soybean variety with trait ratings."""
    
    # Identification
    brand: str
    variety_name: str
    
    # Agronomics
    maturity_group: float = Field(..., ge=0.0, le=6.0, description="Maturity group (0.0-6.0)")
    yield_potential: int = Field(..., ge=1, le=9)
    plant_height: Optional[int] = Field(None, ge=1, le=9)
    lodging_resistance: Optional[int] = Field(None, ge=1, le=9)
    
    # Stress tolerance
    drought_tolerance: Optional[int] = Field(None, ge=1, le=9)
    emergence_vigor: Optional[int] = Field(None, ge=1, le=9)
    idc_tolerance: Optional[int] = Field(None, ge=1, le=9, description="Iron Deficiency Chlorosis")
    
    # Disease ratings
    sds_rating: Optional[int] = Field(None, ge=1, le=9, description="Sudden Death Syndrome")
    scn_source: Optional[str] = Field(None, description="SCN resistance source (PI 88788, Peking, etc.)")
    phytophthora_genes: list[str] = Field(default_factory=list, description="Rps genes")
    phytophthora_field: Optional[int] = Field(None, ge=1, le=9, description="Field tolerance")
    white_mold: Optional[int] = Field(None, ge=1, le=9)
    brown_stem_rot: Optional[int] = Field(None, ge=1, le=9)
    frogeye_leaf_spot: Optional[int] = Field(None, ge=1, le=9)
    
    # Traits
    herbicide_traits: list[str] = Field(default_factory=list)
    
    # Plant architecture
    growth_habit: Optional[str] = Field(None, description="Determinate or Indeterminate")
    branching: Optional[str] = Field(None, description="Bushy, Moderate, or Erect")
    canopy_closure: Optional[str] = Field(None, description="Fast, Medium, or Slow")
    
    # Metadata
    year_introduced: Optional[int] = None
    data_source: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand": "Asgrow",
                "variety_name": "AG27XF2",
                "maturity_group": 2.7,
                "yield_potential": 8,
                "sds_rating": 7,
                "scn_source": "PI 88788",
                "herbicide_traits": ["XtendFlex"],
            }
        }
