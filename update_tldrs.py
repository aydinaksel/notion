#!/usr/bin/env python3
"""Queries last week (Done), this week (In Progress/Emergency), and next week (Next Set) tasks
and prints their IDs, titles, and requestors for TLDR review."""

import json
import subprocess
from datetime import datetime, timedelta

DATA_SOURCE_ID = "ab49c7cb-6a14-445e-9706-9ad4d0efb018"


def ntn(path, method="GET", body=None):
    cmd = ["ntn", "api", path, "-X", method]
    if body:
        cmd.extend(["--data", json.dumps(body)])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)


def notion_query(filter_body):
    pages = []
    cursor = None
    while True:
        body = {"page_size": 100, "filter": filter_body}
        if cursor:
            body["start_cursor"] = cursor
        data = ntn(f"v1/data_sources/{DATA_SOURCE_ID}/query", "POST", body)
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages


def week_bounds(offset_weeks=0):
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset_weeks)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def get_text(page, prop):
    parts = page["properties"][prop]
    if parts["type"] == "title":
        return "".join(p["plain_text"] for p in parts["title"])
    if parts["type"] == "rich_text":
        return "".join(p["plain_text"] for p in parts["rich_text"])
    if parts["type"] == "people":
        people = parts["people"]
        return ", ".join(p["name"].split()[0] for p in people) if people else ""
    return ""


def set_tldr(page_id, tldr):
    ntn(f"v1/pages/{page_id}", "PATCH", {
        "properties": {"TLDR": {"rich_text": [{"text": {"content": tldr}}]}}
    })


def main():
    last_week_start, last_week_end = week_bounds(-1)

    last_week = notion_query({"and": [
        {"property": "Status", "status": {"equals": "Done"}},
        {"property": "Completed Date", "date": {"on_or_after": last_week_start}},
        {"property": "Completed Date", "date": {"on_or_before": last_week_end}},
    ]})

    this_week = notion_query({"or": [
        {"property": "Status", "status": {"equals": "In Progress"}},
        {"property": "Status", "status": {"equals": "Emergency"}},
    ]})

    next_week = notion_query({"property": "Status", "status": {"equals": "Next Set"}})

    sections = [("LAST WEEK", last_week), ("THIS WEEK", this_week), ("NEXT WEEK", next_week)]

    for label, pages in sections:
        print(f"\n--- {label} ---")
        for page in pages:
            title = get_text(page, "Name")
            requestor = get_text(page, "Requested By")
            tldr = get_text(page, "TLDR")
            print(f"{page['id']} | {title} | requestor: {requestor or '(none)'} | tldr: {tldr or '(empty)'}")


if __name__ == "__main__":
    main()
