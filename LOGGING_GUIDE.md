# 日志系统使用指南 (Logging Guide)

## 概述

本项目使用增强的结构化日志系统，基于 `structlog` 和 `rich`，提供清晰、详细的日志输出，便于调试和问题定位。

## 快速开始

### 1. 配置日志级别

编辑 `.env` 文件，设置日志级别：

```bash
# 开发环境：显示所有详细日志
LOG_LEVEL=DEBUG
DEBUG=true

# 生产环境：只显示重要信息
LOG_LEVEL=INFO
DEBUG=false
```

### 2. 日志级别说明

| 级别 | 用途 | 显示内容 |
|------|------|----------|
| **DEBUG** | 最详细，用于开发调试 | - 所有内部操作细节<br>- API 请求/响应<br>- 第三方库日志<br>- 文件名、行号、函数名<br>- 执行时间 |
| **INFO** | 标准日志，用于生产 | - 工作流程进度<br>- 重要事件<br>- 步骤完成状态 |
| **WARNING** | 警告和潜在问题 | - 非致命错误<br>- 降级操作<br>- 配置问题 |
| **ERROR** | 错误信息 | - 失败的操作<br>- 异常堆栈<br>- 错误上下文 |

### 3. 启用详细日志（推荐用于调试）

```bash
# 方法 1: 修改 .env 文件
echo "LOG_LEVEL=DEBUG" >> .env
echo "DEBUG=true" >> .env

# 方法 2: 复制配置模板
cp .env.example .env
# 然后编辑 .env，确保:
# LOG_LEVEL=DEBUG
# DEBUG=true

# 运行 agent
make run
```

## 日志功能详解

### 1. 步骤追踪

Orchestrator 执行时会显示清晰的步骤标记：

```
============================================================
[ORCHESTRATOR] Starting bangumi mode workflow
  session_id: session-abc123
  bangumi_id: 12345

============================================================
[STEP 1/4] Searching bangumi points
  session_id: session-abc123
  bangumi_id: 12345

[COMPLETE] SearchAgent (bangumi mode)
  duration_seconds: 1.234
  session_id: session-abc123

[STEP 1/4] ✓ Points retrieved successfully
  points_count: 15
  user_location: 新宿站
```

### 2. 性能追踪

每个主要操作都会记录执行时间：

```
[START] RouteAgent
  operation: RouteAgent
  session_id: session-abc123

[COMPLETE] RouteAgent
  operation: RouteAgent
  duration_seconds: 2.456
  session_id: session-abc123
```

### 3. 错误诊断

错误日志包含完整上下文：

```
[ORCHESTRATOR] ✗ Bangumi mode workflow failed
  error: No pilgrimage points found
  error_type: RuntimeError
  session_id: session-abc123
  bangumi_id: 12345
  points_retrieved: 0

Traceback (most recent call last):
  File ".../orchestrator_agent.py", line 221, in _execute_bangumi_mode
    raise RuntimeError("No pilgrimage points found for ...")
RuntimeError: No pilgrimage points found for 测试番剧
```

### 4. 第三方库日志

在 DEBUG 模式下，可以看到：

- **httpx**: HTTP 请求/响应详情
- **google.auth**: Google API 认证过程
- **google.api_core**: Google Maps API 调用

## 常见问题排查

### 问题 1: 看不到详细日志

**症状**: 运行时只看到很少的日志输出

**解决方案**:
```bash
# 检查 .env 配置
cat .env | grep LOG_LEVEL
cat .env | grep DEBUG

# 应该看到:
# LOG_LEVEL=DEBUG
# DEBUG=true

# 如果不是，修改配置：
echo "LOG_LEVEL=DEBUG" > .env
echo "DEBUG=true" >> .env
```

### 问题 2: 不知道错误发生在哪个步骤

**解决方案**: 启用 DEBUG 模式后，每个步骤都有清晰标记：

