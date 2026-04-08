# 外部搜索工具集成设计

## 概述

为 deep_paper_qa 的 LangGraph 多管线 Agent 增加三个外部搜索工具：arXiv API、Semantic Scholar API、Tavily Search API。补充本地数据库（81,913 篇 AI 会议论文，2020-2025）无法覆盖的场景。

## 设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 可用管线 | 所有管线 | 各场景都可能需要外部数据补充 |
| 使用策略 | 本地优先，fallback 联网 | 通过 prompt 策略指导，不写编排代码 |
| 工具间分工 | Agent 自主判断 | prompt 描述每个工具特长，LLM 自行选择 |
| 封装方式 | 全部自己封装 `@tool` | 统一风格，用 `aiohttp` 直接调 API |
| 返回格式 | 紧凑风格 | 5-10 条结果，摘要截断 800 字符，与现有工具一致 |

## 工具接口

### 1. search_arxiv

```python
@tool
async def search_arxiv(
    query: str,           # 搜索关键词
    max_results: int = 5, # 最多返回条数
    category: str = "",   # arXiv 分类过滤，如 "cs.AI", "cs.CL"
) -> str
```

- **API**: `http://export.arxiv.org/api/query`
- **解析**: `xml.etree.ElementTree` 解析 Atom XML
- **返回字段**: 标题、作者（前3）、年份、分类、摘要（截断 800 字符）、arXiv 链接
- **适用场景**: 最新预印本、arXiv 独有论文、特定分类搜索

### 2. search_semantic_scholar

```python
@tool
async def search_semantic_scholar(
    query: str,           # 搜索关键词
    max_results: int = 5, # 最多返回条数
    fields_of_study: str = "",  # 领域过滤，如 "Computer Science"
    year: str = "",       # 年份过滤，如 "2024-2026"
) -> str
```

- **API**: `https://api.semanticscholar.org/graph/v1/paper/search`
- **请求字段**: `title,abstract,year,citationCount,authors,venue,openAccessPdf,externalIds`
- **返回字段**: 标题、作者（前3）、年份、venue、引用数、摘要（截断 800 字符）、PDF 链接
- **认证**: 可选 API key（通过 config，提高速率限制）
- **适用场景**: 引用数据、跨数据库论文搜索、领域过滤

### 3. search_web

```python
@tool
async def search_web(
    query: str,           # 搜索关键词
    max_results: int = 5, # 最多返回条数
) -> str
```

- **API**: `https://api.tavily.com/search`
- **返回字段**: 标题、摘要片段、URL、相关度评分
- **认证**: 必填 API key
- **适用场景**: 非论文信息（会议日期、行业动态、开源项目、博客文章）

## 配置

### config.py 新增字段

```python
arxiv_max_results: int = 5
semantic_scholar_api_key: str = ""       # 可选，空则无认证
semantic_scholar_max_results: int = 5
tavily_api_key: str = ""                 # 必填
tavily_max_results: int = 5
external_search_timeout: int = 15        # 三个工具共用超时（秒）
```

### .env 新增

```
SEMANTIC_SCHOLAR_API_KEY=       # 可选
TAVILY_API_KEY=sk-xxx           # 必填
```

### 依赖

- 不引入新 SDK，全部用 `aiohttp` 直接调 API
- arXiv XML 解析用标准库 `xml.etree.ElementTree`
- 需确认 `aiohttp` 在 pyproject.toml 中已声明

## Prompt 策略

### 工具选择规则（写入各管线 system prompt）

```
## 外部搜索工具
你拥有三个联网搜索工具：search_arxiv、search_semantic_scholar、search_web。

### 使用原则
1. **本地优先**：优先使用 execute_sql、search_abstracts、vector_search 查询本地数据库
2. **联网补充**：以下情况使用外部搜索：
   - 本地搜索结果不足（少于 3 条相关结果）
   - 用户明确询问数据库范围外的内容（2026年论文、非收录会议、非论文信息）
   - 需要引用数据、论文推荐、全文片段等本地数据库不具备的信息

### 工具特长
- search_arxiv：最新预印本、arXiv 特定分类、获取 PDF 链接
- search_semantic_scholar：引用数据、跨数据库搜索、领域过滤
- search_web：非学术信息（会议日期、行业动态、开源项目、教程）
```

### 各管线适配

- **general**: tool call 上限从 4 调到 6（允许本地+联网各一轮）
- **research**: 每个子问题允许额外 1 次联网 call
- **trend / reading / compare**: 适用同样的"本地优先"原则

### 工具注册

所有子图构建 agent 时传入全部 6 个工具：

```python
tools = [execute_sql, search_abstracts, vector_search,
         search_arxiv, search_semantic_scholar, search_web]
```

## 错误处理

### 统一降级策略

三个工具统一处理，不抛异常，返回提示信息：

- **超时** → `"搜索超时，请稍后重试或使用本地数据库查询。"`
- **网络错误** → `"外部服务暂不可用，请使用本地数据库查询。"`
- **API 错误（429/500）** → `"外部 API 返回错误 ({status})，请稍后重试。"`
- **无结果** → `"未找到相关论文。"`

Agent 收到错误提示后自然 fallback 到本地工具。

### arXiv XML 容错

缺失字段用空字符串填充，不中断整个结果。

### 不做的事

- 不做重试逻辑（单次失败即返回错误信息）
- 不做结果缓存
- 不做 API 限频控制（靠超时兜底）

## 文件结构

```
src/deep_paper_qa/tools/
├── execute_sql.py          # 现有
├── search_abstracts.py     # 现有
├── vector_search.py        # 现有
├── search_arxiv.py         # 新增
├── search_semantic_scholar.py  # 新增
└── search_web.py           # 新增
```
