"""Real stdio handshake and harmless tool calls; no private data or speech."""
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(command=sys.executable,
                                  args=[str(root / "scripts/server.py")])
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            await client.initialize()
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"read_mail", "speak_text", "stop_speech", "draft_mail_reply"} <= names
            result = await client.call_tool("system_check", {})
            assert not result.isError
            result = await client.call_tool("speak_text", {"text": ""})
            assert result.isError
            print(f"PASS: MCP handshake, {len(names)} tools, doctor, invalid speech input.")


if __name__ == "__main__":
    asyncio.run(main())
