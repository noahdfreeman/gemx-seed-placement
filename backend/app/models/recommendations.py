"""
Recommendation output models.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ComponentScores(BaseModel):
    """Individual scoring components."""
    maturity_fit: float = Field(..., ge=0, le=100)
    yield_potential: float = Field(..., ge=0, le=100)
    stress_tolerance: float = Field(..., ge=0, le=100)
    disease_tolerance: float = Field(..., ge=0, le=100)
    agronomics: float = Field(..., ge=0, le=100)


class Recommendation(BaseModel):
    """A single product recommendation."""
    
    # Product info
    brand: str
    product_name: str
    maturity: float
    
    # Scores
    composite_score: float = Field(..., ge=0, le=100)
    component_scores: ComponentScores
    
    # Explanations
    strengths: list[str]
    watch_outs: list[str]
    
    # Suggestions
    placement: str = Field(..., description="Best fit, Strong fit, etc.")
    suggested_population: int
    
    # Metadata
    data_confidence: float = Field(..., ge=0, le=1)
    
    def to_summary(self) -> dict:
        """Return a summary dict for display."""
        return {
            "product": f"{self.brand} {self.product_name}",
            "maturity": self.maturity,
            "score": round(self.composite_score, 1),
            "placement": self.placement,
            "top_strength": self.strengths[0] if self.strengths else None,
            "top_concern": self.watch_outs[0] if self.watch_outs else None,
        }


class RecommendationSet(BaseModel):
    """A set of recommendations for a field."""
    field_id: str
    field_name: str
    crop: str
    recommendations: list[Recommendation]
    
    # Summary stats
    top_score: float
    avg_score: float
    products_evaluated: int
    products_filtered: int
    
    def to_csv_rows(self) -> list[dict]:
        """Convert to rows for CSV export."""
        return [
            {
                "field": self.field_name,
                "crop": self.crop,
                "rank": i + 1,
                "brand": rec.brand,
                "product": rec.product_name,
                "maturity": rec.maturity,
                "score": rec.composite_score,
                "placement": rec.placement,
                "population": rec.suggested_population,
            }
            for i, rec in enumerate(self.recommendations)
        ]
