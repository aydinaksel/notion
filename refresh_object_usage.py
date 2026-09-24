#!/usr/bin/env python3
"""Refresh Salesforce object usage onto Operations Manual Object pages.

Pulls record count, last write time, and object type from the Salesforce
production org (via the salesforce repo's nix flake) and writes them onto the
matching object pages (`Entry Type` of `Custom Object`, `Custom Setting`, or
`Standard Object`; `System = Salesforce`) in the Operations Manual.

Coverage:
    - Every custom object and custom setting (`*__c`).
    - Standard objects worth tracking: those carrying custom fields, those that
      already have a page, and a license-relevant set (Task, Event, Campaign,
      Order, Quote). Not all ~1300 standard/system objects.

With --create-missing it also creates pages for real objects (custom object or
standard) that lack one. Custom settings are never auto-created; they are
governed separately from the custom-object allowance and only reported.

Usage:
    python3 refresh_object_usage.py [--dry-run] [--create-missing]

Environment:
    SALESFORCE_REPO   Path to the salesforce DX repo (default: ~/Projects/salesforce)
    SALESFORCE_ORG    Target org alias (default: production)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPERATIONS_MANUAL_DATABASE_ID = "39e8f3c9051e80bc8646ea6cda418df5"
OPERATIONS_MANUAL_DATA_SOURCE_ID = "39e8f3c9-051e-80d0-91e0-000b1e059d94"
SALESFORCE_REPO = Path(os.environ.get("SALESFORCE_REPO", Path.home() / "Projects" / "salesforce"))
SALESFORCE_ORG_ALIAS = os.environ.get("SALESFORCE_ORG", "production")

LICENSE_RELEVANT_STANDARD_OBJECTS = {"Task", "Event", "Campaign", "Order", "Quote"}
NON_QUERYABLE_CUSTOM_FIELD_PARENTS = {"Activity"}
OBJECT_ENTRY_TYPES = {"Custom Object", "Custom Setting", "Standard Object"}
DOCUMENT_ICON = {"type": "icon", "icon": {"name": "document", "color": "lightgray"}}

SALESFORCE_SHELL_PREAMBLE = """
  set -uo pipefail
  export SF_AUTOUPDATE_DISABLE=true NO_COLOR=1 FORCE_COLOR=0
  strip_preamble() { sed -n '/^[[{]/,$p'; }
