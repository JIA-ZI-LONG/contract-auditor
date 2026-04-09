# LangChain-Only Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构项目为纯 LangChain 1.x LCEL 架构，移除 LangGraph 和 SSE 代码。

**Architecture:** 使用 RunnableLambda 包装异步函数为 Pipeline，LCEL `|` 操作符组合 prompt + llm 为 chains，`@tool` 装饰器定义工具，简单 POST API 无流式。

**Tech Stack:** LangChain 1.x, LCEL, FastAPI, Pydantic, python-docx

---

## File Structure

```
backend/
├── chains/                    # 新建目录
│   ├── __init__.py           # 导出所有 chains
│   ├── llm.py                # LLM 单例
│   ├── prompts.py            # Prompt 模板（从 graph/prompts.py 迁移）
│   ├── keyword_chain.py      # 关键词提取 chain
│   ├── judge_chain.py        # 合规判定 chain
│   └── audit_pipeline.py     # 主 pipeline
├── tools/                     # 新建目录
│   ├── __init__.py           # 导出所有 tools
│   ├── parse_contract.py     # 解析合同工具
│   └── search_regulations.py # 搜索法规工具
├── services/                  # 保留不变
├── models/
│   ├── schemas.py            # 删除 AuditProgress 类
│   └── __init__.py           # 更新导出
├── tests/
│   ├── test_keyword_chain.py      # 新增
│   ├── test_judge_chain.py        # 新增
│   ├── test_audit_pipeline.py     # 新增
│   ├── test_contract_parser.py    # 保留
│   ├── test_mcp_client.py         # 保留
│   └── test_report_generator.py   # 保留
├── main.py                    # 简化 API
├── config.py                  # 保留
├── requirements.txt           # 移除 langgraph
└── pytest.ini                 # 保留

删除：
├── graph/                     # 整个目录
```

---

## Task 1: 创建 chains 目录和 LLM 配置

**Files:**
- Create: `backend/chains/__init__.py`
- Create: `backend/chains/llm.py`
- Create: `backend/tests/test_llm.py`

- [ ] **Step 1: 创建 chains 目录**

```bash
mkdir -p backend/chains
```

- [ ] **Step 2: 创建 chains/__init__.py**

```python
# backend/chains/__init__.py

from .llm import get_llm
from .keyword_chain import keyword_chain
from .judge_chain import judge_chain
from .audit_pipeline import audit_pipeline

__all__ = ["get_llm", "keyword_chain", "judge_chain", "audit_pipeline"]
```

- [ ] **Step 3: 创建 chains/llm.py**

```python
# backend/chains/llm.py

"""
LLM 单例配置

演示 ChatOpenAI 配置：
- 支持任意 OpenAI 兼容 API
- 通过 base_url 配置自定义端点
"""

from langchain_openai import ChatOpenAI
from config import settings

_llm = None


def get_llm() -> ChatOpenAI:
    """
    获取 LLM 实例（单例模式）

    Returns:
        ChatOpenAI: 配置好的 LLM 实例
    """
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.bailian_model,
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.bailian_base_url,
            temperature=0.3
        )
    return _llm
```

- [ ] **Step 4: 创建测试 tests/test_llm.py**

```python
# backend/tests/test_llm.py

import pytest
from chains.llm import get_llm
from langchain_openai import ChatOpenAI


def test_get_llm_returns_chatopenai_instance():
    """测试 get_llm 返回 ChatOpenAI 实例"""
    llm = get_llm()
    assert isinstance(llm, ChatOpenAI)


def test_get_llm_returns_singleton():
    """测试 get_llm 返回单例"""
    llm1 = get_llm()
    llm2 = get_llm()
    assert llm1 is llm2


def test_get_llm_has_correct_config():
    """测试 LLM 配置正确"""
    llm = get_llm()
    assert llm.model_name == "glm-5"
    assert llm.temperature == 0.3
```

- [ ] **Step 5: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_llm.py -v`

Expected: 3 passed

- [ ] **Step 6: 提交**

```bash
git add backend/chains/ backend/tests/test_llm.py
git commit -m "feat: add LLM singleton configuration"
```

---

## Task 2: 创建 Prompts 模块

**Files:**
- Create: `backend/chains/prompts.py`
- Create: `backend/tests/test_prompts.py`

- [ ] **Step 1: 创建 chains/prompts.py（从 graph/prompts.py 迁移）**

```python
# backend/chains/prompts.py

