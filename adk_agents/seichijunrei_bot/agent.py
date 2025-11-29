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
from adk_agents.seichijunrei_bot._workflows.pilgrimage_workflow import pilgrimage_workflow
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

# ADK Best Practice: Use SequentialAgent directly as root agent instead of wrapping it in AgentTool
# This ensures proper state propagation between sub-agents in the workflow.
# The old approach (wrapping as AgentTool) caused state isolation issues where
# sub-agent outputs were not accessible to downstream agents.

# Utility tools for map and PDF generation
generate_map_tool = FunctionTool(generate_map)
generate_pdf_tool = FunctionTool(generate_pdf)

# Bangumi and Anitabi query tools
search_bangumi_tool = FunctionTool(search_bangumi_subjects)
get_bangumi_tool = FunctionTool(get_bangumi_subject)
get_anitabi_points_tool = FunctionTool(get_anitabi_points)
search_anitabi_bangumi_tool = FunctionTool(search_anitabi_bangumi_near_station)

# Use the SequentialAgent workflow directly as the root agent
# This is the ADK-recommended pattern for deterministic multi-step workflows
root_agent = pilgrimage_workflow


# Entry point for ADK CLI
if __name__ == "__main__":
    # This allows running with `adk run agent.py`
    pass
