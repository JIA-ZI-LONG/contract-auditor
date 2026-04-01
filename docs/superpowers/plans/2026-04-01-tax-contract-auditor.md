# 税务合同审计AI助手 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个税务合同审计AI助手，上传docx合同后自动分析合规性，输出审计报告docx。

**Architecture:** React前端上传文件 → FastAPI后端处理 → MCP搜索法规 + GLM-5分析 → 生成报告docx返回

**Tech Stack:** FastAPI, React, python-docx, httpx, 阿里云百炼GLM-5, MCP (streamable-http)

---

## Task 1: 后端项目初始化

**Files:**

- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建requirements.txt**

```txt
fastapi>=0.100.0
uvicorn>=0.23.0
python-docx>=0.8.11
httpx>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6
openai>=1.0.0
```

- [ ] **Step 2: 创建config.py**

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 阿里云百炼配置
    bailian_api_key: str = os.getenv("BAILIAN_API_KEY", "")
    bailian_base_url: str = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    bailian_model: str = os.getenv("BAILIAN_MODEL", "glm-5")

    # MCP Server配置
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

    # 服务配置
    backend_port: int = 8001

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: 创建.env.example**

```txt
BAILIAN_API_KEY=your_api_key_here
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL=glm-5
MCP_SERVER_URL=http://localhost:8000/mcp
```

- [ ] **Step 4: 安装依赖**

Run: `cd D:/EY/contractAgent/backend && uv pip install -r requirements.txt`
Expected: 依赖安装成功

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/.env.example
git commit -m "feat: init backend project with config"
```

---

## Task 2: 数据模型定义

**Files:**

- Create: `backend/models/__init__.py`
- Create: `backend/models/schemas.py`

- [ ] **Step 1: 创建models目录和__init__.py**

```python
from .schemas import ContractSection, Regulation, SectionAuditResult, AuditReport

__all__ = ["ContractSection", "Regulation", "SectionAuditResult", "AuditReport"]
```

- [ ] **Step 2: 创建schemas.py**

```python
from typing import List
from pydantic import BaseModel

class ContractSection(BaseModel):
    """合同章节"""
    section_name: str       # 章节名称
    content: str            # 条款原文

class Regulation(BaseModel):
    """法规搜索结果"""
    title: str              # 法规标题
    content: str            # 法规内容
    issuing_body: str = ""  # 发文机关
    published_date: str = "" # 发布日期

class SectionAuditResult(BaseModel):
    """单章节审计结果"""
    section_name: str
    original_content: str
    risk_level: str         # "合规"/"高风险"/"不合规"
    violated_regulations: List[str] = []
    reason: str = ""        # 不合规原因分析
    suggestion: str = ""    # 修改建议

class AuditReport(BaseModel):
    """完整审计报告"""
    sections: List[SectionAuditResult]
    summary: str = ""       # 整体风险摘要

class AuditProgress(BaseModel):
    """审计进度（用于前端实时显示）"""
    current_section: int
    total_sections: int
    section_name: str
    status: str  # "processing"/"completed"
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/
git commit -m "feat: add pydantic data models"
```

---

## Task 3: 合同解析服务

**Files:**

- Create: `backend/services/__init__.py`
- Create: `backend/services/contract_parser.py`
- Test: `backend/tests/test_contract_parser.py`

- [ ] **Step 1: 创建services/__init__.py**

```python
from .contract_parser import ContractParser
from .mcp_client import MCPClient
from .ai_analyzer import AIAnalyzer
from .report_generator import ReportGenerator

__all__ = ["ContractParser", "MCPClient", "AIAnalyzer", "ReportGenerator"]
```

- [ ] **Step 2: 创建tests目录并编写测试**

```python
import pytest
from services.contract_parser import ContractParser
from docx import Document
import tempfile
import os

def test_parse_contract_with_sections():
    """测试解析带章节结构的合同"""
    # 创建测试文档
    doc = Document()
    doc.add_heading("付款条款", level=1)
    doc.add_paragraph("买方应在收到发票后30日内支付货款。")
    doc.add_heading("违约条款", level=1)
    doc.add_paragraph("逾期按日利率0.05%计算违约金。")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc.save(f.name)
        temp_path = f.name

    # 解析
    parser = ContractParser()
    sections = parser.parse(temp_path)

    # 清理
    os.unlink(temp_path)

    # 验证
    assert len(sections) == 2
    assert sections[0].section_name == "付款条款"
    assert "发票" in sections[0].content
    assert sections[1].section_name == "违约条款"

