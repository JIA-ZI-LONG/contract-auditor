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