"""
Prompt 模板定义

演示 LangChain ChatPromptTemplate：
- System message 设置 AI 角色
- Human message 作为用户输入
"""

from langchain_core.prompts import ChatPromptTemplate


# 关键词提取 Prompt
KEYWORD_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个税务合同分析专家。你的任务是从合同条款中提取用于搜索相关税务法规的关键词。
提取规则：
1. 提取3-5个关键词，聚焦税务合规相关内容
2. 关键词应能匹配到税务法规库中的相关文档
3. 优先选择：税种、税率、发票、付款、违约金等税务核心概念
请严格按照指定的 JSON Schema 格式输出关键词列表。"""),
    ("human", "请从以下合同条款中提取搜索关键词：\n\n{clause}")
])


# 合规判定 Prompt
COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个税务合同合规审计专家。你的任务是根据税务法规判断合同条款的合规性。

判定标准：
- 合规：条款完全符合税务法规要求
- 高风险：条款存在明显风险点，可能违规但需进一步确认
- 不合规：条款明确违反税务法规

判定流程：
1. 仔细阅读条款内容
2. 对照相关法规要求
3. 判断是否存在违规风险
4. 如有问题，给出具体修改建议

请严格按照指定的 JSON Schema 格式输出判定结果。"""),
    ("human", """请判断以下合同条款的合规性：

【条款内容】
{clause}

【相关法规】
{regulations}
""")
])


# 摘要生成 Prompt
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个税务合同审阅报告撰写专家。你的任务是根据审阅结果生成简洁的摘要。

摘要要求：
1. 统计各风险等级的条款数量
2. 突出需要重点关注的问题
3. 给出整体合规性评价
4. 语言简洁专业，不超过200字"""),
    ("human", """请根据以下审阅结果生成摘要：

{audit_results_summary}
""")
])
```

- [ ] **Step 2: 创建测试 tests/test_prompts.py**

```python
# backend/tests/test_prompts.py

import pytest
from chains.prompts import KEYWORD_PROMPT, COMPLIANCE_PROMPT, SUMMARY_PROMPT
from langchain_core.prompts import ChatPromptTemplate


def test_keyword_prompt_is_chat_prompt_template():
    """测试 KEYWORD_PROMPT 是 ChatPromptTemplate"""
    assert isinstance(KEYWORD_PROMPT, ChatPromptTemplate)


def test_keyword_prompt_has_correct_variables():
    """测试 KEYWORD_PROMPT 包含正确的变量"""
    input_variables = KEYWORD_PROMPT.input_variables
    assert "clause" in input_variables


def test_compliance_prompt_has_correct_variables():
    """测试 COMPLIANCE_PROMPT 包含正确的变量"""
    input_variables = COMPLIANCE_PROMPT.input_variables
    assert "clause" in input_variables
    assert "regulations" in input_variables


def test_summary_prompt_has_correct_variables():
    """测试 SUMMARY_PROMPT 包含正确的变量"""
    input_variables = SUMMARY_PROMPT.input_variables
    assert "audit_results_summary" in input_variables


def test_keyword_prompt_format():
    """测试 KEYWORD_PROMPT 格式化"""
    messages = KEYWORD_PROMPT.format_messages(clause="测试条款内容")
    assert len(messages) == 2
    assert "税务合同分析专家" in messages[0].content
    assert "测试条款内容" in messages[1].content
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_prompts.py -v`

Expected: 5 passed

- [ ] **Step 4: 提交**

```bash
git add backend/chains/prompts.py backend/tests/test_prompts.py
git commit -m "feat: add prompt templates module"
```

---

## Task 3: 创建 Keyword Chain

**Files:**
- Create: `backend/chains/keyword_chain.py`
- Create: `backend/tests/test_keyword_chain.py`

- [ ] **Step 1: 创建 chains/keyword_chain.py**

```python
# backend/chains/keyword_chain.py

"""
关键词提取 Chain

