"""Quick smoke tests for DocumentTools MCP endpoints.

Requires the `elasticsearch-mcp-server` entrypoint to be available on PATH
inside the current environment (e.g., after `pip install -e .`). The script
starts the server over stdio, calls three tools, then prints their responses.
"""

import argparse
import asyncio
import json
from contextlib import AsyncExitStack
from typing import Iterable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _render_tool_content(content_items: Iterable) -> str:
    parts = []
    for item in content_items:
        item_type = getattr(item, "type", None)
        if item_type == "text":
            parts.append(item.text)
        elif item_type == "json":
            parts.append(json.dumps(item.data, ensure_ascii=False, indent=2))
        else:
            parts.append(str(item))
    return "\n".join(parts) if parts else "<no content>"


async def run_tests(command: str, args: list[str], selected_tools: list[str] | None) -> None:
    server_params = StdioServerParameters(command=command, args=args, env=None)

    async with AsyncExitStack() as stack:
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()

        print("Connected. Running DocumentTools test calls...\n")

        tool_plan = selected_tools or [
            "search_chinataxcenter",
            "list_chinataxcenter_tax_type",
            "list_chinataxcenter_topics",
        ]

        if "search_chinataxcenter" in tool_plan:
            search_payload = {
                "query_text": "增值税",  # sample keyword
                "size": 3,
            }
            search_result = await session.call_tool("search_chinataxcenter", search_payload)
            print("search_chinataxcenter:")
            print(_render_tool_content(search_result.content))
            print()

        if "list_chinataxcenter_tax_type" in tool_plan:
            tax_type_result = await session.call_tool("list_chinataxcenter_tax_type", {})
            print("list_chinataxcenter_tax_type:")
            print(_render_tool_content(tax_type_result.content))
            print()

        if "list_chinataxcenter_topics" in tool_plan:
            topic_result = await session.call_tool("list_chinataxcenter_topics", {})
            print("list_chinataxcenter_topics:")
            print(_render_tool_content(topic_result.content))
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test DocumentTools MCP endpoints")
    parser.add_argument(
        "--command",
        default="elasticsearch-mcp-server",
        help="Command used to launch the MCP server (default: elasticsearch-mcp-server)",
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        choices=[
            "search_chinataxcenter",
            "list_chinataxcenter_tax_type",
            "list_chinataxcenter_topics",
        ],
        help="Subset of tools to invoke; default is to call all DocumentTools endpoints",
    )
    parser.add_argument(
        "--",
        dest="server_args",
        nargs=argparse.REMAINDER,
        default=["--transport", "stdio"],
        help="Arguments passed after '--' go directly to the server command",
    )
    args = parser.parse_args()

    asyncio.run(run_tests(args.command, args.server_args, args.tools))


if __name__ == "__main__":
    main()