def test_parse_contract_without_sections():
    """测试解析无章节的纯文本合同"""
    doc = Document()
    doc.add_paragraph("本合同由甲乙双方签订。")
    doc.add_paragraph("付款方式为银行转账。")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        doc.save(f.name)
        temp_path = f.name

    parser = ContractParser()
    sections = parser.parse(temp_path)
    os.unlink(temp_path)

    # 无章节标题时，合并为"全文"章节
    assert len(sections) == 1
    assert sections[0].section_name == "全文"
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_contract_parser.py -v`
Expected: FAIL (ContractParser not defined)

- [ ] **Step 4: 实现ContractParser**

```python
from docx import Document
from models.schemas import ContractSection
import logging

logger = logging.getLogger(__name__)

class ContractParser:
    """解析docx合同文档，提取章节结构"""

    def parse(self, file_path: str) -> list[ContractSection]:
        """
        解析合同文档

        Args:
            file_path: docx文件路径

        Returns:
            章节列表，每个章节包含名称和内容
        """
        doc = Document(file_path)
        sections = []
        current_section_name = None
        current_content = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # 判断是否为章节标题（Heading样式或以"条款"、"第"开头）
            is_heading = (
                para.style.name.startswith("Heading") or
                text.startswith("第") or
                text.endswith("条款") or
                text.endswith("章") or
                text.endswith("节")
            )

            if is_heading:
                # 保存前一个章节
                if current_section_name and current_content:
                    sections.append(ContractSection(
                        section_name=current_section_name,
                        content="\n".join(current_content)
                    ))
                current_section_name = text
                current_content = []
            else:
                current_content.append(text)

        # 保存最后一个章节
        if current_section_name and current_content:
            sections.append(ContractSection(
                section_name=current_section_name,
                content="\n".join(current_content)
            ))

        # 如果没有章节结构，将全文作为一个章节
        if not sections:
            all_text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
            if all_text:
                sections.append(ContractSection(
                    section_name="全文",
                    content=all_text
                ))

        logger.info(f"Parsed {len(sections)} sections from contract")
        return sections
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_contract_parser.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/__init__.py backend/services/contract_parser.py backend/tests/
git commit -m "feat: add contract parser service with tests"
```

---

## Task 4: MCP客户端服务

**Files:**

- Create: `backend/services/mcp_client.py`
- Test: `backend/tests/test_mcp_client.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from services.mcp_client import MCPClient
import json

@pytest.mark.asyncio
async def test_search_regulations_success():
    """测试搜索法规（需要MCP Server运行）"""
    client = MCPClient()
    result = await client.search_regulations("发票 付款", size=5)

    # 验证返回格式
    assert "hits" in result
    hits = result.get("hits", {}).get("hits", [])
    assert len(hits) > 0

    # 验证每条结果包含必要字段
    first_hit = hits[0]
    source = first_hit.get("_source", {})
    assert "title" in source
    assert "content" in source