演示 LCEL 链式调用：
- prompt | llm 组合为 chain
- with_structured_output() 强制结构化输出
- 自动支持 invoke/stream/batch/async
"""

from chains.prompts import KEYWORD_PROMPT
from chains.llm import get_llm
from models.schemas import KeywordOutput

# LCEL chain: prompt | llm.with_structured_output()
keyword_chain = KEYWORD_PROMPT | get_llm().with_structured_output(KeywordOutput)

# 使用方式：
# 同步：keywords = keyword_chain.invoke({"clause": "..."})
# 异步：keywords = await keyword_chain.ainvoke({"clause": "..."})
# 批量：results = await keyword_chain.abatch([{"clause": "..."}, {"clause": "..."}])
```

- [ ] **Step 2: 创建测试 tests/test_keyword_chain.py**

```python
# backend/tests/test_keyword_chain.py

import pytest
from chains.keyword_chain import keyword_chain
from models.schemas import KeywordOutput
from langchain_core.runnables import RunnableSequence


def test_keyword_chain_is_runnable():
    """测试 keyword_chain 是 Runnable"""
    assert hasattr(keyword_chain, 'invoke')
    assert hasattr(keyword_chain, 'ainvoke')
    assert hasattr(keyword_chain, 'batch')
    assert hasattr(keyword_chain, 'abatch')


@pytest.mark.asyncio
async def test_keyword_chain_returns_keyword_output():
    """测试 keyword_chain 返回 KeywordOutput（需要真实 LLM 调用）"""
    # 这个测试需要真实的 API 调用，标记为 integration test
    # 在 CI 中可以跳过
    result = await keyword_chain.ainvoke({
        "clause": "甲方应在收到发票后30日内支付款项，逾期按日万分之五支付违约金。"
    })

    assert isinstance(result, KeywordOutput)
    assert len(result.keywords) >= 1
    assert len(result.keywords) <= 5
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_keyword_chain.py -v -m "not asyncio" `

Expected: 1 passed (跳过异步测试)

- [ ] **Step 4: 提交**

```bash
git add backend/chains/keyword_chain.py backend/tests/test_keyword_chain.py
git commit -m "feat: add keyword extraction chain"
```

---

## Task 4: 创建 Judge Chain

**Files:**
- Create: `backend/chains/judge_chain.py`
- Create: `backend/tests/test_judge_chain.py`

- [ ] **Step 1: 创建 chains/judge_chain.py**

```python
# backend/chains/judge_chain.py

"""
合规判定 Chain

演示 LCEL 链式调用 + 结构化输出：
- prompt | llm 组合为 chain
- with_structured_output() 自动解析为 Pydantic 模型
"""

from chains.prompts import COMPLIANCE_PROMPT
from chains.llm import get_llm
from models.schemas import ComplianceJudgment

# LCEL chain
judge_chain = COMPLIANCE_PROMPT | get_llm().with_structured_output(ComplianceJudgment)

# 使用方式：
# 异步调用：result = await judge_chain.ainvoke({"clause": "...", "regulations": "..."})
# 返回 ComplianceJudgment(risk_level="高风险", reason="...", suggestion="...")
```

- [ ] **Step 2: 创建测试 tests/test_judge_chain.py**

```python
# backend/tests/test_judge_chain.py

import pytest
from chains.judge_chain import judge_chain
from models.schemas import ComplianceJudgment


def test_judge_chain_is_runnable():
    """测试 judge_chain 是 Runnable"""
    assert hasattr(judge_chain, 'invoke')
    assert hasattr(judge_chain, 'ainvoke')
    assert hasattr(judge_chain, 'batch')
    assert hasattr(judge_chain, 'abatch')


@pytest.mark.asyncio
async def test_judge_chain_returns_compliance_judgment():
    """测试 judge_chain 返回 ComplianceJudgment（需要真实 LLM 调用）"""
    result = await judge_chain.ainvoke({
        "clause": "甲方应在收到发票后30日内支付款项。",
        "regulations": "1. 发票管理办法\n   发票是税务管理的重要凭证..."
    })

    assert isinstance(result, ComplianceJudgment)
    assert result.risk_level in ["合规", "高风险", "不合规"]
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_judge_chain.py -v -m "not asyncio"`

Expected: 1 passed

- [ ] **Step 4: 提交**

```bash
git add backend/chains/judge_chain.py backend/tests/test_judge_chain.py
git commit -m "feat: add compliance judgment chain"
```

---

## Task 5: 创建 Tools 目录和 Parse Contract Tool

**Files:**
- Create: `backend/tools/__init__.py`
- Create: `backend/tools/parse_contract.py`
- Create: `backend/tests/test_parse_contract_tool.py`

- [ ] **Step 1: 创建 tools 目录**

```bash
mkdir -p backend/tools
```

- [ ] **Step 2: 创建 tools/__init__.py**

```python
# backend/tools/__init__.py

from .parse_contract import parse_contract
from .search_regulations import search_regulations

__all__ = ["parse_contract", "search_regulations"]
```

- [ ] **Step 3: 创建 tools/parse_contract.py**

```python
# backend/tools/parse_contract.py

"""
合同解析 Tool

