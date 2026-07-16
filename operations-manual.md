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
| Entry Type | select | `Overview`, `Runbook`, `Reference`, or `Object` |
| Reads | relation | Objects this entry reads from. Backlink: `Read by` |
| Writes | relation | Objects this entry writes to. Backlink: `Written by` |

`Entry Type = Reference` pages are a reusable concept glossary. Other entries link to
the same Reference page rather than repeating the explanation.

## Object lineage

`Entry Type = Object` pages represent a single data object (e.g. a Salesforce object
like `Property__c`). They are the nodes for tracking data lineage.

An integration or automation declares its edges once via the `Reads` and `Writes`
relations. Each object page then shows, automatically via backlinks, every system that
reads it (`Read by`) and every system that writes it (`Written by`). Declare the edge
only on the integration side; never restate readers/writers on the object page, the
backlinks keep it in sync.

## Scope

Document only what is relevant to the system being covered. For example, Stitch runs
many integrations, but the Operations Manual only covers the Salesforce-related ones.

## Page conventions

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
- Set the standard bell icon on every page, same as the Task database.
