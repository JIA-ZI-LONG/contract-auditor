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


@pytest.mark.asyncio
async def test_parse_regulations():
    """测试解析搜索结果为Regulation列表"""
    client = MCPClient()

    # 模拟ES搜索结果
    mock_search_result = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "title": "增值税暂行条例",
                        "content": "纳税人销售货物或者应税劳务，应当向索取增值税专用发票的购买方开具增值税专用发票",
                        "issuingBody": "国务院",
                        "publishedDate": "2008-11-10"
                    }
                },
                {
                    "_source": {
                        "title": "发票管理办法",
                        "content": "发票是指在购销商品、提供或者接受服务以及从事其他经营活动中，开具、收取的收付款凭证",
                        "issuingBody": "财政部",
                        "publishedDate": "2010-12-20"
                    }
                }
            ]
        }
    }

    regulations = client.parse_regulations(mock_search_result)

    assert len(regulations) == 2
    assert regulations[0].title == "增值税暂行条例"
    assert regulations[0].issuing_body == "国务院"
    assert regulations[1].title == "发票管理办法"
    assert regulations[1].issuing_body == "财政部"