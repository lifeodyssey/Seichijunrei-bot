# ADK + Tools 重构计划（Bangumi 模式）

> 目标：把番剧解析（Bangumi）和圣地数据（Anitabi）相关逻辑，从本地 `google.generativeai` 调用迁移到 **ADK LLM + FunctionTool**，Python 代码只保留 HTTP 客户端和业务计算。

---

## 0. 总体目标与范围

**目标**

- 所有「理解用户 query / 解析番剧名 / 抽地点」的 LLM 推理逻辑，都在 ADK 的 `root_agent` 中完成。
- Python 代码只做：
  - Bangumi API / Anitabi API / Google Maps / Weather 的调用；
  - Filter / POI / Route / Transport 等纯业务逻辑；
  - `PilgrimageSession` 结构化数据组装。
- 在 ADK 模式下：
  - 不再直接 import / 调用 `google.generativeai`；
  - 通过 ADK 的 `FunctionTool` 暴露 Bangumi / Anitabi / Orchestrator 能力。

**范围（本计划只改造 Bangumi 模式）**

- 涉及模块：
  - `clients/bangumi.py`
  - `clients/anitabi.py`
  - `agents/search_agent.py`
  - `agents/orchestrator_agent.py`
  - `agents/bangumi_resolver_agent.py`（逐步下线）
  - `utils/llm.py`（逐步下线）
  - `adk_agents/seichijunrei_bot/agent.py`
- 不动（暂时）：
  - `FilterAgent / POIAgent / RouteAgent / TransportAgent / WeatherAgent`
  - `clients/google_maps.py` 等 HTTP 客户端实现

---

## 1. Step 0：确认现状

1.1 LLM 使用点

- `agents/bangumi_resolver_agent.py`
  - `_extract_bangumi_name`：直接通过 `google.generativeai.GenerativeModel.generate_content`
  - `_select_best_match`：同样直接调用 `generate_content`
- `utils/llm.py`
  - `GeminiClient.generate()`：封装 `google.generativeai`，被其他 Agent 使用
- `agents/search_agent.py`
  - 通过 `get_llm_client()` 获取 `GeminiClient`
  - `_extract_location()` 中用 LLM 从 `user_query` 抽 `location`

1.2 外部 HTTP 客户端

- `clients/bangumi.py`：Bangumi API
- `clients/anitabi.py`：Anitabi API
- `clients/google_maps.py`、`clients/weather.py` 等

1.3 顶层编排

- `agents/orchestrator_agent.py`
  - 新 Bangumi 模式：`user_query → BangumiResolverAgent → SearchAgent(bangumi_mode) → Weather/Route/Transport`
  - 旧 Station 模式：`station_name → SearchAgent(station_mode) → Filter → POI → Route → Transport`
- `adk_agents/seichijunrei_bot/agent.py`
  - 暴露 `plan_pilgrimage / generate_map / generate_pdf` 三个工具
  - 定义 `root_agent = Agent(..., tools=[...])`，目前未暴露 Bangumi / Anitabi 工具

---

## 2. Step 1：在 ADK 层暴露 Bangumi Tools（不改现有逻辑）

**目标**：先让 ADK LLM 能直接调 Bangumi API 工具，暂时不改 Orchestrator 和 BangumiResolverAgent。

1. 在 `adk_agents/seichijunrei_bot/agent.py` 顶部引入 BangumiClient：

   ```python
   from clients.bangumi import BangumiClient

   _bangumi_client = BangumiClient()
   ```

2. 新增工具函数：

   - `async def search_bangumi_subjects(keyword: str) -> dict`
     - 内部调用 `_bangumi_client.search_subject(keyword, subject_type=BangumiClient.TYPE_ANIME)`
     - 返回 `{ "keyword": keyword, "results": results }`
   - `async def get_bangumi_subject(subject_id: int) -> dict`
     - 内部 `_bangumi_client.get_subject(subject_id)`

3. 使用 `FunctionTool` 包成 ADK 工具：

   ```python
   from google.adk.tools import FunctionTool

   search_bangumi_tool = FunctionTool(search_bangumi_subjects)
   get_bangumi_tool = FunctionTool(get_bangumi_subject)
   ```

4. 将两个工具加入 `root_agent` 的 `tools` 列表（保留已有 tools）：

   ```python
   root_agent = Agent(
       ...,
       tools=[
           plan_pilgrimage_tool,
           generate_map_tool,
           generate_pdf_tool,
           search_bangumi_tool,
           get_bangumi_tool,
       ]
   )
   ```

5. 验证 ADK 能正常启动（`make web` / `uv run adk web ...`）。

---

## 3. Step 2：在 ADK 层暴露 Anitabi Tools

**目标**：让 ADK LLM 能直接通过工具拿到圣地点位和附近番剧列表。

