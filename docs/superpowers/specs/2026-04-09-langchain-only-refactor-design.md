---
name: langchain-only-refactor
description: LangChain 1.x LCEL refactor - removing LangGraph, using Runnable pipeline
type: project
---

# LangChain-Only Refactor Design

## Overview

将项目从 LangChain + LangGraph 架构重构为纯 LangChain 1.x LCEL 架构。

**目标：**
- 移除 LangGraph StateGraph
- 移除 SSE 流式代码
- 使用 LangChain Runnable 组合模式
- 保留核心业务逻辑

## Why

**Why:** 用户希望学习 LangChain native 开发架构，使用 LCEL 组合模式而非 LangGraph 图模式。

**How to apply:** 所有流程控制使用 Python 循环 + Runnable 组合，不使用 StateGraph/条件边/MemorySaver。

## Architecture

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                    AuditPipeline (Runnable)                  │
│                                                              │
│  ainvoke({"file_path": "..."}) → {"report_path": "..."}     │
│  astream({"file_path": "..."}) → AsyncIterator[进度事件]     │
│  abatch([{"file_path": ...}]) → [{"report_path": ...}]      │
│                                                              │
│  Internal:                                                   │
│                                                              │
│  parse_contract → for section in sections:                  │
│                      keyword_chain → search_regulations      │
│                      → judge_chain → append result           │
│                   → summary_chain → report_generator         │
└─────────────────────────────────────────────────────────────┘
```

### 对比 LangGraph

| 特性 | LangGraph (旧) | LangChain Runnable (新) |
|------|---------------|------------------------|
| 数据传递 | State (TypedDict) | 函数参数/返回值 |
| 流程控制 | conditional_edges | Python for 循环 |
| 循环处理 | should_continue 路由 | 普通 for 循环 |
| 状态管理 | MemorySaver checkpoint | 无状态 |
| 组合方式 | 节点 + 边定义图 | Runnable 组合链 |

## File Structure

```
backend/
├── chains/
│   ├── __init__.py
│   ├── llm.py               # LLM 单例配置
│   ├── prompts.py           # ChatPromptTemplate 定义
│   ├── keyword_chain.py     # keyword_chain = PROMPT | llm.with_structured_output()
│   ├── judge_chain.py       # judge_chain = PROMPT | llm.with_structured_output()
│   └── audit_pipeline.py    # AuditPipeline(Runnable) 类
├── tools/
│   ├── __init__.py
│   ├── parse_contract.py    # @tool def parse_contract(...)
│   └── search_regulations.py # @tool async def search_regulations(...)
├── services/                 # 保留不变
│   ├── contract_parser.py
│   ├── mcp_client.py
│   └── report_generator.py
│   └── __init__.py
├── models/                   # 简化
│   ├── schemas.py           # 删除 AuditProgress
│   └── __init__.py          # 更新导出
├── tests/                    # 新增 chain/pipeline 测试
│   ├── test_keyword_chain.py
│   ├── test_judge_chain.py
│   ├── test_audit_pipeline.py
│   ├── test_contract_parser.py   # 保留
│   ├── test_mcp_client.py        # 保留
│   └── test_report_generator.py  # 保留
├── main.py                  # 简化 API（无 SSE）
├── config.py                # 保留
├── requirements.txt         # 移除 langgraph
└── pytest.ini               # 保留

删除：
├── graph/                   # 整个目录删除
```

## Core Chains Design

### LLM 配置

```python
# chains/llm.py

from langchain_openai import ChatOpenAI
from config import settings

_llm = None

def get_llm() -> ChatOpenAI:
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

### Keyword Chain

```python
# chains/keyword_chain.py

from chains.prompts import KEYWORD_PROMPT
from chains.llm import get_llm
from models.schemas import KeywordOutput

keyword_chain = KEYWORD_PROMPT | get_llm().with_structured_output(KeywordOutput)

# 使用：
# keywords = await keyword_chain.ainvoke({"clause": "..."})
```

### Judge Chain

```python
# chains/judge_chain.py

from chains.prompts import COMPLIANCE_PROMPT
from chains.llm import get_llm
from models.schemas import ComplianceJudgment

judge_chain = COMPLIANCE_PROMPT | get_llm().with_structured_output(ComplianceJudgment)

# 使用：
# result = await judge_chain.ainvoke({"clause": "...", "regulations": "..."})
```

### Summary Chain

```python
# chains/summary_chain.py (内联在 pipeline 中)

from langchain_core.output_parsers import StrOutputParser
from chains.prompts import SUMMARY_PROMPT
from chains.llm import get_llm

summary_chain = SUMMARY_PROMPT | get_llm() | StrOutputParser()
```

## AuditPipeline Design