演示 @tool 装饰器：
- 将函数转换为 LangChain Tool
- docstring 成为工具描述
- 类型注解自动生成 Schema
"""

from langchain_core.tools import tool
from typing import List, Dict
from services.contract_parser import ContractParser

_parser = None


def _get_parser() -> ContractParser:
    """获取解析器单例"""
    global _parser
    if _parser is None:
        _parser = ContractParser()
    return _parser


@tool
def parse_contract(file_path: str) -> List[Dict]:
    """
    解析 docx 合同文档，提取章节结构。

    将合同文档按章节划分，每个章节包含名称和内容。
    用于审阅流程的第一步。

    Args:
        file_path: docx 格式的合同文件路径

    Returns:
        章节列表，每项包含:
        - section_name: 章节名称
        - content: 章节内容文本
    """
    parser = _get_parser()
    sections = parser.parse(file_path)

    return [
        {
            "section_name": section.section_name,
            "content": section.content
        }
        for section in sections
    ]


# 使用方式：
# sections = parse_contract.invoke("contract.docx")
```

- [ ] **Step 4: 创建测试 tests/test_parse_contract_tool.py**

```python
# backend/tests/test_parse_contract_tool.py

import pytest
import os
from tools.parse_contract import parse_contract
from langchain_core.tools import StructuredTool


def test_parse_contract_is_tool():
    """测试 parse_contract 是 LangChain Tool"""
    assert isinstance(parse_contract, StructuredTool)


def test_parse_contract_has_correct_description():
    """测试工具描述正确"""
    assert "解析 docx 合同文档" in parse_contract.description


def test_parse_contract_invoke_with_sample_file():
    """测试解析示例文件"""
    # 使用项目根目录的 sample.docx
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample.docx")

    if not os.path.exists(sample_path):
        pytest.skip("sample.docx not found")

    sections = parse_contract.invoke(sample_path)

    assert isinstance(sections, list)
    assert len(sections) > 0
    assert "section_name" in sections[0]
    assert "content" in sections[0]
```

- [ ] **Step 5: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_parse_contract_tool.py -v`

Expected: 2 passed (1 skipped if no sample.docx)

- [ ] **Step 6: 提交**

```bash
git add backend/tools/ backend/tests/test_parse_contract_tool.py
git commit -m "feat: add parse_contract tool"
```

---

## Task 6: 创建 Search Regulations Tool（异步）

**Files:**
- Create: `backend/tools/search_regulations.py`
- Create: `backend/tests/test_search_regulations_tool.py`

- [ ] **Step 1: 创建 tools/search_regulations.py**

```python
# backend/tools/search_regulations.py

"""
法规搜索 Tool（异步）

