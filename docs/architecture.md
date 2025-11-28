# Seichijunrei Bot - ADK 架构设计文档

> 基于 Google ADK (Agent Development Kit) 的确定性工作流架构
>
> 最后更新: 2024-11-29

---

## 1. 架构概览

### 1.1 设计理念

Seichijunrei Bot 采用 **Sequential Thinking** 模式，通过 ADK 的 SequentialAgent 和 ParallelAgent 实现确定性的工作流编排，避免依赖 LLM 理解复杂 instruction 来决定执行顺序。

**核心优势:**
- ✅ **确定性执行** - 步骤顺序固定，结果可预测
- ✅ **架构统一** - 全部使用 ADK 原生 agents
- ✅ **并行优化** - 关键步骤并行执行，提升性能
- ✅ **易于调试** - 单一职责，状态变化可追踪
- ✅ **代码简洁** - 净减少 ~600 行代码

### 1.2 架构层次

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Root Agent (用户交互层)                      │
│  - 理解用户意图                                        │
│  - 路由到合适的工作流或工具                              │
│  - Model: gemini-2.0-flash                          │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│ Layer 2: Workflow Orchestration (工作流编排层)       │
│  - PilgrimageWorkflow (SequentialAgent)            │
│  - 5个确定性步骤                                       │
│  - 2个并行执行节点                                     │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│ Layer 3: Specialized Agents (专业能力层)              │
│  - 3个 LlmAgent (信息提取和搜索)                       │
│  - 4个 BaseAgent (业务逻辑执行)                        │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│ Layer 4: Infrastructure (基础设施层)                  │
│  - API Clients (Anitabi, Bangumi, Maps, Weather)  │
│  - Services (Cache, Retry, Session)               │
│  - Domain Entities (Pydantic models)              │
└─────────────────────────────────────────────────────┘
```

---

## 2. 工作流设计

### 2.1 PilgrimageWorkflow 详细流程

```python
# adk_agents/seichijunrei_bot/workflows/pilgrimage_workflow.py