```
[STEP 0/4] ✓ Bangumi resolved successfully
[STEP 1/4] ✓ Points retrieved successfully
[STEP 2/4] ✗ WeatherAgent failed (non-critical)  ← 这里出错了
[STEP 3/4] ✓ Route optimized
[STEP 4/4] ✓ Transport optimized
```

### 问题 3: 第三方 API 调用失败

**症状**: Google Maps 或其他 API 调用失败

**调试步骤**:

1. 启用 DEBUG 模式查看完整请求:
   ```bash
   LOG_LEVEL=DEBUG
   DEBUG=true
   ```

2. 查看日志中的 API 请求详情:
   ```
   [httpx] POST https://maps.googleapis.com/...
   [httpx] Headers: {...}
   [httpx] Request body: {...}
   [httpx] Response: 403 Forbidden
   ```

3. 检查 API key 配置:
   ```bash
   cat .env | grep API_KEY
   ```

### 问题 4: 性能问题定位

**解决方案**: 查看日志中的 duration_seconds 字段，找出慢操作：

```
[COMPLETE] SearchAgent (bangumi mode)
  duration_seconds: 0.234  ← 正常

[COMPLETE] RouteAgent
  duration_seconds: 15.678  ← 这个操作很慢！
```

## 测试日志系统

运行测试脚本验证日志配置：

```bash
# 运行日志测试
uv run python test_logging.py

# 你应该看到:
# - 不同级别的日志 (DEBUG, INFO, WARNING, ERROR)
# - 结构化数据 (session_id, points_count 等)
# - 步骤标记 ([STEP 1/3], [STEP 2/3], ...)
# - 性能计时 (duration_seconds)
# - 错误堆栈跟踪
```

## 最佳实践

### 开发环境

```bash
# .env
LOG_LEVEL=DEBUG
DEBUG=true
APP_ENV=development
```

- ✅ 能看到所有详细信息
- ✅ 快速定位问题
- ✅ 了解每个步骤的执行情况

### 生产环境

```bash
# .env
LOG_LEVEL=INFO
DEBUG=false
APP_ENV=production
```

- ✅ 减少日志噪音
- ✅ 只记录重要事件
- ✅ 提高性能
- ✅ 仍保留足够的调试信息

## 日志输出示例

### INFO 级别（生产环境）

```
2025-11-28 23:43:21 INFO  Logging configured
  log_level: INFO
  debug_mode: false
  environment: production

2025-11-28 23:43:22 INFO  [ORCHESTRATOR] Starting bangumi mode workflow
  session_id: session-abc123
  bangumi_id: 12345

2025-11-28 23:43:23 INFO  [STEP 1/4] ✓ Points retrieved successfully
  points_count: 15
```

### DEBUG 级别（开发环境）

```
2025-11-28 23:43:21 DEBUG Logging configured
  log_level: DEBUG
  debug_mode: true
  environment: development
  filename: logger.py
  lineno: 93
  func_name: setup_logging

2025-11-28 23:43:21 DEBUG [httpx] GET https://api.anitabi.cn/bangumi/12345
2025-11-28 23:43:21 DEBUG [httpx] Response: 200 OK
2025-11-28 23:43:21 DEBUG [httpx] Body: {"id": 12345, "name": "..."}

2025-11-28 23:43:22 INFO  [START] SearchAgent (bangumi mode)
  operation: SearchAgent (bangumi mode)
  session_id: session-abc123

2025-11-28 23:43:23 INFO  [COMPLETE] SearchAgent (bangumi mode)
  operation: SearchAgent (bangumi mode)
  duration_seconds: 1.234
  session_id: session-abc123
```

## 总结

使用增强的日志系统，你可以：

- ✅ **快速定位问题**: 清晰的步骤标记和错误信息
- ✅ **性能分析**: 每个操作的执行时间
- ✅ **完整上下文**: session_id、bangumi_id 等关键信息
- ✅ **第三方调试**: 查看 API 请求/响应
- ✅ **灵活控制**: 通过 .env 轻松切换详细程度

遇到问题时，首先启用 DEBUG 模式，然后查看日志中的步骤标记和错误信息！
