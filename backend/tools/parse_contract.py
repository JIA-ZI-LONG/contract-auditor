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