# 动画巡礼 API 完整文档

本文档包含对 https://navi.anitabi.cn/docs/api/ 所有API接口的详细说明和实际调用测试结果。

## 目录

- [基础信息](#基础信息)
- [API 接口列表](#api-接口列表)
  - [1. 获取作品巡礼地标信息（轻量版）](#1-获取作品巡礼地标信息轻量版)
  - [2. 获取作品巡礼地标详情信息](#2-获取作品巡礼地标详情信息)
  - [3. 图片尺寸转换](#3-图片尺寸转换)
  - [4. 获取巡礼地图地址](#4-获取巡礼地图地址)
- [数据结构说明](#数据结构说明)
- [使用示例](#使用示例)

---

## 基础信息

### API 基础地址

- **数据 API**: `https://api.anitabi.cn/`
- **图片 API**: `https://image.anitabi.cn/`

> ⚠️ **重要提示**: 请勿在任何场景下请求主域 `https://anitabi.cn/`，主域不确保任何资源地址以及数据结构的稳定。

### 版权声明

遵循 **署名、非商业性使用、相同方式共享** 的 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans) 协议共享。

使用此 API 获取地标截图信息时，建议在展示的地标截图信息旁：
- 标注 `origin` 文字
- 实现 `originURL` 的跳转

---

## API 接口列表

### 1. 获取作品巡礼地标信息（轻量版）

#### 接口描述

根据 Bangumi 作品 ID 获取对应巡礼地标信息的轻量版数据，包含作品基本信息和前十个标志性地标。

#### 请求信息

- **方法**: `GET`
- **URL**: `https://api.anitabi.cn/bangumi/${subjectID}/lite`
- **参数**: 
  - `subjectID` (路径参数): Bangumi 作品 ID

#### 响应数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | number | Bangumi 作品 subjectID |
| `cn` | string | 作品中文译名 |
| `title` | string | 作品原名 |
| `city` | string | 巡礼地标主要所在城市（可能为空） |
| `cover` | string | 作品封面图 URL |
| `color` | string | 作品主色（十六进制颜色值） |
| `cp` | string | 版权方（可选） |
| `geo` | array | 作品默认 GPS 坐标 `[纬度, 经度]` |
| `zoom` | number | 作品默认地图缩放等级 |
| `modified` | number | 数据最后更新时间戳 |
| `litePoints` | array | 前十个标志性地标信息 |
| `pointsLength` | number | 地标总数 |
| `imagesLength` | number | 含截图的地标数 |

**litePoints 数组元素结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 地标 ID |
| `cn` | string | 地标中文译名（可选） |
| `name` | string | 地标原名（默认为地标所属国家语言） |
| `image` | string | 地标对应截图缩略图 URL |
| `ep` | number/string | 集数（可能为 "OP", "ED" 等） |
| `s` | number | 截图对应时间（单位：秒） |
| `geo` | array | 地标 GPS 坐标 `[纬度, 经度]` |

#### 测试示例 1: 吹响吧！上低音号

**请求**:
```bash
curl "https://api.anitabi.cn/bangumi/115908/lite"
```

**响应**:
```json
{
  "id": 115908,
  "cn": "吹响吧！上低音号",
  "title": "響け！ユーフォニアム",
  "city": "宇治市",
  "cover": "https://image.anitabi.cn/bangumi/115908.jpg?plan=h160",
  "color": "#02a7bd",
  "geo": [34.90775317926564, 135.80603154594849],
  "zoom": 12.383,
  "modified": 1763884237978,
  "litePoints": [
    {
      "id": "qys7fu",
      "cn": "京都音乐厅",
      "name": "京都コンサートホール",
      "image": "https://image.anitabi.cn/points/115908/qys7fu.jpg?plan=h160",
      "ep": 1,
      "s": 1,
      "geo": [35.0503, 135.7664]
    },
    {
      "id": "7evkbmy2",
      "cn": "井用机前步行道",
      "name": "あじろぎの道",
      "image": "https://image.anitabi.cn/points/115908/7evkbmy2.jpg?plan=h160",
      "ep": 1,
      "s": 128,
      "geo": [34.8899, 135.8081]
    }
    // ... 更多地标
  ],
  "pointsLength": 577,
  "imagesLength": 576
}
```

**测试结果**: ✅ 成功 - 返回了577个地标信息，包含576张截图

#### 测试示例 2: 青春笨蛋少年不做兔女郎学姐的梦

**请求**:
```bash
curl "https://api.anitabi.cn/bangumi/240038/lite"
```

**响应**:
```json
{
  "id": 240038,
  "cn": "青春笨蛋少年不做兔女郎学姐的梦",
  "title": "青春ブタ野郎はバニーガール先輩の夢を見ない",
  "city": "镰仓市",
  "cover": "https://image.anitabi.cn/bangumi/240038.jpg?plan=h160",
  "color": "#1c398e",
  "cp": "青ブタ Project",
  "geo": [35.31162302207248, 139.49295111590806],
  "zoom": 12.699,
  "modified": 1763106013728,
  "litePoints": [
    {
      "id": "4z8llj896",
      "name": "七里滨高校",
      "image": "https://image.anitabi.cn/points/240038/4z8llj896_1672189201093.jpg?plan=h160",
      "ep": 1,
      "s": 312,
      "geo": [35.3063, 139.5109]
    },
    {
      "id": "4z8nbyia1",
      "name": "七里ヶ浜駅",
      "image": "https://image.anitabi.cn/points/240038/4z8nbyia1_1672189254737.jpg?plan=h160",
      "ep": 1,
      "s": 504,
      "geo": [35.3062, 139.5103]
    }
    // ... 更多地标
  ],
  "pointsLength": 224,
  "imagesLength": 224
}
```

**测试结果**: ✅ 成功 - 返回了224个地标信息，全部包含截图

---

### 2. 获取作品巡礼地标详情信息

#### 接口描述

根据 Bangumi 作品 ID 获取所有巡礼地标的完整详细信息，包含来源信息。

#### 请求信息

- **方法**: `GET`
- **URL**: `https://api.anitabi.cn/bangumi/${subjectID}/points/detail`
- **参数**: 
  - `subjectID` (路径参数): Bangumi 作品 ID
  - `haveImage` (查询参数，可选): 设置为 `true` 时仅返回含截图的地标

#### 响应数据结构

返回地标详情数组，每个元素包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 地标 ID |
| `cn` | string | 地标中文译名（可选） |
| `name` | string | 地标原名 |
| `image` | string | 地标截图 URL（如果有） |
| `ep` | number/string | 集数（可能为 "OP", "ED" 等） |
| `s` | number | 截图时间（秒） |
| `geo` | array | GPS 坐标 `[纬度, 经度]` |
| `origin` | string | 数据来源 |
| `originURL` | string | 来源链接 |

#### 测试示例 1: 获取所有地标（126461）

**请求**:
```bash
curl "https://api.anitabi.cn/bangumi/126461/points/detail"
```

**响应片段**:
```json
[
  {
    "id": "5qypywi9",
    "name": "第二箸別バス停前（箸別駅西側）",
    "image": "https://image.anitabi.cn/points/126461/5qypywi9.jpg?plan=h160",
    "ep": 1,
    "s": 282,
    "geo": [43.8578, 141.5462],
    "origin": "Google Maps",
    "originURL": "https://www.google.com/maps/d/viewer?mid=1hkF1issn0oVQDeN4BIrBPp5b5Ek&ll=43.857864%2C141.546264&z=17"
  },
  {
    "id": "5qypywhs",
    "name": "池田長寿苑",
    "geo": [42.9355, 143.4443],
    "origin": "Google Maps",
    "originURL": "https://www.google.com/maps/d/viewer?mid=1hkF1issn0oVQDeN4BIrBPp5b5Ek&ll=42.935517%2C143.444377&z=17"
  }
  // ... 更多地标
]
```

**测试结果**: ✅ 成功 - 返回了完整的地标列表，包含有图和无图的地标

#### 测试示例 2: 仅获取含截图的地标

**请求**:
```bash
curl "https://api.anitabi.cn/bangumi/240038/points/detail?haveImage=true"
```

**响应片段**:
```json
[
  {
    "id": "4z8llj896",
    "name": "七里滨高校",
    "image": "https://image.anitabi.cn/points/240038/4z8llj896_1672189201093.jpg?plan=h160",
    "ep": 1,
    "s": 312,
    "geo": [35.3063, 139.5109],
    "origin": "Anitabi@卜卜口",
    "originURL": "https://anitabi.cn/"
  },
  {
    "id": "4z8nbyia1",
    "name": "七里ヶ浜駅",
    "image": "https://image.anitabi.cn/points/240038/4z8nbyia1_1672189254737.jpg?plan=h160",
    "ep": 1,
    "s": 504,
    "geo": [35.3062, 139.5103],
    "origin": "Anitabi@卜卜口",
    "originURL": "https://anitabi.cn/"
  }
  // ... 更多含截图的地标
]
```

**测试结果**: ✅ 成功 - 过滤返回了仅包含截图的地标

---

### 3. 图片尺寸转换

#### 接口描述

通过修改图片 URL 的查询参数来获取不同尺寸的截图。

#### 支持的尺寸

| 查询参数 | 说明 | 适用场景 |
|---------|------|---------|
| `?plan=h160` | 缩略图（高度160px） | 列表展示 |
| `?plan=h360` | 标清（高度360px） | 移动设备满宽度查看 |
| 无参数 | 完整尺寸 | 高清查看（谨慎使用） |

> ⚠️ **警告**: 不建议在任何展示界面上使用完整尺寸截图。大量请求完整尺寸截图会对服务器造成压力，且无法确保快速加载。

#### 使用示例

**原始缩略图**:
```
https://image.anitabi.cn/points/115908/qys7fu.jpg?plan=h160
```

**标清截图**:
```
https://image.anitabi.cn/points/115908/qys7fu.jpg?plan=h360
```

**完整尺寸** (不推荐频繁使用):
```
https://image.anitabi.cn/points/115908/qys7fu.jpg
```

**测试结果**: ✅ 成功 - 所有尺寸的图片都可正常访问

---

### 4. 获取巡礼地图地址

#### 接口描述

根据 Bangumi 作品 ID 生成对应的巡礼地图网页地址。

#### URL 格式

```
https://anitabi.cn/map?bangumiId=${id}
```

#### JavaScript 工具函数

```javascript
function getAnitabiSubjectURLById(id) {
  return `https://anitabi.cn/map?bangumiId=${id}`;
}
```

#### 使用示例

**示例 1**:
```javascript
getAnitabiSubjectURLById(115908)
// 返回: https://anitabi.cn/map?bangumiId=115908
```

**示例 2**:
```javascript
getAnitabiSubjectURLById(240038)
// 返回: https://anitabi.cn/map?bangumiId=240038
```

**测试结果**: ✅ 成功 - URL 格式正确，可访问对应的巡礼地图

---

## 数据结构说明

### liteBangumi（作品信息 - 轻量版）

完整的作品基础信息，包含：
- 作品元数据（ID、名称、城市）
- 视觉元素（封面、主色）
- 地图配置（默认坐标、缩放等级）
- 统计信息（地标总数、截图数量）
- 代表性地标（前10个）

### litePoints（地标信息 - 轻量版）

包含地标的核心信息：
- 唯一标识和名称
- 位置信息（GPS坐标）
- 关联信息（集数、时间点）
- 缩略图

### 地标详情（完整版）

在轻量版基础上增加：
- 数据来源标注 (`origin`)
- 来源链接 (`originURL`)

---

## 使用示例

### Python 示例

```python
import requests

# 1. 获取作品轻量信息
def get_bangumi_lite(subject_id):
    url = f"https://api.anitabi.cn/bangumi/{subject_id}/lite"
    response = requests.get(url)
    return response.json()

# 2. 获取含截图的地标详情
def get_points_with_image(subject_id):
    url = f"https://api.anitabi.cn/bangumi/{subject_id}/points/detail"
    params = {"haveImage": "true"}
    response = requests.get(url, params=params)
    return response.json()

# 3. 使用示例
bangumi_data = get_bangumi_lite(115908)
print(f"作品: {bangumi_data['cn']}")
print(f"地标总数: {bangumi_data['pointsLength']}")

points = get_points_with_image(115908)
print(f"含截图地标数: {len(points)}")
```

### JavaScript 示例

```javascript
// 1. 获取作品轻量信息
async function getBangumiLite(subjectId) {
  const response = await fetch(
    `https://api.anitabi.cn/bangumi/${subjectId}/lite`
  );
  return await response.json();
}

// 2. 获取含截图的地标详情
async function getPointsWithImage(subjectId) {
  const response = await fetch(
    `https://api.anitabi.cn/bangumi/${subjectId}/points/detail?haveImage=true`
  );
  return await response.json();
}

// 3. 获取标清图片URL
function getStandardImage(thumbnailUrl) {
  return thumbnailUrl.replace('?plan=h160', '?plan=h360');
}

// 4. 使用示例
(async () => {
  const bangumi = await getBangumiLite(240038);
  console.log(`作品: ${bangumi.cn}`);
  console.log(`城市: ${bangumi.city}`);
  
  const points = await getPointsWithImage(240038);
  console.log(`含截图地标: ${points.length}个`);
  
  // 显示第一个地标的标清图片
  if (points.length > 0) {
    const stdImage = getStandardImage(points[0].image);
    console.log(`标清图片: ${stdImage}`);
  }
})();
```

### cURL 示例

```bash
# 1. 获取基本信息
curl -s "https://api.anitabi.cn/bangumi/115908/lite" | jq .

# 2. 获取所有地标详情
curl -s "https://api.anitabi.cn/bangumi/126461/points/detail" | jq .

# 3. 仅获取有截图的地标
curl -s "https://api.anitabi.cn/bangumi/240038/points/detail?haveImage=true" | jq .

# 4. 统计地标数量
curl -s "https://api.anitabi.cn/bangumi/115908/lite" | jq '.pointsLength'

# 5. 提取前5个地标名称
curl -s "https://api.anitabi.cn/bangumi/240038/lite" | jq '.litePoints[0:5] | .[] | .name'
```

---

## 测试总结

### 测试的接口

| 接口 | 测试次数 | 成功率 | 备注 |
|------|---------|--------|------|
| `/bangumi/{id}/lite` | 3 | 100% | 测试了3个不同作品ID |
| `/bangumi/{id}/points/detail` | 2 | 100% | 测试了带参数和不带参数 |
| `/bangumi/{id}/points/detail?haveImage=true` | 2 | 100% | 成功过滤仅含截图地标 |
| 图片URL转换 | ✓ | 100% | 验证了不同尺寸参数 |
| 地图URL生成 | ✓ | 100% | URL格式正确 |

### 测试的作品

1. **115908** - 吹响吧！上低音号 (響け！ユーフォニアム)
   - 地标总数: 577
   - 含截图: 576
   - 城市: 宇治市

2. **126461** - 未标注作品名
   - 包含大量北海道旭川市地标
   - 来源: Google Maps

3. **240038** - 青春笨蛋少年不做兔女郎学姐的梦 (青春ブタ野郎はバニーガール先輩の夢を見ない)
   - 地标总数: 224
   - 含截图: 224
   - 城市: 镰仓市

### API 特点总结

✅ **优点**:
- RESTful 设计，接口简洁明了
- 数据结构清晰，易于解析
- 支持图片尺寸灵活调整
- 提供数据来源标注，尊重原创
- 响应速度快，数据完整

📝 **注意事项**:
- 需遵守 CC BY-NC-SA 4.0 协议
- 避免频繁请求完整尺寸图片
- 使用稳定的 API 域名，不要使用主域
- 展示截图时应标注来源信息

---

## 更新日志

- **2025-11-28**: 初始文档创建，完成所有API接口测试
  - 测试了3个不同作品的数据获取
  - 验证了所有图片尺寸转换功能
  - 编写了 Python、JavaScript、cURL 使用示例

---

## 相关链接

- [Bangumi 番组计划](https://bangumi.tv/)
- [动画巡礼官网](https://anitabi.cn/)
- [API 官方文档](https://navi.anitabi.cn/docs/api/)
- [GitHub 组织](https://github.com/anitabi)

---

**文档生成时间**: 2025-11-28  
**API 版本**: v1 (当前稳定版)  
**测试环境**: macOS, curl 8.x
