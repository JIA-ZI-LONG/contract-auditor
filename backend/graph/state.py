"""
LangGraph State 定义

演示 TypedDict State 模式：
- 使用 TypedDict 定义结构化状态
- Annotated[List, add] 实现列表累加
"""

from typing import TypedDict, List, Annotated
from operator import add


class AuditState(TypedDict):
    """
    税务合同审阅状态

    Attributes:
        file_path: 上传的合同文件路径
        sections: 解析后的合同章节列表
        current_section_idx: 当前正在处理的章节索引
        audit_results: 累积的审阅结果（使用 Annotated 实现自动累加）
        regulations: 当前章节搜索到的法规列表
        keywords: 当前章节提取的关键词
        summary: 最终审阅摘要
        report_path: 生成的报告文件路径
        error: 错误信息（如有）
    """
    file_path: str
    sections: List[dict]
    current_section_idx: int
    audit_results: Annotated[List[dict], add]  # 自动累加模式
    regulations: List[dict]
    keywords: List[str]
    summary: str
    report_path: str
    error: str