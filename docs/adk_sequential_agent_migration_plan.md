# ADK SequentialAgent 完全迁移设计方案

## 目标
将整个 Seichijunrei Bot 从自定义 `AbstractBaseAgent` 体系完全迁移到 ADK 原生 agents（BaseAgent/LlmAgent/SequentialAgent），实现确定性的工作流编排。

---

## 当前架构分析

### 现有 Agents (8个 AbstractBaseAgent)
1. **BangumiResolverAgent** - 番剧名解析（使用本地 LLM）
2. **SearchAgent** - 搜索圣地点位
3. **WeatherAgent** - 获取天气信息
4. **FilterAgent** - 过滤圣地
5. **POIAgent** - POI 详情
6. **RouteAgent** - 路线优化
7. **TransportAgent** - 交通方式优化
8. **OrchestratorAgent** - 编排上述 agents

### 问题
- 依赖 LLM 理解复杂 instruction 来决定执行顺序
- 非确定性执行
- ADK 和自定义 agent 系统不兼容

---

## 目标架构（全 ADK）

### 新架构层次

```
┌────────────────────────────────────────────────────────┐
│ Root Agent (LlmAgent)                                  │
│ - 模型: gemini-2.0-flash                               │
│ - 角色: 理解用户意图，路由到合适的工作流              │
│ - Tools: pilgrimage_workflow_tool                     │
└────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ PilgrimageWorkflow (SequentialAgent)                   │
│ 确定性执行以下步骤:                                    │
│                                                        │
│  Step 1: ExtractionAgent (LlmAgent)                   │
│          提取番剧名 + 位置                              │
│          output_key: "bangumi_name", "location"       │
│          ↓                                             │
│  Step 2: ParallelGatherAgent (ParallelAgent)          │
│          ├─ BangumiSearchAgent (LlmAgent)             │
│          │  - 调用 search_bangumi_subjects            │
│          │  - output_key: "bangumi_id"                │
│          └─ LocationSearchAgent (LlmAgent)            │
│             - 调用 search_anitabi_near_station        │
│             - output_key: "user_coordinates"          │
│          ↓                                             │
│  Step 3: PointsSearchAgent (BaseAgent 自定义)         │
│          调用 Anitabi API 获取圣地点位                 │
│          input: {bangumi_id}, {user_coordinates}      │
│          output_key: "points"                         │
│          ↓                                             │
│  Step 4: ParallelEnrichment (ParallelAgent)           │
│          ├─ WeatherAgent (BaseAgent)                  │
│          │  - 获取天气                                 │
│          └─ RouteOptimizationAgent (BaseAgent)        │
│             - 优化路线顺序                             │
│          ↓                                             │
│  Step 5: TransportAgent (BaseAgent)                   │
│          优化交通方式                                   │
│          output_key: "final_plan"                     │
└────────────────────────────────────────────────────────┘
```

---

## 迁移计划（6 个阶段）

### Stage 1: 设计 ADK Agent 接口规范

**目标**: 定义统一的数据格式和通信协议

**产出文件**: `docs/adk_migration_spec.md`

**内容**:
```markdown
# State Schema 定义

所有 agents 通过 InvocationContext.session.state 共享数据

## 核心字段
- user_query: str           # 原始用户查询
- bangumi_name: str         # 提取的番剧名
- location: str             # 提取的位置
- bangumi_id: int           # Bangumi ID
- user_coordinates: dict    # {latitude, longitude}
- points: list[dict]        # 圣地点位列表
- weather: dict             # 天气信息
- route: dict               # 优化后的路线
- final_plan: dict          # 完整的朝圣计划

## Event 格式约定
所有 agent 必须 yield Event：
- author: agent.name
- content: 返回的数据（写入 state）
- actions: EventActions(escalate=True/False)
```

---

### Stage 2: 重写提取和搜索 Agents (3个 LlmAgent)

**目标**: 创建基于 LLM 的智能提取和搜索 agents

#### 2.1 ExtractionAgent (LlmAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/extraction_agent.py`

**代码结构**:
```python
from google.adk.agents import LlmAgent

extraction_agent = LlmAgent(
    name="ExtractionAgent",
    model="gemini-2.0-flash",
    instruction="""
    从用户查询中提取信息：
    1. 番剧名称（移除《》等符号）
    2. 位置/车站名称

    用户查询: {user_query}

    输出 JSON:
    {
        "bangumi_name": "...",
        "location": "..."
    }
    """,
    output_key="extraction_result"  # 写入 state
)
```

#### 2.2 BangumiSearchAgent (LlmAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/bangumi_search_agent.py`

**代码结构**:
```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

bangumi_search_agent = LlmAgent(
    name="BangumiSearchAgent",
    model="gemini-2.0-flash",
    instruction="""
    搜索番剧并选择最佳匹配。

    番剧名: {bangumi_name}

    步骤:
    1. 调用 search_bangumi_subjects(keyword="{bangumi_name}")
    2. 从结果中选择最相关的番剧
    3. 返回其 ID
    """,
    tools=[FunctionTool(search_bangumi_subjects)],
    output_key="bangumi_id"
)
```