1. 在 `adk_agents/seichijunrei_bot/agent.py` 引入 AnitabiClient：

   ```python
   from clients.anitabi import AnitabiClient

   _anitabi_client = AnitabiClient()
   ```

2. 新增工具函数 1：按番剧 ID 获取圣地：

   ```python
   async def get_anitabi_points(bangumi_id: str) -> dict:
       points = await _anitabi_client.get_bangumi_points(bangumi_id)
       return {
           "bangumi_id": bangumi_id,
           "points": [
               {
                   "id": p.id,
                   "name": p.name,
                   "cn_name": p.cn_name,
                   "lat": p.coordinates.latitude,
                   "lng": p.coordinates.longitude,
                   "episode": p.episode,
                   "time_seconds": p.time_seconds,
                   "screenshot_url": p.screenshot_url,
                   "address": p.address,
               }
               for p in points
           ],
       }
   ```

3. 新增工具函数 2：按车站名搜索附近番剧：

   ```python
   async def search_anitabi_bangumi_near_station(
       station_name: str,
       radius_km: float = 5.0,
   ) -> dict:
       station = await _anitabi_client.get_station_info(station_name)
       bangumi_list = await _anitabi_client.search_bangumi(station, radius_km=radius_km)
       return {
           "station": {
               "name": station.name,
               "lat": station.coordinates.latitude,
               "lng": station.coordinates.longitude,
               "city": station.city,
               "prefecture": station.prefecture,
           },
           "bangumi_list": [
               {
                   "id": b.id,
                   "title": b.title,
                   "cn_title": b.cn_title,
                   "cover_url": b.cover_url,
                   "points_count": b.points_count,
                   "distance_km": b.distance_km,
               }
               for b in bangumi_list
           ],
           "radius_km": radius_km,
       }
   ```

4. 包成工具并加入 `root_agent.tools`：

   ```python
   get_anitabi_points_tool = FunctionTool(get_anitabi_points)
   search_anitabi_bangumi_tool = FunctionTool(search_anitabi_bangumi_near_station)

   root_agent = Agent(
       ...,
       tools=[
           plan_pilgrimage_tool,
           generate_map_tool,
           generate_pdf_tool,
           search_bangumi_tool,
           get_bangumi_tool,
           get_anitabi_points_tool,
           search_anitabi_bangumi_tool,
       ]
   )
   ```

---

## 4. Step 3：扩展 ADK Instruction，让 LLM 知道如何用这些 Tools

**目标**：在 `root_agent` 的 `instruction` 里描述新的调用策略，但暂时仍保留老的 `plan_pilgrimage` 流程。

1. 在 instruction 中增加规则（用自然语言写）：

   - 当用户提到某个番剧的圣地（示例：“我在新宿站想去《你的名字》的圣地”）：
     - 从用户话语中理解番剧名称；
     - 调用 `search_bangumi_subjects(keyword=番剧名)`；
     - 根据返回 `results` 中的 `name` / `name_cn` 以及上下文，在对话中选择一个最合适的 `id`；
   - 一旦选定 `bangumi_id`，用户确实想去这个番剧的圣地：
     - 调用 `get_anitabi_points(bangumi_id=...)`；
     - 用返回的 `points` 回复用户，或作为后续规划路线的输入；
   - 当用户给出出发车站（Station 模式）：
     - 调用 `search_anitabi_bangumi_near_station(station_name=...)`；
     - 展示返回的 `bangumi_list`，和用户确认要哪一部 / 哪几部。

2. 此阶段只增强 ADK 端语义能力，不改 Python Orchestrator 行为。

---

## 5. Step 4：新增 plan_pilgrimage_with_bangumi 工具（绕开 BangumiResolverAgent）

**目标**：在 ADK 已经选好了 `bangumi_id` 时，走一个“直连 Orchestrator / SearchAgent”的工具，而不是再走 Python 端的 LLM。

1. 在 `adk_agents/seichijunrei_bot/agent.py` 新增函数：

   ```python
   async def plan_pilgrimage_with_bangumi(
       bangumi_id: int,
       user_query: Optional[str] = None,
       session_id: Optional[str] = None,
   ) -> dict:
       # 1. 生成 session_id（如为空）
       # 2. 构造 AgentInput：data={"bangumi_id": bangumi_id, "user_query": user_query or ""}
       # 3. 直接走 Orchestrator / SearchAgent 的 bangumi 模式
       #    （可以抽出一个内部函数来复用现有 orchestration 逻辑）
       # 4. 返回 session / success / steps_completed / errors 等结构
   ```

   *具体内部可以复用 `OrchestratorAgent._execute_bangumi_mode` 中已有的 Route/Transport/Weather 流程，只是在入口绕过 `BangumiResolverAgent`。*

