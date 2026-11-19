"""Own-data version: ask questions about the CursorClip AEO tracking sheet.
Run: python tool_call.py "your question" """
import csv, io, json, os, sys
import requests
from typing import Annotated
from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("GROQ_API_KEY"):
    raise SystemExit("No GROQ_API_KEY found. Make a file called .env next to tool_call.py with one line: GROQ_API_KEY=your key")

# ---------- THE SHEET ----------
GIDS = {
    "screen studio alternative": "0",
    "best screen recorder for mac": "1",
    "loom cheaper alternative": "2",
    "tella alternative": "3",
}

def get_keyword(name: Annotated[str, "The keyword to look up, e.g. 'screen studio alternative'"]):
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

def get_overall():
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

def get_priority_tasks():
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

# dispatch table: card name -> actual function to call
FUNCTIONS = {
    "get_keyword": get_keyword,
    "get_overall": get_overall,
    "get_priority_tasks": get_priority_tasks,
}

# ---------- THE MODEL (given, unchanged) ----------
def ask_model(messages, tools=None):
    body = {"model": "openai/gpt-oss-120b", "messages": messages}
    if tools:
        body["tools"] = tools
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]

# ---------- THE CARDS ----------
cards = [
    {"type": "function", "function": {
        "name": "get_keyword",
        "description": "Use this when the user asks about one specific keyword/prompt — returns its full task list, each marked with whether it's done or still pending.",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string",
                                               "description": "The keyword to look up, e.g. 'screen studio alternative'"}},
                       "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "get_overall",
        "description": "Use this when the user asks for overall numbers — rankings, search volume, or which competitors the AI names, across all keywords.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_priority_tasks",
        "description": "Use this when the user asks what's pending or what to do next — returns every unfinished P1 task across all keywords.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]

# ---------- YOUR SERVER ----------
question = " ".join(sys.argv[1:]) or "What are my pending priority tasks?"
messages = [{"role": "user", "content": question}]

reply = ask_model(messages, cards)

while reply.get("tool_calls"):
    call = reply["tool_calls"][0]
    name = call["function"]["name"]
    args = json.loads(call["function"]["arguments"])
    args.pop("", None)
    print("The model asked for:", name, args)
    result = FUNCTIONS[name](**args)   # look up the right function by name, call it
    messages.append(reply)
    messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
    reply = ask_model(messages, cards)

print("\n" + reply["content"])