#### 2.3 LocationSearchAgent (LlmAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/location_search_agent.py`

**代码结构**:
```python
location_search_agent = LlmAgent(
    name="LocationSearchAgent",
    model="gemini-2.0-flash",
    instruction="""
    获取车站坐标。

    车站名: {location}

    调用 search_anitabi_bangumi_near_station(station_name="{location}")
    提取返回的 station.lat 和 station.lng
    """,
    tools=[FunctionTool(search_anitabi_bangumi_near_station)],
    output_key="user_coordinates"
)
```

---

### Stage 3: 重写业务逻辑 Agents (4个 BaseAgent)

**目标**: 将现有的业务逻辑 agents 重写为 ADK BaseAgent

#### 3.1 PointsSearchAgent (BaseAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/points_search_agent.py`

**代码结构**:
```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from clients.anitabi import AnitabiClient

class PointsSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="PointsSearchAgent")
        self.anitabi_client = AnitabiClient()

    async def _run_async_impl(self, ctx):
        bangumi_id = ctx.session.state.get("bangumi_id")
        user_coords = ctx.session.state.get("user_coordinates")

        # 调用 Anitabi API
        points = await self.anitabi_client.get_bangumi_points(bangumi_id)

        # 计算距离并排序
        # ... 业务逻辑 ...

        # 写入 state
        ctx.session.state["points"] = points_data

        yield Event(
            author=self.name,
            content={"points_count": len(points)},
            actions=EventActions(escalate=True)
        )
```

#### 3.2 WeatherAgent (BaseAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/weather_agent.py`

**代码结构**:
```python
class WeatherAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        coords = ctx.session.state.get("user_coordinates")

        # 调用天气 API
        weather_data = await self._fetch_weather(coords)

        ctx.session.state["weather"] = weather_data
        yield Event(...)
```

#### 3.3 RouteOptimizationAgent (BaseAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/route_agent.py`

**代码结构**:
```python
class RouteOptimizationAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        points = ctx.session.state.get("points")
        user_coords = ctx.session.state.get("user_coordinates")

        # TSP 路线优化
        optimized_route = await self._optimize_route(points, user_coords)

        ctx.session.state["route"] = optimized_route
        yield Event(...)
```

#### 3.4 TransportAgent (BaseAgent)

**文件**: `adk_agents/seichijunrei_bot/agents/transport_agent.py`

**代码结构**:
```python
class TransportAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        route = ctx.session.state.get("route")

        # 为每段路线推荐交通方式
        route_with_transport = await self._add_transport_modes(route)

        ctx.session.state["final_plan"] = route_with_transport
        yield Event(...)
```

---

### Stage 4: 组装 SequentialAgent 工作流

**目标**: 用 SequentialAgent/ParallelAgent 编排确定性工作流

**文件**: `adk_agents/seichijunrei_bot/workflows/pilgrimage_workflow.py`

**代码结构**:
```python
from google.adk.agents import SequentialAgent, ParallelAgent

# 步骤 2: 并行搜索
parallel_search = ParallelAgent(
    name="ParallelSearch",
    sub_agents=[
        bangumi_search_agent,      # 搜索番剧 ID
        location_search_agent,     # 搜索车站坐标
    ]
)

# 步骤 4: 并行增强
parallel_enrichment = ParallelAgent(
    name="ParallelEnrichment",
    sub_agents=[
        weather_agent,             # 获取天气
        route_optimization_agent,  # 优化路线
    ]
)

# 主工作流
pilgrimage_workflow = SequentialAgent(
    name="PilgrimageWorkflow",
    description="完整的圣地巡礼规划工作流",
    sub_agents=[
        extraction_agent,          # 步骤 1: 提取信息
        parallel_search,           # 步骤 2: 并行搜索（番剧+位置）
        points_search_agent,       # 步骤 3: 获取圣地点位
        parallel_enrichment,       # 步骤 4: 并行增强（天气+路线）
        transport_agent,           # 步骤 5: 优化交通
    ]
)
```

---

### Stage 5: 更新 Root Agent

**文件**: `adk_agents/seichijunrei_bot/agent.py`

**修改内容**:

#### 5.1 导入新依赖
```python
from google.adk import Agent
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool, agent_tool

from workflows.pilgrimage_workflow import pilgrimage_workflow
```

#### 5.2 包装工作流为工具
```python
# 将 SequentialAgent 转为可调用的工具
pilgrimage_workflow_tool = agent_tool.AgentTool(
    agent=pilgrimage_workflow,
    name="plan_pilgrimage",
    description="""
    规划完整的圣地巡礼路线。

    输入: user_query (用户的自然语言查询)
    输出: 完整的圣地巡礼计划

    示例:
    - "我在新宿 想圣地巡礼你的名字"
    - "秋叶原站附近有什么动漫圣地"
    """
)
```

