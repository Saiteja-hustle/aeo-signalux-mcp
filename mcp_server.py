"""Own-data version: expose the 3 CursorClip functions as an MCP server.
Run: python mcp_server.py"""
import csv, io, socket
from typing import Annotated
import requests
from fastmcp import FastMCP

GIDS = {
    "screen studio alternative": "0",
    "best screen recorder for mac": "1",
    "loom cheaper alternative": "2",
    "tella alternative": "3",
}

mcp = FastMCP("CursorClip AEO tracker")

@mcp.tool
def get_keyword(name: Annotated[str, "The keyword to look up, e.g. 'screen studio alternative'"]) -> list:
    """Use this when the user asks about one specific keyword/prompt —
    returns its full task list, each marked with whether it's done or still pending."""
    gid = GIDS[name]
    sheet_url = f"https://docs.google.com/spreadsheets/d/1kgcQ_gaZIFGMO1EGZiWlHTWCuDjZgfAZqPoHE9IQmf8/gviz/tq?tqx=out:csv&headers=0&gid={gid}"
    rows = []
    for row in csv.reader(io.StringIO(requests.get(sheet_url).text)):
        if row[0] in ("P1", "P2", "P3"):
            rows.append({
                "priority": row[0], "task": row[1], "where": row[2],
                "why": row[3], "how": row[4], "status": row[7],
            })
    return rows

@mcp.tool
def get_overall() -> list:
    """Use this when the user asks for overall numbers — rankings,
    search volume, or which competitors the AI names, across all keywords."""
    sheet_url = "https://docs.google.com/spreadsheets/d/1kgcQ_gaZIFGMO1EGZiWlHTWCuDjZgfAZqPoHE9IQmf8/gviz/tq?tqx=out:csv&headers=0&gid=5"
    rows, seen = [], set()
    for row in csv.reader(io.StringIO(requests.get(sheet_url).text)):
        if row[0] in GIDS and row[0] not in seen:
            rows.append({
                "prompt": row[0], "rank": row[1], "searches": row[2],
                "who_ai_names_instead": row[6],
            })
            seen.add(row[0])
    return rows

@mcp.tool
def get_priority_tasks() -> list:
    """Use this when the user asks what's pending or what to do next —
    returns every unfinished P1 task across all keywords."""
    pending = []
    for name in GIDS:
        for task in get_keyword(name):
            if task["priority"] == "P1" and task["status"] != "Done":
                pending.append({
                    "keyword": name, "task": task["task"],
                    "where": task["where"], "status": task["status"],
                })
    return pending

# Any app can now reach it at http://localhost:8000/mcp
if __name__ == "__main__":
    if socket.socket().connect_ex(("127.0.0.1", 8000)) == 0:
        raise SystemExit("Port 8000 is already in use, probably by a server you started earlier. "
                         "Stop it with Ctrl+C in its terminal, or run: kill $(lsof -t -i:8000)")
    mcp.run(transport="http", port=8000)