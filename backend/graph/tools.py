"""
LangChain 工具定义

演示 @tool 装饰器模式：
- 使用 @tool 将函数转换为 LangChain Tool
- 清晰的 docstring 作为工具描述
- 类型注解自动生成工具 Schema
"""

import asyncio
import logging
from langchain_core.tools import tool
from typing import List, Dict

from services.mcp_client import MCPClient
from services.contract_parser import ContractParser

logger = logging.getLogger(__name__)

# 全局客户端实例（懒加载）
_mcp_client: MCPClient = None
_contract_parser: ContractParser = None


def _get_mcp_client() -> MCPClient:
    """获取 MCP 客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


def _get_contract_parser() -> ContractParser:
    """获取合同解析器单例"""
    global _contract_parser
    if _contract_parser is None:
        _contract_parser = ContractParser()
    return _contract_parser


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
    logger.info(f"解析合同文件: {file_path}")
    parser = _get_contract_parser()
    sections = parser.parse(file_path)

    # 转换为字典列表
    return [
        {
            "section_name": section.section_name,
            "content": section.content
        }
        for section in sections
    ]


@tool
def search_regulations(query_text: str, size: int = 10) -> List[Dict]:
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
    logger.info(f"搜索法规: query={query_text}, size={size}")

    # MCPClient 是异步的，需要在事件循环中运行
    client = _get_mcp_client()

    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的事件循环，创建新的
        loop = None

    async def _search():
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

    if loop and loop.is_running():
        # 在已有事件循环中，使用 run_coroutine_threadsafe
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _search())
            return future.result()
    else:
        # 直接运行异步函数
        return asyncio.run(_search())


# 导出工具列表，方便在 StateGraph 中使用
TOOLS = [parse_contract, search_regulations]