@pytest.mark.asyncio
async def test_search_regulations_empty_query():
    """测试空查询"""
    client = MCPClient()
    result = await client.search_regulations("", size=5)
    # 空查询应该返回结果（match_all）
    assert "hits" in result
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_mcp_client.py -v`
Expected: FAIL (MCPClient not defined)

- [ ] **Step 3: 实现MCPClient**

```python
import httpx
import json
import logging
from config import settings
from models.schemas import Regulation

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP Server HTTP客户端"""

    def __init__(self):
        self.base_url = settings.mcp_server_url
        self.timeout = 30.0

    async def search_regulations(
        self,
        query_text: str,
        effectiveness: str = "有效",
        size: int = 10
    ) -> dict:
        """
        搜索税务法规

        Args:
            query_text: 搜索关键词（多个关键词用空格分隔）
            effectiveness: 法规有效性，默认"有效"
            size: 返回结果数量

        Returns:
            Elasticsearch搜索结果JSON
        """
        logger.info(f"Searching regulations: query={query_text}, size={size}")

        # MCP streamable-http协议调用
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_chinataxcenter",
                "arguments": {
                    "query_text": query_text,
                    "effectiveness": effectiveness,
                    "size": size
                }
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

        # 解析MCP响应格式
        if "result" in result:
            # MCP返回格式: {"result": {"content": [{"text": "JSON结果"}]}}
            content = result.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text_content = content[0].get("text", "{}")
                return json.loads(text_content)

        logger.warning(f"Unexpected MCP response format: {result}")
        return {"hits": {"hits": []}}

    def parse_regulations(self, search_result: dict) -> list[Regulation]:
        """
        解析搜索结果为Regulation列表

        Args:
            search_result: ES搜索结果JSON

        Returns:
            Regulation对象列表
        """
        regulations = []
        hits = search_result.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            reg = Regulation(
                title=source.get("title", ""),
                content=source.get("content", "")[:500],  # 截取前500字符
                issuing_body=source.get("issuingBody", ""),
                published_date=source.get("publishedDate", "")
            )
            regulations.append(reg)

        return regulations
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_mcp_client.py -v`
Expected: PASS (需要MCP Server在localhost:8000运行)

- [ ] **Step 5: Commit**

```bash
git add backend/services/mcp_client.py backend/tests/test_mcp_client.py
git commit -m "feat: add MCP client for regulation search"
```

---

## Task 5: AI分析服务

**Files:**

- Create: `backend/services/ai_analyzer.py`
- Test: `backend/tests/test_ai_analyzer.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from services.ai_analyzer import AIAnalyzer

@pytest.mark.asyncio
async def test_extract_keywords():
    """测试关键词提取"""
    analyzer = AIAnalyzer()
    clause = "买方应在收到发票后30日内支付货款，逾期按日利率0.05%计算违约金。"

    keywords = await analyzer.extract_keywords(clause)

    assert isinstance(keywords, list)
    assert len(keywords) >= 3
    # 应包含税务相关关键词
    assert any(k in ["发票", "付款", "违约金", "增值税", "货款"] for k in keywords)

@pytest.mark.asyncio
async def test_judge_compliance():
    """测试合规判定"""
    analyzer = AIAnalyzer()
    clause = "买方应在收到发票后30日内支付货款。"
    regulations = [
        {"title": "增值税发票管理办法", "content": "发票应在交易发生后及时开具..."}
    ]

    result = await analyzer.judge_compliance(clause, regulations)

    assert result.risk_level in ["合规", "高风险", "不合规"]
    assert isinstance(result.violated_regulations, list)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_ai_analyzer.py -v`
Expected: FAIL (AIAnalyzer not defined)

- [ ] **Step 3: 实现AIAnalyzer**

```python
import json
import logging
from openai import AsyncOpenAI
from config import settings
from models.schemas import SectionAuditResult

logger = logging.getLogger(__name__)

KEYWORD_PROMPT = """你是一个税务合同分析专家。请从以下合同条款中提取用于搜索相关税务法规的关键词。

条款内容：
{clause}

要求：
1. 提取3-5个关键词，聚焦税务合规相关内容
2. 关键词应能匹配到税务法规库中的相关文档
3. 输出格式：JSON数组，如 ["发票", "付款期限", "违约金"]

请直接输出关键词JSON数组，不要其他解释。"""

COMPLIANCE_PROMPT = """你是一个税务合同合规审计专家。请根据相关税务法规，判断以下合同条款的合规性。

【条款内容】
{clause}

【相关法规】
{regulations}

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

