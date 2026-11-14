import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


def test_real_stdio_protocol(tmp_path):
    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "cli_anything.kselect.server"], cwd=tmp_path)
        async with stdio_client(params) as streams:
            async with ClientSession(*streams, read_timeout_seconds=15) as session:
                info = await session.initialize()
                assert info.server_info.name == "K-Select Agent Toolkit"
                names = {t.name for t in (await session.list_tools()).tools}
                assert names == {"get_capabilities", "get_status", "launch", "calculate_performance", "read_report", "verify_result"}
                result = await session.call_tool("get_capabilities", {})
                data = json.loads(result.content[0].text)
                assert data["ok"]
                bad = await session.call_tool("calculate_performance", {"airflow": -1})
                assert not json.loads(bad.content[0].text)["ok"]
                fixture = Path(__file__).parent / "fixtures/1400-8in-300cfm.pdf"
                result = await session.call_tool("verify_result", {"pdf": str(fixture.resolve()), "airflow": 300})
                assert json.loads(result.content[0].text)["checks"]["airflow"]
    asyncio.run(run())