"""


def run_in_salesforce_shell(script, extra_args=()):
    completed = subprocess.run(
        ["nix", "develop", str(SALESFORCE_REPO), "--command", "bash", "-c", script, "_", *extra_args],
        cwd=str(SALESFORCE_REPO),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.exit(f"Salesforce query failed:\n{completed.stderr}")
    return completed.stdout


def parse_usage_line(line):
    _, object_api_name, object_type, records_raw, last_write_raw = line.split("\t")
    records = int(records_raw) if records_raw.isdigit() else None
    last_write = None if last_write_raw == "null" else last_write_raw
    return object_api_name, {"object_type": object_type, "records": records, "last_write": last_write}


def fetch_custom_objects_and_field_bearing_standard_objects():
    script = SALESFORCE_SHELL_PREAMBLE + f"""
      custom_objects=$(sf sobject list --sobject all --target-org {SALESFORCE_ORG_ALIAS} --json 2>/dev/null \
        | strip_preamble | jq -r '.result[] | select(endswith("__c"))')
      while read -r object_api_name; do
        if [ -z "$object_api_name" ]; then continue; fi
        described=$(sf sobject describe --sobject "$object_api_name" --target-org {SALESFORCE_ORG_ALIAS} --json 2>/dev/null | strip_preamble)
        object_type=$(echo "$described" | jq -r 'if .result.customSetting then "Custom Setting" else "Custom Object" end')
        aggregate=$(sf data query --query "SELECT COUNT(Id) records_count, MAX(SystemModstamp) last_write FROM $object_api_name" \
          --target-org {SALESFORCE_ORG_ALIAS} --json 2>/dev/null | strip_preamble)
        records=$(echo "$aggregate" | jq -r '.result.records[0].records_count // "null"')
        last_write=$(echo "$aggregate" | jq -r '.result.records[0].last_write // "null"')
        printf 'USAGE\t%s\t%s\t%s\t%s\n' "$object_api_name" "$object_type" "$records" "$last_write"
      done <<< "$custom_objects"
      sf data query --use-tooling-api \
        --query "SELECT TableEnumOrId, COUNT(Id) custom_field_count FROM CustomField GROUP BY TableEnumOrId" \
        --target-org {SALESFORCE_ORG_ALIAS} --json 2>/dev/null | strip_preamble \
        | jq -r '.result.records[] | select(.TableEnumOrId | test("^[0-9]") | not)
                 | select(.TableEnumOrId | endswith("__c") | not) | "STDFIELD\t\\(.TableEnumOrId)"'
    """
    usage_by_object = {}
    field_bearing_standard_objects = set()
    for line in run_in_salesforce_shell(script).splitlines():
        if line.startswith("USAGE\t"):
            object_api_name, usage = parse_usage_line(line)
            usage_by_object[object_api_name] = usage
        elif line.startswith("STDFIELD\t"):
            field_bearing_standard_objects.add(line.split("\t", 1)[1])
    return usage_by_object, field_bearing_standard_objects


def fetch_standard_object_usage(object_api_names):
    script = SALESFORCE_SHELL_PREAMBLE + f"""
      for object_api_name in "$@"; do
        aggregate=$(sf data query --query "SELECT COUNT(Id) records_count, MAX(SystemModstamp) last_write FROM $object_api_name" \
          --target-org {SALESFORCE_ORG_ALIAS} --json 2>/dev/null | strip_preamble)
        records=$(echo "$aggregate" | jq -r '.result.records[0].records_count // "null"')
        last_write=$(echo "$aggregate" | jq -r '.result.records[0].last_write // "null"')
        printf 'USAGE\t%s\tStandard Object\t%s\t%s\n' "$object_api_name" "$records" "$last_write"
      done
    """
    usage_by_object = {}
    for line in run_in_salesforce_shell(script, extra_args=sorted(object_api_names)).splitlines():
        if line.startswith("USAGE\t"):
            object_api_name, usage = parse_usage_line(line)
            usage_by_object[object_api_name] = usage
    return usage_by_object


def fetch_notion_salesforce_object_pages():
    completed = subprocess.run(
        ["ntn", "datasources", "query", OPERATIONS_MANUAL_DATA_SOURCE_ID, "--limit", "500", "--json"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.exit(f"Notion query failed:\n{completed.stderr}")

    page_id_by_object = {}
    for page in json.loads(completed.stdout)["results"]:
        properties = page["properties"]
        entry_type = (properties["Entry Type"].get("select") or {}).get("name")
        system = (properties["System"].get("select") or {}).get("name")
        if entry_type not in OBJECT_ENTRY_TYPES or system != "Salesforce":
            continue
        title = properties["Name"]["title"]
        if title:
            page_id_by_object[title[0]["plain_text"]] = page["id"]
    return page_id_by_object


def create_object_page(object_api_name, entry_type):
    body = {
        "parent": {"database_id": OPERATIONS_MANUAL_DATABASE_ID},
        "icon": DOCUMENT_ICON,
        "properties": {
            "Name": {"title": [{"text": {"content": object_api_name}}]},
            "System": {"select": {"name": "Salesforce"}},
            "Entry Type": {"select": {"name": entry_type}},
        },
    }
    completed = subprocess.run(
        ["ntn", "api", "/v1/pages"],
        input=json.dumps(body),
        capture_output=True,
        text=True,
    )
    response = json.loads(completed.stdout or "{}")
    if response.get("object") == "error":
        raise RuntimeError(response.get("message", "unknown Notion error"))
    return response["id"]


def patch_page_usage(page_id, usage, checked_iso):
    records = usage["records"]
    last_write = usage["last_write"]
    properties = {
        "Entry Type": {"select": {"name": usage["object_type"]}},
        "Records": {"number": records},
        "Last Write": {"date": {"start": last_write} if last_write else None},
        "Usage Checked": {"date": {"start": checked_iso}},
    }
    completed = subprocess.run(
        ["ntn", "api", f"/v1/pages/{page_id}", "-X", "PATCH"],
        input=json.dumps({"properties": properties}),
        capture_output=True,
        text=True,
    )
    response = json.loads(completed.stdout or "{}")
    if response.get("object") == "error":
        raise RuntimeError(response.get("message", "unknown Notion error"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing to Notion")
    parser.add_argument("--create-missing", action="store_true", help="Create pages for real objects that lack one")
    arguments = parser.parse_args()

    usage_by_object, field_bearing_standard_objects = fetch_custom_objects_and_field_bearing_standard_objects()
    page_id_by_object = fetch_notion_salesforce_object_pages()

    standard_objects_with_pages = {name for name in page_id_by_object if not name.endswith("__c")}
    standard_targets = (
        field_bearing_standard_objects | standard_objects_with_pages | LICENSE_RELEVANT_STANDARD_OBJECTS
    ) - NON_QUERYABLE_CUSTOM_FIELD_PARENTS
    usage_by_object.update(fetch_standard_object_usage(standard_targets))

    checked_iso = datetime.now(timezone.utc).date().isoformat()

    created = []
    if arguments.create_missing and not arguments.dry_run:
        for object_api_name, usage in usage_by_object.items():
            if usage["object_type"] == "Custom Setting" or object_api_name in page_id_by_object:
                continue
            page_id_by_object[object_api_name] = create_object_page(object_api_name, usage["object_type"])
            created.append(object_api_name)

    updated = []
    for object_api_name, usage in sorted(usage_by_object.items(), key=lambda item: -(item[1]["records"] or 0)):
        page_id = page_id_by_object.get(object_api_name)
        if not page_id:
            continue
        if not arguments.dry_run:
            patch_page_usage(page_id, usage, checked_iso)
        updated.append((object_api_name, usage))

    print(f"{'OBJECT':<32} {'TYPE':<16} {'RECORDS':>10}  LAST WRITE")
    for object_api_name, usage in updated:
        records = "n/a" if usage["records"] is None else str(usage["records"])
        last_write = (usage["last_write"] or "-")[:10]
        print(f"{object_api_name:<32} {usage['object_type']:<16} {records:>10}  {last_write}")

    print(f"\nUpdated {len(updated)} page(s){' (dry run, nothing written)' if arguments.dry_run else ''}.")
    if created:
        print(f"Created {len(created)} page(s): {', '.join(sorted(created))}")

    settings_without_page = sorted(
        name for name, usage in usage_by_object.items()
        if usage["object_type"] == "Custom Setting" and name not in page_id_by_object
    )
    objects_without_page = sorted(
        name for name, usage in usage_by_object.items()
        if usage["object_type"] != "Custom Setting" and name not in page_id_by_object
    )
    if objects_without_page:
        print(f"\nObjects with no page (rerun with --create-missing to add): {', '.join(objects_without_page)}")
    if settings_without_page:
        print(f"\nCustom settings (not paged by design): {', '.join(settings_without_page)}")


if __name__ == "__main__":
    main()