pilgrimage_workflow = SequentialAgent(
    name="plan_pilgrimage_workflow",
    sub_agents=[
        extraction_agent,       # Step 1: 提取信息
        parallel_search,        # Step 2: 并行搜索
        points_search_agent,    # Step 3: 获取圣地
        parallel_enrichment,    # Step 4: 并行增强
        transport_agent,        # Step 5: 优化交通
    ],
)
```

#### Step 1: ExtractionAgent (LlmAgent)

**输入:**
```json
{
  "user_query": "我在新宿想去你的名字的圣地"
}
```

**LLM 任务:**
- 提取番剧名称 (去除《》等符号)
- 提取位置/车站名称
- 返回严格的 JSON

**输出 (写入 state):**
```json
{
  "extraction_result": {
    "bangumi_name": "你的名字",
    "location": "新宿"
  }
}
```

**实现:** `adk_agents/seichijunrei_bot/agents/extraction_agent.py`

---

#### Step 2: ParallelSearch (ParallelAgent)

并行执行两个搜索任务：

**2.1 BangumiSearchAgent (LlmAgent)**

**输入 (from state):**
```json
{
  "bangumi_name": "你的名字"
}
```

**LLM 任务:**
- 调用 `search_bangumi_subjects(keyword="你的名字")`
- 从结果中选择最相关的番剧
- 返回 `bangumi_id`

**输出 (写入 state):**
```json
{
  "bangumi_id": 140001
}
```

**2.2 LocationSearchAgent (LlmAgent)**

**输入 (from state):**
```json
{
  "location": "新宿"
}
```

**LLM 任务:**
- 调用 `search_anitabi_bangumi_near_station(station_name="新宿")`
- 提取 `station.lat` 和 `station.lng`

**输出 (写入 state):**
```json
{
  "user_coordinates": {
    "latitude": 35.6895,
    "longitude": 139.7006
  },
  "station": {
    "name": "新宿駅",
    "city": "新宿区",
    "prefecture": "東京都"
  }
}
```

**实现:**
- `adk_agents/seichijunrei_bot/agents/bangumi_search_agent.py`
- `adk_agents/seichijunrei_bot/agents/location_search_agent.py`

---

#### Step 3: PointsSearchAgent (BaseAgent)

**输入 (from state):**
```json
{
  "bangumi_id": 140001,
  "user_coordinates": {"latitude": 35.6895, "longitude": 139.7006},
  "max_radius_km": 50.0
}
```

**业务逻辑:**
1. 调用 `anitabi_client.get_bangumi_points(bangumi_id)`
2. 计算每个点到用户的距离
3. 过滤超出半径的点
4. 按距离排序

**输出 (写入 state):**
```json
{
  "points": [
    {
      "id": "p1",
      "name": "新宿御苑",
      "cn_name": "新宿御苑",
      "coordinates": {"latitude": 35.6851, "longitude": 139.7101},
      "episode": 1,
      "screenshot_url": "https://...",
      "address": "東京都新宿区内藤町11"
    },
    // ... more points
  ],
  "points_meta": {
    "total": 15,
    "source": "anitabi",
    "max_radius_km": 50.0
  }
}
```

**实现:** `adk_agents/seichijunrei_bot/agents/points_search_agent.py`

---

#### Step 4: ParallelEnrichment (ParallelAgent)

并行执行天气查询和路线优化：

**4.1 WeatherAgent (BaseAgent)**

**输入 (from state):**
```json
{
  "user_coordinates": {"latitude": 35.6895, "longitude": 139.7006}
}
```

**业务逻辑:**
- 调用 `weather_client.get_current_weather(lat, lng)`

**输出 (写入 state):**
```json
{
  "weather": {
    "temperature": 18.5,
    "condition": "Partly Cloudy",
    "precipitation_probability": 10
  }
}
```

**4.2 RouteOptimizationAgent (BaseAgent)**

**输入 (from state):**
```json
{
  "station": {...},
  "user_coordinates": {...},
  "points": [...]
}
```

**业务逻辑:**
- 调用 Google Maps Directions API
- 使用 `optimize:true` 参数优化访问顺序

**输出 (写入 state):**
```json
{
  "route": {
    "waypoint_order": [0, 2, 1, 3, ...],
    "total_distance_km": 6.5,
    "total_duration_minutes": 210,
    "legs": [...]
  },
  "route_meta": {
    "optimized": true,
    "waypoints_count": 15
  }
}
```

**实现:**
- `adk_agents/seichijunrei_bot/agents/weather_agent.py`
- `adk_agents/seichijunrei_bot/agents/route_agent.py`

---

#### Step 5: TransportAgent (BaseAgent)

**输入 (from state):**
```json
{
  "route": {...}
}
```

**业务逻辑:**
- 遍历 `route.legs`
- 对每段距离应用规则:
  - < 1.5km: 步行
  - ≥ 1.5km: 查询公共交通

**输出 (写入 state):**
```json
{
  "final_plan": {
    "route": {...},
    "weather": {...},
    "points": [...],
    "transport_recommendations": [
      {
        "from": "新宿駅",
        "to": "新宿御苑",
        "mode": "walking",
        "distance_km": 1.2,
        "duration_minutes": 15
      },
      {
        "from": "新宿御苑",
        "to": "代々木公園",
        "mode": "subway",
        "line": "東京メトロ副都心線",
        "duration_minutes": 12,
        "fare_yen": 200
      }
    ]
  }
}
```

**实现:** `adk_agents/seichijunrei_bot/agents/transport_agent.py`

---

### 2.2 State Schema

所有 agents 通过 `ctx.session.state` 共享数据。

**完整 State 结构:**

```python
{
    # Step 1 输出
    "user_query": str,
    "extraction_result": {
        "bangumi_name": str,
        "location": str
    },

    # Step 2 输出
    "bangumi_id": int,
    "user_coordinates": {
        "latitude": float,
        "longitude": float
    },
    "station": {
        "name": str,
        "city": str,
        "prefecture": str,
        "coordinates": {...}
    },

    # Step 3 输出
    "points": List[dict],
    "points_meta": {
        "total": int,
        "source": str,
        "max_radius_km": float
    },

    # Step 4 输出
    "weather": dict,
    "route": {
        "waypoint_order": List[int],
        "total_distance_km": float,
        "total_duration_minutes": int,
        "legs": List[dict]
    },
    "route_meta": dict,

    # Step 5 输出
    "final_plan": {
        "route": dict,
        "weather": dict,
        "points": List[dict],
        "transport_recommendations": List[dict]
    }
}
```

---

## 3. Agent 设计模式

### 3.1 LlmAgent 模式

**适用场景:** 需要 LLM 推理的任务 (信息提取、语义匹配、选择决策)

**示例:** ExtractionAgent

```python
from google.adk.agents import LlmAgent

