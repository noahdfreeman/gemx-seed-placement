"""
Management practice input models.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum


class TillageSystem(str, Enum):
    NO_TILL = "no-till"
    STRIP_TILL = "strip-till"
    MINIMUM_TILL = "minimum-till"
    CONVENTIONAL = "conventional"


class HerbicideSystem(str, Enum):
    CONVENTIONAL = "conventional"
    ROUNDUP_READY = "roundup_ready"
    LIBERTY_LINK = "liberty_link"
    ENLIST = "enlist"
    XTEND_FLEX = "xtend_flex"


class FungicideProgram(str, Enum):
    NONE = "none"
    AS_NEEDED = "as_needed"
    ROUTINE = "routine"


class SeedTreatment(str, Enum):
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"


class ManagementInputs(BaseModel):
    """Management practice inputs from questionnaire."""
    
    # Rotation
    previous_crop: str = Field(..., description="corn, soybean, wheat, other")
    crop_2_years_ago: Optional[str] = None
    soy_frequency_5yr: Optional[int] = Field(None, ge=0, le=5, description="Years of soy in last 5")
    corn_frequency_5yr: Optional[int] = Field(None, ge=0, le=5, description="Years of corn in last 5")
    
    # Tillage
    tillage: TillageSystem = TillageSystem.MINIMUM_TILL
    
    # Timing
    typical_planting_date: Optional[date] = None
    target_harvest_date: Optional[date] = None
    
    # Irrigation
    irrigation: str = Field("none", description="none, pivot, drip, flood")
    
    # Population
    target_population: Optional[int] = None
    row_spacing: int = Field(30, description="Row spacing in inches")
    
    # Inputs
    herbicide_system: HerbicideSystem = HerbicideSystem.ROUNDUP_READY
    fungicide_program: FungicideProgram = FungicideProgram.AS_NEEDED
    seed_treatment: SeedTreatment = SeedTreatment.BASIC
    
    # Bt traits (corn)
    bt_requirement: Optional[str] = None
    
    # Known issues
    known_pest_issues: list[str] = Field(default_factory=list)
    known_disease_issues: list[str] = Field(default_factory=list)
    
    # SCN history (soybean)
    scn_egg_count: Optional[int] = Field(None, description="If soil sampled")
    scn_source_history: list[str] = Field(default_factory=list, description="Previous SCN sources planted")
    
    class Config:
        json_schema_extra = {
            "example": {
                "previous_crop": "soybean",
                "tillage": "no-till",
                "typical_planting_date": "2024-04-25",
                "irrigation": "none",
                "row_spacing": 30,
                "herbicide_system": "roundup_ready",
                "fungicide_program": "as_needed",
            }
        }