2. 将其包成工具并加入 `root_agent.tools`：

   ```python
   plan_pilgrimage_with_bangumi_tool = FunctionTool(plan_pilgrimage_with_bangumi)
   ```

3. 在 instruction 里补充说明：

   - 当你已经通过 `search_bangumi_subjects` + 对话选定了一个 `bangumi_id`：
     - 优先调用 `plan_pilgrimage_with_bangumi` 来规划完整巡礼；
     - 不再调用只带 `user_query` 的 `plan_pilgrimage`。

---

## 6. Step 5：SearchAgent 和 Orchestrator 支持“跳过本地 LLM”的输入模式

**目标**：让后端 Agent 不再必须依赖本地 LLM（`utils.llm`），可以直接用 ADK 提供的结构化信息。

1. SearchAgent：增强 Bangumi 模式输入

   - 当前：Bangumi 模式要求 `bangumi_id + user_query`，内部通过 `_extract_location(user_query)` 抽地理位置。
   - 修改 `_execute_bangumi_mode` 输入约定：
     - 新增可选字段 `user_coordinates: dict`：
       - 若存在，直接用 `Coordinates(**user_coordinates)`，绕过 `_extract_location`；
       - 若不存在，仍按旧逻辑调用 `_extract_location(user_query)` 作为回退。
   - 这样 ADK 可以：
     - 先在对话中问清用户出发位置；
     - 用自身能力（或自建 Tool）把它变成坐标；
     - 调 `plan_pilgrimage_with_bangumi(bangumi_id, user_query?, user_coordinates=...)`。

2. OrchestratorAgent：支持“上游已解析好番剧”的路径

   - 在 `_execute_bangumi_mode` 中：
     - 判断 `input_data.data` 中是否已经有 `bangumi_id`：
       - 如果有：跳过 `_execute_bangumi_resolver`，直接调用 `SearchAgent` 的 Bangumi 模式；
       - 如果没有：保持原逻辑，使用 `BangumiResolverAgent`。
   - 这允许：
     - ADK 模式：通过新 Tool 传入 `bangumi_id`，绕开本地 LLM；
     - 旧 CLI 模式：仍可以用 `BangumiResolverAgent` 本地解析番剧名。

3. 将 `_extract_location` 标记为 legacy 路径

   - 在后续文档和 instruction 中推荐：
     - 尽量让 ADK 在调用时提供 `user_coordinates`；
     - `_extract_location` 只作为没有坐标信息时的后备方案。

---

## 7. Step 6：移除 google.generativeai 依赖（最后收尾）

**前提**：ADK 工具链已稳定，所有入口在 ADK 模式下都不再需要本地 LLM。

1. 删除 / 重构以下引用：

   - `agents/bangumi_resolver_agent.py` 中的 `import google.generativeai as genai`
   - `utils/llm.py` 中的所有 `google.generativeai` 使用

2. 依赖管理：

   - 从 `pyproject.toml` / `requirements.txt` 中移除 `google-generativeai`；
   - 确保 `uv sync` / `pip install` 时不再安装该包。

3. 文档更新：

   - 在 `LOCAL_SETUP.md` / `README.md` 中说明：
     - 本地 Python 代码不再需要 `GEMINI_API_KEY`；
     - LLM 推理统一通过 ADK 的 Agent 完成。

4. 视情况处理 `BangumiResolverAgent`：

   - 若 ADK 模式完全替代，可以：
     - 标记为 deprecated，或者直接删除；
   - 若仍用于某些纯 Python 场景，则：
     - 保留其“调用 BangumiClient + 业务逻辑”部分；
     - 移除所有 LLM 相关逻辑，使其成为一个纯 API 适配层。

---

## 8. Step 7：测试与迭代

1. 单元测试

   - 为新加的 ADK 工具编写单元测试：
     - 对 `search_bangumi_subjects` / `get_anitabi_points` 等函数：
       - 使用 mock 的 `BangumiClient` / `AnitabiClient`；
       - 验证返回结构、字段名、错误处理。

2. 集成测试（如环境允许跑 ADK）

   - 场景示例：
     - 输入：“我在新宿站，想去《你的名字》的圣地”；
     - 期望 LLM 调用顺序：
       - `search_bangumi_subjects` → 选择正确 `bangumi_id`；
       - `get_anitabi_points` → 获得 points；
       - `plan_pilgrimage_with_bangumi` → 获取完整路线；
     - 最终返回包含 `session` / `route` / `points` 的结构。

3. 渐进下线旧逻辑

   - 当 ADK 工作流经过多轮验证后：
     - 考虑完全移除 `BangumiResolverAgent` 和 `_extract_location` 中的 LLM 逻辑；
     - 保留必要的纯业务功能与兼容路径。

---