extraction_agent = LlmAgent(
    name="ExtractionAgent",
    model="gemini-2.0-flash",
    instruction="""
    从用户查询中提取番剧名称和位置。

    用户查询: {user_query}

    返回 JSON:
    {
      "bangumi_name": "...",
      "location": "..."
    }
    """,
    output_key="extraction_result",
)
```

**特点:**
- ✅ 配置即代码 (no custom Python logic)
- ✅ 通过 `output_key` 写入 state
- ✅ 可以配置 `tools` 列表

---

### 3.2 BaseAgent 模式

**适用场景:** 确定性业务逻辑 (API 调用、数据处理、算法计算)

**示例:** PointsSearchAgent

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

class PointsSearchAgent(BaseAgent):
    model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)

    def __init__(self, anitabi_client: Optional[AnitabiClient] = None):
        super().__init__(name="PointsSearchAgent")
        self.anitabi_client = anitabi_client or AnitabiClient()
        self.logger = get_logger(__name__)

    async def _run_async_impl(self, ctx):
        # 1. 从 state 读取输入
        state = ctx.session.state
        bangumi_id = state.get("bangumi_id")
        user_coords = Coordinates(**state.get("user_coordinates"))

        # 2. 执行业务逻辑
        points = await self.anitabi_client.get_bangumi_points(str(bangumi_id))
        nearby_points = [p for p in points if user_coords.distance_to(p.coordinates) <= 50.0]
        nearby_points.sort(key=lambda p: user_coords.distance_to(p.coordinates))

        # 3. 写入 state
        state["points"] = [p.model_dump() for p in nearby_points]
        state["points_meta"] = {"total": len(nearby_points)}

        # 4. Yield Event
        yield Event(
            author=self.name,
            content={"points_count": len(nearby_points)},
            actions=EventActions(escalate=True)
        )
```

**必须遵循的规范:**
1. ✅ 继承 `BaseAgent`
2. ✅ 实现 `async def _run_async_impl(self, ctx)`
3. ✅ 通过 `ctx.session.state` 读写数据
4. ✅ `yield Event(...)` 传递结果
5. ✅ 使用 `EventActions(escalate=True/False)` 控制流程

---

### 3.3 Event 通信协议

**Event 结构:**

```python
Event(
    author=self.name,           # Agent 名称
    content={...},              # 传递的数据（可选）
    actions=EventActions(
        escalate=True           # True: 继续下一个 agent
                                # False: 停止当前流程
    )
)
```

**escalate 使用场景:**
- `escalate=True`: 正常完成，继续工作流
- `escalate=False`: 可选步骤完成，但不影响后续

---

## 4. FunctionTools 设计

### 4.1 工具分类

**1. 工作流入口 (AgentTool):**
```python
pilgrimage_workflow_tool = agent_tool.AgentTool(
    agent=pilgrimage_workflow
)
```

**2. API 查询工具 (FunctionTool):**
```python
async def search_bangumi_subjects(keyword: str) -> dict:
    results = await _bangumi_client.search_subject(keyword, subject_type=BangumiClient.TYPE_ANIME)
    return {"keyword": keyword, "results": results}

search_bangumi_tool = FunctionTool(search_bangumi_subjects)
```

**3. 输出生成工具 (FunctionTool):**
```python
async def generate_map(session_data: dict) -> dict:
    session = PilgrimageSession(**session_data)
    map_path = await _map_generator.generate(session)
    return {"map_path": map_path, "success": True}

generate_map_tool = FunctionTool(generate_map)
```

### 4.2 工具设计原则

1. ✅ **单一职责** - 每个工具只做一件事
2. ✅ **类型安全** - 使用 Python 类型注解
3. ✅ **异步优先** - 所有 I/O 操作使用 async/await
4. ✅ **错误友好** - 返回结构化错误信息
5. ✅ **幂等性** - 相同输入产生相同输出

---

## 5. Root Agent 设计

### 5.1 职责边界

Root Agent **应该做:**
- ✅ 理解用户意图
- ✅ 路由到合适的工作流或工具
- ✅ 友好地呈现结果

Root Agent **不应该做:**
- ❌ 复杂的业务逻辑
- ❌ 直接调用 API
- ❌ 深层次的错误处理

### 5.2 Instruction 设计

```python
root_agent = Agent(
    name="seichijunrei_bot",
    model="gemini-2.0-flash",
    instruction="""
    你是 Seichijunrei Bot，专门帮助用户规划动漫圣地巡礼。

    ## 核心能力

    **完整路线规划:**
    - 工具: plan_pilgrimage_workflow(user_query)
    - 示例: "我在新宿想去你的名字的圣地"

    **探索模式:**
    - search_anitabi_bangumi_near_station(station_name)
    - search_bangumi_subjects(keyword)
    - get_anitabi_points(bangumi_id)

    **生成输出:**
    - generate_map(session_data)
    - generate_pdf(session_data)

    优先使用 plan_pilgrimage_workflow 完成完整规划！
    """,
    tools=[...]
)
```

