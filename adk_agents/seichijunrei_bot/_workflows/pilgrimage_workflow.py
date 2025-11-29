"""Sequential/Parallel ADK workflow for Seichijunrei pilgrimage planning.

This module wires together the LlmAgents and BaseAgents defined under
`adk_agents.seichijunrei_bot.agents` into a deterministic workflow using
SequentialAgent and ParallelAgent, as described in
`docs/adk_sequential_agent_migration_plan.md` (Stage 4).

At this stage, the workflow is defined but not yet used by the root agent.
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from adk_agents.seichijunrei_bot._agents.bangumi_search_agent import bangumi_search_agent
from adk_agents.seichijunrei_bot._agents.extraction_agent import extraction_agent
from adk_agents.seichijunrei_bot._agents.location_search_agent import location_search_agent
from adk_agents.seichijunrei_bot._agents.points_filtering_agent import points_filtering_agent
from adk_agents.seichijunrei_bot._agents.points_search_agent import points_search_agent
from adk_agents.seichijunrei_bot._agents.route_agent import route_optimization_agent
from adk_agents.seichijunrei_bot._agents.transport_agent import transport_agent


# Step 2: parallel search for bangumi + location
parallel_search = ParallelAgent(
    name="ParallelSearch",
    sub_agents=[
        bangumi_search_agent,
        location_search_agent,
    ],
)


# Step 4: route optimization (weather removed - API not configured)
parallel_enrichment = ParallelAgent(
    name="ParallelEnrichment",
    sub_agents=[
        route_optimization_agent,
    ],
)


# Main Sequential workflow
# This workflow IS the root agent (not wrapped as a tool), following ADK best practices
# The name must match the expected app name for ADK Web deployment
pilgrimage_workflow = SequentialAgent(
    name="seichijunrei_bot",
    description="""
    Seichijunrei Bot - An AI-powered travel assistant for anime pilgrimage planning.

    This agent helps users plan pilgrimage routes to visit real-world locations
    featured in anime through a deterministic multi-step workflow:
    1. Extract bangumi name and location from user query
    2. Search for matching anime and resolve location coordinates (parallel)
    3. Fetch pilgrimage points for the anime
    4. Filter points to top 20 for route optimization
    5. Get weather forecast and optimize route (parallel)
    6. Optimize transportation modes and generate final plan
    """,
    sub_agents=[
        extraction_agent,        # Step 1: extract bangumi + location from incoming message
        parallel_search,         # Step 2: resolve bangumi + location in parallel
        points_search_agent,     # Step 3: fetch all pilgrimage points
        points_filtering_agent,  # Step 4: filter to top 20 points for route optimization
        parallel_enrichment,     # Step 5: fetch weather + optimize route
        transport_agent,         # Step 6: optimize transport & finalize plan
    ],
)
