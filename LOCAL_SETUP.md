# Seichijunrei Bot - 本地启动手册

> 快速上手指南 - 在本地环境启动和测试 Seichijunrei Bot

---

## 📋 目录

- [必需的 API Keys](#必需的-api-keys)
- [配置步骤](#配置步骤)
- [本地启动方法](#本地启动方法)
- [测试和验证](#测试和验证)
- [API Key 获取指南](#api-key-获取指南)
- [故障排查](#故障排查)

---

## 🔑 必需的 API Keys

### 核心功能必需

| API Key | 用途 | 是否必需 | 说明 |
|---------|------|---------|------|
| `GOOGLE_MAPS_API_KEY` | 地理和路线服务 | ✅ **必需** | 用于地理编码、距离计算、交通建议 |
| `WEATHER_API_KEY` | 天气查询服务 | ⚠️ 可选 | 开发环境可以不提供 |

> 说明：原先本地 Python 代码会直接调用 Gemini (`google.generativeai`) 进行 LLM 推理，需要 `GEMINI_API_KEY`。
> 现在所有 LLM 推理逻辑都迁移到了 ADK / Agent Engine 侧，Python 仅负责 HTTP 客户端和业务逻辑，
> 因此本地运行不再需要 `GEMINI_API_KEY`。

### API Key 依赖说明

#### 1. GOOGLE_MAPS_API_KEY（必需）
- **影响范围**:
  - SearchAgent - 地铁站名 → GPS 坐标转换
  - RouteAgent - 计算圣地之间的实际距离
  - TransportAgent - 查询步行/地铁/公交建议
  - POIAgent - 查询圣地营业时间（可选）
- **无法绕过**: 核心路线规划功能依赖此 API
- **来源**: [Google Cloud Console](https://console.cloud.google.com/)
- **费用**: 每月 $200 免费额度，开发测试完全够用

#### 2. WEATHER_API_KEY（可选）
- **影响范围**: WeatherAgent - 查询天气和出行建议
- **可以跳过**: 系统会优雅处理，只是 PDF 中没有天气信息
- **执行方式**: 并行异步执行，失败不影响主流程
- **来源**: [OpenWeatherMap](https://openweathermap.org/api)
- **代码位置**: `agents/orchestrator_agent.py:163-169`

```python
# 天气查询失败的容错处理
try:
    weather_result = await weather_task
    session.weather = Weather(**weather_result["weather"])
except Exception as e:
    self.logger.warning("WeatherAgent failed, continuing without weather data")
    session.weather = None  # 不影响其他功能
```

---

## ⚙️ 配置步骤

### 第一步：创建环境配置文件

```bash
# 在项目根目录执行
cd /Users/zhenjiazhou/Documents/Seichijunrei
cp .env.example .env
```

### 第二步：编辑 `.env` 文件

使用任意文本编辑器打开 `.env` 文件：

```bash
# 推荐使用 VSCode
code .env

# 或使用系统默认编辑器
open .env
```

### 第三步：填写 API Keys

**最小配置（仅核心功能）**:
```env
# 必需 - 地理和路线服务
GOOGLE_MAPS_API_KEY=AIzaSy...你的实际key

# 可选配置保持默认即可
ANITABI_API_URL=https://api.anitabi.cn/bangumi
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
```

**完整配置（包含天气功能）**:
```env
# 必需
GOOGLE_MAPS_API_KEY=AIzaSy...你的实际key

# 可选 - 天气服务
WEATHER_API_KEY=你的_OpenWeatherMap_Key
WEATHER_API_URL=https://api.openweathermap.org/data/2.5

# 其他配置
ANITABI_API_URL=https://api.anitabi.cn/bangumi
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false
MAX_RETRIES=3
TIMEOUT_SECONDS=30
CACHE_TTL_SECONDS=3600
USE_CACHE=true
OUTPUT_DIR=outputs
TEMPLATE_DIR=templates
```

### 第四步：验证配置

运行配置验证脚本：

```bash
# 方法 1: 使用 Python 直接验证
uv run python -c "from config.settings import get_settings; s = get_settings(); print('Missing keys:', s.validate_api_keys())"

# 方法 2: 运行健康检查
make health
```

**预期输出**:
```
Missing keys: []  # 空列表表示所有必需的 key 都已配置

# 或者健康检查输出
Startup Check Result: OK
  ✅ agents: healthy
  ✅ tools: healthy
  ✅ domain: healthy
```

---

## 🚀 本地启动方法

### 方法 1: ADK Web 界面（推荐）⭐

启动带有聊天 UI 的 Web 界面：

```bash
# 第一次运行需要安装依赖
make dev

# 启动 ADK Web 界面
make web
```

或使用完整命令：
```bash
uv run adk web agent.py
```

**启动后**:
1. 终端会显示访问地址，通常是 `http://localhost:8000`
2. 在浏览器中打开该地址
3. 你会看到类似 ChatGPT 的聊天界面
4. 直接输入消息开始对话

**示例对话**:
```
用户: 我在新宿站，想去看新海诚作品的圣地
Bot: 好的！让我帮你规划一条圣地巡礼路线。首先搜索新宿站周边的圣地...
     [系统自动调用 plan_pilgrimage_workflow 工作流]

     找到了以下番剧的圣地：
     - 你的名字 (15个圣地)
     - 天气之子 (12个圣地)
     - 言叶之庭 (8个圣地)

     你看过这些番剧吗？想去哪些圣地？
```

### 方法 2: 命令行界面

启动终端交互界面：

```bash
make run
```

或使用完整命令：
```bash
uv run adk run agent.py
```

这会在终端中启动一个交互式 CLI，你可以直接输入消息。

### 方法 3: （推荐）继续使用 ADK Agent 接口

当前版本已经不再提供直接的 `plan_pilgrimage` Python 函数入口，
而是通过 ADK 的 `seichijunrei_bot` Agent 和 `plan_pilgrimage_workflow`
工作流来完成整条圣地巡礼规划。

如果需要在代码中集成，请优先参考 ADK 官方文档，使用
HTTP / gRPC 或 ADK SDK 调用 Agent；本仓库推荐的本地开发和测试方式
仍然是：

- Web 界面：`uv run adk web agent.py`
- 终端 CLI：`uv run adk run agent.py`

通过这两种方式可以完整覆盖规划、地图和 PDF 生成的能力，而不会依赖已删除的旧接口。

---

## 🧪 测试和验证

### 1. 运行健康检查

验证所有组件是否正常：

```bash
make health
```

**预期输出**:
```
Startup Check Result: OK
  ✅ agents: healthy
  ✅ tools: healthy
  ✅ domain: healthy
```

### 2. 运行单元测试

测试各个模块的功能：

```bash
# 运行所有单元测试
make test

# 查看测试覆盖率
make test-cov
```

### 3. 测试基本功能

启动 ADK Web 界面后，尝试以下对话：

**测试 1: 基本搜索**
```
用户: 帮我找新宿站附近的动漫圣地
预期: 系统应该返回番剧列表
```

**测试 2: 路线规划**
```
用户: 我在秋叶原站，想去看凉宫春日的圣地，帮我规划路线
预期: 系统应该生成完整的巡礼路线
```

**测试 3: 地图生成**
```
用户: 帮我生成地图
预期: 系统应该生成 HTML 地图并返回路径
```

### 4. 检查输出文件

生成的文件会保存在 `outputs/` 目录：

```bash
# 查看生成的地图
ls outputs/maps/

# 查看生成的 PDF
ls outputs/pdfs/
```

---

## 🔧 API Key 获取指南

### 1. Gemini API Key（必需）

**步骤**:
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用 Google 账号登录
3. 点击 "Create API Key" 按钮
4. 选择一个 Google Cloud 项目（或创建新项目）
5. 复制生成的 API Key

**费用**:
- 免费版本有每日调用限制
- Gemini 1.5 Flash: 每天 1500 次请求
- Gemini 1.5 Pro: 每天 50 次请求

**限制**:
- 开发测试完全够用
- 如需更高额度可升级到付费版

---

### 2. Google Maps API Key（必需）

**步骤**:

#### Step 1: 创建 Google Cloud 项目
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 点击顶部的项目选择器
3. 点击 "New Project"
4. 输入项目名称（如 "Seichijunrei-Dev"）
5. 点击 "Create"

#### Step 2: 启用必需的 APIs
1. 在左侧菜单选择 "APIs & Services" > "Library"
2. 搜索并启用以下 APIs:
   - **Geocoding API** (必需) - 地址 → GPS 坐标
   - **Directions API** (必需) - 路线规划
   - **Places API** (可选) - 营业时间查询

#### Step 3: 创建 API Key
1. 进入 "APIs & Services" > "Credentials"
2. 点击 "Create Credentials" > "API Key"
3. 复制生成的 API Key

#### Step 4: 限制 API Key（推荐，提高安全性）
1. 在 Credentials 页面点击刚创建的 API Key
2. 设置 "Application restrictions":
   - 选择 "IP addresses"
   - 添加你的本地 IP 和服务器 IP
3. 设置 "API restrictions":
   - 选择 "Restrict key"
   - 只勾选你启用的 APIs
4. 点击 "Save"

**费用和免费额度**:
- 每月 $200 免费额度
- Geocoding API: 0.005美元/次，免费额度内可用 40,000 次/月
- Directions API: 0.005美元/次，免费额度内可用 40,000 次/月
- Places API: 0.017美元/次，免费额度内可用 11,000 次/月

**开发测试估算**:
- 每次完整测试约消耗: 10-20 次 API 调用
- 每月 200 美元额度 = 每月约 10,000 次完整测试
- **完全够用，不会产生费用**

**注意事项**:
- 需要绑定信用卡才能激活免费额度
- 不会自动扣费，除非主动升级到付费计划
- 可以设置预算提醒和限额

---

### 3. OpenWeatherMap API Key（可选）

**步骤**:
1. 访问 [OpenWeatherMap](https://openweathermap.org/api)
2. 点击 "Sign Up" 创建账号
3. 验证邮箱
4. 进入 [API Keys 页面](https://home.openweathermap.org/api_keys)
5. 复制默认的 API Key（或创建新的）

**费用**:
- 免费版本: 每分钟 60 次调用，每天 1,000,000 次
- 开发测试完全够用

**注意**:
- 新创建的 API Key 可能需要 10-120 分钟激活
- 如果立即使用可能返回 401 错误

---

## 🔍 故障排查

### 问题 1: "No module named 'uv'"

**原因**: 没有安装 `uv` 包管理器

**解决方案**:
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 验证安装
uv --version
```

---

### 问题 2: "Missing API keys: GEMINI_API_KEY"

**原因**: `.env` 文件中缺少必需的 API Key

**解决方案**:
1. 确认 `.env` 文件存在于项目根目录
2. 确认已填写 `GEMINI_API_KEY=你的实际key`
3. 确认 key 前后没有多余的空格或引号
4. 重启应用

**验证配置**:
```bash
# 检查 .env 文件是否存在
ls -la .env

# 查看配置（不会显示实际 key 值）
uv run python -c "from config.settings import get_settings; print(get_settings().validate_api_keys())"
```

---

### 问题 3: "Weather API key not provided - using limited mode"

**这不是错误**！

**说明**:
- 这只是一个警告，不是错误
- 系统会继续运行，只是没有天气信息
- 如果不需要天气功能，可以忽略

**如果想添加天气功能**:
1. 获取 OpenWeatherMap API Key（参见上方指南）
2. 在 `.env` 中添加 `WEATHER_API_KEY=你的key`
3. 重启应用

---

### 问题 4: ADK Web 界面无法访问

**可能原因**:
- 端口被占用
- 防火墙阻止
- 启动失败

**解决方案**:

**检查端口占用**:
```bash
# 检查 8000 端口是否被占用
lsof -i :8000

# 如果被占用，杀死进程或更换端口
uv run adk web agent.py --port 8080
```

**查看详细日志**:
```bash
# 启动时查看详细输出
LOG_LEVEL=DEBUG make web
```

**检查防火墙**:
```bash
# macOS - 允许应用访问网络
系统偏好设置 > 安全性与隐私 > 防火墙 > 防火墙选项
```

---

### 问题 5: "playwright install chromium" 失败

**原因**: PDF 生成需要 Chromium 浏览器

**解决方案**:
```bash
# 手动安装 playwright 浏览器
uv run playwright install chromium

# 如果网络问题，设置国内镜像
export PLAYWRIGHT_DOWNLOAD_HOST=https://playwright.azureedge.net
uv run playwright install chromium
```

**如果仍然失败，临时跳过 PDF 功能**:
- PDF 生成不影响核心路线规划功能
- 可以先测试其他功能，后续再解决

---

### 问题 6: Google Maps API 返回 "REQUEST_DENIED"

**可能原因**:
1. API Key 无效或未激活
2. 没有启用必需的 APIs
3. API Key 有 IP/域名限制
4. 超出免费额度

**解决方案**:

**1. 验证 API Key**:
```bash
# 测试 Geocoding API
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Tokyo&key=你的API_KEY"

# 应该返回 JSON 数据，而不是错误
```

**2. 检查 API 是否启用**:
- 访问 [Google Cloud Console](https://console.cloud.google.com/)
- APIs & Services > Dashboard
- 确认已启用 Geocoding API 和 Directions API

**3. 移除 API 限制（仅用于本地测试）**:
- APIs & Services > Credentials
- 编辑你的 API Key
- Application restrictions: 选择 "None"
- API restrictions: 选择 "Don't restrict key"
- 保存

**4. 检查配额使用情况**:
- APIs & Services > Dashboard
- 点击对应的 API
- 查看 "Quotas" 标签页

---

### 问题 7: 找不到番剧数据

**可能原因**:
- Anitabi API 不稳定
- 搜索位置没有圣地
- 网络连接问题

**解决方案**:

**1. 测试 Anitabi API**:
```bash
# 直接测试 API
curl "https://api.anitabi.cn/bangumi/list?page=1&limit=10"

# 应该返回番剧列表
```

**2. 尝试知名圣地**:
- 新宿站（你的名字、天气之子）
- 秋叉原站（命运石之门）
- 京都站（冰菓、吹响吧上低音号）

**3. 检查搜索半径**:
- 默认搜索半径: 5km
- 可以在代码中调整: `config/settings.py`

---

### 问题 8: 测试全部失败

**可能原因**:
- 缺少测试依赖
- API Keys 配置问题
- 数据库/缓存问题

**解决方案**:

**1. 重新安装依赖**:
```bash
# 清理缓存
make clean

# 重新安装开发依赖
make dev
```

**2. 只运行不依赖 API 的测试**:
```bash
# 运行单元测试（使用 mock 数据）
uv run pytest tests/unit/ -v -m "not integration"
```

**3. 跳过集成测试**:
```bash
# 集成测试需要真实 API Keys
uv run pytest tests/unit/ -v --ignore=tests/integration/
```

---

## 📚 其他资源

### 项目文档
- [README.md](./README.md) - 项目概述和功能介绍
- [SPEC.md](./SPEC.md) - 详细技术规格
- [CLAUDE.md](./CLAUDE.md) - 开发指南和最佳实践
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - 实现计划和进度

### 相关链接
- [Google ADK 文档](https://cloud.google.com/vertex-ai/docs/agent-builder)
- [Gemini API 文档](https://ai.google.dev/docs)
- [Google Maps Platform 文档](https://developers.google.com/maps/documentation)
- [Anitabi API 文档](https://github.com/anitabi/anitabi.cn-document/blob/main/api.md)

### 获取帮助
- 提交 Issue: [GitHub Issues](https://github.com/your-repo/issues)
- 查看日志: `logs/` 目录
- 健康检查: `make health`

---

## ✅ 快速启动检查清单

在开始之前，确认以下项目已完成：

- [ ] 已安装 `uv` 包管理器
- [ ] 已获取 `GOOGLE_MAPS_API_KEY` 和启用必需的 APIs:
  - ⚠️ **必需**: Geocoding API
  - ⚠️ **必需**: Directions API (用于路线优化)
  - 📝 可选: Places API (用于营业时间查询)
- [ ] 已创建 `.env` 文件并填写 API Keys
- [ ] 已运行 `make dev` 安装依赖
- [ ] 已运行 `make health` 验证配置
- [ ] 已运行 `make web` 启动 Web 界面
- [ ] 在浏览器中成功访问 `http://localhost:8000`

**全部完成？恭喜！你可以开始使用 Seichijunrei Bot 了！** 🎉

---

**最后更新**: 2025-11-26
**维护者**: Zhenjia Zhou