请直接输出JSON，不要其他解释。"""

class AIAnalyzer:
    """GLM-5 AI分析服务"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.bailian_api_key,
            base_url=settings.bailian_base_url
        )
        self.model = settings.bailian_model

    async def extract_keywords(self, clause: str) -> list[str]:
        """
        从条款中提取搜索关键词

        Args:
            clause: 条款文本

        Returns:
            关键词列表
        """
        logger.info(f"Extracting keywords from clause: {clause[:50]}...")

        prompt = KEYWORD_PROMPT.format(clause=clause)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON数组
        try:
            # 清理可能的markdown格式
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            keywords = json.loads(content)
            if isinstance(keywords, list):
                return [str(k).strip() for k in keywords]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse keywords: {content}")
            # fallback: 分词
            return clause.split()[:5]

        return []

    async def judge_compliance(
        self,
        clause: str,
        regulations: list[dict]
    ) -> SectionAuditResult:
        """
        判断条款合规性

        Args:
            clause: 条款文本
            regulations: 相关法规列表

        Returns:
            审计结果
        """
        logger.info(f"Judging compliance for clause: {clause[:50]}...")

        # 格式化法规文本
        reg_text = "\n".join([
            f"{i+1}. {r.get('title', '未知法规')}\n   {r.get('content', '')[:300]}"
            for i, r in enumerate(regulations)
        ])

        prompt = COMPLIANCE_PROMPT.format(clause=clause, regulations=reg_text)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # 解析JSON
        try:
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            return SectionAuditResult(
                section_name="",  # 由调用者填充
                original_content=clause,
                risk_level=result.get("risk_level", "合规"),
                violated_regulations=result.get("violated_regulations", []),
                reason=result.get("reason", ""),
                suggestion=result.get("suggestion", "")
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse compliance result: {content}")
            return SectionAuditResult(
                section_name="",
                original_content=clause,
                risk_level="合规",
                violated_regulations=[],
                reason="AI响应解析失败",
                suggestion=""
            )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_ai_analyzer.py -v`
Expected: PASS (需要配置百炼API Key)

- [ ] **Step 5: Commit**

```bash
git add backend/services/ai_analyzer.py backend/tests/test_ai_analyzer.py
git commit -m "feat: add AI analyzer for keyword extraction and compliance judgment"
```

---

## Task 6: 报告生成服务

**Files:**

- Create: `backend/services/report_generator.py`
- Test: `backend/tests/test_report_generator.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from services.report_generator import ReportGenerator
from models.schemas import AuditReport, SectionAuditResult
import os

def test_generate_report():
    """测试生成审计报告docx"""
    report_data = AuditReport(
        sections=[
            SectionAuditResult(
                section_name="付款条款",
                original_content="买方应在收到发票后30日内支付货款。",
                risk_level="合规",
                violated_regulations=[],
                reason="条款符合增值税发票管理规定",
                suggestion=""
            ),
            SectionAuditResult(
                section_name="违约条款",
                original_content="逾期按日利率0.05%计算违约金。",
                risk_level="高风险",
                violated_regulations=["合同法第114条"],
                reason="违约金比例偏高，可能超过实际损失30%",
                suggestion="建议调整违约金比例至日利率0.03%以下"
            )
        ],
        summary="共审计2个章节，1个高风险条款需要关注"
    )

    generator = ReportGenerator()
    output_path = generator.generate(report_data, "test_output.docx")

    # 验证文件存在
    assert os.path.exists(output_path)

    # 清理
    os.unlink(output_path)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_report_generator.py -v`
Expected: FAIL (ReportGenerator not defined)

- [ ] **Step 3: 实现ReportGenerator**

```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from models.schemas import AuditReport, SectionAuditResult
import os
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    """生成审计报告docx"""

    def generate(self, report: AuditReport, output_filename: str = "审计报告.docx") -> str:
        """
        生成审计报告

        Args:
            report: 审计报告数据
            output_filename: 输出文件名

        Returns:
            生成的文件路径
        """
        doc = Document()

        # 标题
        title = doc.add_heading("税务合同审计报告", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 整体摘要
        doc.add_heading("审计摘要", level=1)
        doc.add_paragraph(report.summary)

        # 统计信息
        compliant_count = sum(1 for s in report.sections if s.risk_level == "合规")
        high_risk_count = sum(1 for s in report.sections if s.risk_level == "高风险")
        non_compliant_count = sum(1 for s in report.sections if s.risk_level == "不合规")

        stats_para = doc.add_paragraph()
        stats_para.add_run(f"合规条款: {compliant_count}  ")
        stats_para.add_run(f"高风险条款: {high_risk_count}  ").bold = True
        stats_para.add_run(f"不合规条款: {non_compliant_count}  ").bold = True

        # 各章节详情
        doc.add_heading("详细分析", level=1)

        for section in report.sections:
            self._add_section(doc, section)

        # 保存文件
        output_path = os.path.join(os.getcwd(), output_filename)
        doc.save(output_path)
        logger.info(f"Report saved to {output_path}")

        return output_path

    def _add_section(self, doc: Document, section: SectionAuditResult):
        """添加单个章节的分析结果"""

        # 章节标题
        heading = doc.add_heading(section.section_name, level=2)

        # 风险等级（颜色标记）
        risk_para = doc.add_paragraph()
        risk_para.add_run("风险等级: ").bold = True

        risk_run = risk_para.add_run(section.risk_level)
        if section.risk_level == "不合规":
            risk_run.font.color.rgb = RGBColor(255, 0, 0)  # 红色
            risk_run.bold = True
        elif section.risk_level == "高风险":
            risk_run.font.color.rgb = RGBColor(255, 165, 0)  # 橙色
            risk_run.bold = True
        else:
            risk_run.font.color.rgb = RGBColor(0, 128, 0)  # 绿色

        # 条款原文
        doc.add_paragraph().add_run("条款原文:").bold = True
        doc.add_paragraph(section.original_content)

        # 违反法规
        if section.violated_regulations:
            doc.add_paragraph().add_run("违反法规:").bold = True
            for reg in section.violated_regulations:
                doc.add_paragraph(f"  - {reg}", style="List Bullet")

        # 原因分析
        if section.reason:
            doc.add_paragraph().add_run("原因分析:").bold = True
            doc.add_paragraph(section.reason)

        # 修改建议
        if section.suggestion:
            doc.add_paragraph().add_run("修改建议:").bold = True
            suggestion_para = doc.add_paragraph(section.suggestion)
            suggestion_para.runs[0].font.color.rgb = RGBColor(0, 100, 0)

        # 分隔线
        doc.add_paragraph("─" * 40)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/EY/contractAgent/backend && pytest tests/test_report_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/report_generator.py backend/tests/test_report_generator.py
git commit -m "feat: add report generator for docx output"
```

---

## Task 7: FastAPI主入口

**Files:**

- Create: `backend/main.py`

- [ ] **Step 1: 创建main.py**

```python
import os
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from services.contract_parser import ContractParser
from services.mcp_client import MCPClient
from services.ai_analyzer import AIAnalyzer
from services.report_generator import ReportGenerator
from models.schemas import AuditReport, SectionAuditResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="税务合同审计助手", version="1.0.0")

# CORS配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务实例
parser = ContractParser()
mcp_client = MCPClient()
ai_analyzer = AIAnalyzer()
report_generator = ReportGenerator()


@app.post("/api/upload")
async def upload_contract(file: UploadFile = File(...)):
    """
    上传合同进行审计

    Args:
        file: docx合同文件

    Returns:
        审计报告docx文件
    """
    logger.info(f"Received file: {file.filename}")

    # 验证文件类型
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持docx格式文件")

    # 保存临时文件
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp:
        content = await file.read()
        temp.write(content)
        temp_path = temp.name

    try:
        # 1. 解析合同
        sections = parser.parse(temp_path)
        logger.info(f"Parsed {len(sections)} sections")

        # 2. 逐章节分析
        audit_results = []
        for section in sections:
            # 提取关键词
            keywords = await ai_analyzer.extract_keywords(section.content)
            logger.info(f"Keywords for {section.section_name}: {keywords}")

            # 搜索法规
            query_text = " ".join(keywords)
            search_result = await mcp_client.search_regulations(query_text)
            regulations = mcp_client.parse_regulations(search_result)
            logger.info(f"Found {len(regulations)} regulations for {section.section_name}")

            # 合规判定
            audit_result = await ai_analyzer.judge_compliance(
                section.content,
                [{"title": r.title, "content": r.content} for r in regulations]
            )
            audit_result.section_name = section.section_name
            audit_results.append(audit_result)

        # 3. 生成摘要
        high_risk_count = sum(1 for r in audit_results if r.risk_level == "高风险")
        non_compliant_count = sum(1 for r in audit_results if r.risk_level == "不合规")

        summary = f"共审计{len(audit_results)}个章节，"
        if non_compliant_count > 0:
            summary += f"{non_compliant_count}个不合规条款需立即整改，"
        if high_risk_count > 0:
            summary += f"{high_risk_count}个高风险条款需要关注。"
        else:
            summary += "整体合规性良好。"

        # 4. 生成报告
        report = AuditReport(sections=audit_results, summary=summary)
        report_path = report_generator.generate(report, "审计报告.docx")

        # 5. 返回文件
        return FileResponse(
            path=report_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="审计报告.docx"
        )

    finally:
        # 清理临时文件
        os.unlink(temp_path)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

- [ ] **Step 2: 启动服务验证**

Run: `cd D:/EY/contractAgent/backend && uvicorn main:app --reload --port 8001`
Expected: 服务启动成功，访问 http://localhost:8001/docs 可见API文档

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: add FastAPI main entry with upload endpoint"
```

---

## Task 8: 前端项目初始化

**Files:**

- Create: `frontend/` (使用Vite初始化)

- [ ] **Step 1: 初始化React项目**

Run: `cd D:/EY/contractAgent && npm create vite@latest frontend -- --template react-ts`
Expected: frontend目录创建成功

- [ ] **Step 2: 安装依赖**

Run: `cd D:/EY/contractAgent/frontend && npm install`
Expected: npm依赖安装成功

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: init react frontend with vite"
```

---

## Task 9: 前端API层

**Files:**

- Create: `frontend/src/api/upload.ts`

- [ ] **Step 1: 创建API调用文件**

```typescript
const API_BASE = 'http://localhost:8001';

export async function uploadContract(file: File): Promise<Blob> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || '上传失败');
  }

  return response.blob();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/upload.ts
git commit -m "feat: add frontend api layer"
```

---

## Task 10: 前端文件上传组件

**Files:**

- Create: `frontend/src/components/FileUpload.tsx`

- [ ] **Step 1: 创建文件上传组件**

```tsx
import React, { useState, useRef } from 'react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled: boolean;
}

export function FileUpload({ onFileSelect, disabled }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.docx')) {
        setSelectedFile(file);
        onFileSelect(file);
      } else {
        alert('请上传docx格式文件');
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.endsWith('.docx')) {
        setSelectedFile(file);
        onFileSelect(file);
      } else {
        alert('请上传docx格式文件');
      }
    }
  };

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <div
      className={`upload-area ${dragActive ? 'drag-active' : ''} ${disabled ? 'disabled' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".docx"
        onChange={handleChange}
        disabled={disabled}
        style={{ display: 'none' }}
      />
      <div className="upload-icon">📄</div>
      <p className="upload-text">
        {selectedFile ? `已选择: ${selectedFile.name}` : '点击或拖拽上传docx文件'}
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FileUpload.tsx
git commit -m "feat: add file upload component with drag support"
```

---

## Task 11: 前端进度条组件

**Files:**

- Create: `frontend/src/components/ProgressBar.tsx`

- [ ] **Step 1: 创建进度条组件**

```tsx
interface ProgressBarProps {
  current: number;
  total: number;
  sectionName: string;
}

export function ProgressBar({ current, total, sectionName }: ProgressBarProps) {
  const percentage = Math.round((current / total) * 100);

  return (
    <div className="progress-container">
      <div className="progress-info">
        <span>处理进度:</span>
        <span>{current}/{total} 章节</span>
      </div>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="progress-section">正在分析: {sectionName}</p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ProgressBar.tsx
git commit -m "feat: add progress bar component"
```

---

## Task 12: 前端下载按钮组件

**Files:**

- Create: `frontend/src/components/DownloadButton.tsx`

- [ ] **Step 1: 创建下载按钮组件**

```tsx
	interface DownloadButtonProps {
  blob: Blob;
  filename: string;
  onReset: () => void;
}

export function DownloadButton({ blob, filename, onReset }: DownloadButtonProps) {
  const handleDownload = () => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="download-container">
      <button className="download-btn" onClick={handleDownload}>
        📥 下载审计报告
      </button>
      <button className="reset-btn" onClick={onReset}>
        重新审计
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/DownloadButton.tsx
git commit -m "feat: add download button component"
```

---

## Task 13: 前端主页面

**Files:**

- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.css`

- [ ] **Step 1: 创建样式文件**

```css
.container {
  max-width: 800px;
  margin: 50px auto;
  padding: 20px;
}

.title {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 10px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #007bff;
  background: #f8f9fa;
}

.upload-area.drag-active {
  border-color: #007bff;
  background: #e7f3ff;
}

.upload-area.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.upload-text {
  color: #666;
}

.btn {
  display: block;
  margin: 20px auto;
  padding: 12px 30px;
  font-size: 16px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.start-btn {
  background: #007bff;
  color: white;
}

.start-btn:hover:not(:disabled) {
  background: #0056b3;
}

.start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-container {
  margin: 20px 0;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 5px;
}

.progress-bar {
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #00d4ff);
  transition: width 0.3s;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.progress-section {
  margin-top: 10px;
  color: #666;
}

.download-container {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.download-btn {
  background: #28a745;
  color: white;
}

.download-btn:hover {
  background: #1e7e34;
}

.reset-btn {
  background: #6c757d;
  color: white;
}

.reset-btn:hover {
  background: #545b62;
}

.error-message {
  color: #dc3545;
  text-align: center;
  margin: 20px 0;
}
```

- [ ] **Step 2: 实现App.tsx**

```tsx
import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { ProgressBar } from './components/ProgressBar';
import { DownloadButton } from './components/DownloadButton';
import { uploadContract } from './api/upload';
import './App.css';

type Status = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

export function App() {
  const [status, setStatus] = useState<Status>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string>('');
  const [progress, setProgress] = useState({ current: 0, total: 0, section: '' });

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setStatus('idle');
    setError('');
  };

  const handleStart = async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setError('');

    try {
      const blob = await uploadContract(selectedFile);
      setResultBlob(blob);
      setStatus('done');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : '审计失败，请重试');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setSelectedFile(null);
    setResultBlob(null);
    setError('');
    setProgress({ current: 0, total: 0, section: '' });
  };

  return (
    <div className="container">
      <h1 className="title">税务合同审计助手</h1>

      <FileUpload
        onFileSelect={handleFileSelect}
        disabled={status === 'uploading' || status === 'processing'}
      />

      {status === 'idle' && selectedFile && (
        <button
          className="btn start-btn"
          onClick={handleStart}
          disabled={!selectedFile}
        >
          开始审计
        </button>
      )}

      {(status === 'uploading' || status === 'processing') && (
        <ProgressBar
          current={progress.current}
          total={progress.total}
          sectionName={progress.section}
        />
      )}

      {status === 'error' && (
        <p className="error-message">{error}</p>
      )}

      {status === 'done' && resultBlob && (
        <DownloadButton
          blob={resultBlob}
          filename="审计报告.docx"
          onReset={handleReset}
        />
      )}
    </div>
  );
}

export default App;
```

- [ ] **Step 3: 启动前端验证**

Run: `cd D:/EY/contractAgent/frontend && npm run dev`
Expected: 前端启动成功，访问 http://localhost:3000 可见页面

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: implement main app page with upload flow"
```

---

## Task 14: 集成测试

**Files:**

- Test: 整体流程测试

- [ ] **Step 1: 确保MCP Server运行**

Run: `cd D:/EY/contractAgent/mcp && python -m src.server elasticsearch-mcp-server --transport streamable-http --port 8000`
Expected: MCP Server在8000端口运行

- [ ] **Step 2: 启动FastAPI后端**

Run: `cd D:/EY/contractAgent/backend && uvicorn main:app --port 8001`
Expected: 后端在8001端口运行

- [ ] **Step 3: 启动React前端**

Run: `cd D:/EY/contractAgent/frontend && npm run dev`
Expected: 前端在3000端口运行

- [ ] **Step 4: 测试完整流程**

手动测试：

1. 访问 http://localhost:3000
2. 上传 `税务合同审计测试样本.docx`
3. 点击"开始审计"
4. 等待处理完成
5. 点击"下载审计报告"
6. 验证下载的docx文件内容

Expected: 整个流程正常，审计报告docx格式正确

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: complete tax contract auditor integration"
```

---

## Self-Review Checklist

- [X] **Spec coverage:** 所有设计需求已覆盖

  - docx解析 ✓ (Task 3)
  - MCP法规搜索 ✓ (Task 4)
  - GLM-5分析 ✓ (Task 5)
  - 报告生成 ✓ (Task 6)
  - 前端上传下载 ✓ (Tasks 8-13)
- [X] **Placeholder scan:** 无TBD/TODO占位符
- [X] **Type consistency:** 数据模型一致

  - ContractSection.section_name → SectionAuditResult.section_name ✓
  - Regulation结构一致 ✓
