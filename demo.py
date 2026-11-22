"""Run a readable, fixture-only MCP walkthrough. No bank setup is accepted."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import redirect_stderr
import html
import io
import json
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent
TOOLS = {"list_accounts", "get_balance", "get_transactions",
         "search_transactions", "summarize_transactions"}
CALLS = (
    ("list_accounts", {}),
    ("get_balance", {"account": "demo-eur"}),
    ("get_transactions", {"account": "demo-eur", "start": "2026-01-01",
                          "end": "2026-01-05", "limit": 2}),
    ("search_transactions", {"account": "demo-eur", "start": "2026-01-01",
                             "end": "2026-01-05", "query": "refund"}),
    ("summarize_transactions", {"account": "demo-eur", "start": "2026-01-01",
                                "end": "2026-01-05"}),
)


async def walkthrough():
    """Use the real stdio protocol with the existing network-denying launcher."""
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "fixture_audit_launcher.py"), str(ROOT / "server.py")],
        env={},
    )
    steps = []
    # Never echo server diagnostics or unexpected payloads on failure.
    with tempfile.TemporaryFile(mode="w+") as diagnostics:
        async with stdio_client(params, errlog=diagnostics) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                discovered = await client.list_tools()
                if {tool.name for tool in discovered.tools} != TOOLS:
                    raise RuntimeError("Unexpected demo tool set")
                for name, arguments in CALLS:
                    result = await client.call_tool(name, arguments)
                    if result.isError or len(result.content) != 1:
                        raise RuntimeError("Demo read failed")
                    payload = json.loads(result.content[0].text)
                    if (payload.get("live") is not False
                            or payload.get("source") != "synthetic-fixtures"
                            or payload.get("as_of") != "2026-01-05"):
                        raise RuntimeError("Unexpected demo provenance")
                    steps.append({"tool": name, "arguments": arguments, "result": payload})
                denied = await client.call_tool("make_payment", {})
                if not denied.isError:
                    raise RuntimeError("Unsupported tool was not rejected")
    return {"source": "synthetic-fixtures", "live": False,
            "as_of": "2026-01-05", "steps": steps, "payment_tool_rejected": True}


def render_text(report):
    lines = ["PERSONAL BANKING MCP | SYNTHETIC DEMO", "No bank connection. No money movement.",
             "Fixture date: 2026-01-05 (not a current balance)", ""]
    for index, step in enumerate(report["steps"], 1):
        lines.extend([f"{index}. {step['tool']}", json.dumps(step["result"], indent=2), ""])
    lines.append("Unsupported make_payment tool: REJECTED")
    return "\n".join(lines) + "\n"


def render_html(report):
    sections = "".join(
        f"<section><h2>{i}. {html.escape(step['tool'])}</h2>"
        f"<pre>{html.escape(json.dumps(step['result'], indent=2))}</pre></section>"
        for i, step in enumerate(report["steps"], 1)
    )
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>Personal Banking MCP | synthetic demo</title><style>'
            'body{font:16px/1.6 system-ui,sans-serif;background:#101827;color:#edf3fa;'
            'max-width:900px;margin:0 auto;padding:32px 20px}h1{line-height:1.15;font-size:36px}'
            '.label{color:#7de4c4;font-weight:700;letter-spacing:.08em}'
            '.notice{border-left:4px solid #7de4c4;padding:12px 18px;background:#1b2b40}'
            'section{margin-top:28px}h2{font-size:21px}pre{background:#19263a;padding:18px;'
            'border-radius:10px;overflow-x:auto;font-size:14px;line-height:1.5}'
            '</style><main><p class="label">LOCAL / READ ONLY / INVENTED DATA</p>'
            '<h1>See the five tools work.<br>No bank account needed.</h1>'
            '<p class="notice">Synthetic MCP walkthrough. No bank connection or money movement. '
            'Fixture date: <strong>2026-01-05</strong>, not a current balance. '
            'Generated from a local stdio session; this is not a banking dashboard.</p>'
            + sections + '<p class="notice">Unsupported make_payment tool: REJECTED</p>'
            '<p>No scripts, remote fonts, telemetry or external resources in this report. '
            'Local execution does not prevent your MCP client from sharing results with its AI service.</p>'
            '</main></html>\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, help="Create a new, local HTML report (never overwrite)")
    args = parser.parse_args(argv)
    try:
        # The SDK may print diagnostic payloads. Capture them, including errors.
        with redirect_stderr(io.StringIO()):
            report = asyncio.run(walkthrough())
        if args.html:
            with args.html.open("x", encoding="utf-8") as handle:
                handle.write(render_html(report))
        print(render_text(report), end="")
        return 0
    except Exception:
        print("Demo failed. No live bank connection was attempted. Check dependencies and choose a new report filename.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
