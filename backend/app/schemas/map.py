from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Choropleth (GeoJSON FeatureCollection)
# ---------------------------------------------------------------------------

class ChoroplethProperties(BaseModel):
    """Properties attached to each GeoJSON Feature in a choropleth map."""

    barrio_id: int
    barrio_name: str
    slug: str
    metric: str = Field(description="Name of the visualised metric")
    value: Optional[Decimal] = None
    color: Optional[str] = Field(
        None,
        description="Hex colour string for this feature (e.g. #2b8cbe)",
    )
    listing_count: Optional[int] = None


class ChoroplethFeature(BaseModel):
    """A single GeoJSON Feature for the choropleth layer."""

    type: str = "Feature"
    geometry: dict[str, Any] = Field(
        description="GeoJSON geometry (MultiPolygon / Polygon)",
    )
    properties: ChoroplethProperties


class ChoroplethResponse(BaseModel):
    """Full GeoJSON FeatureCollection returned by the choropleth endpoint."""

    type: str = "FeatureCollection"
    features: list[ChoroplethFeature] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Extra info: metric name, min/max values, colour scale, etc.",
    )


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

class HeatmapPoint(BaseModel):
    """Single weighted point for a heatmap layer."""

    lat: Decimal
    lon: Decimal
    weight: Decimal = Field(
        default=Decimal("1"),
        description="Weight / intensity at this point",
    )


class HeatmapResponse(BaseModel):
    """Collection of heatmap points."""

    points: list[HeatmapPoint] = Field(default_factory=list)
    metric: Optional[str] = None
    total: int = 0


# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------

class ClusterPoint(BaseModel):
    """Aggregated cluster marker shown at lower zoom levels."""

    lat: Decimal
    lon: Decimal
    count: int = Field(description="Number of listings in this cluster")
    avg_price: Optional[Decimal] = Field(
        None,
        description="Average listing price (USD) in this cluster",
    )
    avg_price_m2: Optional[Decimal] = Field(
        None,
        description="Average price per m2 (USD) in this cluster",
    )
    bounds: Optional[dict[str, Decimal]] = Field(
        None,
        description="Bounding box {north, south, east, west} of the cluster",
    )


class ClusterResponse(BaseModel):
    """Collection of cluster markers."""

    clusters: list[ClusterPoint] = Field(default_factory=list)
    total_listings: int = 0
    zoom_level: Optional[int] = None
