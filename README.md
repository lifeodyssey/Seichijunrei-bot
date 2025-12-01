# Seichijunrei Bot

> An intelligent 聖地巡礼 (seichijunrei) travel assistant built on Google ADK

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Track: Concierge Agents](https://img.shields.io/badge/Track-Concierge%20Agents-blue)](https://www.kaggle.com/competitions/google-adk-capstone)

---

## Overview

Seichijunrei Bot is a conversational AI agent that helps anime fans plan
聖地巡礼 (seichijunrei) trips to real‑world locations featured in anime.

Through a natural 2-stage dialogue, the agent:

- **Stage 1**: Searches for anime by name and presents top candidates
- **Stage 2**: Uses LLM reasoning to select 8-12 suitable 聖地巡礼 points
- Asks the LLM to consider geography, story importance, and visit feasibility when choosing points
- Generates simple narrative routes with rough time/distance estimates and generic transport tips

The agent automatically detects the user's language (Chinese / English / Japanese)
and presents results and routes in that language, while keeping Japanese titles
as the canonical reference.

The project is implemented using the Google Agent Development Kit (ADK) with
Gemini 2.0 Flash for intelligent decision-making.

---

## Key Features

- **Conversational Search**
  - Natural language anime search via Bangumi API
  - Presents 3-5 top candidates with summaries
  - User-friendly selection through dialogue

- **LLM-Driven Intelligent Selection**
  - Gemini 2.0 Flash intelligently selects 8-12 optimal 聖地巡礼 points
  - Configured to consider geographic clustering, plot importance, and visit feasibility
  - Balances route feasibility with content coverage

- **Automated Route Planning**
  - Simple narrative-order-based route suggestions via a custom tool
  - Rough estimates for duration and distance
  - Generic transport tips based on the starting location

- **Multilingual UX**
  - Detects user language from the initial query (`zh-CN`, `en`, `ja`)
  - Stage 1 and Stage 2 responses are generated in the user's language
  - Unified title format: **user-language title (Japanese original[, air date])**
  - Uses a dedicated Gemini-powered translation tool for anime titles

- **Rich Outputs**
  - Session-based state management for multi-turn conversations

---

## Architecture (High Level)

The core workflow is implemented as a **2-stage conversational flow** using ADK agents:

### Stage 1: Bangumi Search Workflow
1. **ExtractionAgent (LlmAgent)**
   - Extracts `bangumi_name`, `location`, and `user_language` from user query
   - Output: `extraction_result` → session state

2. **BangumiCandidatesAgent (SequentialAgent)**
   - Searches Bangumi API for matching anime works
   - Selects top 3-5 candidates
   - Output: `bangumi_candidates` → session state

3. **UserPresentationAgent (LlmAgent)**
   - Generates multilingual, natural language presentation of candidates
   - Formats titles as **user-language title (Japanese original, air date)**
   - Uses a translation tool for Chinese titles when missing
   - No output_schema (conversational response); user selects their preferred anime

### Stage 2: Route Planning Workflow
4. **UserSelectionAgent (LlmAgent)**
   - Confirms and normalizes user's anime selection
   - Output: `selected_bangumi` → session state

5. **PointsSearchAgent (BaseAgent)**
   - Fetches all 聖地巡礼 points from Anitabi API
   - Output: `all_points` → session state

6. **PointsSelectionAgent (LlmAgent)**
   - Intelligently selects 8-12 best points using LLM reasoning
   - Considers: geography, plot importance, accessibility
   - Output: `points_selection_result` → session state

7. **RoutePlanningAgent (LlmAgent)**
   - Calls custom `plan_route` tool for optimization
   - Generates final route with transport suggestions
   - Output: `route_plan` → session state

8. **RoutePresentationAgent (LlmAgent)**
   - Reads `route_plan`, `selected_bangumi`, and `extraction_result.user_language`
   - Presents a structured, user-language route summary (overview, ordered list,
     time/distance, transport tips, special notes)
   - Uses the same unified title format as Stage 1

**State Management:**
- Uses `InMemorySessionService` for multi-turn conversations
- State keys flow through workflow stages
- Root agent (`seichijunrei_bot`) routes between stages based on state

**Supporting Layers:**
- **Domain layer** (`domain/`) – Pydantic entities: `Bangumi`, `Point`, `Route`, `SeichijunreiSession`
- **Infrastructure** (`clients/`, `services/`) – HTTP clients, retry, cache, session management
- **Tools** (`tools/`) – Map and PDF generator tools exposed to agent
- **Templates** (`templates/`) – HTML/PDF layouts for user-facing outputs

---

## Getting Started

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- Google API Key with Gemini API access
- No additional API keys required (Bangumi and Anitabi APIs are public)

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Required configuration:

```env
GEMINI_API_KEY=your_gemini_api_key
ANITABI_API_URL=https://api.anitabi.cn
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
```

### 3. Run the ADK web UI (recommended)

```bash
make dev      # first time only – installs tools
make web      # start ADK Web UI
```

or directly:

```bash
uv run adk web adk_agents
```

Then open the URL printed in the terminal (typically
`http://localhost:8000`) and chat with the agent.

### 4. Run from the command line

```bash
make run
# or
uv run adk run adk_agents/seichijunrei_bot
```

---

## Project Structure

```text
Seichijunrei/
├── README.md                # Overview (this file)
├── .env.example             # Environment template
├── pyproject.toml           # Project configuration
├── Makefile                 # Convenience commands
│
├── adk_agents/
│   └── seichijunrei_bot/
│       ├── agent.py              # ADK root agent entry point
│       ├── _agents/              # ADK agent implementations
│       │   ├── extraction_agent.py
│       │   ├── bangumi_candidates_agent.py
│       │   ├── bangumi_search_agent.py
│       │   ├── user_presentation_agent.py
│       │   ├── user_selection_agent.py
│       │   ├── points_search_agent.py
│       │   ├── points_selection_agent.py
│       │   ├── route_planning_agent.py
│       │   └── route_presentation_agent.py
│       ├── _schemas.py           # Pydantic schemas for ADK agents
│       ├── _workflows/           # 2 workflow orchestrations
│       │   ├── bangumi_search_workflow.py
│       │   └── route_planning_workflow.py
│       └── tools/                # Custom function tools
│           ├── __init__.py       # ADK FunctionTools export
│           ├── route_planning.py # Route optimization tool (SimpleRoutePlanner)
│           └── translation.py    # Gemini-based title translation tool
│
├── clients/                 # HTTP API clients
│   ├── anitabi.py           # Anitabi 聖地巡礼 data client
│   ├── bangumi.py           # Bangumi subject search client
│   └── base.py              # Base HTTP client
│
├── config/                  # Configuration management
│   └── settings.py          # Pydantic settings
│
├── domain/                  # Domain models
│   └── entities.py          # Core Pydantic entities
│
├── services/
│   ├── cache.py             # In‑memory cache helpers
│   ├── retry.py             # Retry and rate‑limiting utilities
│   ├── session.py           # Session state management
│   └── simple_route_planner.py  # Route planning service
│
├── tools/                   # (reserved for future non-ADK utilities)
│   └── __init__.py
│
├── utils/                   # Utilities
│   └── logger.py            # Structured logging
│
├── templates/               # (currently unused; reserved for future HTML/PDF outputs)
│
└── tests/
    ├── unit/                # Unit tests
    └── integration/         # Integration tests
```

---

## Data Sources and APIs

- **Bangumi** (bangumi.tv) – Anime metadata and subject information
- **Anitabi** (api.anitabi.cn) – 聖地巡礼 location database
- **Google Gemini 2.0 Flash** – LLM for intelligent point selection and conversational AI

---

## TODO / Roadmap

The following items are planned or partially implemented and tracked here
instead of being documented as completed features:

- **Google Maps integration**
  - Use the existing Google Maps client more deeply to fetch real route/directions
    data and surface Google Maps links or snippets alongside the LLM-planned route.

- **PDF / document export**
  - Reintroduce a lightweight, template-based PDF or document generator that can
    turn a planned route into a printable guide, without bloating the core agent.

- **Weather integration**
  - Add an optional weather lookup step that annotates the planned day-trip with
    basic forecast info and suggestions (e.g., bring umbrella, temperature range).

- **Deeper multilingual support**
  - Extend the current zh-CN/en/ja chat experience to additional outputs
    (for example, future map or document generation features).

- **Route planning enhancements**
  - Replace the heuristic `SimpleRoutePlanner` with a more realistic planner
    that leverages transit/walking directions APIs while keeping ADK tool
    boundaries clean.

- **Persistent session storage**
  - Add an optional Redis/Cloud-backed `SessionService` for long-lived user
    sessions beyond the current in-memory implementation.

---

## License

This project is released under the MIT License (see `LICENSE`).

Built as a Google ADK Capstone Project in the "Concierge Agents" track.
