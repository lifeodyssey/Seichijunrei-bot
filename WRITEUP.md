# Seichijunrei Bot: AI-Powered Anime Location Tourism Assistant

**Track**: Concierge Agents

**Author**: Zhenjia Zhou

**Repository**: https://github.com/lifeodyssey/Seichijunrei-bot

---

## Problem Statement

### What is Seichijunrei (聖地巡礼)?

Seichijunrei (聖地巡礼), literally "sacred place pilgrimage," is a Japanese cultural phenomenon where anime fans travel to real-world locations that appear in their favorite shows. For example, fans of *Sound! Euphonium* visit Uji City in Kyoto Prefecture to see the bridges and schools featured in the anime. This form of location-based tourism has become increasingly popular worldwide, with fans traveling from China, Southeast Asia, Europe, and the Americas to visit these iconic spots in Japan.

![Seichijunrei Example: Fans visiting the famous stairs from Your Name](https://image1.gamme.com.tw/news2/2016/04/82/qZqYpJ_ekKWcrKQ.jpg)

*Example: Fans recreating iconic scenes from "Your Name" (君の名は) at Suga Shrine stairs in Tokyo*



### The Problem

Planning a seichijunrei trip is surprisingly complex and time-consuming:

1. **Information Fragmentation**: Seichijunrei location data is scattered across multiple Japanese websites, fan wikis, and social media posts. There's no centralized, reliable database that's easily accessible to international fans.

2. **Language Barriers**: Most seichijunrei resources are in Japanese only. International fans struggle to find anime by their localized titles (e.g., searching for "Sound! Euphonium" vs "響け！ユーフォニアム"), understand location descriptions, and navigate Japanese mapping services.

3. **Information Overload**: Popular anime can have 50-200+ documented locations across entire regions. How do you decide which spots are worth visiting? Which ones fit into a one-day trip? Which locations are accessible to the public vs. private property?

4. **Route Optimization**: Even after identifying interesting locations, travelers face a complex optimization problem: what's the best visiting order considering geographic clustering, transportation networks, opening hours, and narrative flow (visiting locations in the order they appear in the anime)?

5. **Manual Research Time**: Enthusiast fans report spending 10-20 hours researching and planning a single-day seichijunrei itinerary manually.

### Why This Matters

As anime becomes a global cultural phenomenon, making Japanese location tourism accessible to international fans bridges cultural gaps and supports regional economies in Japan. Automating the planning process democratizes this experience, allowing more fans to engage with the stories they love in meaningful, real-world ways.

---

## Why Agents?

### The Case for Multi-Agent Architecture

Seichijunrei trip planning is a perfect use case for AI agents because it requires:

**1. Conversational Intelligence**
Users often describe their intent ambiguously: "I want to visit gbc locations near Kawasaki." The system needs to:
- Understand "gbc" means "Girls Band Cry" (not "Great British Cooking" or other interpretations)
- Clarify with the user if multiple anime match
- Handle multilingual queries (Chinese, English, Japanese)

This requires **natural language understanding and multi-turn dialogue** that agents excel at.

**2. Complex Decision-Making**
Given 50+ potential locations, the system must intelligently select 8-12 optimal spots considering:
- Geographic feasibility (can you visit them in one day?)
- Plot importance (iconic scenes vs. background shots)
- Location accessibility (public vs. private spaces)
- Transportation logistics (walkable clusters vs. train-hopping)

Traditional rule-based systems would require hundreds of hardcoded heuristics. **LLM-powered agents can reason** about these trade-offs holistically using natural language instructions.

**3. Multi-Stage Workflow**
The process naturally divides into sequential stages:
- **Stage 1**: Search and disambiguate the anime
- **Stage 2**: Select locations and generate optimized routes

Each stage has multiple sub-tasks (extract query → search → format → present). **Agent composition patterns** (sequential agents, conditional routing) elegantly model this workflow.

**4. Stateful Conversation**
The system must remember:
- Which anime candidates were presented
- Which one the user selected
- The user's starting location and language preference

**Session management** is critical for maintaining conversation context across multiple turns.

### Why Not Simpler Alternatives?

- **Single LLM Call**: Cannot handle complex multi-turn clarification or modular tool integration
- **Traditional Web Service**: Lacks natural language understanding and intelligent point selection
- **RAG System Alone**: Cannot orchestrate multi-stage workflows or maintain conversational state

Agents provide the right abstraction layer for this problem.

---

## What I Created

### Overall Architecture

Seichijunrei Bot is built using **Google's Agent Development Kit (ADK)** with a multi-agent orchestration pattern. The architecture consists of:

```
Root Agent (Conditional Router with LLM)
│
├─── Stage 1: BangumiSearchWorkflow (SequentialAgent)
│    ├── ExtractionAgent (LlmAgent)
│    │   └── Extracts: user language, anime name, start location
│    ├── BangumiCandidatesAgent (SequentialAgent)
│    │   ├── BangumiSearcher (LlmAgent + search tool)
│    │   └── CandidatesFormatter (LlmAgent + structured output)
│    └── UserPresentationAgent (LlmAgent)
│        └── Returns natural language presentation to user
│
└─── Stage 2: RoutePlanningWorkflow (SequentialAgent)
     ├── UserSelectionAgent (LlmAgent)
     │   └── Confirms user's anime selection
     ├── PointsSearchAgent (BaseAgent + API tool)
     │   └── Fetches all seichijunrei points from Anitabi API
     ├── PointsSelectionAgent (LlmAgent)
     │   └── Intelligently selects 8-12 optimal points using LLM reasoning
     ├── RoutePlanningAgent (LlmAgent + route tool)
     │   └── Generates optimized visiting order and route description
     └── RoutePresentationAgent (LlmAgent)
         └── Returns final route plan in user's language
```

### Key Design Patterns

**1. Sequential Agent Composition**
Both workflows use ADK's `SequentialAgent` to chain agents together. Output from one agent flows as input to the next via session state.

**2. Conditional Routing**
The root agent examines session state to decide which workflow to invoke:
- If no `bangumi_candidates` exist → Stage 1 (search anime)
- If candidates exist but no `selected_bangumi` → Re-present candidates
- If selection confirmed → Stage 2 (plan route)

**3. Tool/Schema Separation**
ADK best practice: agents with `tools` shouldn't have `output_schema` (structured output). We separate concerns:
- `BangumiSearcher` calls search tools, outputs raw results
- `CandidatesFormatter` transforms raw data into structured JSON

**4. Presentation Layer Pattern**
Final presentation agents have **no output_schema**—they generate free-form natural language responses directly shown to users. This decouples data processing from UX.

### ADK Key Concepts Demonstrated

✅ **Multi-Agent System** (Sequential + Conditional routing)

✅ **Custom Tools** (4 FunctionTools: Bangumi search, Anitabi points lookup, route planning, translation)

✅ **Sessions & Memory** (InMemorySessionService for multi-turn conversation state)

✅ **Agent Evaluation** (gbc.evalset.json - Girls Band Cry test case with multi-turn conversation)

✅ **Deployment** (Vertex AI Agent Engine with auto-scaling)

✅ **Observability** (Structured logging with context, tracing enabled)


### Session State Flow

The system maintains conversation state across turns:

```
extraction_result (language, anime_name, location)
    ↓
bangumi_candidates (top 3-5 matching anime)
    ↓
selected_bangumi (user's confirmed choice)
    ↓
all_points (50-200 seichijunrei locations from API)
    ↓
points_selection_result (LLM-selected 8-12 optimal points)
    ↓
route_plan (optimized visiting order + descriptions)
```

### Intelligent Point Selection with LLM

Unlike distance-based filtering, we use **Gemini 2.0 Flash** to reason about point selection:

**Prompt Example**:
"Given these 50 locations for Girls Band Cry, select 8-12 optimal points considering: (1) geographic clustering near Kawasaki Station, (2) episode importance in the narrative, (3) public accessibility, (4) one-day trip feasibility."

This produces semantically meaningful routes rather than just "closest 10 points."

---

## Demo

### Example Conversation Flow

**User Input** (Chinese):
```
我在川崎 想巡礼gbc
(I'm in Kawasaki, want to do seichijunrei for gbc)
```

**Bot Response** (Stage 1 - Disambiguation):
```
您好！接下来是寻找您想巡礼的动画作品的阶段。

我理解您想在川崎出发，寻找《Girls Band Cry》的巡礼地点。是这样吗？

如果是的话，我会开始为您规划巡礼路线。
```

**User Confirmation**:
```
是的 (Yes)
```

**Bot Response** (Stage 2 - Intelligent Route):
```
好的！为您规划《Girls Band Cry》（ガールズバンドクライ）的圣地巡礼路线。
从川崎出发，为您推荐以下行程：

推荐顺序：
1. 川崎駅東口 (Episode 1)
2. JR川崎駅 (Episode 1)
3. たちばな通 (Episode 4)
4. 銀座街 (Episode 4)
... [10 optimized locations]

行程详情：
- 预计时长：约 5.0 小时
- 预计距离：约 15.0 公里

交通提示：
利用火车和公共汽车等公共交通工具在各个地点之间穿梭。步行适合银座商业街区域。

特别提示：
- 提前查询商店和设施的营业时间
- 拍照时请尊重当地居民和商家
```

### Key Features Demonstrated

- **Multilingual Support**: Detected Chinese input, responded in Chinese, preserved Japanese location names
- **Intelligent Selection**: Chose 10 locations from 50+ available, clustered around Kawasaki Station
- **Narrative Ordering**: Locations grouped by episode (Episode 1 → Episode 4) for story immersion
- **Practical Guidance**: Duration/distance estimates, transportation tips, etiquette reminders

**Visual Demo**: See attached screenshot for full conversation interface.

### Evaluation

We've created an evaluation set (`gbc.evalset.json`) containing real multi-turn conversations with the bot. This demonstrates:
- Handling ambiguous queries ("gbc" → "Girls Band Cry")
- Multi-turn clarification and confirmation
- Correct tool invocations and state transitions
- Quality of final route outputs

---

## The Build

### Technologies & Frameworks

**Core Framework**:
- **Google ADK (Agent Development Kit) 1.0+**: Multi-agent orchestration, session management, tool integration
- **Gemini 2.0 Flash**: LLM powering all intelligent agents (reasoning, language understanding, translation)

**External APIs**:
- **Bangumi API** (bangumi.tv): Anime metadata search with 24-hour response caching
- **Anitabi API** (api.anitabi.cn): Seichijunrei location database with 1-hour caching

**Production Infrastructure**:
- **aiohttp**: Async HTTP client with automatic retry (exponential backoff), rate limiting (token-bucket), and LRU cache
- **Pydantic 2.0**: Type validation and schema enforcement for domain models
- **structlog**: Structured logging with contextual metadata

### Development Approach

**1. Domain-Driven Design**
Clean separation of concerns:
- `domain/entities.py`: Core models (Bangumi, Point, Route, Coordinates)
- `clients/`: HTTP clients with resilience patterns (retry, rate-limit, cache)
- `services/`: Business logic (SimpleRoutePlanner for heuristic optimization)
- `adk_agents/`: ADK agent definitions and workflows

**2. Resilience Patterns**
- **Retry Logic**: 3 retries with exponential backoff (1s → 2s → 4s), capped at 30s, with jitter
- **Rate Limiting**: 30 calls/60s per API client using token-bucket algorithm
- **Caching**: Bangumi (24h TTL), Anitabi (1h TTL), LRU eviction at 1000 entries

**3. Testing Strategy**
- **Unit Tests**: HTTP clients, domain models, caching, retry logic (15+ test files)
- **Integration Tests**: Presentation agents with multilingual output
- **Evaluation Sets**: `gbc.evalset.json` for end-to-end conversation quality

**4. Multilingual Support**
- Language detection from user query (Chinese, English, Japanese)
- Gemini-powered translation tool for anime titles
- All responses generated in detected user language

### Deployment: Vertex AI Agent Engine

**GitHub Actions CI/CD**:
- **Platform**: Google Vertex AI Agent Engine (us-central1 region)
- **Workflow**: `.github/workflows/deploy.yml` (manual trigger via workflow_dispatch)
- **Environments**: staging / production (selectable at deploy time)
- **Command**:
  ```bash
  adk deploy agent_engine \
    --project=$GCP_PROJECT_ID \
    --region=us-central1 \
    --staging_bucket=gs://$GCP_PROJECT_ID-agent-staging \
    --display_name=seichijunrei-bot-{env} \
    adk_agents
  ```
- **Configuration**: Uses ADK default settings (auto-scaling, resource limits)

**Deployment Process**:
1. Set up GCP project with required APIs and service account
2. Configure GitHub repository secrets (`GCP_PROJECT_ID`, `GCP_SA_KEY`)
3. Navigate to GitHub Actions → "Deploy to Agent Engine" workflow
4. Click "Run workflow" → Select environment → Deploy

See `DEPLOYMENT.md` for full step-by-step deployment guide.

---

## If I Had More Time

### Priority Enhancements

**1. Google Maps Integration**
Replace heuristic route planning with real routing APIs:
- Actual travel times via public transit
- Turn-by-turn navigation links
- Real-time transit delays and alternatives

**2. PDF/Document Export**
Generate printable route guides:
- Map images with numbered waypoints
- Location photos and anime screenshots side-by-side
- QR codes linking to Google Maps

**3. Weather Integration**
Seasonal recommendations:
- Weather forecasts for travel dates
- Best seasons to visit (cherry blossoms, autumn foliage)
- Indoor alternative suggestions for rainy days

**4. Persistent Sessions**
Upgrade from in-memory to cloud-backed storage (Redis/Cloud Storage):
- Save partial itineraries
- Cross-device access (start on mobile, finish on desktop)
- History of past seichijunrei trips

**5. Community Features**
- User reviews and tips for each location
- Photo uploads (user-contributed images)
- Difficulty ratings (accessibility, crowding levels)

**6. Expanded Evaluation**
Create evaluation sets for:
- Top 20 most-searched anime series
- Multi-city routes (e.g., Tokyo + Kyoto in one trip)
- Edge cases (anime with no locations found, ambiguous queries)

---


## Repository & Links

- **GitHub**: https://github.com/lifeodyssey/Seichijunrei-bot
- **Documentation**: See `README.md` for quickstart, `DEPLOYMENT.md` for deployment guide
- **Evaluation Set**: `adk_agents/seichijunrei_bot/gbc.evalset.json`

---

**Thank you for considering this submission!** 🎌
Let's make seichijunrei accessible to anime fans worldwide through the power of AI agents.