**设计原则:**
- 📏 **简洁** - Instruction < 50 行
- 🎯 **清晰** - 工具调用策略明确
- 📝 **示例驱动** - 提供具体使用示例
- 🚫 **避免冗余** - 不重复工具文档

---

## 6. 数据流图

```
User Query
    │
    ▼
[Root Agent]
    │ user_query
    ▼
[ExtractionAgent]
    │ bangumi_name, location
    ├────────────┬────────────┐
    ▼            ▼            │
[BangumiSearch][LocationSearch]
    │ bangumi_id │ user_coordinates, station
    └────────────┴────────────┘
    │
    ▼
[PointsSearchAgent]
    │ points, points_meta
    ├──────────┬──────────┐
    ▼          ▼          │
[WeatherAgent][RouteAgent]
    │ weather  │ route, route_meta
    └──────────┴──────────┘
    │
    ▼
[TransportAgent]
    │ final_plan
    ▼
[Root Agent]
    │
    ▼
User Response
```

---

## 7. 错误处理策略

### 7.1 分层错误处理

**Layer 4 (Infrastructure):**
- API 客户端使用 retry 装饰器
- 抛出 `APIError`, `TooManyPointsError` 等自定义异常

**Layer 3 (Agents):**
- 捕获 Layer 4 异常
- 记录详细日志
- 向上抛出或返回 `escalate=False`

**Layer 2 (Workflow):**
- SequentialAgent 自动处理 agent 失败
- 可选: 配置 fallback strategies

**Layer 1 (Root):**
- 捕获所有异常
- 向用户返回友好错误信息

### 7.2 示例

```python
# Layer 4: Client
@retry_with_backoff(max_attempts=3)
async def get_bangumi_points(self, bangumi_id: str) -> List[Point]:
    response = await self._session.get(f"/api/v1/bangumi/{bangumi_id}/points")
    if response.status_code != 200:
        raise APIError(f"Anitabi API error: {response.status_code}")
    return [Point(**p) for p in response.json()]

# Layer 3: Agent
async def _run_async_impl(self, ctx):
    try:
        points = await self.anitabi_client.get_bangumi_points(str(bangumi_id))
    except APIError as exc:
        self.logger.error("Failed to get points", error=str(exc), exc_info=True)
        raise  # Re-raise to workflow

# Layer 1: Root Agent instruction
"""
如遇问题，提供替代方案（如切换车站或番剧）
"""
```

---

## 8. 性能优化

### 8.1 并行执行

**ParallelAgent 使用场景:**

```python
# ✅ 好的并行: 无依赖关系
parallel_search = ParallelAgent(
    sub_agents=[
        bangumi_search_agent,    # 搜索番剧
        location_search_agent,   # 搜索车站
    ]
)

# ✅ 好的并行: 共享输入
parallel_enrichment = ParallelAgent(
    sub_agents=[
        weather_agent,           # 查天气
        route_optimization_agent,# 优化路线
    ]
)

# ❌ 不应并行: 有依赖关系
# points_search_agent 依赖 bangumi_id
```

### 8.2 缓存策略

**API 响应缓存 (TTL 1小时):**
```python
@cache_response(ttl_seconds=3600)
async def search_subject(self, keyword: str) -> List[dict]:
    ...
```

**适用场景:**
- ✅ Bangumi API 搜索
- ✅ 车站信息查询
- ✅ 圣地点位数据
- ❌ 天气信息 (实时数据)

---

## 9. 测试策略

### 9.1 测试金字塔

```
         ┌─────────────┐
         │  E2E Tests  │  (6个 - 完整工作流)
         └─────────────┘
      ┌─────────────────────┐
      │ Integration Tests   │  (集成测试)
      └─────────────────────┘
   ┌──────────────────────────────┐
   │      Unit Tests (288个)       │  (单元测试)
   └──────────────────────────────┘
```

### 9.2 ADK Agent 测试

**LlmAgent 测试:**
- 由于依赖 LLM 推理，主要通过集成测试验证
- 可以测试工具配置正确性

**BaseAgent 测试:**

