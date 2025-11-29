"""Pydantic schemas for structured LlmAgent outputs in the pilgrimage workflow.

These schemas enforce strict JSON structure and enable automatic type validation
when used with LlmAgent's output_schema parameter. This ensures downstream
BaseAgents can safely access nested fields from session state.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    """Extracted bangumi name and location from user query."""

    bangumi_name: str = Field(
        description=(
            "Anime (bangumi) title extracted from the user query. "
            "Remove decorative brackets such as 《》 or 「」 and keep only the core title."
        )
    )
    location: str = Field(
        description=(
            "User's current location or the station/area name they want to depart from."
        )
    )


class BangumiResult(BaseModel):
    """Matched bangumi from Bangumi API search results."""

    bangumi_id: int = Field(description="Selected work's Bangumi subject ID.")
    bangumi_title: str = Field(description="Original Japanese title of the work.")
    bangumi_title_cn: Optional[str] = Field(
        default=None,
        description="Chinese title of the work, if available.",
    )
    bangumi_confidence: float = Field(
        description="Match confidence between 0 and 1 (0 = no match, 1 = perfect match).",
        ge=0.0,
        le=1.0,
    )


class CoordinatesData(BaseModel):
    """Geographic coordinates."""

    latitude: float = Field(description="Latitude in decimal degrees.")
    longitude: float = Field(description="Longitude in decimal degrees.")


class StationInfo(BaseModel):
    """Station information with coordinates."""

    name: str = Field(description="Station name.")
    coordinates: CoordinatesData = Field(description="Station coordinates.")
    city: Optional[str] = Field(default=None, description="City name.")
    prefecture: Optional[str] = Field(default=None, description="Prefecture name.")


class LocationResult(BaseModel):
    """Resolved location with station info and user coordinates."""

    station: Optional[StationInfo] = Field(
        default=None,
        description="Resolved station information, or null if lookup failed.",
    )
    user_coordinates: CoordinatesData = Field(
        description="User coordinates (usually the same as the station coordinates)."
    )
    search_radius_km: float = Field(
        default=5.0,
        description="Search radius in kilometers.",
    )
