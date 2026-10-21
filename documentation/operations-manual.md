# Operations Manual

A second Notion database documenting the systems Aydin owns (Salesforce, Stitch,
3CX, n8n, and others). It is separate from the Platform Tasks database. Keep it
deliberately lean to avoid metadata bloat.

## Database

- Database ID: `39e8f3c9051e80bc8646ea6cda418df5`
- Data source ID: `39e8f3c9-051e-80d0-91e0-000b1e059d94`
- Use the `ntn` CLI for all API calls (see `CLAUDE.md` for recipes).

## Properties

| Property | Type | Notes |
|---|---|---|
| Name | title | The page subject |
| System | select | The system the page is about (e.g. `Stitch`, `Salesforce`) |
| Touches | multi-select | Other systems it integrates with. Answers "what breaks if X changes?" |
| Entry Type | select | `Overview`, `Runbook`, `Reference`, or an object type (`Custom Object`, `Custom Setting`, `Standard Object`). The object types are set by the usage refresh |
| Reads | relation | Objects this entry reads from. Backlink: `Read by` |
| Writes | relation | Objects this entry writes to. Backlink: `Written by` |
| Records | number | Row count in the org. Point-in-time snapshot, maintained by the usage refresh |
| Last Write | date | `MAX(SystemModstamp)` in the org, i.e. when the object last changed. Snapshot |
| Usage Checked | date | When `Records` and `Last Write` were last refreshed |

`Entry Type = Reference` pages are a reusable concept glossary. Other entries link to
the same Reference page rather than repeating the explanation.

## Object Lineage

Object pages (`Entry Type` of `Custom Object`, `Custom Setting`, or `Standard Object`)
represent a single data object (e.g. a Salesforce object like `Property__c`). They are
the nodes for tracking data lineage.

An integration or automation declares its edges once via the `Reads` and `Writes`
relations. Each object page then shows, automatically via backlinks, every system that
reads it (`Read by`) and every system that writes it (`Written by`). Declare the edge
only on the integration side; never restate readers/writers on the object page, the
backlinks keep it in sync.

## Object Usage Refresh

`refresh_object_usage.py` (in the repo root) keeps the `Entry Type` (set to
`Custom Object`, `Custom Setting`, or `Standard Object`), `Records`, `Last Write`, and
`Usage Checked` properties current on the `System = Salesforce` object pages. It reads
the Salesforce production org (through the `salesforce` repo's nix flake) and writes the
numbers onto the matching Object pages.

It covers every custom object and custom setting (`*__c`) plus the standard
objects worth tracking: those carrying custom fields, those that already have a
page, and a license-relevant set (`Task`, `Event`, `Campaign`, `Order`, `Quote`).
It does not touch the ~1300 internal standard objects. Objects that cannot be
counted (history objects such as `CaseHistory`) are stamped with their type but
left without a record count rather than a misleading zero.

```sh
python3 refresh_object_usage.py                  # write to Notion
python3 refresh_object_usage.py --dry-run        # preview, no writes
python3 refresh_object_usage.py --create-missing # also create pages for objects that lack one
```

`--create-missing` creates pages only for real objects (custom object or
standard). Custom settings are never auto-created (they are governed separately
from the custom-object allowance); they are only reported. Override
`SALESFORCE_REPO` or `SALESFORCE_ORG` via environment if the repo lives elsewhere
or a different org alias is needed (default: `~/Projects/salesforce`,
`production`). Record counts are snapshots, never treat them as live.

## Scope

Document only what is relevant to the system being covered. For example, Stitch runs
many integrations, but the Operations Manual only covers the Salesforce-related ones.

## Page Conventions

Pages follow a markdown-documentation style: concise, sectioned with `##` headings,
not unwieldy.

- **Headings** in proper Title Case (e.g. `How It Works`, `Replicated Tables`).
- **External links** collect in an `## External Links` section at the bottom, one
  bullet each. Do not scatter external URLs inline. Internal Notion cross-links
  (between our own pages) stay inline as navigation.
- Wrap identifiers (table names, column/key names, IP addresses) in `` `code` ``.
- Keep volatile data out of tables so pages do not go stale (e.g. no row counts in
  the replicated-tables list).
- Diagrams use Mermaid in a `mermaid` code block. A diagram shows topology and flow,
  not data that already lives in a table. Do not duplicate a list into a diagram; keep
  one source of truth.
- Standard pages use the white document icon: `{"type": "icon", "icon": {"name":
  "document", "color": "lightgray"}}` (not the Task database's blue bell). Exception:
  pages where `System = Snowflake` use the blue `snowflake` icon. Do not overwrite a
  page's icon with the bell when editing.
