"""ADK BaseAgent for filtering pilgrimage points to meet route optimization constraints.

Reads `points` from `ctx.session.state`, selects the top N most relevant points
(where N ≤ MAX_POINTS_FOR_ROUTE), and writes `points_filtered` back to state.
"""

from typing import Any, Dict, List, ClassVar

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from pydantic import ConfigDict

from utils.logger import get_logger


class PointsFilteringAgent(BaseAgent):
    """Filter and select top N pilgrimage points for route optimization."""

    model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)

    # Maximum points to include in route (Google Maps API limit is 25 waypoints)
    MAX_POINTS_FOR_ROUTE: ClassVar[int] = 20

    def __init__(self) -> None:
        super().__init__(name="PointsFilteringAgent")
        self.logger = get_logger(__name__)

    async def _run_async_impl(self, ctx):  # type: ignore[override]
        state: Dict[str, Any] = ctx.session.state

        points_data = state.get("points") or []

        if not points_data:
            self.logger.warning(
                "[PointsFilteringAgent] No points found in state",
            )
            # Set empty filtered list
            state["points_filtered"] = []
            yield Event(
                author=self.name,
                content=None,
                actions=EventActions(escalate=False),
            )
            return

        total_points = len(points_data)

        # PointsSearchAgent already sorted points by distance from user
        # Simply take the first N points
        selected_points = points_data[: self.MAX_POINTS_FOR_ROUTE]

        state["points_filtered"] = selected_points

        self.logger.info(
            "[PointsFilteringAgent] Points filtered for route optimization",
            total_points=total_points,
            selected_points=len(selected_points),
            max_allowed=self.MAX_POINTS_FOR_ROUTE,
        )

        yield Event(
            author=self.name,
            content=None,
            actions=EventActions(escalate=False),
        )


points_filtering_agent = PointsFilteringAgent()
