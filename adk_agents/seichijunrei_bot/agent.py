"""
Seichijunrei Bot - ADK Agent Entry Point

This module defines the root ADK agent for the Seichijunrei (anime pilgrimage)
planning bot. It exposes a Gemini-powered LlmAgent that orchestrates the
multi-agent workflows for:

- Stage 1: extracting user intent and searching Bangumi for candidates
- Stage 2: interpreting the user's selection, fetching pilgrimage points
  from Anitabi, selecting the best points, and generating a route plan
"""

import os

from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool

from config import get_settings
from utils.logger import get_logger, setup_logging

from ._workflows.bangumi_search_workflow import bangumi_search_workflow
from ._workflows.route_planning_workflow import route_planning_workflow
from .tools import (
    get_anitabi_points,
    get_bangumi_subject,
    search_anitabi_bangumi_near_station,
    search_bangumi_subjects,
)

# Initialize logging when module is loaded
setup_logging()
logger = get_logger(__name__)

# Log startup information
settings = get_settings()
logger.info(
    "Seichijunrei Bot initialized",
    adk_version="2.0",
    python_path=os.getcwd(),
    debug_mode=settings.debug,
    log_level=settings.log_level,
)

# Configure persistent session storage for multi-invocation conversations.
session_service = InMemorySessionService()

# === ADK Tools Definition ===
# (Bangumi & Anitabi query functions are imported from the local tools module)

# ADK Best Practice: Use SequentialAgent directly as root agent instead of wrapping it in AgentTool
# This ensures proper state propagation between sub-agents in the workflow.
# The old approach (wrapping as AgentTool) caused state isolation issues where
# sub-agent outputs were not accessible to downstream agents.

# Bangumi and Anitabi query tools
search_bangumi_tool = FunctionTool(search_bangumi_subjects)
get_bangumi_tool = FunctionTool(get_bangumi_subject)
get_anitabi_points_tool = FunctionTool(get_anitabi_points)
search_anitabi_bangumi_tool = FunctionTool(search_anitabi_bangumi_near_station)

# Root LlmAgent with conditional routing between Stage 1 and Stage 2 workflows.
# Name is kept as 'seichijunrei_bot' to match ADK Web app_name configuration.
root_agent = LlmAgent(
    name="seichijunrei_bot",
    model="gemini-2.0-flash",
    instruction="""
    You are the Seichijunrei Bot, a 聖地巡礼 (anime location pilgrimage) planning assistant that helps users plan routes to visit real-world locations featured in anime.

    The conversation flow is divided into two stages:
    1. Bangumi Search & Candidate Presentation (Stage 1)
    2. User Selection + Point Retrieval + Route Planning + Route Presentation (Stage 2)

    You must decide what to do based on the session state:

    - If there is no 'bangumi_candidates' in the state yet:
        This means it's the first request or the user has changed to a different anime.
        Call BangumiSearchWorkflow (bangumi_search_workflow):
        - ExtractionAgent extracts the bangumi name and departure location
        - BangumiCandidatesAgent searches and organizes 3-5 candidate works
        Then present the candidate list to the user in natural language and prompt them to make a selection using a number or description.

    - If 'bangumi_candidates' already exists in the state, but there is no 'selected_bangumi' yet:
        This means the candidate list was already presented in the previous round, and the user is now making a selection.
        Do NOT call any workflow again.
        Read the previous list from state.bangumi_candidates, present it clearly again,
        explain how to select a specific work using a number or description, and parse whether the user's input is clear.
        If the user's input is sufficiently clear, you can directly state that you will begin planning the 聖地巡礼 route for that work.

    - If 'selected_bangumi' already exists in the state:
        This means the user has completed their work selection.
        Call RoutePlanningWorkflow (route_planning_workflow):
        - UserSelectionAgent confirms and normalizes the user's selection
        - PointsSearchAgent retrieves all 聖地巡礼 points for this work from Anitabi
        - PointsSelectionAgent uses LLM to intelligently select the 8-12 most suitable points from all available points
        - RoutePlanningAgent calls the custom plan_route tool to generate a structured RoutePlan
        - RoutePresentationAgent reads the RoutePlan and presents it in the user's language (Chinese, English, or Japanese),
          including the recommended order, estimated time, distance, transportation suggestions, and special notes, using
          the unified title format: user-language title (Japanese original).

    Conversation style requirements:
    - Always stay focused on the 聖地巡礼 theme with natural, polite, and concise language.
    - Clearly tell the user which stage they are currently at and what they need to do next (e.g., "Please select a number from the candidates").
    - If critical information is missing (such as the bangumi name or departure location), politely ask for it rather than guessing arbitrarily.
    """,
    sub_agents=[
        bangumi_search_workflow,
        route_planning_workflow,
    ],
)


# Entry point for ADK CLI
if __name__ == "__main__":
    # This allows running with `adk run agent.py`
    pass
