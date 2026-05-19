#!/usr/bin/env python3
"""Generates a Slack-formatted weekly summary from the Platform Tasks Notion database."""

import json
import subprocess
from datetime import datetime, timedelta

DATA_SOURCE_ID = "ab49c7cb-6a14-445e-9706-9ad4d0efb018"

SCHEDULE_PLACEHOLDER = """- *Tuesday* • 09:00 - 13:00 (BST)
- *Thursday* • 09:00 - 18:00 (BST)
- *Friday* • 09:00 - 18:00 (BST) • In Office"""


def notion_query(filter_body: dict) -> list[dict]:
    pages = []
    cursor = None

    while True:
        body = {"page_size": 100, "filter": filter_body}
        if cursor:
            body["start_cursor"] = cursor

        result = subprocess.run(
            [
                "ntn",
                "api",
                f"v1/data_sources/{DATA_SOURCE_ID}/query",
                "-X",
                "POST",
                "--data",
                json.dumps(body),
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return pages


def task_line(page: dict) -> str:
    tldr_parts = page["properties"]["TLDR"]["rich_text"]
    if tldr_parts:
        return "".join(part["plain_text"] for part in tldr_parts)
    title_parts = page["properties"]["Name"]["title"]
    return "".join(part["plain_text"] for part in title_parts)


def completed_date(page: dict) -> datetime | None:
    date_value = page["properties"]["Completed Date"]["date"]
    if not date_value:
        return None
    return datetime.fromisoformat(date_value["start"])


def week_bounds(offset_weeks: int = 0) -> tuple[datetime, datetime]:
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset_weeks)
    sunday = monday + timedelta(days=6)
    return datetime.combine(monday, datetime.min.time()), datetime.combine(
        sunday, datetime.max.time()
    )


def format_task_list(pages: list[dict]) -> str:
    lines = [f"- {task_line(page)}" for page in pages]
    return "\n".join(lines) if lines else "- (nothing)"


def main():
    last_week_start, last_week_end = week_bounds(-1)
    this_week_start, this_week_end = week_bounds(0)

    last_week_pages = notion_query(
        {
            "and": [
                {"property": "Status", "status": {"equals": "Done"}},
                {
                    "property": "Completed Date",
                    "date": {"on_or_after": last_week_start.date().isoformat()},
                },
                {
                    "property": "Completed Date",
                    "date": {"on_or_before": last_week_end.date().isoformat()},
                },
            ]
        }
    )

    this_week_pages = notion_query(
        {
            "or": [
                {"property": "Status", "status": {"equals": "In Progress"}},
                {"property": "Status", "status": {"equals": "Emergency"}},
            ]
        }
    )

    next_week_pages = notion_query(
        {"property": "Status", "status": {"equals": "Next Set"}}
    )

    print(f"*SCHEDULE THIS WEEK*\n{SCHEDULE_PLACEHOLDER}")
    print(":blank:")
    print(f"*LAST WEEK*\n{format_task_list(last_week_pages)}")
    print(":blank:")
    print(f"*THIS WEEK*\n{format_task_list(this_week_pages)}")
    print(":blank:")
    print(f"*NEXT WEEK*\n{format_task_list(next_week_pages)}")


if __name__ == "__main__":
    main()
