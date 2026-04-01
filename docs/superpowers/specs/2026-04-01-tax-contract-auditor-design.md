# 税务合同审计AI助手 - 设计文档

## 项目概述

开发一个税务合同审计AI助手，通过MCP连接Elasticsearch数据库（含17万篇税务法规），对输入的税务合同文档（docx）进行合规审计，找出不合规、高风险条款，输出审计报告（docx格式）。

## 系统架构

```
React前端 → FastAPI后端 → MCP Client → Elasticsearch(17万法规)
                        ↓
                  GLM-5(条款分析)
```

**技术栈：**
- 前端：React
- 后端：FastAPI（异步Python）
- AI模型：阿里云百炼 GLM-5
- 数据源：MCP Server (localhost:8000) → Elasticsearch
- 文档处理：python-docx

**端口分配：**
- MCP Server: 8000（已存在）
- FastAPI后端: 8001
- React前端: 3000

## 处理流程

```
步骤1: 合同上传
用户上传 → FastAPI接收 → 保存临时文件

步骤2: 文档解析
python-docx → 提取章节结构 → 得到[(章节名, 条款文本)]列表

步骤3: 逐章节分析（循环）

  3.1 GLM-5提取关键词
      输入: 条款文本
      输出: ["关键词1", "关键词2", ...]

      ↓

  3.2 MCP搜索法规
      search_chinataxcenter(query_text=关键词, effectiveness="有效")
      输出: [(法规标题, 法规内容, ...)]

      ↓

  3.3 GLM-5合规判定
      输入: 条款文本 + 相关法规内容
      输出: {
        risk_level: "合规/高风险/不合规",
        reason: "不合规原因分析",
        violated_regulations: ["法规标题1", ...],
        suggestion: "修改建议"
      }

步骤4: 生成报告
收集所有章节分析结果 → python-docx生成审计报告
按原合同章节组织，包含：风险等级、法规引用、原因、修改建议

步骤5: 返回用户
FastAPI返回docx文件 → 前端下载
```

## API设计

### 后端API

| 接口 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/api/upload` | POST | 上传合同审计 | docx文件 | 审计报告docx文件 |

**请求格式：**
```
POST /api/upload
Content-Type: multipart/form-data
file: <合同.docx>
```

**响应格式：**
```
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="审计报告.docx"
<审计报告.docx 二进制内容>
```

### MCP调用

只使用 `search_chinataxcenter` 工具：
- 使用 `query_text` 全文检索
- 过滤 `effectiveness="有效"` 的法规
- 不使用 `taxType` 参数

```python
search_chinataxcenter(
    query_text="发票 付款期限 违约金",
    effectiveness="有效",
    size=10
)
```

## 前端设计

**页面组件：**
- 文件上传组件（支持拖拽上传docx）
- 进度显示（实时显示分析进度）
- 结果下载按钮

**用户流程：**
1. 上传合同docx文件
2. 点击"开始审计"
3. 显示处理进度
4. 完成后点击"下载审计报告"

## 数据模型

```python
# 合同章节
class ContractSection(BaseModel):
    section_name: str       # 章节名称
    content: str            # 条款原文

# 法规搜索结果
class Regulation(BaseModel):
    title: str              # 法规标题
    content: str            # 法规内容
    issuing_body: str       # 发文机关
    published_date: str     # 发布日期

# 单章节审计结果
class SectionAuditResult(BaseModel):
    section_name: str
    original_content: str
    risk_level: str         # "合规"/"高风险"/"不合规"
    violated_regulations: List[str]
    reason: str             # 不合规原因分析
    suggestion: str         # 修改建议

# 完整审计报告
class AuditReport(BaseModel):
    sections: List[SectionAuditResult]
    summary: str            # 整体风险摘要
```

## Prompt设计

### Prompt 1 - 关键词提取

```
你是一个税务合同分析专家。请从以下合同条款中提取用于搜索相关税务法规的关键词。

条款内容：
{条款文本}

要求：
1. 提取3-5个关键词，聚焦税务合规相关内容
2. 关键词应能匹配到税务法规库中的相关文档
3. 输出格式：JSON数组，如 ["发票", "付款期限", "违约金"]

请直接输出关键词JSON数组，不要其他解释。
```

### Prompt 2 - 合规判定

```
你是一个税务合同合规审计专家。请根据相关税务法规，判断以下合同条款的合规性。

【条款内容】
{条款文本}

【相关法规】
{法规列表，每个包含标题和内容}

请判断该条款是否存在税务合规风险，并输出以下JSON格式：
{
  "risk_level": "合规/高风险/不合规",
  "violated_regulations": ["违反的法规标题1", "法规标题2"],
  "reason": "详细分析该条款为什么存在风险或不合规，引用法规原文说明",
  "suggestion": "如果存在问题，给出具体的修改建议或替代条款"
}

判定标准：
- 合规：条款完全符合税务法规要求
- 高风险：条款存在明显风险点，可能违规但需进一步确认
- 不合规：条款明确违反税务法规

请直接输出JSON，不要其他解释。
```

## 项目文件结构

```
D:\EY\contractAgent\
├── mcp/                          # 现有MCP服务器（不变）
│
├── backend/                      # 新建FastAPI后端
│   ├── main.py                   # FastAPI入口
│   ├── config.py                 # 配置管理
│   ├── services/
│   │   ├── contract_parser.py    # docx解析
│   │   ├── mcp_client.py         # MCP HTTP调用
│   │   ├── ai_analyzer.py        # GLM-5调用
│   │   └── report_generator.py   # 生成报告docx
│   ├── models/
│   │   └── schemas.py            # Pydantic模型
│   └── requirements.txt
│
├── frontend/                     # 新建React前端
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   └── DownloadButton.tsx
│   │   └── api/
│   │   │   └── upload.ts
│   └── public/
│
└── docs/
    └── superpowers/specs/
        └── 2026-04-01-tax-contract-auditor-design.md
```

## 报告输出格式

审计报告docx按原合同章节组织，每个章节包含：

| 内容 | 说明 |
|------|------|
| 章节名称 | 原合同章节标题 |
| 条款原文 | 该章节的条款文本 |
| 风险等级 | 合规/高风险/不合规 |
| 违反法规 | 引用的法规标题列表 |
| 原因分析 | 为什么存在风险或不合规 |
| 修改建议 | 具体的修改建议或替代条款 |

不包含法规链接URL。

## 成功标准

1. 能正确解析docx合同文档，提取章节结构
2. 能通过MCP搜索到相关税务法规
3. 能准确判定条款合规性（三级风险）
4. 能生成格式正确的审计报告docx
5. 前端能上传文件并下载报告