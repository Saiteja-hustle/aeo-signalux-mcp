import csv
import io
import requests
from typing import Annotated

# Lookup table: keyword name -> that tab's gid number
GIDS = {
    "screen studio alternative": "0",
    "best screen recorder for mac": "1",
    "loom cheaper alternative": "2",
    "tella alternative": "3",
}

def get_keyword(name: Annotated[str, "The keyword to look up, e.g. 'screen studio alternative'"]):
    """Use this when the user asks about one specific keyword/prompt —
    returns its full task list, each marked with whether it's done or still pending."""
    gid = GIDS[name]  # find the gid for this keyword name

    # build the CSV download link for that specific tab
    sheet_url = f"https://docs.google.com/spreadsheets/d/1kgcQ_gaZIFGMO1EGZiWlHTWCuDjZgfAZqPoHE9IQmf8/gviz/tq?tqx=out:csv&headers=0&gid={gid}"

    rows = []  # empty basket to collect real task rows into

    # download the tab as CSV text, then read it row by row
    for row in csv.reader(io.StringIO(requests.get(sheet_url).text)):
        if row[0] in ("P1", "P2", "P3"):  # only keep real task rows, skip titles/blank lines/headers
            rows.append({
                "priority": row[0],
                "task": row[1],
                "where": row[2],
                "why": row[3],
                "how": row[4],
                "status": row[7],
            })

    return rows  # hand back every task row found for this keyword

print(get_keyword("screen studio alternative"))

def get_overall():
    """Use this when the user asks for overall numbers — rankings,
    search volume, or which competitors the AI names, across all keywords."""
    sheet_url = "https://docs.google.com/spreadsheets/d/1kgcQ_gaZIFGMO1EGZiWlHTWCuDjZgfAZqPoHE9IQmf8/gviz/tq?tqx=out:csv&headers=0&gid=5"

    rows = []
    seen = set()  # keeps track of which prompts we've already taken a row for

    for row in csv.reader(io.StringIO(requests.get(sheet_url).text)):
        if row[0] in ("screen studio alternative", "best screen recorder for mac",
                      "loom cheaper alternative", "tella alternative") and row[0] not in seen:
            rows.append({
                "prompt": row[0],
                "rank": row[1],
                "searches": row[2],
                "who_ai_names_instead": row[6],
            })
            seen.add(row[0])  # mark this prompt as taken, so the second table's copy gets skipped

    return rows

print(get_overall())

def get_priority_tasks():
    """Use this when the user asks what's pending or what to do next —
    returns every unfinished P1 task across all keywords."""
    pending = []  # collects P1 tasks that are still not done, across all 4 keywords

    for name in GIDS:  # loop over each keyword name
        for task in get_keyword(name):  # reuse get_keyword to fetch that keyword's tasks
            if task["priority"] == "P1" and task["status"] != "Done":
                pending.append({
                    "keyword": name,  # so you know which keyword this task belongs to
                    "task": task["task"],
                    "where": task["where"],
                    "status": task["status"],
                })

    return pending

print(get_priority_tasks())