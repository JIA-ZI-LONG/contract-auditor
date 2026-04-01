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