演示 @tool + async def：
- 异步 Tool 定义
- LangChain 自动处理 async/sync 转换
"""

from langchain_core.tools import tool
from typing import List, Dict
from services.mcp_client import MCPClient

_client = None


def _get_client() -> MCPClient:
    """获取 MCP 客户端单例"""
    global _client
    if _client is None:
        _client = MCPClient()
    return _client


@tool
async def search_regulations(query_text: str, size: int = 10) -> List[Dict]:
    """
    搜索税务法规库，查找相关法规。

    使用关键词在税务法规库中搜索，返回相关法规列表。
    关键词应聚焦税务合规相关内容。

    Args:
        query_text: 搜索关键词，多个关键词用空格分隔
        size: 返回结果数量，默认10条

    Returns:
        法规列表，每项包含:
        - title: 法规标题
        - content: 法规内容摘要
        - issuing_body: 发文机关
        - published_date: 发布日期
    """
    client = _get_client()
    result = await client.search_regulations(query_text, size=size)
    regulations = client.parse_regulations(result)

    return [
        {
            "title": r.title,
            "content": r.content[:500],  # 截取前500字符
            "issuing_body": r.issuing_body,
            "published_date": r.published_date
        }
        for r in regulations
    ]


# 使用方式：
# regulations = await search_regulations.ainvoke({"query_text": "发票 税率", "size": 10})
```

- [ ] **Step 2: 创建测试 tests/test_search_regulations_tool.py**

```python
# backend/tests/test_search_regulations_tool.py

import pytest
from tools.search_regulations import search_regulations
from langchain_core.tools import StructuredTool


def test_search_regulations_is_tool():
    """测试 search_regulations 是 LangChain Tool"""
    assert isinstance(search_regulations, StructuredTool)


def test_search_regulations_has_correct_description():
    """测试工具描述正确"""
    assert "搜索税务法规库" in search_regulations.description


@pytest.mark.asyncio
async def test_search_regulations_ainvoke():
    """测试异步调用（需要 MCP Server 运行）"""
    # 这个测试需要 MCP Server 运行，标记为 integration test
    # 在 CI 中可以跳过
    result = await search_regulations.ainvoke({
        "query_text": "发票",
        "size": 5
    })

    assert isinstance(result, list)
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_search_regulations_tool.py -v -m "not asyncio"`

Expected: 2 passed

- [ ] **Step 4: 提交**

```bash
git add backend/tools/search_regulations.py backend/tests/test_search_regulations_tool.py
git commit -m "feat: add async search_regulations tool"
```

---

## Task 7: 创建 Audit Pipeline

**Files:**
- Create: `backend/chains/audit_pipeline.py`
- Create: `backend/tests/test_audit_pipeline.py`

- [ ] **Step 1: 创建 chains/audit_pipeline.py**

```python
# backend/chains/audit_pipeline.py

"""
审阅流水线 Pipeline