```python
@pytest.mark.asyncio
async def test_points_search_agent():
    # 1. Mock dependencies
    mock_client = AsyncMock()
    mock_client.get_bangumi_points.return_value = [
        Point(id="p1", name="Test Point", coordinates=Coordinates(...))
    ]

    # 2. Create agent
    agent = PointsSearchAgent(anitabi_client=mock_client)

    # 3. Prepare context
    ctx = Mock()
    ctx.session.state = {
        "bangumi_id": 123,
        "user_coordinates": {"latitude": 35.6895, "longitude": 139.7006}
    }

    # 4. Run agent
    events = [event async for event in agent._run_async_impl(ctx)]

    # 5. Assert
    assert ctx.session.state["points"] is not None
    assert len(events) == 1
    assert events[0].author == "PointsSearchAgent"
```

---

## 10. 部署架构

### 10.1 部署目标

- **平台:** Google Agent Engine
- **模型:** Gemini 2.0 Flash
- **环境:** Python 3.13 + uv

### 10.2 环境变量

```bash
# API Keys
GEMINI_API_KEY=...
GOOGLE_MAPS_API_KEY=...

# Application Config
DEBUG=false
LOG_LEVEL=INFO
MAX_RADIUS_KM=50.0
```

### 10.3 CI/CD

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv sync
      - run: uv run pytest
```

---

## 11. 迁移历史

### 11.1 旧架构 (AbstractBaseAgent)

```
OrchestratorAgent
├─ BangumiResolverAgent (本地 LLM)
├─ SearchAgent
├─ WeatherAgent
├─ FilterAgent
├─ POIAgent
├─ RouteAgent
└─ TransportAgent
```

**问题:**
- ❌ 依赖 LLM 理解复杂 instruction
- ❌ 非确定性执行
- ❌ 自定义 agent 系统与 ADK 不兼容

### 11.2 新架构 (ADK)

```
Root Agent (LlmAgent)
└─ PilgrimageWorkflow (SequentialAgent)
   ├─ ExtractionAgent (LlmAgent)
   ├─ ParallelSearch (ParallelAgent)
   ├─ PointsSearchAgent (BaseAgent)
   ├─ ParallelEnrichment (ParallelAgent)
   └─ TransportAgent (BaseAgent)
```

**改进:**
- ✅ 确定性工作流
- ✅ ADK 原生架构
- ✅ 代码量减少 ~600 行
- ✅ 性能优化 (并行执行)

### 11.3 迁移时间线

| 阶段 | 日期 | 状态 |
|------|------|------|
| Stage 1: 设计规范 | 11-24 | ✅ 完成 |
| Stage 2: LlmAgent 实现 | 11-25 | ✅ 完成 |
| Stage 3: BaseAgent 实现 | 11-26 | ✅ 完成 |
| Stage 4: 工作流组装 | 11-27 | ✅ 完成 |
| Stage 5: Root Agent 更新 | 11-28 | ✅ 完成 |
| Stage 6: 清理旧代码 | 11-29 | ✅ 完成 |

---

## 12. 最佳实践总结

### 12.1 Do's ✅

1. **使用 SequentialAgent 编排确定性流程**
2. **用 ParallelAgent 优化无依赖步骤**
3. **LlmAgent 处理语义理解任务**
4. **BaseAgent 处理确定性业务逻辑**
5. **通过 ctx.session.state 传递数据**
6. **每个 agent 单一职责**
7. **Root Agent instruction 保持简洁 (<50行)**
8. **使用 Pydantic 保证类型安全**
9. **所有 I/O 操作异步执行**
10. **记录详细的结构化日志**

### 12.2 Don'ts ❌

1. ❌ **不要在 Root Agent 中执行业务逻辑**
2. ❌ **不要依赖 LLM 理解复杂执行顺序**
3. ❌ **不要在有依赖关系的步骤使用 ParallelAgent**
4. ❌ **不要在 LlmAgent 中编写 Python 逻辑**
5. ❌ **不要直接修改 state，使用 Event 传递**
6. ❌ **不要忽略错误处理**
7. ❌ **不要混用同步和异步代码**
8. ❌ **不要在 instruction 中重复工具文档**

---

## 13. 参考资料

- [Google ADK Documentation](https://cloud.google.com/agent-development-kit)
- [Gemini API Reference](https://ai.google.dev/gemini-api/docs)
- [Anitabi API Documentation](docs/api/anitabi.md)
- [Migration Plan](docs/archive/migration_plans/adk_bangumi_tools_refactor_plan.md) (已完成)
- [Implementation Plan](docs/archive/IMPLEMENTATION_PLAN.md) (已完成)

---

**文档维护:** 本文档应随架构演进持续更新。如有疑问，请联系项目维护者。
