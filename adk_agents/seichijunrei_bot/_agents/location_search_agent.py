"""ADK BaseAgent for resolving a location name to coordinates via Google Maps.

This agent uses the Google Maps Geocoding API to convert human-readable
location names (e.g., "Uji" or "Kyoto") into GPS coordinates.

NOTE: Refactored from LlmAgent to BaseAgent to avoid ADK output_schema + tools bug.
See docs/adk_output_schema_tools_fix.md for details.
"""

from typing import Any, Dict

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

from adk_agents.seichijunrei_bot.tools import geocode_location
from adk_agents.seichijunrei_bot._schemas import LocationResult, CoordinatesData
from utils.logger import get_logger


logger = get_logger(__name__)


class LocationSearchAgent(BaseAgent):
    """Resolves location names to GPS coordinates using Google Maps API.

    This agent:
    1. Reads the location field from session state (extraction_result)
    2. Calls the geocode_location tool
    3. Constructs a LocationResult object
    4. Saves it to session state under 'location_result' key

    This is a deterministic agent with no LLM involvement.
    """

    # Allow arbitrary runtime attributes if ADK / Pydantic attaches any.
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    async def _run_async_impl(self, ctx):  # type: ignore[override]
        """ADK async entrypoint used by Sequential/ParallelAgent workflows."""
        state: Dict[str, Any] = ctx.session.state

        try:
            # 1. Read extraction_result from state
            extraction_result = state.get("extraction_result")
            if not isinstance(extraction_result, dict):
                logger.error("extraction_result not found or invalid in session state")
                raise ValueError("LocationSearchAgent requires extraction_result dict in session.state")

            # Normalise location and handle 'null'/empty cases
            raw_location = extraction_result.get("location")
            location_name: str | None = None
            if isinstance(raw_location, str):
                normalized = raw_location.strip()
                if normalized and normalized.lower() != "null":
                    location_name = normalized

            if not location_name:
                # If we already have a previous successful location_result,
                # reuse it instead of trying to geocode an invalid value like "null".
                if "location_result" in state:
                    logger.info(
                        "Location missing or null in extraction_result; reusing existing location_result",
                        raw_location=raw_location,
                    )
                    yield Event(
                        author=self.name,
                        content=None,
                        actions=EventActions(escalate=False),
                    )
                    return

                logger.error(
                    "location field missing or invalid in extraction_result",
                    raw_location=raw_location,
                )
                raise ValueError(
                    "LocationSearchAgent requires non-empty location in extraction_result when no prior location_result"
                )

            logger.info("Geocoding location", location=location_name)

            # 2. Call geocode_location tool
            geocode_result = await geocode_location(location_name)

            if not geocode_result.get("success"):
                error_msg = geocode_result.get("error", "Unknown error")
                logger.error("Geocoding failed", error=error_msg)
                raise ValueError(f"Geocoding failed: {error_msg}")

            # 3. Construct LocationResult
            coords = geocode_result["coordinates"] or {}
            latitude = coords.get("latitude")
            longitude = coords.get("longitude")

            if latitude is None or longitude is None:
                logger.error("Geocoding result missing coordinates", result=geocode_result)
                raise ValueError("Geocoding result missing latitude/longitude")

            location_result = LocationResult(
                station=None,  # This agent does not resolve station metadata
                user_coordinates=CoordinatesData(
                    latitude=latitude,
                    longitude=longitude,
                ),
                # Default search radius; can be overridden later by other agents if needed
                search_radius_km=state.get("max_radius_km", 5.0),
            )

            logger.info(
                "Location geocoded successfully",
                location=location_name,
                coordinates={"latitude": latitude, "longitude": longitude},
            )

            # 4. Save to session state
            state["location_result"] = location_result.model_dump()

            # BaseAgent Event content must be None or specific ADK types, not arbitrary dict
            yield Event(
                author=self.name,
                content=None,
                actions=EventActions(escalate=False),
            )

        except Exception as e:
            logger.error(
                "LocationSearchAgent failed",
                error=str(e),
                exc_info=True,
            )
            raise


# Export for use in workflow
location_search_agent = LocationSearchAgent(
    name="LocationSearchAgent",
    description="Resolves location names to GPS coordinates using Google Maps",
)