演示 RunnableLambda：
- 将异步函数包装为 Runnable
- 自动获得 ainvoke/abatch 等方法
- 简单 for 循环替代 LangGraph 条件路由
"""

from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from models.schemas import AuditReport, SectionAuditResult
from tools.parse_contract import parse_contract
from tools.search_regulations import search_regulations
from chains.keyword_chain import keyword_chain
from chains.judge_chain import judge_chain
from chains.llm import get_llm
from chains.prompts import SUMMARY_PROMPT
from services.report_generator import ReportGenerator


def format_regulations(regulations: list) -> str:
    """格式化法规列表为文本"""
    if not regulations:
        return "未找到相关法规"
    return "\n".join([
        f"{i+1}. {r['title']}\n   {r['content'][:300]}"
        for i, r in enumerate(regulations)
    ])


async def generate_summary(results: list) -> str:
    """生成审阅摘要"""
    compliant_count = sum(1 for r in results if r.risk_level == "合规")
    high_risk_count = sum(1 for r in results if r.risk_level == "高风险")
    non_compliant_count = sum(1 for r in results if r.risk_level == "不合规")

    summary_text = f"""
    共审阅 {len(results)} 个章节：
    - 合规条款: {compliant_count} 个
    - 高风险条款: {high_risk_count} 个
    - 不合规条款: {non_compliant_count} 个
    """

    summary_chain = SUMMARY_PROMPT | get_llm() | StrOutputParser()
    return await summary_chain.ainvoke({"audit_results_summary": summary_text})


async def audit_contract(input: dict) -> dict:
    """
    审阅合同核心逻辑

    Args:
        input: {"file_path": "合同文件路径"}

    Returns:
        {"report_path": "报告路径", "report": AuditReport}
    """
    file_path = input["file_path"]

    # 1. 解析合同
    sections = parse_contract.invoke(file_path)

    # 2. 逐章节处理
    results = []
    for section in sections:
        # 关键词提取
        keywords = await keyword_chain.ainvoke({"clause": section["content"]})

        # 法规搜索
        regulations = await search_regulations.ainvoke({
            "query_text": " ".join(keywords.keywords),
            "size": 10
        })

        # 格式化法规文本
        reg_text = format_regulations(regulations)

        # 合规判定
        judgment = await judge_chain.ainvoke({
            "clause": section["content"],
            "regulations": reg_text
        })

        # 构建结果
        results.append(SectionAuditResult(
            section_name=section["section_name"],
            original_content=section["content"],
            risk_level=judgment.risk_level,
            violated_regulations=judgment.violated_regulations,
            reason=judgment.reason,
            suggestion=judgment.suggestion
        ))

    # 3. 生成摘要
    summary = await generate_summary(results)

    # 4. 生成报告
    report = AuditReport(sections=results, summary=summary)
    report_path = ReportGenerator().generate(report, "审阅报告.docx")

    return {"report_path": report_path, "report": report}


# 包装为 Runnable
audit_pipeline = RunnableLambda(audit_contract)

# 使用方式：
# result = await audit_pipeline.ainvoke({"file_path": "contract.docx"})
# results = await audit_pipeline.abatch([{"file_path": "1.docx"}, {"file_path": "2.docx"}])
```

- [ ] **Step 2: 创建测试 tests/test_audit_pipeline.py**

```python
# backend/tests/test_audit_pipeline.py

import pytest
import os
from chains.audit_pipeline import audit_pipeline, audit_contract, format_regulations
from langchain_core.runnables import RunnableLambda


def test_audit_pipeline_is_runnable():
    """测试 audit_pipeline 是 Runnable"""
    assert isinstance(audit_pipeline, RunnableLambda)


def test_format_regulations_empty():
    """测试空法规列表格式化"""
    result = format_regulations([])
    assert result == "未找到相关法规"


def test_format_regulations_with_data():
    """测试法规列表格式化"""
    regulations = [
        {"title": "发票管理办法", "content": "这是发票管理的内容..." * 100},
        {"title": "税收征管法", "content": "这是税收征管的内容..." * 100}
    ]
    result = format_regulations(regulations)

    assert "发票管理办法" in result
    assert "税收征管法" in result


@pytest.mark.asyncio
async def test_audit_contract_returns_dict():
    """测试 audit_contract 返回正确格式（需要完整环境）"""
    # 这个测试需要完整的 LLM + MCP 环境
    # 使用 sample.docx 测试
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample.docx")

    if not os.path.exists(sample_path):
        pytest.skip("sample.docx not found")

    result = await audit_contract({"file_path": sample_path})

    assert "report_path" in result
    assert "report" in result
```

- [ ] **Step 3: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_audit_pipeline.py -v -m "not asyncio"`

Expected: 3 passed

- [ ] **Step 4: 提交**

```bash
git add backend/chains/audit_pipeline.py backend/tests/test_audit_pipeline.py
git commit -m "feat: add audit pipeline with RunnableLambda"
```

---

## Task 8: 更新 Models（删除 AuditProgress）

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/models/__init__.py`

- [ ] **Step 1: 删除 models/schemas.py 中的 AuditProgress 类**

删除以下代码（约第45-51行）：

```python
class AuditProgress(BaseModel):
    """审计进度（用于前端实时显示）"""
    current_section: int
    total_sections: int
    section_name: str
    status: str  # "processing"/"completed"
```

修改后的文件应保留：
- ContractSection
- Regulation
- SectionAuditResult
- AuditReport
- KeywordOutput
- ComplianceJudgment

- [ ] **Step 2: 更新 models/__init__.py**

```python
# backend/models/__init__.py

from .schemas import (
    ContractSection,
    Regulation,
    SectionAuditResult,
    AuditReport,
    KeywordOutput,
    ComplianceJudgment
)

__all__ = [
    "ContractSection",
    "Regulation",
    "SectionAuditResult",
    "AuditReport",
    "KeywordOutput",
    "ComplianceJudgment"
]
```

- [ ] **Step 3: 验证现有测试仍通过**

Run: `cd backend && python -m pytest tests/ -v -m "not asyncio"`

Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add backend/models/
git commit -m "refactor: remove AuditProgress class (no longer needed)"
```

---

## Task 9: 简化 main.py（移除 SSE）

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 重写 main.py**

```python
# backend/main.py

"""
FastAPI 主应用

演示 LangChain Runnable 与 FastAPI 集成：
- 使用 ainvoke() 异步执行
- 简单 POST API（无 SSE）
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from chains.audit_pipeline import audit_pipeline
from config import settings

