"""
Seichijunrei Bot - ADK Agent Entry Point

This module defines the root agent for the Seichijunrei (anime pilgrimage) planning bot.
It wraps the OrchestratorAgent and exposes it as an ADK-compatible agent for deployment
to Google Agent Engine.
"""

import os
from typing import Optional, Dict, Any

from google.adk import Agent
from google.adk.tools import FunctionTool, agent_tool

from tools import MapGeneratorTool, PDFGeneratorTool
from domain.entities import PilgrimageSession
from utils.logger import get_logger, setup_logging
from config import get_settings
from adk_agents.seichijunrei_bot.workflows.pilgrimage_workflow import pilgrimage_workflow
from adk_agents.seichijunrei_bot.tools import (
    search_bangumi_subjects,
    get_bangumi_subject,
    get_anitabi_points,
    search_anitabi_bangumi_near_station,
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

# Initialize sub-components (removed old OrchestratorAgent)
_map_generator = MapGeneratorTool()
_pdf_generator = PDFGeneratorTool()


# === Core Orchestration Tools ===
# (Old plan_pilgrimage and plan_pilgrimage_with_bangumi functions removed -
#  replaced by pilgrimage_workflow via agent_tool)
# (Bangumi/Anitabi query tools moved to adk_agents.seichijunrei_bot.tools to avoid circular imports)

async def generate_map(session_data: dict) -> dict:
    """
    Generate an interactive HTML map for a pilgrimage session.

    Args:
        session_data: Dictionary containing PilgrimageSession data

    Returns:
        Dictionary containing:
        - map_path: Path to the generated HTML map file
        - success: Boolean indicating success
        - error: Error message if failed
    """
    try:
        session = PilgrimageSession(**session_data)
        map_path = await _map_generator.generate(session)

        logger.info(
            "Map generated successfully",
            session_id=session.session_id,
            map_path=map_path
        )

        return {
            "map_path": map_path,
            "success": True,
            "error": None
        }

    except Exception as e:
        logger.error(
            "Map generation failed",
            error=str(e)
        )
        return {
            "map_path": None,
            "success": False,
            "error": str(e)
        }


async def generate_pdf(session_data: dict, map_image_path: Optional[str] = None) -> dict:
    """
    Generate a PDF pilgrimage guide for a session.

    Args:
        session_data: Dictionary containing PilgrimageSession data
        map_image_path: Optional path to a map image to embed

    Returns:
        Dictionary containing:
        - pdf_path: Path to the generated PDF file
        - success: Boolean indicating success
        - error: Error message if failed
    """
    try:
        session = PilgrimageSession(**session_data)
        pdf_path = await _pdf_generator.generate(session, map_image_path)

        logger.info(
            "PDF generated successfully",
            session_id=session.session_id,
            pdf_path=pdf_path
        )

        return {
            "pdf_path": pdf_path,
            "success": True,
            "error": None
        }

    except Exception as e:
        logger.error(
            "PDF generation failed",
            error=str(e)
        )
        return {
            "pdf_path": None,
            "success": False,
            "error": str(e)
        }


# === ADK Tools Definition ===
# (Bangumi & Anitabi query functions are imported from adk_agents.seichijunrei_bot.tools)

# Wrap the SequentialAgent workflow as an AgentTool
# Note: AgentTool automatically uses the agent's name and description
pilgrimage_workflow_tool = agent_tool.AgentTool(agent=pilgrimage_workflow)

# Utility tools for map and PDF generation
generate_map_tool = FunctionTool(generate_map)
generate_pdf_tool = FunctionTool(generate_pdf)

# Bangumi and Anitabi query tools
search_bangumi_tool = FunctionTool(search_bangumi_subjects)
get_bangumi_tool = FunctionTool(get_bangumi_subject)
get_anitabi_points_tool = FunctionTool(get_anitabi_points)
search_anitabi_bangumi_tool = FunctionTool(search_anitabi_bangumi_near_station)


# Define the root agent
root_agent = Agent(
    name="seichijunrei_bot",
    model="gemini-2.0-flash",
    description="""
    Seichijunrei Bot (圣地巡礼机器人) - An AI-powered travel assistant for anime pilgrims.

    This agent helps users plan pilgrimage routes to visit real-world locations
    featured in anime. It can:
    - Search for anime locations near a train station
    - Check weather conditions for the visit
    - Filter locations based on user preferences
    - Optimize the visiting route
    - Suggest transportation modes (walking vs transit)
    - Generate interactive maps and PDF guides
    """,
    instruction="""
    You are Seichijunrei Bot (圣地巡礼机器人), an enthusiastic AI travel assistant
    specialized in anime pilgrimage planning.

    ## CORE WORKFLOW - Pilgrimage Planning

    When a user asks to plan a pilgrimage route, use the automated workflow:

    **Main Tool: plan_pilgrimage_workflow**
    - This tool automatically handles: extraction → search → points → weather → route → transport
    - Input: Set session.state["user_query"] to the user's complete question
    - Output: Returns final_plan with complete route, weather, and points

    Example:
    User: "我在新宿想去你的名字的圣地"
    → Call plan_pilgrimage_workflow
    → Workflow extracts "你的名字" + "新宿", searches, plans route automatically
    → Present the final_plan results to user in a friendly format

    ## BROWSE MODE - Exploration Tools

    For browsing or exploring (not full planning):

    **Search nearby bangumi:**
    - Tool: search_anitabi_bangumi_near_station(station_name="...")
    - Use when: User asks "附近有什么动漫圣地？"

    **Search bangumi by name:**
    - Tool: search_bangumi_subjects(keyword="...")
    - Use when: User wants info about a specific anime

    **List all points for a bangumi:**
    - Tool: get_anitabi_points(bangumi_id="...")
    - Use when: User asks to see all locations without planning a route

    ## OUTPUT GENERATION - After Planning

    **Generate interactive map:**
    - Tool: generate_map(session_data)
    - Use after successful planning to create HTML map

    **Generate PDF guide:**
    - Tool: generate_pdf(session_data, map_image_path)
    - Use after planning to create printable guide

    ## PERSONALITY & STYLE

    - Enthusiastic about anime culture and travel
    - Use natural Chinese/Japanese mix (e.g., "新宿駅" or "新宿站")
    - Structure responses clearly with numbered lists and distances
    - Proactive: automatically offer maps/PDFs after successful planning
    - Always try to help - if one approach fails, suggest alternatives!

    ## ERROR HANDLING

    If workflow fails:
    - Explain what went wrong simply
    - Suggest alternatives (nearby stations, different bangumi)
    - Offer to browse instead of plan if data is incomplete

    Keep responses warm, concise, and actionable!
    """,
    tools=[
        pilgrimage_workflow_tool,  # Main workflow (replaces old plan_pilgrimage*)
        search_bangumi_tool,
        get_bangumi_tool,
        get_anitabi_points_tool,
        search_anitabi_bangumi_tool,
        generate_map_tool,
        generate_pdf_tool,
    ]
)


# Entry point for ADK CLI
if __name__ == "__main__":
    # This allows running with `adk run agent.py`
    pass