```python
# chains/audit_pipeline.py

from langchain_core.runnables import Runnable
from typing import AsyncIterator
from models.schemas import AuditReport, SectionAuditResult
from tools.parse_contract import parse_contract
from tools.search_regulations import search_regulations
from chains.keyword_chain import keyword_chain
from chains.judge_chain import judge_chain
from chains.llm import get_llm
from chains.prompts import SUMMARY_PROMPT
from services.report_generator import ReportGenerator
from langchain_core.output_parsers import StrOutputParser

class AuditPipeline(Runnable):
    """税务合同审阅流水线"""

    async def _ainvoke(self, input: dict, config: dict = None) -> dict:
        file_path = input["file_path"]

        # 1. 解析
        sections = parse_contract.invoke(file_path)

        # 2. 逐章节处理
        results = []
        for section in sections:
            keywords = await keyword_chain.ainvoke({"clause": section["content"]})
            regulations = await search_regulations.ainvoke({"query_text": " ".join(keywords.keywords), "size": 10})
            reg_text = self._format_regulations(regulations)
            judgment = await judge_chain.ainvoke({"clause": section["content"], "regulations": reg_text})
            results.append(SectionAuditResult(
                section_name=section["section_name"],
                original_content=section["content"],
                risk_level=judgment.risk_level,
                violated_regulations=judgment.violated_regulations,
                reason=judgment.reason,
                suggestion=judgment.suggestion
            ))

        # 3. 摘要
        summary = await self._generate_summary(results)

        # 4. 报告
        report = AuditReport(sections=results, summary=summary)
        report_path = ReportGenerator().generate(report, "审阅报告.docx")

        return {"report_path": report_path, "report": report}

    async def _astream(self, input: dict, config: dict = None) -> AsyncIterator[dict]:
        # 流式输出进度（可选实现）
        ...

    def _format_regulations(self, regulations: list) -> str:
        if not regulations:
            return "未找到相关法规"
        return "\n".join([f"{i+1}. {r['title']}\n   {r['content'][:300]}" for i, r in enumerate(regulations)])

    async def _generate_summary(self, results: list) -> str:
        summary_chain = SUMMARY_PROMPT | get_llm() | StrOutputParser()
        summary_text = f"共审阅 {len(results)} 个章节..."
        return await summary_chain.ainvoke({"audit_results_summary": summary_text})
```

## Tools Design

### Parse Contract（同步）

```python
# tools/parse_contract.py

from langchain_core.tools import tool
from typing import List, Dict
from services.contract_parser import ContractParser

_parser = None

def _get_parser() -> ContractParser:
    global _parser
    if _parser is None:
        _parser = ContractParser()
    return _parser

@tool
def parse_contract(file_path: str) -> List[Dict]:
    """解析 docx 合同文档，提取章节结构。"""
    parser = _get_parser()
    sections = parser.parse(file_path)
    return [{"section_name": s.section_name, "content": s.content} for s in sections]
```

### Search Regulations（异步）

```python
# tools/search_regulations.py

from langchain_core.tools import tool
from typing import List, Dict
from services.mcp_client import MCPClient

_client = None

def _get_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient()
    return _client

@tool
async def search_regulations(query_text: str, size: int = 10) -> List[Dict]:
    """搜索税务法规库，查找相关法规。"""
    client = _get_client()
    result = await client.search_regulations(query_text, size=size)
    regulations = client.parse_regulations(result)
    return [{"title": r.title, "content": r.content[:500], ...} for r in regulations]
```

## API Design

```python
# main.py (简化版)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from chains.audit_pipeline import AuditPipeline

app = FastAPI(title="税务合同审阅助手", version="3.0.0")

_pipeline = None

def get_pipeline() -> AuditPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AuditPipeline()
    return _pipeline

@app.post("/api/upload")
async def upload_contract(file: UploadFile = File(...)):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 docx 格式")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    pipeline = get_pipeline()
    result = await pipeline.ainvoke({"file_path": temp_path})

    return {"report_path": result["report_path"]}
```

## Models Cleanup

### 删除 AuditProgress

```python
# models/schemas.py - 删除以下类
class AuditProgress(BaseModel):
    """审计进度（用于前端实时显示）"""
    current_section: int
    total_sections: int
    section_name: str
    status: str
```

### 更新导出

```python
# models/__init__.py
from .schemas import ContractSection, Regulation, SectionAuditResult, AuditReport, KeywordOutput, ComplianceJudgment

__all__ = ["ContractSection", "Regulation", "SectionAuditResult", "AuditReport", "KeywordOutput", "ComplianceJudgment"]
```

## Requirements

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

# 移除：
# langgraph>=1.0.0
```

## Key LangChain Concepts Learned

1. **LCEL (| 操作符)** - 组合 Runnable 为链，自动支持 invoke/stream/batch/async
2. **RunnablePassthrough** - 传递数据（但我们用直接传 dict）
3. **RunnableLambda** - 包装 Python 函数为 Runnable
4. **with_structured_output()** - Pydantic schema 强制 LLM 输出格式
5. **@tool 装饰器** - 函数转换为 Tool，支持 async def
6. **自定义 Runnable 类** - 继承 Runnable，实现 _ainvoke/_astream
7. **StrOutputParser** - 提取 AIMessage.content 为字符串

## Implementation Notes

- 所有 LLM 调用使用 async：`await chain.ainvoke(...)`
- Tool 异步定义：`@tool async def ...`
- Pipeline 无状态：每次执行新建，不保留状态
- 简单 for 循环替代 LangGraph conditional_edges
- 保留 services 不变（纯业务逻辑）