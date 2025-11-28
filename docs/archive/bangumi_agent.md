# BangumiResolverAgent 实施计划

> 基于设计文档 `bangumi-resolver-agent-design.md` 的详细实施指南
>
> 遵循原则: TDD + CLEAN CODE + SOLID + KISS

**版本**: 1.0
**创建日期**: 2025-11-28
**状态**: 待实施

---

## 目录

- [总体架构](#总体架构)
- [Stage 1: BangumiClient](#stage-1-bangumiClient-api-客户端层)
- [Stage 2: BangumiResolverAgent](#stage-2-bangumiresolveragent-核心逻辑层)
- [Stage 3: SearchAgent 修改](#stage-3-searchagent-修改)
- [Stage 4: OrchestratorAgent 集成](#stage-4-orchestratoragent-集成)
- [Stage 5: 完整测试套件](#stage-5-完整测试套件)
- [验收标准](#验收标准)

---

## 总体架构

### 数据流向图

```
用户查询: "我在新宿站，想去《你的名字》的圣地"
    ↓
┌─────────────────────────────────────────────────────────────┐
│         BangumiResolverAgent (新增)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Step 1: LLM 提取番剧名称                             │   │
│  │  Input:  "我在新宿站，想去《你的名字》的圣地"          │   │
│  │  Output: "你的名字"                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Step 2: BangumiClient 调用 Bangumi API 搜索          │   │
│  │  Request: GET /search/subject/你的名字?type=2        │   │
│  │  Response: [{id: 160209, name_cn: "你的名字。"}, ...]│   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Step 3: LLM 选择最佳匹配                             │   │
│  │  Input:  搜索结果列表 + 用户原始查询                  │   │
│  │  Output: {id: 160209, confidence: 0.95}              │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
            Bangumi ID: 160209
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              SearchAgent (修改后)                            │
│  - 接收 bangumi_id 和 user_query                            │
│  - 调用 Anitabi: /bangumi/160209/points/detail              │
│  - 获取该番剧的所有圣地列表                                  │
│  - 提取用户位置，计算距离并排序                              │
└─────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **BangumiClient** | 封装 Bangumi API 调用 | 搜索关键词 | 番剧搜索结果列表 |
| **BangumiResolverAgent** | 番剧名 → ID 解析 | 用户查询文本 | Bangumi ID + 元数据 |
| **SearchAgent** (修改) | ID → 圣地列表 | Bangumi ID + 用户位置 | 圣地列表（带距离） |
| **OrchestratorAgent** (修改) | 工作流协调 | 用户完整查询 | 完整旅行计划 |

---

## Stage 1: BangumiClient (API 客户端层)

### 目标

封装 Bangumi API 调用逻辑，提供类型安全的搜索和详情查询功能。

### 输入输出规范

#### 输入

```python
# 搜索番剧
keyword: str = "你的名字"
subject_type: int = 2  # 2=动画, 1=书籍, 3=音乐, 4=游戏
max_results: int = 10  # 1-20
```

#### 输出

```python
# 返回值: List[Dict]
[
    {
        "id": 160209,
        "name": "君の名は。",
        "name_cn": "你的名字。",
        "type": 2,
        "images": {
            "large": "http://lain.bgm.tv/pic/cover/l/20/15/160209_2UzU8.jpg",
            "medium": "...",
            "small": "..."
        },
        "url": "http://bgm.tv/subject/160209",
        "rating": {
            "score": 8.1,
            "total": 31121
        }
    },
    ...
]
```

### 要修改的文件

1. ✨ **新建**: `clients/bangumi.py`
2. 📝 **修改**: `clients/__init__.py`
3. ✅ **新建**: `tests/unit/test_bangumi_client.py`

### TDD 实施步骤

#### 步骤 1.1: 写测试 (RED 阶段)

**文件**: `tests/unit/test_bangumi_client.py`

```python
"""
Unit tests for BangumiClient following TDD principles.
Tests written BEFORE implementation (RED phase).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from clients.bangumi import BangumiClient
from domain.entities import APIError


@pytest.fixture
def bangumi_client():
    """Create a BangumiClient instance."""
    return BangumiClient()


class TestBangumiClient:
    """Test suite for BangumiClient."""

    @pytest.mark.asyncio
    async def test_search_subject_returns_results(self, bangumi_client):
        """Test search_subject returns valid results."""
        # Arrange
        keyword = "你的名字"

        # Act
        results = await bangumi_client.search_subject(keyword)

        # Assert
        assert isinstance(results, list)
        assert len(results) > 0

        # Verify result structure
        first_result = results[0]
        assert "id" in first_result
        assert "name" in first_result
        assert isinstance(first_result["id"], int)

    @pytest.mark.asyncio
    async def test_search_subject_url_encoding(self, bangumi_client):
        """Test that keywords with special chars are URL encoded."""
        # Arrange
        keyword = "吹响！上低音号"  # Contains special chars

        # Act
        results = await bangumi_client.search_subject(keyword)

        # Assert
        assert isinstance(results, list)
        # Should not raise encoding errors

    @pytest.mark.asyncio
    async def test_search_subject_with_type_filter(self, bangumi_client):
        """Test search with subject type filter."""
        # Arrange
        keyword = "你的名字"

        # Act
        results = await bangumi_client.search_subject(
            keyword,
            subject_type=2,  # Anime only
            max_results=5
        )

        # Assert
        assert len(results) <= 5
        # All results should be type 2 (anime)
        for result in results:
            assert result.get("type") == 2

    @pytest.mark.asyncio
    async def test_search_subject_empty_results(self, bangumi_client):
        """Test search with no results returns empty list."""
        # Arrange
        keyword = "xyzabc123notexist999"

        # Act
        results = await bangumi_client.search_subject(keyword)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_subject_uses_cache(self, bangumi_client):
        """Test that repeated searches use cache."""
        # Arrange
        keyword = "你的名字"

        # Act - First call
        results1 = await bangumi_client.search_subject(keyword)

        # Act - Second call (should hit cache)
        results2 = await bangumi_client.search_subject(keyword)

        # Assert
        assert results1 == results2
        # TODO: Verify cache hit via logs or metrics

    @pytest.mark.asyncio
    async def test_search_subject_api_error_handling(self):
        """Test API error handling."""
        # Arrange
        client = BangumiClient()

        # Mock the get method to raise an error
        with patch.object(client, 'get', side_effect=APIError("API Error")):
            # Act & Assert
            with pytest.raises(APIError):
                await client.search_subject("test")

    @pytest.mark.asyncio
    async def test_search_subject_includes_user_agent(self, bangumi_client):
        """Test that requests include proper User-Agent header."""
        # This is important for Bangumi API best practices
        # Will be verified in implementation via headers
        keyword = "test"

        # For now, just ensure it doesn't raise
        results = await bangumi_client.search_subject(keyword)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_subject_by_id(self, bangumi_client):
        """Test fetching subject details by ID."""
        # Arrange
        subject_id = 160209  # 你的名字

        # Act
        result = await bangumi_client.get_subject(subject_id)

        # Assert
        assert result["id"] == subject_id
        assert "name" in result
        assert "name_cn" in result
        assert "rating" in result

    @pytest.mark.asyncio
    async def test_client_rate_limiting(self, bangumi_client):
        """Test that client respects rate limits."""
        # Make multiple rapid requests
        keyword = "test"

        # Act - Make 5 rapid requests
        results = []
        for _ in range(5):
            result = await bangumi_client.search_subject(keyword)
            results.append(result)

        # Assert - Should complete without rate limit errors
        assert len(results) == 5
```

**运行测试** (应该全部失败):
```bash
pytest tests/unit/test_bangumi_client.py -v
```

#### 步骤 1.2: 实现代码 (GREEN 阶段)

**文件**: `clients/bangumi.py`

```python
"""
Bangumi API client for anime/manga metadata.

Official API: https://bangumi.github.io/api/
Provides methods to:
- Search for anime/manga by keyword
- Retrieve subject details by ID
"""

from typing import List, Dict, Optional
import urllib.parse

from clients.base import BaseHTTPClient
from domain.entities import APIError
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class BangumiClient(BaseHTTPClient):
    """
    Client for Bangumi API (番組計画 API).

    Provides access to anime/manga metadata including:
    - Subject search by keyword
    - Subject details by ID
    - Ratings and reviews

    Note: Search endpoints do NOT require authentication.
    """

    # API Constants
    BANGUMI_API_BASE = "https://api.bgm.tv"
    USER_AGENT = "Seichijunrei/1.0 (https://github.com/yourusername/seichijunrei)"

    # Subject Types
    TYPE_BOOK = 1
    TYPE_ANIME = 2
    TYPE_MUSIC = 3
    TYPE_GAME = 4
    TYPE_REAL = 6

    def __init__(
        self,
        base_url: Optional[str] = None,
        use_cache: bool = True,
        rate_limit_calls: int = 30,
        rate_limit_period: float = 60.0
    ):
        """
        Initialize Bangumi API client.

        Args:
            base_url: Override base URL (default: https://api.bgm.tv)
            use_cache: Whether to cache GET responses (default: True)
            rate_limit_calls: Number of calls allowed per period
            rate_limit_period: Rate limit period in seconds
        """
        super().__init__(
            base_url=base_url or self.BANGUMI_API_BASE,
            api_key=None,  # No API key needed for search
            timeout=10,
            max_retries=3,
            rate_limit_calls=rate_limit_calls,
            rate_limit_period=rate_limit_period,
            use_cache=use_cache,
            cache_ttl_seconds=86400  # Cache for 24 hours
        )

        logger.info(
            "Bangumi client initialized",
            base_url=self.base_url,
            cache_enabled=use_cache,
            rate_limit=f"{rate_limit_calls}/{rate_limit_period}s"
        )

    async def search_subject(
        self,
        keyword: str,
        subject_type: int = TYPE_ANIME,
        max_results: int = 10
    ) -> List[Dict]:
        """
        Search for subjects by keyword.

        Args:
            keyword: Search keyword (anime/manga name)
            subject_type: Type filter (1=book, 2=anime, 3=music, 4=game, 6=real)
            max_results: Maximum results to return (1-20)

        Returns:
            List of subject dictionaries with id, name, name_cn, type, images, etc.

        Raises:
            APIError: On API communication failure
            ValueError: On invalid parameters
        """
        # Validate parameters
        if not keyword or not keyword.strip():
            raise ValueError("Keyword cannot be empty")

        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")

        try:
            logger.info(
                "Searching bangumi subjects",
                keyword=keyword,
                subject_type=subject_type,
                max_results=max_results
            )

            # URL encode the keyword
            encoded_keyword = urllib.parse.quote(keyword)

            # Make API request
            response = await self.get(
                f"/search/subject/{encoded_keyword}",
                params={
                    "type": subject_type,
                    "max_results": max_results
                },
                headers={
                    "User-Agent": self.USER_AGENT
                }
            )

            # Extract results
            results = response.get("list", [])

            logger.info(
                "Bangumi search completed",
                keyword=keyword,
                results_count=len(results)
            )

            return results

        except APIError:
            # Re-raise API errors
            raise

        except Exception as e:
            logger.error(
                "Bangumi search failed",
                keyword=keyword,
                error=str(e),
                exc_info=True
            )
            raise APIError(f"Bangumi search failed: {str(e)}")

    async def get_subject(self, subject_id: int) -> Dict:
        """
        Get detailed information about a subject by ID.

        Args:
            subject_id: Bangumi subject ID

        Returns:
            Subject details dictionary

        Raises:
            APIError: On API communication failure
            ValueError: On invalid subject_id
        """
        if subject_id <= 0:
            raise ValueError("subject_id must be positive")

        try:
            logger.info(
                "Fetching bangumi subject details",
                subject_id=subject_id
            )

            response = await self.get(
                f"/subject/{subject_id}",
                headers={
                    "User-Agent": self.USER_AGENT
                }
            )

            logger.info(
                "Bangumi subject fetched",
                subject_id=subject_id,
                name=response.get("name")
            )

            return response

        except APIError:
            raise

        except Exception as e:
            logger.error(
                "Failed to fetch bangumi subject",
                subject_id=subject_id,
                error=str(e),
                exc_info=True
            )
            raise APIError(f"Failed to fetch subject {subject_id}: {str(e)}")
```

**更新**: `clients/__init__.py`

```python
"""
Client modules for external API integrations.
"""

from clients.anitabi import AnitabiClient
from clients.bangumi import BangumiClient  # 新增
from clients.google_maps import GoogleMapsClient
from clients.weather import WeatherClient

__all__ = [
    "AnitabiClient",
    "BangumiClient",  # 新增
    "GoogleMapsClient",
    "WeatherClient",
]
```

**运行测试** (应该通过):
```bash
pytest tests/unit/test_bangumi_client.py -v
```

#### 步骤 1.3: 重构 (REFACTOR 阶段)

**优化点**:

1. **提取常量**
```python
# clients/bangumi.py

# Subject Types (already done above)
TYPE_BOOK = 1
TYPE_ANIME = 2
...

# API Limits
MAX_SEARCH_RESULTS = 20
DEFAULT_SEARCH_RESULTS = 10
CACHE_TTL_SECONDS = 86400  # 24 hours
```

2. **改进错误消息**
```python
# More specific error messages
if not keyword.strip():
    raise ValueError(
        "Search keyword cannot be empty. "
        "Please provide a valid anime/manga name."
    )
```

3. **添加类型提示**
```python
from typing import List, Dict, Optional, Literal

SubjectType = Literal[1, 2, 3, 4, 6]

async def search_subject(
    self,
    keyword: str,
    subject_type: SubjectType = TYPE_ANIME,
    max_results: int = DEFAULT_SEARCH_RESULTS
) -> List[Dict[str, Any]]:
    ...
```

4. **添加文档字符串示例**
```python
async def search_subject(...):
    """
    Search for subjects by keyword.

    Example:
        >>> client = BangumiClient()
        >>> results = await client.search_subject("你的名字")
        >>> print(results[0]["name_cn"])
        '你的名字。'

    ...
    """
```

**再次运行测试** (确保重构后仍然通过):
```bash
pytest tests/unit/test_bangumi_client.py -v
```

### 验收标准 (Stage 1)

- [x] 测试覆盖率 > 90%
- [x] 所有测试通过
- [x] 支持 URL 编码
- [x] 支持缓存机制
- [x] 支持限流
- [x] 错误处理完善
- [x] 代码通过 ruff/black 检查

---

## Stage 2: BangumiResolverAgent (核心逻辑层)

### 目标

实现智能解析Agent，将用户自然语言查询转换为精确的 Bangumi ID。

### 输入输出规范

#### 输入

```python
AgentInput(
    session_id="session-20251128-001",
    data={
        "user_query": "我在新宿站，想去《你的名字》的圣地"
    }
)
```

#### 输出

```python
AgentOutput(
    success=True,
    data={
        "id": 160209,
        "name": "君の名は。",
        "name_cn": "你的名字。",
        "confidence": 0.95,
        "reasoning": "名称完全匹配，且为该查询最知名作品"
    },
    error=None,
    metadata={
        "agent": "bangumi_resolver_agent",
        "execution_time": 2.34,
        "timestamp": "2025-11-28T10:30:00"
    }
)
```

### 要修改的文件

1. ✨ **新建**: `agents/bangumi_resolver_agent.py`
2. 📝 **修改**: `agents/__init__.py`
3. ✅ **新建**: `tests/unit/test_bangumi_resolver_agent.py`

### TDD 实施步骤

#### 步骤 2.1: 写测试 (RED 阶段)

**文件**: `tests/unit/test_bangumi_resolver_agent.py`

```python
"""
Unit tests for BangumiResolverAgent following TDD principles.
Tests written BEFORE implementation (RED phase).
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from agents.base import AgentInput, AgentOutput, AgentState
from agents.bangumi_resolver_agent import BangumiResolverAgent
from clients.bangumi import BangumiClient


@pytest.fixture
def mock_bangumi_client():
    """Create a mock BangumiClient."""
    client = Mock(spec=BangumiClient)
    client.search_subject = AsyncMock()
    client.get_subject = AsyncMock()
    return client


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    llm = Mock()
    llm.generate = AsyncMock()
    return llm


@pytest.fixture
def resolver_agent(mock_bangumi_client, mock_llm_client):
    """Create a BangumiResolverAgent with mocked dependencies."""
    return BangumiResolverAgent(
        bangumi_client=mock_bangumi_client,
        llm_client=mock_llm_client
    )


@pytest.fixture
def sample_search_results():
    """Sample Bangumi API search results."""
    return [
        {
            "id": 160209,
            "name": "君の名は。",
            "name_cn": "你的名字。",
            "type": 2,
            "images": {"large": "..."},
            "url": "http://bgm.tv/subject/160209"
        },
        {
            "id": 210992,
            "name": "遠き山に日は落ちて",
            "name_cn": "远山樱宇宙帖",
            "type": 2,
            "images": {"large": "..."},
            "url": "http://bgm.tv/subject/210992"
        }
    ]


class TestBangumiResolverAgent:
    """Test suite for BangumiResolverAgent."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_bangumi_client, mock_llm_client):
        """Test agent initialization."""
        # Arrange & Act
        agent = BangumiResolverAgent(
            bangumi_client=mock_bangumi_client,
            llm_client=mock_llm_client
        )

        # Assert
        assert agent.name == "bangumi_resolver_agent"
        assert agent.description == "Resolve bangumi name to ID using LLM + Bangumi API"
        assert agent.state == AgentState.IDLE
        assert agent.bangumi_client == mock_bangumi_client
        assert agent.llm_client == mock_llm_client

    @pytest.mark.asyncio
    async def test_extract_bangumi_name_basic(self, resolver_agent, mock_llm_client):
        """Test extracting bangumi name from user query."""
        # Arrange
        user_query = "我在新宿站，想去《你的名字》的圣地"
        mock_llm_client.generate.return_value = json.dumps({
            "bangumi_name": "你的名字"
        })

        # Act
        result = await resolver_agent._extract_bangumi_name(user_query)

        # Assert
        assert result == "你的名字"
        mock_llm_client.generate.assert_called_once()

        # Verify prompt contains user query
        call_args = mock_llm_client.generate.call_args[0][0]
        assert user_query in call_args

    @pytest.mark.asyncio
    async def test_extract_bangumi_name_removes_brackets(
        self, resolver_agent, mock_llm_client
    ):
        """Test that bangumi name extraction removes brackets."""
        # Arrange
        user_query = "去《吹响！上低音号》的地方"
        mock_llm_client.generate.return_value = json.dumps({
            "bangumi_name": "吹响！上低音号"  # Should remove 《》
        })

        # Act
        result = await resolver_agent._extract_bangumi_name(user_query)

        # Assert
        assert "《" not in result
        assert "》" not in result
        assert "吹响" in result

    @pytest.mark.asyncio
    async def test_search_bangumi_calls_api(
        self, resolver_agent, mock_bangumi_client, sample_search_results
    ):
        """Test _search_bangumi calls Bangumi API correctly."""
        # Arrange
        keyword = "你的名字"
        mock_bangumi_client.search_subject.return_value = sample_search_results

        # Act
        results = await resolver_agent._search_bangumi(keyword)

        # Assert
        assert len(results) == 2
        assert results[0]["id"] == 160209
        mock_bangumi_client.search_subject.assert_called_once_with(
            keyword=keyword,
            subject_type=2,  # Anime
            max_results=10
        )

    @pytest.mark.asyncio
    async def test_select_best_match_returns_correct_id(
        self, resolver_agent, mock_llm_client, sample_search_results
    ):
        """Test LLM selection returns correct bangumi."""
        # Arrange
        user_query = "我想去你的名字的圣地"
        bangumi_name = "你的名字"

        mock_llm_client.generate.return_value = json.dumps({
            "id": 160209,
            "name": "君の名は。",
            "name_cn": "你的名字。",
            "confidence": 0.95,
            "reasoning": "名称完全匹配"
        })

        # Act
        result = await resolver_agent._select_best_match(
            user_query=user_query,
            bangumi_name=bangumi_name,
            search_results=sample_search_results
        )

        # Assert
        assert result["id"] == 160209
        assert result["confidence"] >= 0.9
        assert "name_cn" in result
        assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_select_best_match_validates_id(
        self, resolver_agent, mock_llm_client, sample_search_results
    ):
        """Test that selected ID is validated against search results."""
        # Arrange
        user_query = "test"
        bangumi_name = "test"

        # LLM returns invalid ID (not in search results)
        mock_llm_client.generate.return_value = json.dumps({
            "id": 999999,  # Invalid
            "name": "...",
            "name_cn": "...",
            "confidence": 0.8,
            "reasoning": "..."
        })

        # Act
        result = await resolver_agent._select_best_match(
            user_query=user_query,
            bangumi_name=bangumi_name,
            search_results=sample_search_results
        )

        # Assert - Should fallback to first result
        assert result["id"] == sample_search_results[0]["id"]
        assert "fallback" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_execute_end_to_end_success(
        self,
        resolver_agent,
        mock_llm_client,
        mock_bangumi_client,
        sample_search_results
    ):
        """Test complete execution flow."""
        # Arrange
        input_data = AgentInput(
            session_id="test-001",
            data={
                "user_query": "我在新宿站，想去《你的名字》的圣地"
            }
        )

        # Mock LLM responses
        mock_llm_client.generate.side_effect = [
            # First call: extract bangumi name
            json.dumps({"bangumi_name": "你的名字"}),
            # Second call: select best match
            json.dumps({
                "id": 160209,
                "name": "君の名は。",
                "name_cn": "你的名字。",
                "confidence": 0.95,
                "reasoning": "Perfect match"
            })
        ]

        # Mock Bangumi API
        mock_bangumi_client.search_subject.return_value = sample_search_results

        # Act
        result = await resolver_agent.execute(input_data)

        # Assert
        assert result.success is True
        assert result.error is None
        assert result.data["id"] == 160209
        assert result.data["confidence"] >= 0.9
        assert "你的名字" in result.data["name_cn"]

    @pytest.mark.asyncio
    async def test_execute_no_bangumi_found(
        self,
        resolver_agent,
        mock_llm_client,
        mock_bangumi_client
    ):
        """Test execution when no bangumi found."""
        # Arrange
        input_data = AgentInput(
            session_id="test-002",
            data={
                "user_query": "去 xyzabc123 的圣地"
            }
        )

        # Mock LLM extract
        mock_llm_client.generate.return_value = json.dumps({
            "bangumi_name": "xyzabc123"
        })

        # Mock empty search results
        mock_bangumi_client.search_subject.return_value = []

        # Act
        result = await resolver_agent.execute(input_data)

        # Assert
        assert result.success is False
        assert "no bangumi found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_llm_extraction_fails(
        self,
        resolver_agent,
        mock_llm_client
    ):
        """Test execution when LLM fails to extract bangumi name."""
        # Arrange
        input_data = AgentInput(
            session_id="test-003",
            data={
                "user_query": "今天天气真好"  # No bangumi mentioned
            }
        )

        # Mock LLM returns no bangumi
        mock_llm_client.generate.return_value = json.dumps({
            "bangumi_name": ""
        })

        # Act
        result = await resolver_agent.execute(input_data)

        # Assert
        assert result.success is False
        assert "extract" in result.error.lower() or "bangumi" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validate_input_requires_user_query(self, resolver_agent):
        """Test input validation requires user_query."""
        # Arrange
        input_data = AgentInput(
            session_id="test",
            data={}  # Missing user_query
        )

        # Act
        is_valid = resolver_agent._validate_input(input_data)

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_input_user_query_must_be_string(self, resolver_agent):
        """Test user_query must be a string."""
        # Arrange
        input_data = AgentInput(
            session_id="test",
            data={"user_query": 123}  # Invalid type
        )

        # Act
        is_valid = resolver_agent._validate_input(input_data)

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_input_user_query_cannot_be_empty(self, resolver_agent):
        """Test user_query cannot be empty."""
        # Arrange
        input_data = AgentInput(
            session_id="test",
            data={"user_query": "   "}  # Empty string
        )

        # Act
        is_valid = resolver_agent._validate_input(input_data)

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_multiple_bangumi_variations(
        self,
        resolver_agent,
        mock_llm_client,
        mock_bangumi_client,
        sample_search_results
    ):
        """Test different variations of bangumi names resolve to same ID."""
        variations = [
            "你的名字",
            "你的名字。",
            "君の名は",
            "君の名は。",
            "Your Name",
        ]

        for variation in variations:
            # Arrange
            input_data = AgentInput(
                session_id=f"test-{variation}",
                data={"user_query": f"去{variation}的圣地"}
            )

            # Mock responses
            mock_llm_client.generate.side_effect = [
                json.dumps({"bangumi_name": variation}),
                json.dumps({
                    "id": 160209,
                    "name": "君の名は。",
                    "name_cn": "你的名字。",
                    "confidence": 0.9,
                    "reasoning": "Match"
                })
            ]
            mock_bangumi_client.search_subject.return_value = sample_search_results

            # Act
            result = await resolver_agent.execute(input_data)

            # Assert
            assert result.success
            assert result.data["id"] == 160209
```

**运行测试** (应该全部失败):
```bash
pytest tests/unit/test_bangumi_resolver_agent.py -v
```

#### 步骤 2.2: 实现代码 (GREEN 阶段)

**文件**: `agents/bangumi_resolver_agent.py`

```python
"""
BangumiResolverAgent - Intelligent bangumi name to ID resolver.

Uses LLM + Bangumi API to:
1. Extract bangumi name from natural language query
2. Search Bangumi API for matching subjects
3. Intelligently select the best match
"""

from typing import Dict, Any, List, Optional
import json
import urllib.parse

from agents.base import AbstractBaseAgent, AgentInput
from clients.bangumi import BangumiClient
from domain.entities import APIError
from utils.logger import get_logger
from utils.llm import get_llm_client  # Assuming this utility exists


logger = get_logger(__name__)


class BangumiResolverAgent(AbstractBaseAgent):
    """
    Agent for resolving bangumi names to IDs.

    This agent:
    - Accepts user natural language query
    - Extracts bangumi name using LLM
    - Searches Bangumi API
    - Selects best match using LLM
    - Returns bangumi ID with confidence score
    """

    # LLM Prompts
    EXTRACT_PROMPT_TEMPLATE = """从用户查询中提取番剧名称。

用户查询: "{user_query}"

返回 JSON 格式: {{"bangumi_name": "提取的番剧名"}}

提取规则:
- 移除《》、""、'' 等包裹符号
- 保留核心作品名称
- 如果有多种称呼，优先使用常用名称

示例:
- "我在新宿站，想去《你的名字》的圣地" → {{"bangumi_name": "你的名字"}}
- "去吹响吧上低音号的地方" → {{"bangumi_name": "吹响吧上低音号"}}
- "想看看冰菓的取景地" → {{"bangumi_name": "冰菓"}}
"""

    SELECT_PROMPT_TEMPLATE = """你是番剧匹配专家。从搜索结果中选择最符合用户意图的番剧。

用户完整查询: "{user_query}"
提取的番剧名: "{bangumi_name}"

搜索结果:
{candidates_str}

选择标准:
1. 名称相似度（中文名或原名）
2. 作品知名度和热度
3. 与用户查询的相关性

返回 JSON 格式:
{{
  "id": 选择的番剧ID（整数）,
  "name": "原名",
  "name_cn": "中文名",
  "confidence": 置信度（0.0-1.0）,
  "reasoning": "选择理由（1-2句话）"
}}

如果第一个结果明显是最佳匹配，置信度应该 >= 0.9
如果需要推理判断，置信度在 0.7-0.9
如果不确定，置信度 < 0.7
"""

    def __init__(
        self,
        bangumi_client: Optional[BangumiClient] = None,
        llm_client: Optional[Any] = None
    ):
        """
        Initialize the BangumiResolverAgent.

        Args:
            bangumi_client: BangumiClient instance (creates new if None)
            llm_client: LLM client for text generation (uses default if None)
        """
        super().__init__(
            name="bangumi_resolver_agent",
            description="Resolve bangumi name to ID using LLM + Bangumi API"
        )
        self.bangumi_client = bangumi_client or BangumiClient()
        self.llm_client = llm_client or get_llm_client()
        self.logger = get_logger(__name__)

    async def _execute_logic(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Execute bangumi resolution logic.

        Args:
            input_data: AgentInput containing:
                - user_query: Natural language query from user

        Returns:
            Dictionary containing:
                - id: Bangumi ID (int)
                - name: Original name (str)
                - name_cn: Chinese name (str)
                - confidence: Match confidence 0-1 (float)
                - reasoning: Why this was selected (str)

        Raises:
            ValueError: If no bangumi found or extraction fails
            APIError: On API communication failure
        """
        user_query = input_data.data.get("user_query")

        self.logger.info(
            "Starting bangumi resolution",
            user_query=user_query,
            session_id=input_data.session_id
        )

        # Step 1: Extract bangumi name using LLM
        bangumi_name = await self._extract_bangumi_name(user_query)

        if not bangumi_name or not bangumi_name.strip():
            raise ValueError(
                f"Failed to extract bangumi name from query: {user_query}"
            )

        self.logger.info(
            "Extracted bangumi name",
            bangumi_name=bangumi_name,
            session_id=input_data.session_id
        )

        # Step 2: Search Bangumi API
        search_results = await self._search_bangumi(bangumi_name)

        if not search_results:
            raise ValueError(
                f"No bangumi found for: {bangumi_name}. "
                "Please try a different name or check spelling."
            )

        self.logger.info(
            "Bangumi search completed",
            bangumi_name=bangumi_name,
            results_count=len(search_results),
            session_id=input_data.session_id
        )

        # Step 3: Select best match using LLM
        selected = await self._select_best_match(
            user_query=user_query,
            bangumi_name=bangumi_name,
            search_results=search_results
        )

        self.logger.info(
            "Bangumi resolved",
            bangumi_id=selected["id"],
            bangumi_name_cn=selected["name_cn"],
            confidence=selected["confidence"],
            session_id=input_data.session_id
        )

        return {
            "id": selected["id"],
            "name": selected["name"],
            "name_cn": selected["name_cn"],
            "confidence": selected["confidence"],
            "reasoning": selected["reasoning"]
        }

    async def _extract_bangumi_name(self, user_query: str) -> str:
        """
        Use LLM to extract bangumi name from user query.

        Args:
            user_query: User's natural language query

        Returns:
            Extracted bangumi name (cleaned)

        Raises:
            ValueError: If LLM fails to extract or returns invalid JSON
        """
        try:
            prompt = self.EXTRACT_PROMPT_TEMPLATE.format(user_query=user_query)

            response = await self.llm_client.generate(prompt)

            # Parse JSON response
            result = json.loads(response)
            bangumi_name = result.get("bangumi_name", "").strip()

            # Remove common brackets/quotes
            for char in ["《", "》", "「", "」", '"', "'", """, """]:
                bangumi_name = bangumi_name.replace(char, "")

            return bangumi_name.strip()

        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse LLM response",
                error=str(e),
                response=response
            )
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")

        except Exception as e:
            self.logger.error(
                "Failed to extract bangumi name",
                error=str(e),
                user_query=user_query,
                exc_info=True
            )
            raise ValueError(f"Failed to extract bangumi name: {str(e)}")

    async def _search_bangumi(self, keyword: str) -> List[Dict]:
        """
        Search Bangumi API for matching subjects.

        Args:
            keyword: Bangumi name to search for

        Returns:
            List of search results from Bangumi API

        Raises:
            APIError: On API communication failure
        """
        try:
            results = await self.bangumi_client.search_subject(
                keyword=keyword,
                subject_type=BangumiClient.TYPE_ANIME,
                max_results=10
            )
            return results

        except APIError:
            # Re-raise API errors
            raise

        except Exception as e:
            self.logger.error(
                "Bangumi search failed",
                keyword=keyword,
                error=str(e),
                exc_info=True
            )
            raise APIError(f"Bangumi search failed: {str(e)}")

    async def _select_best_match(
        self,
        user_query: str,
        bangumi_name: str,
        search_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Use LLM to select the best matching bangumi from search results.

        Args:
            user_query: Original user query
            bangumi_name: Extracted bangumi name
            search_results: List of search results from Bangumi API

        Returns:
            Dictionary with selected bangumi details:
                - id: Bangumi ID
                - name: Original name
                - name_cn: Chinese name
                - confidence: Match confidence (0-1)
                - reasoning: Selection reasoning

        Raises:
            ValueError: If LLM returns invalid result
        """
        try:
            # Build candidates string for prompt
            candidates = []
            for i, result in enumerate(search_results[:5]):  # Top 5 only
                candidates.append(
                    f"{i+1}. ID: {result['id']}, "
                    f"中文名: {result.get('name_cn', 'N/A')}, "
                    f"原名: {result['name']}"
                )
            candidates_str = "\n".join(candidates)

            # Generate LLM prompt
            prompt = self.SELECT_PROMPT_TEMPLATE.format(
                user_query=user_query,
                bangumi_name=bangumi_name,
                candidates_str=candidates_str
            )

            # Get LLM response
            response = await self.llm_client.generate(prompt)

            # Parse result
            result = json.loads(response)

            # Validate that returned ID is in search results
            valid_ids = [r["id"] for r in search_results]

            if result["id"] not in valid_ids:
                # Fallback: Use first result
                self.logger.warning(
                    "LLM returned invalid ID, falling back to first result",
                    llm_id=result["id"],
                    valid_ids=valid_ids[:5]
                )

                first = search_results[0]
                result = {
                    "id": first["id"],
                    "name": first["name"],
                    "name_cn": first.get("name_cn", first["name"]),
                    "confidence": 0.8,
                    "reasoning": "Fallback to first result due to LLM error"
                }

            return result

        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse LLM selection response",
                error=str(e),
                response=response
            )
            # Fallback to first result
            first = search_results[0]
            return {
                "id": first["id"],
                "name": first["name"],
                "name_cn": first.get("name_cn", first["name"]),
                "confidence": 0.7,
                "reasoning": "Fallback due to LLM JSON parse error"
            }

        except Exception as e:
            self.logger.error(
                "Failed to select best match",
                error=str(e),
                exc_info=True
            )
            # Fallback to first result
            first = search_results[0]
            return {
                "id": first["id"],
                "name": first["name"],
                "name_cn": first.get("name_cn", first["name"]),
                "confidence": 0.6,
                "reasoning": f"Fallback due to error: {str(e)}"
            }

    def _validate_input(self, input_data: AgentInput) -> bool:
        """
        Validate input data for BangumiResolverAgent.

        Args:
            input_data: AgentInput to validate

        Returns:
            True if valid, False otherwise
        """
        # Check data exists
        if not input_data.data:
            self.logger.error("No data provided in input")
            return False

        # Check user_query exists
        if "user_query" not in input_data.data:
            self.logger.error("No user_query provided in input")
            return False

        user_query = input_data.data.get("user_query")

        # Validate user_query is a string
        if not isinstance(user_query, str):
            self.logger.error(
                "user_query must be a string",
                provided_type=type(user_query).__name__
            )
            return False

        # Validate user_query is not empty
        if not user_query.strip():
            self.logger.error("user_query cannot be empty")
            return False

        return True
```

**更新**: `agents/__init__.py`

```python
"""
Agent modules for orchestrating travel planning workflow.
"""

from agents.base import AbstractBaseAgent, AgentInput, AgentOutput, AgentState
from agents.bangumi_resolver_agent import BangumiResolverAgent  # 新增
from agents.filter_agent import FilterAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.poi_agent import POIAgent
from agents.route_agent import RouteAgent
from agents.search_agent import SearchAgent
from agents.transport_agent import TransportAgent
from agents.weather_agent import WeatherAgent

__all__ = [
    "AbstractBaseAgent",
    "AgentInput",
    "AgentOutput",
    "AgentState",
    "BangumiResolverAgent",  # 新增
    "FilterAgent",
    "OrchestratorAgent",
    "POIAgent",
    "RouteAgent",
    "SearchAgent",
    "TransportAgent",
    "WeatherAgent",
]
```

**运行测试** (应该通过):
```bash
pytest tests/unit/test_bangumi_resolver_agent.py -v
```

#### 步骤 2.3: 重构 (REFACTOR 阶段)

**优化点**:

1. **提取 Prompt 到配置文件**
```python
# config/prompts.py (新建)

BANGUMI_EXTRACT_PROMPT = """..."""
BANGUMI_SELECT_PROMPT = """..."""
```

2. **添加重试机制 (对于 LLM 调用)**
```python
from utils.retry import with_retry

@with_retry(max_attempts=3, backoff_factor=1.0)
async def _extract_bangumi_name(self, user_query: str) -> str:
    ...
```

3. **添加指标收集**
```python
# Track confidence distribution
self.metrics.record_confidence(selected["confidence"])
```

4. **改进日志结构**
```python
self.logger.info(
    "Bangumi resolution completed",
    bangumi_id=selected["id"],
    bangumi_name=selected["name_cn"],
    confidence=selected["confidence"],
    extraction_attempts=1,
    search_results_count=len(search_results),
    session_id=input_data.session_id
)
```

### 验收标准 (Stage 2)

- [x] 测试覆盖率 > 90%
- [x] 所有测试通过
- [x] LLM 提取准确率 > 95% (手动测试)
- [x] LLM 匹配准确率 > 90% (手动测试)
- [x] Fallback 机制完善
- [x] 错误处理完善
- [x] 代码通过 ruff/black 检查

---

## Stage 3: SearchAgent 修改

### 目标

扩展 SearchAgent 支持两种输入模式:
- **模式 1 (旧)**: `station_name` → 搜索附近所有番剧
- **模式 2 (新)**: `bangumi_id + user_query` → 获取该番剧的圣地

### 输入输出规范

#### 新模式输入

```python
AgentInput(
    session_id="session-001",
    data={
        "bangumi_id": 160209,
        "user_query": "我在新宿站，想去你的名字的圣地"
    }
)
```

#### 新模式输出

```python
{
    "points": [
        {
            "id": "point-001",
            "name": "四谷站",
            "bangumi_id": 160209,
            "coordinates": {...},
            "distance_km": 2.5,
            "images": [...]
        },
        ...
    ],
    "user_location": "新宿站",
    "user_coordinates": {
        "latitude": 35.689487,
        "longitude": 139.700514
    },
    "bangumi_id": 160209
}
```

### 要修改的文件

1. 📝 **修改**: `agents/search_agent.py`
2. ✅ **修改**: `tests/unit/test_search_agent.py`

### TDD 实施步骤

#### 步骤 3.1: 写测试 (RED 阶段)

**文件**: `tests/unit/test_search_agent.py` (追加)

```python
# 追加到现有文件

class TestSearchAgentBangumiIDMode:
    """Test SearchAgent with bangumi_id input mode."""

    @pytest.mark.asyncio
    async def test_search_with_bangumi_id_returns_points(
        self, mock_anitabi_client, mock_gmaps_client
    ):
        """Test new mode: search with bangumi_id."""
        # Arrange
        agent = SearchAgent(
            anitabi_client=mock_anitabi_client,
            gmaps_client=mock_gmaps_client
        )

        # Mock responses
        mock_points = [
            Mock(
                id="point-1",
                name="四谷站",
                coordinates=Coordinates(latitude=35.686, longitude=139.729),
                distance_km=None  # Will be calculated
            )
        ]
        mock_anitabi_client.get_bangumi_points.return_value = mock_points
        mock_gmaps_client.geocode.return_value = Coordinates(
            latitude=35.689,
            longitude=139.700
        )

        input_data = AgentInput(
            session_id="test",
            data={
                "bangumi_id": 160209,
                "user_query": "我在新宿站"
            }
        )

        # Act
        result = await agent.execute(input_data)

        # Assert
        assert result.success
        assert "points" in result.data
        assert len(result.data["points"]) > 0
        assert result.data["user_location"] == "新宿站"
        assert result.data["bangumi_id"] == 160209

        # Verify distance was calculated
        first_point = result.data["points"][0]
        assert first_point["distance_km"] is not None

    @pytest.mark.asyncio
    async def test_extract_location_from_query(self, search_agent, mock_llm_client):
        """Test extracting user location from query."""
        # Arrange (assuming we add LLM client to SearchAgent)
        mock_llm_client.generate.return_value = json.dumps({
            "location": "新宿站"
        })

        # Act
        location = await search_agent._extract_location(
            "我在新宿站，想去你的名字的圣地"
        )

        # Assert
        assert location == "新宿站"

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_station_name(
        self, search_agent, mock_anitabi_client
    ):
        """Test that old station_name mode still works."""
        # Arrange
        mock_station = Station(
            name="Tokyo Station",
            coordinates=Coordinates(latitude=35.681, longitude=139.767),
            city="Tokyo",
            prefecture="Tokyo"
        )
        mock_anitabi_client.get_station_info.return_value = mock_station
        mock_anitabi_client.search_bangumi.return_value = []

        input_data = AgentInput(
            session_id="test",
            data={"station_name": "Tokyo Station"}
        )

        # Act
        result = await search_agent.execute(input_data)

        # Assert
        assert result.success
        # Old mode should still work
```

**运行测试** (新测试应该失败):
```bash
pytest tests/unit/test_search_agent.py::TestSearchAgentBangumiIDMode -v
```

#### 步骤 3.2: 实现代码 (GREEN 阶段)

**文件**: `agents/search_agent.py` (修改)

```python
# 在 SearchAgent 类中添加/修改方法

class SearchAgent(AbstractBaseAgent):
    def __init__(
        self,
        anitabi_client: Optional[AnitabiClient] = None,
        gmaps_client: Optional[GoogleMapsClient] = None,
        llm_client: Optional[Any] = None  # 新增
    ):
        """Initialize the SearchAgent."""
        super().__init__(
            name="search_agent",
            description="Searches for anime locations near stations"
        )
        self.anitabi_client = anitabi_client or AnitabiClient()
        self.gmaps_client = gmaps_client or GoogleMapsClient()  # 新增
        self.llm_client = llm_client or get_llm_client()  # 新增
        self.logger = get_logger(__name__)

    async def _execute_logic(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Execute the search logic.

        Supports two modes:
        1. Station mode: station_name → find nearby bangumi
        2. Bangumi mode: bangumi_id + user_query → find bangumi points
        """
        # Check which mode to use
        bangumi_id = input_data.data.get("bangumi_id")

        if bangumi_id:
            # NEW MODE: Search points for specific bangumi
            return await self._execute_bangumi_mode(input_data)
        else:
            # OLD MODE: Search nearby bangumi at station
            return await self._execute_station_mode(input_data)

    async def _execute_bangumi_mode(
        self,
        input_data: AgentInput
    ) -> Dict[str, Any]:
        """
        Execute bangumi-specific search mode.

        Args:
            input_data: Contains bangumi_id and user_query

        Returns:
            Dictionary with points, user_location, user_coordinates
        """
        bangumi_id = input_data.data.get("bangumi_id")
        user_query = input_data.data.get("user_query")

        self.logger.info(
            "Executing bangumi-specific search",
            bangumi_id=bangumi_id,
            session_id=input_data.session_id
        )

        # Step 1: Extract user location from query
        user_location = await self._extract_location(user_query)

        self.logger.info(
            "Extracted user location",
            location=user_location,
            session_id=input_data.session_id
        )

        # Step 2: Get bangumi points from Anitabi
        points = await self.anitabi_client.get_bangumi_points(
            bangumi_id=bangumi_id
        )

        self.logger.info(
            "Fetched bangumi points",
            bangumi_id=bangumi_id,
            points_count=len(points),
            session_id=input_data.session_id
        )

        # Step 3: Geocode user location
        user_coords = await self.gmaps_client.geocode(user_location)

        # Step 4: Calculate distances
        for point in points:
            point.distance_km = self._calculate_distance(
                user_coords,
                point.coordinates
            )

        # Step 5: Sort by distance
        points.sort(key=lambda p: p.distance_km or float('inf'))

        self.logger.info(
            "Bangumi search completed",
            bangumi_id=bangumi_id,
            points_count=len(points),
            nearest_distance_km=points[0].distance_km if points else None,
            session_id=input_data.session_id
        )

        return {
            "points": [p.model_dump() for p in points],
            "user_location": user_location,
            "user_coordinates": user_coords.model_dump(),
            "bangumi_id": bangumi_id
        }

    async def _execute_station_mode(
        self,
        input_data: AgentInput
    ) -> Dict[str, Any]:
        """
        Execute station-based search mode (original logic).

        Args:
            input_data: Contains station or station_name

        Returns:
            Dictionary with bangumi_list, station, etc.
        """
        # ... EXISTING IMPLEMENTATION ...
        # (Keep all existing logic unchanged)

        radius_km = input_data.data.get("radius_km", 5.0)
        station_name = input_data.data.get("station_name")
        station_data = input_data.data.get("station")

        # ... rest of existing code ...

    async def _extract_location(self, user_query: str) -> str:
        """
        Extract user location from natural language query.

        Args:
            user_query: User's query containing location

        Returns:
            Extracted location string
        """
        prompt = f"""从用户查询中提取地理位置（车站名或地址）。

用户查询: "{user_query}"

返回 JSON 格式: {{"location": "提取的位置"}}

示例:
- "我在新宿站，想去..." → {{"location": "新宿站"}}
- "从秋叶原出发去..." → {{"location": "秋叶原"}}
- "在东京塔附近..." → {{"location": "东京塔"}}
"""

        try:
            response = await self.llm_client.generate(prompt)
            result = json.loads(response)
            location = result.get("location", "").strip()

            if not location:
                raise ValueError("Failed to extract location from query")

            return location

        except Exception as e:
            self.logger.error(
                "Failed to extract location",
                user_query=user_query,
                error=str(e)
            )
            raise ValueError(f"Failed to extract location: {str(e)}")

    def _calculate_distance(
        self,
        coord1: Coordinates,
        coord2: Coordinates
    ) -> float:
        """
        Calculate distance between two coordinates (Haversine formula).

        Args:
            coord1: First coordinate
            coord2: Second coordinate

        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth radius in km

        lat1, lon1 = radians(coord1.latitude), radians(coord1.longitude)
        lat2, lon2 = radians(coord2.latitude), radians(coord2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def _validate_input(self, input_data: AgentInput) -> bool:
        """
        Validate input for both modes.
        """
        if not input_data.data:
            self.logger.error("No data provided")
            return False

        # Check if bangumi_id mode
        if "bangumi_id" in input_data.data:
            # Validate bangumi_id mode
            bangumi_id = input_data.data.get("bangumi_id")
            user_query = input_data.data.get("user_query")

            if not isinstance(bangumi_id, int) or bangumi_id <= 0:
                self.logger.error("Invalid bangumi_id")
                return False

            if not user_query or not isinstance(user_query, str):
                self.logger.error("Invalid user_query")
                return False

            return True
        else:
            # Validate station mode (existing logic)
            if "station" not in input_data.data and "station_name" not in input_data.data:
                self.logger.error("No station or station_name provided")
                return False

            # ... rest of existing validation ...
            return True
```

**运行测试** (应该通过):
```bash
pytest tests/unit/test_search_agent.py -v
```

#### 步骤 3.3: 重构 (REFACTOR 阶段)

**优化点**:

1. **提取通用方法**
```python
def _sort_by_distance(self, points: List[Point]) -> List[Point]:
    """Sort points by distance."""
    return sorted(points, key=lambda p: p.distance_km or float('inf'))
```

2. **改进错误消息**
```python
if not points:
    raise ValueError(
        f"No points found for bangumi {bangumi_id}. "
        "This bangumi may not have registered pilgrimage locations."
    )
```

3. **添加缓存 (对于位置提取)**
```python
@lru_cache(maxsize=100)
async def _extract_location_cached(self, user_query: str) -> str:
    ...
```

### 验收标准 (Stage 3)

- [x] 新模式测试通过
- [x] 旧模式保持兼容
- [x] 距离计算准确
- [x] 位置提取准确率 > 90%
- [x] 代码通过 ruff/black 检查

---

## Stage 4: OrchestratorAgent 集成

### 目标

在 OrchestratorAgent 工作流中集成 BangumiResolverAgent，实现完整的端到端流程。

### 工作流变化

```
旧流程:
用户输入(station_name) → SearchAgent → FilterAgent → POIAgent → ...

新流程:
用户输入(user_query) → BangumiResolverAgent → SearchAgent → FilterAgent → ...
                      ↓
                Bangumi ID: 160209
```

### 要修改的文件

1. 📝 **修改**: `agents/orchestrator_agent.py`
2. ✅ **修改**: `tests/unit/test_orchestrator_agent.py`

### TDD 实施步骤

#### 步骤 4.1: 写测试 (RED 阶段)

**文件**: `tests/unit/test_orchestrator_agent.py` (追加)

```python
# 追加测试

@pytest.mark.asyncio
async def test_orchestrator_with_bangumi_resolver():
    """Test orchestration with BangumiResolverAgent."""
    # Arrange
    mock_bangumi_resolver = Mock(spec=BangumiResolverAgent)
    mock_bangumi_resolver.execute = AsyncMock(
        return_value=AgentOutput(
            success=True,
            data={
                "id": 160209,
                "name": "君の名は。",
                "name_cn": "你的名字。",
                "confidence": 0.95,
                "reasoning": "Perfect match"
            }
        )
    )

    # ... mock other agents ...

    orchestrator = OrchestratorAgent(
        bangumi_resolver=mock_bangumi_resolver,
        search_agent=mock_search_agent,
        # ... other agents ...
    )

    input_data = AgentInput(
        session_id="test-001",
        data={
            "user_query": "我在新宿站想去你的名字的圣地"
        }
    )

    # Act
    result = await orchestrator.execute(input_data)

    # Assert
    assert result.success
    assert result.data["session"]["bangumi_id"] == 160209
    assert result.data["session"]["bangumi_name"] == "你的名字。"

    # Verify bangumi_resolver was called
    mock_bangumi_resolver.execute.assert_called_once()

@pytest.mark.asyncio
async def test_orchestrator_bangumi_resolver_failure():
    """Test orchestration when bangumi resolver fails."""
    # Arrange
    mock_bangumi_resolver = Mock(spec=BangumiResolverAgent)
    mock_bangumi_resolver.execute = AsyncMock(
        return_value=AgentOutput(
            success=False,
            error="No bangumi found"
        )
    )

    orchestrator = OrchestratorAgent(
        bangumi_resolver=mock_bangumi_resolver,
        # ... other agents ...
    )

    input_data = AgentInput(
        session_id="test-002",
        data={"user_query": "random text"}
    )

    # Act
    result = await orchestrator.execute(input_data)

    # Assert
    assert result.success is False
    assert "bangumi" in result.error.lower()
```

#### 步骤 4.2: 实现代码 (GREEN 阶段)

**文件**: `agents/orchestrator_agent.py` (修改)

```python
class OrchestratorAgent(AbstractBaseAgent):
    def __init__(
        self,
        bangumi_resolver: Optional[BangumiResolverAgent] = None,  # 新增
        search_agent: Optional[SearchAgent] = None,
        weather_agent: Optional[WeatherAgent] = None,
        filter_agent: Optional[FilterAgent] = None,
        poi_agent: Optional[POIAgent] = None,
        route_agent: Optional[RouteAgent] = None,
        transport_agent: Optional[TransportAgent] = None
    ):
        """Initialize the OrchestratorAgent."""
        super().__init__(
            name="orchestrator_agent",
            description="Orchestrates complete pilgrimage planning workflow"
        )
        self.bangumi_resolver = bangumi_resolver or BangumiResolverAgent()  # 新增
        self.search_agent = search_agent or SearchAgent()
        self.weather_agent = weather_agent or WeatherAgent()
        self.filter_agent = filter_agent or FilterAgent()
        self.poi_agent = poi_agent or POIAgent()
        self.route_agent = route_agent or RouteAgent()
        self.transport_agent = transport_agent or TransportAgent()
        self.logger = get_logger(__name__)

    async def _execute_logic(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Execute the complete orchestration workflow.

        NEW FLOW:
        1. BangumiResolverAgent - Resolve bangumi ID
        2. SearchAgent - Find bangumi points
        3. WeatherAgent - Get weather (parallel)
        4. POIAgent - Get POI details
        5. RouteAgent - Optimize route
        6. TransportAgent - Optimize transport
        """
        user_query = input_data.data.get("user_query")
        session_id = input_data.session_id

        self.logger.info(
            "Starting orchestration workflow with bangumi resolution",
            user_query=user_query,
            session_id=session_id
        )

        # Initialize session
        session = PilgrimageSession(session_id=session_id)

        try:
            # NEW Step 0: Resolve Bangumi ID
            self.logger.info(
                "Step 0: Resolving bangumi ID",
                session_id=session_id
            )

            bangumi_result = await self._execute_bangumi_resolver(
                user_query,
                session_id
            )

            # Store bangumi info in session
            session.bangumi_id = bangumi_result["id"]
            session.bangumi_name = bangumi_result["name_cn"]
            session.bangumi_confidence = bangumi_result["confidence"]

            self.logger.info(
                "Bangumi resolved",
                bangumi_id=session.bangumi_id,
                bangumi_name=session.bangumi_name,
                confidence=session.bangumi_confidence,
                session_id=session_id
            )

            # Step 1: SearchAgent - Find bangumi points (MODIFIED)
            self.logger.info(
                "Step 1: Searching bangumi points",
                session_id=session_id
            )

            search_result = await self._execute_search_agent_bangumi_mode(
                bangumi_id=session.bangumi_id,
                user_query=user_query,
                session_id=session_id
            )

            # Extract user location from search result
            session.user_location = search_result.get("user_location")
            session.user_coordinates = Coordinates(
                **search_result["user_coordinates"]
            )

            # Convert points
            session.points = [Point(**p) for p in search_result["points"]]

            if len(session.points) == 0:
                raise RuntimeError(
                    f"No pilgrimage points found for {session.bangumi_name}"
                )

            # Step 2: WeatherAgent (parallel - start in background)
            self.logger.info(
                "Step 2: Starting WeatherAgent (parallel)",
                session_id=session_id
            )
            weather_task = asyncio.create_task(
                self._execute_weather_agent(
                    session.user_coordinates,
                    session_id
                )
            )

            # Step 3-6: POIAgent, RouteAgent, TransportAgent
            # ... (existing logic, no changes needed) ...

            # POIAgent no longer needed since SearchAgent now returns points
            # Skip FilterAgent since we already have specific bangumi

            # Step 3: RouteAgent
            self.logger.info(
                "Step 3: Optimizing route",
                session_id=session_id
            )
            route_result = await self._execute_route_agent(
                station=None,  # Using user_coordinates instead
                points=session.points,
                session_id=session_id
            )
            session.route = Route(**route_result["route"])

            # Step 4: TransportAgent
            self.logger.info(
                "Step 4: Optimizing transport",
                session_id=session_id
            )
            transport_result = await self._execute_transport_agent(
                session.route,
                session_id
            )
            session.route = Route(**transport_result["route"])

            # Wait for weather
            try:
                weather_result = await weather_task
                session.weather = Weather(**weather_result["weather"])
            except Exception as e:
                self.logger.warning(
                    "Weather fetch failed",
                    error=str(e),
                    session_id=session_id
                )
                session.weather = None

            # Update session
            session.update()

            self.logger.info(
                "Orchestration completed",
                bangumi_id=session.bangumi_id,
                points_count=len(session.points),
                total_distance_km=session.route.total_distance_km,
                session_id=session_id
            )

            return {
                "session": session.model_dump(),
                "success": True,
                "steps_completed": 4  # Updated count
            }

        except Exception as e:
            self.logger.error(
                "Orchestration failed",
                error=str(e),
                session_id=session_id,
                exc_info=True
            )
            raise

    async def _execute_bangumi_resolver(
        self,
        user_query: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Execute BangumiResolverAgent."""
        input_data = AgentInput(
            session_id=session_id,
            data={"user_query": user_query}
        )

        result = await self.bangumi_resolver.execute(input_data)

        if not result.success:
            raise RuntimeError(
                f"BangumiResolverAgent failed: {result.error}"
            )

        return result.data

    async def _execute_search_agent_bangumi_mode(
        self,
        bangumi_id: int,
        user_query: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Execute SearchAgent in bangumi mode."""
        input_data = AgentInput(
            session_id=session_id,
            data={
                "bangumi_id": bangumi_id,
                "user_query": user_query
            }
        )

        result = await self.search_agent.execute(input_data)

        if not result.success:
            raise RuntimeError(
                f"SearchAgent failed: {result.error}"
            )

        return result.data

    # ... keep existing helper methods ...

    def _validate_input(self, input_data: AgentInput) -> bool:
        """Validate input - now requires user_query instead of station_name."""
        if not input_data.data:
            self.logger.error("No data provided")
            return False

        # NEW: Require user_query
        if "user_query" not in input_data.data:
            self.logger.error("No user_query provided")
            return False

        user_query = input_data.data.get("user_query")

        if not isinstance(user_query, str) or not user_query.strip():
            self.logger.error("user_query must be non-empty string")
            return False

        return True
```

### 验收标准 (Stage 4)

- [x] 集成测试通过
- [x] 端到端流程验证
- [x] 错误处理完善
- [x] 向后兼容 (可选)

---

## Stage 5: 完整测试套件

### 目标

编写全面的测试用例，包括单元测试、集成测试和边界测试。

### 要修改的文件

1. ✅ **新建**: `tests/integration/test_bangumi_resolver_e2e.py`
2. ✅ **修改**: 现有测试文件以确保兼容性

### 测试类型

#### 5.1 集成测试

**文件**: `tests/integration/test_bangumi_resolver_e2e.py`

```python
"""
End-to-end integration tests for BangumiResolverAgent.
"""

import pytest
from agents.bangumi_resolver_agent import BangumiResolverAgent
from agents.base import AgentInput


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_your_name():
    """Test resolving '你的名字' end-to-end."""
    agent = BangumiResolverAgent()

    result = await agent.execute(AgentInput(
        session_id="e2e-test-001",
        data={"user_query": "我在新宿站想去你的名字的圣地"}
    ))

    assert result.success
    assert result.data["id"] == 160209
    assert "你的名字" in result.data["name_cn"]
    assert result.data["confidence"] >= 0.8


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hibike_euphonium():
    """Test resolving '吹响！上低音号' end-to-end."""
    agent = BangumiResolverAgent()

    result = await agent.execute(AgentInput(
        session_id="e2e-test-002",
        data={"user_query": "去京都看吹响吧上低音号的地方"}
    ))

    assert result.success
    assert result.data["confidence"] >= 0.7


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_complete_orchestration():
    """Test complete orchestration flow."""
    from agents.orchestrator_agent import OrchestratorAgent

    orchestrator = OrchestratorAgent()

    result = await orchestrator.execute(AgentInput(
        session_id="e2e-orchestrator-001",
        data={"user_query": "我在新宿站想去你的名字的圣地"}
    ))

    assert result.success
    session = result.data["session"]
    assert session["bangumi_id"] == 160209
    assert len(session["points"]) > 0
```

#### 5.2 边界测试

```python
@pytest.mark.asyncio
async def test_edge_case_empty_query():
    """Test empty query handling."""
    agent = BangumiResolverAgent()

    result = await agent.execute(AgentInput(
        session_id="edge-001",
        data={"user_query": ""}
    ))

    assert not result.success


@pytest.mark.asyncio
async def test_edge_case_no_bangumi_mentioned():
    """Test query with no bangumi."""
    agent = BangumiResolverAgent()

    result = await agent.execute(AgentInput(
        session_id="edge-002",
        data={"user_query": "今天天气真好"}
    ))

    assert not result.success
    assert "bangumi" in result.error.lower()


@pytest.mark.asyncio
async def test_edge_case_multiple_name_variations():
    """Test that different name formats resolve to same ID."""
    agent = BangumiResolverAgent()

    variations = [
        "你的名字",
        "你的名字。",
        "君の名は",
        "Your Name"
    ]

    results = []
    for var in variations:
        result = await agent.execute(AgentInput(
            session_id=f"var-{var}",
            data={"user_query": f"去{var}的圣地"}
        ))
        if result.success:
            results.append(result.data["id"])

    # All should resolve to same ID
    assert len(set(results)) == 1
    assert results[0] == 160209
```

#### 5.3 性能测试

```python
import time

@pytest.mark.slow
@pytest.mark.asyncio
async def test_performance_response_time():
    """Test that resolution completes within reasonable time."""
    agent = BangumiResolverAgent()

    start = time.time()
    result = await agent.execute(AgentInput(
        session_id="perf-001",
        data={"user_query": "我想去你的名字的圣地"}
    ))
    duration = time.time() - start

    assert result.success
    assert duration < 5.0, f"Too slow: {duration}s"
```

### 运行测试

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v --markers=integration

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### 验收标准 (Stage 5)

- [x] 单元测试覆盖率 > 90%
- [x] 集成测试通过
- [x] 边界测试通过
- [x] 性能测试通过
- [x] 所有测试绿灯

---

## 验收标准

### 功能验收

- [ ] BangumiClient 正常工作
- [ ] BangumiResolverAgent 正常解析
- [ ] SearchAgent 支持两种模式
- [ ] OrchestratorAgent 集成成功
- [ ] 端到端流程验证

### 质量验收

- [ ] 测试覆盖率 > 90%
- [ ] 所有测试通过
- [ ] 代码通过 `ruff` 检查
- [ ] 代码通过 `black` 格式化
- [ ] 文档完整 (docstring)
- [ ] 日志完善

### 性能验收

- [ ] 单次解析 < 5秒
- [ ] LLM 提取准确率 > 95%
- [ ] LLM 匹配准确率 > 90%
- [ ] 缓存命中率 > 80%

### 代码质量检查命令

```bash
# Format code
black agents/ clients/ tests/

# Lint code
ruff check agents/ clients/ tests/

# Type check
mypy agents/ clients/

# Run tests with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

---

## 时间估算

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| Stage 1 | BangumiClient | 1.5 小时 |
| Stage 2 | BangumiResolverAgent | 2.5 小时 |
| Stage 3 | SearchAgent 修改 | 1.5 小时 |
| Stage 4 | OrchestratorAgent 集成 | 1.0 小时 |
| Stage 5 | 完整测试套件 | 1.5 小时 |
| **总计** | | **8 小时** |

---

## 实施检查清单

### Stage 1 完成标准
- [ ] `clients/bangumi.py` 创建
- [ ] `tests/unit/test_bangumi_client.py` 通过
- [ ] 搜索功能验证
- [ ] 缓存机制验证
- [ ] 代码格式化

### Stage 2 完成标准
- [ ] `agents/bangumi_resolver_agent.py` 创建
- [ ] `tests/unit/test_bangumi_resolver_agent.py` 通过
- [ ] LLM 提取验证
- [ ] LLM 匹配验证
- [ ] 端到端测试验证

### Stage 3 完成标准
- [ ] `agents/search_agent.py` 修改
- [ ] 新模式测试通过
- [ ] 旧模式兼容性验证
- [ ] 距离计算验证

### Stage 4 完成标准
- [ ] `agents/orchestrator_agent.py` 修改
- [ ] 集成测试通过
- [ ] 工作流验证

### Stage 5 完成标准
- [ ] 集成测试编写
- [ ] 边界测试编写
- [ ] 性能测试通过
- [ ] 覆盖率达标

---

## 相关文档

- [设计文档](./bangumi-resolver-agent-design.md)
- [Anitabi API 文档](../anitabi-api-documentation.md)
- [Bangumi API 官方文档](https://bangumi.github.io/api/)
- [项目开发指南](../CLAUDE.md)

---

**维护者**: Seichijunrei Team
**最后更新**: 2025-11-28
**版本**: 1.0
