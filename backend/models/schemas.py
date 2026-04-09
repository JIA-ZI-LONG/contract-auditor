"""
Pydantic 数据模型

演示结构化输出模式：
- 使用 Pydantic BaseModel 定义 LLM 输出 Schema
- 配合 LLM.with_structured_output() 实现可靠解析
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ============ 基础数据模型 ============

class ContractSection(BaseModel):
    """合同章节"""
    section_name: str
    content: str


class Regulation(BaseModel):
    """法规搜索结果"""
    title: str
    content: str
    issuing_body: str = ""
    published_date: str = ""


class SectionAuditResult(BaseModel):
    """单章节审计结果"""
    section_name: str
    original_content: str
    risk_level: str  # "合规"/"高风险"/"不合规"
    violated_regulations: List[str] = []
    reason: str = ""
    suggestion: str = ""


class AuditReport(BaseModel):
    """完整审计报告"""
    sections: List[SectionAuditResult]
    summary: str = ""


# ============ LLM 结构化输出 Schema ============

class KeywordOutput(BaseModel):
    """
    关键词提取输出 Schema

    演示 LLM 结构化输出模式：
    - 明确的字段类型和描述
    - LLM 会根据 Schema 生成符合格式的 JSON
    """
    keywords: List[str] = Field(
        description="从合同条款中提取的3-5个税务相关搜索关键词"
    )


class ComplianceJudgment(BaseModel):
    """
    合规判定输出 Schema

    演示复杂结构化输出：
    - Literal 类型约束枚举值
    - 嵌套列表结构
    - 详细字段描述指导 LLM 生成
    """
    risk_level: Literal["合规", "高风险", "不合规"] = Field(
        description="合规性判定结果"
    )
    violated_regulations: List[str] = Field(
        default_factory=list,
        description="违反的法规标题列表，合规时为空"
    )
    reason: str = Field(
        description="详细分析该条款为什么存在风险或不合规，引用法规原文说明"
    )
    suggestion: str = Field(
        description="如果存在问题，给出具体的修改建议或替代条款"
    )