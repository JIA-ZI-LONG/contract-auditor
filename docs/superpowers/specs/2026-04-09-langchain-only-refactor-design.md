---
name: langchain-only-refactor
description: LangChain 1.x LCEL refactor - removing LangGraph, using RunnableLambda pipeline
type: project
---

# LangChain-Only Refactor Design

## Overview

将项目从 LangChain + LangGraph 架构重构为纯 LangChain 1.x LCEL 架构。

**目标：**
- 移除 LangGraph StateGraph
- 移除 SSE 流式代码
- 使用 LangChain RunnableLambda 组合模式
- 保留核心业务逻辑

## Why

**Why:** 用户希望学习 LangChain native 开发架构，使用 LCEL 组合模式而非 LangGraph 图模式。

**How to apply:** 所有流程控制使用 Python 循环 + RunnableLambda 包装，不使用 StateGraph/条件边/MemorySaver。

## Design Decisions

| 决策项 | 选择 | 原因 |
|--------|------|------|
| Runnable 类型 | RunnableLambda | 无需自定义类，一行包装 |
| API 方式 | 简单 POST | 最简单，无流式 |
| 异步 | async（ainvoke） | LangChain 原生支持 |

## Architecture

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                 audit_pipeline (RunnableLambda)              │
│                                                              │
│  ainvoke({"file_path": "..."}) → {"report_path": "..."}     │
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

| 特性 | LangGraph (旧) | LangChain RunnableLambda (新) |
|------|---------------|------------------------------|
| 数据传递 | State (TypedDict) | 函数参数/返回值 |
| 流程控制 | conditional_edges | Python for 循环 |
| 循环处理 | should_continue 路由 | 普通 for 循环 |
| 状态管理 | MemorySaver checkpoint | 无状态 |
| 组合方式 | 节点 + 边定义图 | 函数 + RunnableLambda 包装 |

## File Structure

```
backend/
├── chains/
│   ├── __init__.py
│   ├── llm.py               # LLM 单例配置
│   ├── prompts.py           # ChatPromptTemplate 定义
│   ├── keyword_chain.py     # keyword_chain = PROMPT | llm.with_structured_output()
│   ├── judge_chain.py       # judge_chain = PROMPT | llm.with_structured_output()
│   └── audit_pipeline.py    # audit_pipeline = RunnableLambda(audit_contract)
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
├── tests/                    # 新增 chain 测试
│   ├── test_keyword_chain.py
│   ├── test_judge_chain.py
│   ├── test_audit_pipeline.py
│   ├── test_contract_parser.py   # 保留
│   ├── test_mcp_client.py        # 保留
│   └── test_report_generator.py  # 保留
├── main.py                  # 简单 API（无 SSE）
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

## AuditPipeline Design

```python
# chains/audit_pipeline.py

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
    """
    解析 docx 合同文档，提取章节结构。

    Args:
        file_path: docx 合同文件路径

    Returns:
        章节列表，每项包含 section_name 和 content
    """
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
    """
    搜索税务法规库，查找相关法规。

    Args:
        query_text: 搜索关键词，多个用空格分隔
        size: 返回结果数量

    Returns:
        法规列表，每项包含 title、content、issuing_body、published_date
    """
    client = _get_client()
    result = await client.search_regulations(query_text, size=size)
    regulations = client.parse_regulations(result)
    return [
        {
            "title": r.title,
            "content": r.content[:500],
            "issuing_body": r.issuing_body,
            "published_date": r.published_date
        }
        for r in regulations
    ]
```

## API Design

```python
# main.py

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
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 docx 格式")

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
    return {"status": "ok", "version": "3.0.0", "framework": "LangChain 1.x LCEL"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.backend_port)
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
2. **RunnableLambda** - 包装 Python 函数为 Runnable，一行代码
3. **with_structured_output()** - Pydantic schema 强制 LLM 输出格式
4. **@tool 装饰器** - 函数转换为 Tool，支持 async def
5. **StrOutputParser** - 提取 AIMessage.content 为字符串

## Implementation Notes

- 所有 LLM 调用使用 async：`await chain.ainvoke(...)`
- Tool 异步定义：`@tool async def ...`
- Pipeline 无状态：每次执行独立，不保留状态
- 简单 for 循环替代 LangGraph conditional_edges
- 保留 services 不变（纯业务逻辑）
- RunnableLambda 自动获得 ainvoke/abatch 等方法