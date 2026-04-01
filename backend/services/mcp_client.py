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
        self.session_id = None

    async def _ensure_initialized(self, client: httpx.AsyncClient):
        """确保MCP会话已初始化"""
        if self.session_id:
            return

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        # Step 1: 发送initialize请求
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tax-contract-auditor", "version": "1.0"}
            }
        }

        response = await client.post(
            self.base_url,
            json=init_payload,
            headers=headers
        )
        response.raise_for_status()

        # 从response header中提取session ID
        self.session_id = response.headers.get("mcp-session-id")
        logger.info(f"MCP session initialized: {self.session_id}")

        # Step 2: 发送initialized通知 (必须!)
        notify_payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        headers_with_session = headers.copy()
        if self.session_id:
            headers_with_session["mcp-session-id"] = self.session_id

        response = await client.post(
            self.base_url,
            json=notify_payload,
            headers=headers_with_session
        )
        response.raise_for_status()
        logger.info("MCP initialized notification sent")

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

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
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

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 先初始化会话
            await self._ensure_initialized(client)

            # 添加session ID到header
            if self.session_id:
                headers["mcp-session-id"] = self.session_id

            # 调用工具
            response = await client.post(
                self.base_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            # 解析SSE格式响应
            text = response.text
            result = self._parse_sse_response(text)

        # 解析MCP响应格式
        if "result" in result:
            content = result.get("result", {}).get("content", [])
            if content and isinstance(content, list):
                text_content = content[0].get("text", "{}")
                return json.loads(text_content)

        logger.warning(f"Unexpected MCP response format: {result}")
        return {"hits": {"hits": []}}

    def _parse_sse_response(self, text: str) -> dict:
        """解析SSE格式的响应"""
        # SSE格式: "event: message\ndata: {...}\n\n"
        for line in text.split("\n"):
            if line.startswith("data: "):
                return json.loads(line[6:])
        # 如果不是SSE格式，尝试直接解析JSON
        try:
            return json.loads(text)
        except:
            return {}

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