app = FastAPI(
    title="税务合同审阅助手",
    description="基于 LangChain 1.x LCEL 的税务合同审阅系统",
    version="3.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    上传合同进行审阅

    使用 audit_pipeline.ainvoke() 异步执行
    """
    # 验证文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 docx 格式文件")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    # 执行审阅
    result = await audit_pipeline.ainvoke({"file_path": temp_path})

    return {"report_path": result["report_path"]}


@app.get("/api/download/{filename}")
async def download_report(filename: str):
    """下载审阅报告"""
    report_path = os.path.join(os.getcwd(), "审阅报告.docx")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="报告不存在")

    return FileResponse(
        path=report_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename
    )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "3.0.0",
        "framework": "LangChain 1.x LCEL"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
```

- [ ] **Step 2: 提交**

```bash
git add backend/main.py
git commit -m "refactor: simplify main.py, remove SSE streaming"
```

---

## Task 10: 更新 requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

```text
fastapi>=0.100.0
uvicorn>=0.23.0
python-docx>=0.8.11
httpx>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
pytest>=7.0.0
pytest-asyncio>=0.21.0

# LangChain 1.x only
langchain>=1.0.0
langchain-openai>=1.0.0
langchain-core>=1.0.0
```

- [ ] **Step 2: 提交**

```bash
git add backend/requirements.txt
git commit -m "refactor: remove langgraph from dependencies"
```

---

## Task 11: 删除 graph 目录

**Files:**
- Delete: `backend/graph/` 整个目录

- [ ] **Step 1: 删除 graph 目录**

```bash
rm -rf backend/graph/
```

- [ ] **Step 2: 提交**

```bash
git add -A
git commit -m "refactor: remove LangGraph graph directory"
```

---

## Task 12: 更新 chains/__init__.py 导入

**Files:**
- Modify: `backend/chains/__init__.py`

- [ ] **Step 1: 确保 chains/__init__.py 正确导出**

```python
# backend/chains/__init__.py

from .llm import get_llm
from .keyword_chain import keyword_chain
from .judge_chain import judge_chain
from .audit_pipeline import audit_pipeline

__all__ = ["get_llm", "keyword_chain", "judge_chain", "audit_pipeline"]
```

- [ ] **Step 2: 验证导入正常**

Run: `cd backend && python -c "from chains import audit_pipeline, keyword_chain, judge_chain; print('OK')"`

Expected: OK

- [ ] **Step 3: 提交**

```bash
git add backend/chains/__init__.py
git commit -m "fix: update chains module exports"
```

---

## Task 13: 最终验证

**Files:**
- All files

- [ ] **Step 1: 运行所有测试**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass

- [ ] **Step 2: 验证 API 启动**

Run: `cd backend && python main.py`

Expected: Server starts on port 8002

- [ ] **Step 3: 验证健康检查**

Run: `curl http://localhost:8002/api/health`

Expected: `{"status":"ok","version":"3.0.0","framework":"LangChain 1.x LCEL"}`

- [ ] **Step 4: 创建新分支并提交所有更改**

```bash
git checkout -b langchain_only
git add -A
git commit -m "refactor: complete LangChain-only refactor

- Remove LangGraph StateGraph
- Remove SSE streaming code
- Use RunnableLambda for pipeline
- Use LCEL chains (keyword_chain, judge_chain)
- Use @tool decorator for tools
- Simplify API to simple POST
- Remove AuditProgress model"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | 创建 chains 目录和 LLM 配置 | 3 files |
| 2 | 创建 Prompts 模块 | 2 files |
| 3 | 创建 Keyword Chain | 2 files |
| 4 | 创建 Judge Chain | 2 files |
| 5 | 创建 Parse Contract Tool | 3 files |
| 6 | 创建 Search Regulations Tool | 2 files |
| 7 | 创建 Audit Pipeline | 2 files |
| 8 | 更新 Models | 2 files |
| 9 | 简化 main.py | 1 file |
| 10 | 更新 requirements.txt | 1 file |
| 11 | 删除 graph 目录 | - |
| 12 | 更新 chains 导入 | 1 file |
| 13 | 最终验证 | - |

**Total: ~20 files changed**