#### 5.3 简化 Root Agent Instruction
```python
root_agent = Agent(
    name="seichijunrei_bot",
    model="gemini-2.0-flash",
    description="圣地巡礼规划助手",
    instruction="""
    你是 Seichijunrei Bot，专门帮助用户规划动漫圣地巡礼。

    当用户询问圣地巡礼时：
    1. 直接调用 plan_pilgrimage(user_query="用户完整查询")
    2. 该工具会自动处理所有步骤（提取、搜索、规划）
    3. 将结果友好地呈现给用户

    保持热情、专业，使用中日混合语言风格。
    """,
    tools=[
        pilgrimage_workflow_tool,  # 主工作流
        generate_map_tool,         # 辅助工具
        generate_pdf_tool,         # 辅助工具
    ]
)
```

---

### Stage 6: 清理旧代码

**目标**: 移除不再使用的 AbstractBaseAgent 系统

#### 6.1 删除文件 (7个)
```
agents/base.py                    # 旧的 AbstractBaseAgent
agents/orchestrator_agent.py      # 被 SequentialAgent 替代
agents/bangumi_resolver_agent.py  # 被 LlmAgent 替代
agents/search_agent.py            # 被新 BaseAgent 替代
agents/weather_agent.py           # 被新 BaseAgent 替代
agents/route_agent.py             # 被新 BaseAgent 替代
agents/transport_agent.py         # 被新 BaseAgent 替代
```

#### 6.2 删除旧测试 (7个)
```
tests/unit/test_base_agent.py
tests/unit/test_orchestrator_agent.py
tests/unit/test_search_agent.py
tests/unit/test_weather_agent.py
tests/unit/test_route_agent.py
tests/unit/test_transport_agent.py
```

#### 6.3 删除旧入口 (2个函数)
```python
# adk_agents/seichijunrei_bot/agent.py 中删除
- async def plan_pilgrimage(...)
- async def plan_pilgrimage_with_bangumi(...)
```

---

## 文件结构对比

### 迁移前
```
adk_agents/seichijunrei_bot/
  ├─ agent.py                    (626 行，复杂 instruction)
  └─ __init__.py

agents/
  ├─ base.py                     (250 行)
  ├─ orchestrator_agent.py       (432 行)
  ├─ bangumi_resolver_agent.py   (514 行)
  ├─ search_agent.py
  ├─ weather_agent.py
  ├─ route_agent.py
  └─ transport_agent.py
```

### 迁移后
```
adk_agents/seichijunrei_bot/
  ├─ agent.py                    (150 行，简化)
  ├─ __init__.py
  ├─ agents/
  │   ├─ extraction_agent.py     (LlmAgent, 80 行)
  │   ├─ bangumi_search_agent.py (LlmAgent, 100 行)
  │   ├─ location_search_agent.py(LlmAgent, 90 行)
  │   ├─ points_search_agent.py  (BaseAgent, 120 行)
  │   ├─ weather_agent.py        (BaseAgent, 80 行)
  │   ├─ route_agent.py          (BaseAgent, 150 行)
  │   └─ transport_agent.py      (BaseAgent, 100 行)
  └─ workflows/
      └─ pilgrimage_workflow.py  (SequentialAgent 组装, 100 行)

agents/  (删除整个目录)
```

---

## 关键优势

### 1. 确定性执行 ✅
- SequentialAgent 保证步骤顺序
- 不依赖 LLM 理解 instruction

### 2. 架构统一 ✅
- 全部使用 ADK 原生 agents
- 无需 adapter 桥接

### 3. 并行优化 ✅
- 番剧搜索 + 位置搜索 并行
- 天气获取 + 路线优化 并行

### 4. 易于调试 ✅
- 每个 agent 职责单一
- State 变化清晰可追踪

### 5. 代码量减少 ✅
- 删除 ~1500 行旧代码
- 新增 ~900 行 ADK 代码
- **净减少 600 行**

---

## 迁移时间估算

| 阶段 | 任务 | 预估时间 |
|------|------|---------|
| Stage 1 | 设计规范文档 | 2 小时 |
| Stage 2 | 3 个 LlmAgent | 4 小时 |
| Stage 3 | 4 个 BaseAgent | 8 小时 |
| Stage 4 | 组装工作流 | 3 小时 |
| Stage 5 | 更新 Root Agent | 2 小时 |
| Stage 6 | 清理旧代码 | 2 小时 |
| **总计** | | **21 小时** (~3 工作日) |

---

## 风险与缓解

### ⚠️ 风险 1: 大规模重构，可能引入 bug
**缓解**:
- 先保留旧代码，新旧并行运行
- 对比测试结果一致后再删除
- 使用 evalset 验证

### ⚠️ 风险 2: ADK 学习曲线
**缓解**:
- 详细注释每个 agent
- 参考官方文档示例
- 先实现 MVP，逐步完善

### ⚠️ 风险 3: 性能下降（多层 agent 调用）
**缓解**:
- 使用 ParallelAgent 并行执行
- 监控性能指标
- 必要时优化热点路径

---

## 成功标准

- ✅ "我在新宿 想圣地巡礼你的名字" 成功执行
- ✅ 所有 evalset 测试用例通过
- ✅ 代码行数减少 > 30%
- ✅ Instruction 减少至 50 行以内
- ✅ 完全移除 AbstractBaseAgent 依赖
