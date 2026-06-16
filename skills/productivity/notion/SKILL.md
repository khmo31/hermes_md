---
name: notion
description: "Notion API + ntn CLI: pages, databases, markdown, Workers."
version: 2.7.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [NOTION_API_KEY]
metadata:
  hermes:
    tags: [Notion, Productivity, Notes, Database, API, CLI, Workers]
    homepage: https://developers.notion.com
---

# Notion

Talk to Notion two ways. Same integration token works for both — pick by what's available.

◆ **`ntn` CLI** — Notion's official CLI. Shorter syntax, one-line file uploads, required for Workers. macOS + Linux only as of May 2026 (Windows support "coming soon"). **Default when installed.**
◆ **HTTP + curl** — works everywhere including Windows. **Default fallback** when `ntn` isn't installed.

## Setup

### 1. Get an integration token (required for both paths)

1. Create an integration at https://notion.so/my-integrations
2. Copy the API key (starts with `ntn_` or `secret_`)
3. Store in `~/.hermes/.env`:
   ```
   NOTION_API_KEY=ntn_your_key_here
   ```
4. **Share target pages/databases with the integration** in Notion: page menu `...` → `Connect to` → your integration name. Without this, the API returns 404 for that page even though it exists.

### 2. Install `ntn` (preferred path on macOS / Linux)

```bash
# Recommended
curl -fsSL https://ntn.dev | bash

# Or via npm (needs Node 22+, npm 10+)
npm install --global ntn

ntn --version    # verify
```

**Skip `ntn login` — use the integration token instead.** This works headlessly, no browser needed:
```bash
export NOTION_API_TOKEN=$NOTION_API_KEY      # ntn reads NOTION_API_TOKEN
export NOTION_KEYRING=0                       # don't try to use the OS keychain
```

Add those exports to your shell profile (or to `~/.hermes/.env`) so every session inherits them.

### 3. Choose path at runtime

```bash
if command -v ntn >/dev/null 2>&1; then
  # use ntn
else
  # fall back to curl
fi
```

Windows users: skip step 2 entirely until native `ntn` ships — Path B works fine. If you want CLI ergonomics now, install `ntn` inside WSL2.

## API Basics

`Notion-Version: 2025-09-03` is required on all HTTP requests. `ntn` handles this for you. In this version, what users call "databases" are called **data sources** in the API.

## Path A — `ntn` CLI (preferred, macOS / Linux)

### Raw API calls (shorthand for curl)
```bash
ntn api v1/users                                  # GET
ntn api v1/pages parent[page_id]=abc123 \         # POST with inline body
  properties[title][0][text][content]="Notes"
ntn api v1/pages/abc123 -X PATCH archived:=true   # PATCH; := is non-string (bool/num/null)
```

Syntax notes:
- `key=value` — string fields
- `key[nested]=value` — nested object fields
- `key:=value` — typed assignment (booleans, numbers, null, arrays)

### Search
```bash
ntn api v1/search query="page title"
```

### Read page metadata
```bash
ntn api v1/pages/{page_id}
```

### Read page as Markdown (agent-friendly)
```bash
ntn api v1/pages/{page_id}/markdown
```

### Read page content as blocks
```bash
ntn api v1/blocks/{page_id}/children
```

### Create page from Markdown
```bash
ntn api v1/pages \
  parent[page_id]=xxx \
  properties[title][0][text][content]="Notes from meeting" \
  markdown="# Agenda

- Q3 roadmap
- Hiring"
```

### Patch a page with Markdown
```bash
ntn api v1/pages/{page_id}/markdown -X PATCH \
  markdown="## Update

Shipped the prototype."
```

### Query a database (data source)
```bash
ntn api v1/data_sources/{data_source_id}/query -X POST \
  filter[property]=Status filter[select][equals]=Active
```

For complex queries with `sorts`, multiple filter clauses, or compound logic, pipe JSON in:
```bash
echo '{"filter": {"property": "Status", "select": {"equals": "Active"}}, "sorts": [{"property": "Date", "direction": "descending"}]}' | \
  ntn api v1/data_sources/{data_source_id}/query -X POST --json -
```

### File uploads (one-liner — biggest CLI win)
```bash
ntn files create < photo.png
ntn files create --external-url https://example.com/photo.png
ntn files list
```

Compare to the 3-step HTTP flow (create upload → PUT bytes → reference).

### Useful env vars
| Var | Effect |
|---|---|
| `NOTION_API_TOKEN` | Auth token (overrides keychain) — set this to your integration token |
| `NOTION_KEYRING=0` | File-based creds at `~/.config/notion/auth.json` instead of OS keychain |
| `NOTION_WORKSPACE_ID` | Skip the workspace picker prompt |

## Path B — HTTP + curl (cross-platform, default on Windows)

All requests share this pattern:

```bash
curl -s -X GET "https://api.notion.com/v1/..." \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json"
```

On Windows the `curl` shipped with Windows 10+ works as-is. PowerShell users can also use `Invoke-RestMethod`.

### Search
```bash
curl -s -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"query": "page title"}'
```

### Read page metadata
```bash
curl -s "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

### Read page as Markdown (agent-friendly)

Easier to feed to a model than block JSON.

```bash
curl -s "https://api.notion.com/v1/pages/{page_id}/markdown" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

### Read page content as blocks (when you need structure)
```bash
curl -s "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

### Create page from Markdown

`POST /v1/pages` accepts a `markdown` body param.

```bash
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"page_id": "xxx"},
    "properties": {"title": [{"text": {"content": "Notes from meeting"}}]},
    "markdown": "# Agenda\n\n- Q3 roadmap\n- Hiring\n\n## Decisions\n- Ship MVP Friday"
  }'
```

### Patch a page with Markdown

**⚠️ v2025-09-03 format change:** Simple `{"markdown": "..."}` no longer works. The API now expects a type-action wrapper:

```bash
curl -s -X PATCH "https://api.notion.com/v1/pages/{page_id}/markdown" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "replace_content",
    "replace_content": {"new_str": "## Update\n\nShipped the prototype."}
  }'
```

**Available type values:**
| type | field | effect |
|------|-------|--------|
| `replace_content` | `replace_content.new_str` | Replace entire page content |
| `insert_content` | `insert_content.{position,new_str}` | Insert at position (before/after/start/end) |

**⚠️ `replace_content_range` REMOVED — use read-modify-write instead.** The documented `replace_content_range` type (`{"replace_content_range": {"old_str": "...", "new_str": "..."}}`) has been changed/broken in the v2025-09-03 API. It returns validation errors (`content should be defined`, `content_range should be a string`) and the intended parameter shape is unclear. **Do not use it.** Instead, use the **read-modify-write pattern** below for targeted edits: read the full markdown, apply string replacements in Python, then write back with `replace_content`. This is more reliable and handles multiple substitutions in a single API call.
For large markdown content, build the payload via Python to avoid shell quoting issues (see Pitfall #4).

### Targeted edits: read-modify-write pattern (preferred over `replace_content_range`)

When you need targeted find-and-replace on a Notion page (not a full rewrite), use Python to read the page, apply string replacements, and write back with `replace_content`:

```python
import json, subprocess, os

NOTION_KEY = os.environ["NOTION_API_KEY"]
PAGE_ID = "page_uuid"

# 1. Read current markdown
result = subprocess.run([
    "curl", "-s",
    f"https://api.notion.com/v1/pages/{PAGE_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
md = json.loads(result.stdout).get("markdown", "")

# 2. Apply replacements
md = md.replace("OldTerm", "NewTerm")
md = md.replace("old_count+", "new_count+")

# 3. Write back
payload = json.dumps({
    "type": "replace_content",
    "replace_content": {"new_str": md}
}, ensure_ascii=False)

subprocess.run([
    "curl", "-s", "-X", "PATCH",
    f"https://api.notion.com/v1/pages/{PAGE_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", payload
], capture_output=True, timeout=15)
```

This avoids `replace_content_range` entirely and handles arbitrary numbers of substitutions in a single API call — much more efficient than one PATCH per replacement.

### Create page in a database (typed properties)
```bash
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "xxx"},
    "properties": {
      "Name": {"title": [{"text": {"content": "New Item"}}]},
      "Status": {"select": {"name": "Todo"}}
    }
  }'
```

### Query a database (data source)
```bash
curl -s -X POST "https://api.notion.com/v1/data_sources/{data_source_id}/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"property": "Status", "select": {"equals": "Active"}},
    "sorts": [{"property": "Date", "direction": "descending"}]
  }'
```

### Create a database

**⚠️ CRITICAL: Use `/v1/databases`, NOT `/v1/data_sources`.** Despite the v2025-09-03 rename, creating new databases uses the old `/v1/databases` endpoint. POST to `/v1/data_sources` returns: `"Creating new databases with data sources is not supported in this endpoint for API version 2025-09-03 and later. Use the Create Database API instead."`

```bash
curl -s -X POST "https://api.notion.com/v1/databases" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"type": "page_id", "page_id": "xxx"},
    "icon": {"type": "emoji", "emoji": "📋"},
    "title": [{"text": {"content": "My Database"}}],
    "description": [{"text": {"content": "Optional description"}}],
    "properties": {
      "Name": {"title": {}},
      "Status": {"select": {"options": [{"name": "Todo"}, {"name": "Done"}]}},
      "Date": {"date": {}}
    }
  }'
```

> **Note on title property name:** When created via `/v1/databases`, the title property is named `"Name"` by default regardless of what you name the first title property. You can rename it afterward via a PATCH to `/v1/data_sources/{id}` (see "Update data source properties" below).

### Update data source properties

**⚠️ Use `/v1/data_sources/{id}`, NOT `/v1/databases/{id}`.** PATCHing `/v1/databases/{id}` with new properties silently ignores them — the response looks successful but no changes appear. Always PATCH `/v1/data_sources/{id}`:

```bash
curl -s -X PATCH "https://api.notion.com/v1/data_sources/{data_source_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "New Status": {
        "status": {
          "options": [
            {"name": "시작 전", "color": "gray"},
            {"name": "진행 중", "color": "blue"},
            {"name": "완료", "color": "green"}
          ]
        }
      },
      "Tags": {
        "multi_select": {
          "options": [
            {"name": "AI", "color": "purple"},
            {"name": "자동화", "color": "blue"}
          ]
        }
      }
    }
  }'
```

This works for adding new properties AND for modifying select/status/multi-select options on existing properties.

### Update page properties
```bash
curl -s -X PATCH "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"Status": {"select": {"name": "Done"}}}}'
```

### Append blocks to a page
```bash
curl -s -X PATCH "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello from Hermes!"}}]}}
    ]
  }'
```

### File uploads (3-step flow)
```bash
# 1. Create upload
curl -s -X POST "https://api.notion.com/v1/file_uploads" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"filename": "photo.png", "content_type": "image/png"}'

# 2. PUT bytes to the upload_url returned above
curl -s -X PUT "{upload_url}" --data-binary @photo.png

# 3. Reference {file_upload_id} in a page/block payload
```

## Property Types

Common property formats for database items:

- **Title:** `{"title": [{"text": {"content": "..."}}]}`
- **Rich text:** `{"rich_text": [{"text": {"content": "..."}}]}`
- **Select:** `{"select": {"name": "Option"}}`
- **Multi-select:** `{"multi_select": [{"name": "A"}, {"name": "B"}]}`
- **Date:** `{"date": {"start": "2026-01-15", "end": "2026-01-16"}}`
- **Checkbox:** `{"checkbox": true}`
- **Number:** `{"number": 42}`
- **URL:** `{"url": "https://..."}`
- **Email:** `{"email": "user@example.com"}`
- **Relation:** `{"relation": [{"id": "page_id"}]}`

## API Version 2025-09-03 — Databases vs Data Sources

- **Databases became data sources.** Use `/data_sources/` endpoints for queries and retrieval.
- **Two IDs per database:** `database_id` and `data_source_id`.
  - `database_id` when creating pages: `parent: {"database_id": "..."}`
  - `data_source_id` when querying: `POST /v1/data_sources/{id}/query`
- Search returns databases as `"object": "data_source"` with the `data_source_id` field.

## Notion Workers (advanced, requires `ntn`)

Workers are TypeScript programs Notion hosts for you. One worker can expose any combination of:
- **Syncs** — pull data from external APIs into a Notion database on a schedule (default 30 min).
- **Tools** — appear as callable tools inside Notion's Custom Agents.
- **Webhooks** — receive HTTP events from external services (GitHub, Stripe, etc.) and act in Notion.

**Plan / platform gating:**
- CLI works on all plans. **Deploying Workers requires Business or Enterprise.**
- `ntn` is macOS/Linux only as of May 2026. Windows users need WSL2 or to wait for native support.
- Free through August 11, 2026; metered on Notion credits after.

### Minimal Worker

```bash
ntn workers new my-worker      # scaffold
cd my-worker
# Edit src/index.ts
ntn workers deploy --name my-worker
```

`src/index.ts`:
```typescript
import { Worker } from "@notionhq/workers";

const worker = new Worker();
export default worker;

worker.tool("greet", {
  title: "Greet a User",
  description: "Returns a friendly greeting",
  inputSchema: { type: "object", properties: { name: { type: "string" } }, required: ["name"] },
  execute: async ({ name }) => `Hello, ${name}!`,
});
```

### Webhook capability

```typescript
worker.webhook("onGithubPush", {
  title: "GitHub Push Handler",
  execute: async (events, { notion }) => {
    for (const event of events) {
      // event.body, event.rawBody (for signature verification), event.headers
      console.log("got delivery", event.deliveryId);
    }
  },
});
```

After deploy: `ntn workers webhooks list` shows the URL Notion generates. Treat that URL as a secret — anyone with it can POST events unless you add signature verification.

### Worker lifecycle commands

```bash
ntn workers deploy
ntn workers list
ntn workers exec <capability-key> -d '{"name": "world"}'
ntn workers sync trigger <key>            # run a sync now
ntn workers sync pause <key>
ntn workers env set GITHUB_WEBHOOK_SECRET=...
ntn workers runs list                     # recent invocations
ntn workers runs logs <run-id>
ntn workers webhooks list
```

When asked to build a Worker, scaffold with `ntn workers new`, write the code in `src/index.ts`, set any secrets with `ntn workers env set`, and deploy. Notion's docs at https://developers.notion.com/workers cover the full API surface.

## Notion-Flavored Markdown (used by `/markdown` endpoints)

Standard CommonMark plus XML-like tags for Notion-specific blocks. Use **tabs** for indentation.

**Blocks beyond CommonMark:**
```
<callout icon="🎯" color="blue_bg">
	Ship the MVP by **Friday**.
</callout>

<details color="gray">
<summary>Toggle title</summary>
	Children indented one tab
</details>

<columns>
	<column>Left side</column>
	<column>Right side</column>
</columns>

<table_of_contents color="gray"/>
```

**Inline:**
- Mentions: `<mention-user url="..."/>`, `<mention-page url="...">Title</mention-page>`, `<mention-date start="2026-05-15"/>`
- Underline: `<span underline="true">text</span>`
- Color: `<span color="blue">text</span>` or block-level `{color="blue"}` on the first line
- Math: inline `$x^2$`, block `$$ ... $$`
- Citations: `[^https://example.com]`

**Colors:** `gray brown orange yellow green blue purple pink red`, plus `*_bg` variants for backgrounds.

Headings 5/6 collapse to H4. Multiple `>` lines render as separate quote blocks — use `<br>` inside a single `>` for multi-line quotes.

## Choosing the Right Path

| Task | mac / Linux | Windows |
|---|---|---|
| Read/write pages, search, query databases | `ntn api ...` | curl |
| Read a page for an agent to summarize | `ntn api v1/pages/{id}/markdown` | curl `/markdown` endpoint |
| Upload a file | `ntn files create < file` | 3-step HTTP flow |
| One-off API exploration | `ntn api ...` | curl |
| Build a sync / webhook / agent tool hosted by Notion | `ntn workers ...` | WSL2 + `ntn workers ...` |

## Notes

- **Support file:** `references/workspace-exploration.md` — multi-step audit pattern for exploring a new workspace (search → discover DBs → get schemas → query items → traverse child pages). Load this when you need to understand a workspace from scratch.
- **Support file:** `references/batch-page-creation.md` — creating multiple child pages under a parent, collecting IDs, building index with `<page>` tags. Use this when splitting a page into weekly/monthly sub-pages.
- **Support file:** `references/portfolio-content-expansion.md` — expanding specific sections (e.g. 활동 상세/Activity Details) across multiple child pages linked from a parent index. Covers the read → identify → expand → write-back cycle with the **배경→방법→결과** structure. Use this when a user asks you to elaborate or add detail to a multi-page Notion portfolio.
- **Support file:** `references/portfolio-narrative-pattern.md` — structuring portfolio content to show decision-making and evolution rather than linear outcomes. Use the "pivot narrative" pattern with comparison tables when the project had false starts, constraint-driven pivots, or architectural evolution. Covers data-source evolution tables, architecture-evolution tables, **cross-document sync** (propagating narrative improvements to final reports and presentations), and **final report integration** (where to place pivot narratives in a formal report structure).
- **Support file:** `references/portfolio-review-pattern.md` — audit multiple related portfolio pages for content overlap, narrative inconsistencies, and timeline contradictions, then apply precision edits. Use when the user asks "겹치는것 같은데 확인해줘", "비교해줘", or requests a targeted content addition to an existing section. Complements `portfolio-content-expansion.md` (bulk expansion) with an audit-first approach.
- **Support file:** `references/portfolio-consolidation-pattern.md` — merging multiple child portfolio pages into one integrated page, with cross-document fact-checking against a sibling report. Use when the user asks for "하나로 통합" or "하나의 페이지에 모든 내용".
- Page/database IDs are UUIDs (with or without dashes — both accepted).
- Rate limit: ~3 requests/second average. The CLI doesn't bypass this.
- The API cannot set database **view** filters — that's UI-only.
- Use `"is_inline": true` when creating data sources to embed them in a page.
- Always pass `-s` to curl to suppress progress bars (cleaner agent output).
- Pipe JSON through `jq` when reading: `... | jq '.results[0].properties'`.
- Notion also ships an MCP server now (`Notion MCP`, ~91% more token-efficient on DB ops than the previous version) — wire it via Hermes' MCP support if you want streaming Notion access from inside a session, but the paths above are enough for most one-shot tasks.

## Pitfalls

### 1. Internal integrations cannot create workspace-level pages

Bot/internal integrations (the most common type) cannot create pages at the workspace root:

```
"Internal integrations aren't owned by a single user, so creating workspace-level
private pages is not supported."
```

**Fix:** Create the page under an existing page that's already shared with the integration (any page/database the user has connected). Use `parent: {"page_id": "xxx"}` with that page's ID. The user can drag it to workspace root in the Notion UI afterward if needed.

To find suitable parent pages, run a search for objects whose `parent.type == "workspace"` — those are root-level pages that are guaranteed to be shared (since they appeared in search results).

**⚠️ Lost-page trap:** Pages created under a parent that the integration CAN read (content updates succeed) but CANNOT search (the parent doesn't appear in search results) become **invisible to search**. The creation call returns a valid page ID, but subsequent searches never return that page. Workaround: save the created page ID immediately from the API response — it won't be findable later. Test parent accessibility early by running a search for it before creating anything under it. If you need to relocate such a page later, request the user to open Notion and move it manually via drag-and-drop.

### 2. Property updates: use `/v1/data_sources/{id}`, not `/v1/databases/{id}`

PATCHing `/v1/databases/{id}` with new properties LOOKS like it succeeds (200, no error) but actually does nothing — the properties are silently ignored. Always PATCH `/v1/data_sources/{id}` to add or modify properties.

### 3. Creating a database uses `/v1/databases`, not `/v1/data_sources`

The `POST /v1/data_sources` endpoint rejects database creation in v2025-09-03. Use `POST /v1/databases` instead. The newly created DB gets a matching `data_source_id` automatically.

### 4. Handling large markdown content in curl

When creating pages with long markdown (e.g., >20 lines with complex formatting), inline JSON escaping in bash heredocs is fragile. **Use Python's `json.dumps()` to safely escape the markdown string:**

```bash
# Safe pattern: read markdown from file, escape via Python, pass to curl
MARKDOWN=$(cat /tmp/content.md | python3 -c "
import json,sys
content = sys.stdin.read()
print(json.dumps(content))
")

curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d "{
    \"parent\": {\"page_id\": \"xxx\"},
    \"properties\": {\"title\": {\"title\": [{\"text\": {\"content\": \"Page Title\"}}]}},
    \"markdown\": $MARKDOWN
  }"
```

**For very complex payloads (e.g., `replace_content` with embedded newlines), use Python `subprocess.run` + a JSON file instead of shell heredocs:**

```python
import json, subprocess

with open("/tmp/content.md") as f:
    md_content = f.read()

payload = {
    "type": "replace_content",
    "replace_content": {"new_str": md_content}
}

with open("/tmp/payload.json", "w") as f:
    json.dump(payload, f, ensure_ascii=False)

result = subprocess.run([
    "curl", "-s", "-X", "PATCH",
    f"https://api.notion.com/v1/pages/{page_id}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", "@tmp/payload.json"
], capture_output=True, text=True, timeout=30)
```

This is the safest pattern for any payload with multi-line strings, special characters, or Unicode. Write from `execute_code` context.

### 5. ⚠️ `allow_deleting_content` placement and `replace_content` pitfalls

**`allow_deleting_content` must be inside `replace_content`, not at the top level.**

When using `replace_content` on a page that has existing `child_page` sub-pages, the API may refuse with:

```
This operation would delete N child page(s) or database(s):
- page: "title" (id: ...)

To proceed, either:
1. Include these items in content using <page url="..."> tags, OR
2. Set allow_deleting_content: true to confirm deletion.
```

The `allow_deleting_content: true` parameter MUST go **inside** the `replace_content` object, not at the top level:

```json
// ✅ CORRECT
{"type": "replace_content", "replace_content": {"new_str": "...", "allow_deleting_content": true}}

// ❌ WRONG — top-level parameter is silently ignored
{"type": "replace_content", "replace_content": {"new_str": "..."}, "allow_deleting_content": true}
```

When set to `true`, child pages that are no longer referenced via `<page>` tags in the new markdown get **detached and archived** (not just unlinked). To move a child page between parents, you must create a new page under the new parent and let the old one be archived — the API does not support re-parenting.

**`&` in `<page>` tag titles must be escaped.**

Within `<page url="...">Title</page>` tags, use `&amp;` or `&#38;` instead of raw `&`. The raw `&` character causes a `Failed to create block` validation error.

```html
<!-- OK -->
<page url="https://app.notion.com/p/abc">Data Sources &amp; Problem Definition</page>

<!-- FAILS with Failed to create block -->
<page url="https://app.notion.com/p/abc">Data Sources & Problem Definition</page>
```

### 6. ⚠️ `replace_content_range` is unreliable — use `replace_content` instead

**The `replace_content_range` API endpoint (find-and-replace substring in page markdown) does NOT work as documented in the v2025-09-03 API version.** It returns confusing validation errors regardless of payload structure:

```json
// Attempt 1 — what the docs say:
{"type": "replace_content_range", "replace_content_range": {"old_str": "...", "new_str": "..."}}
// ❌ "body.replace_content_range.content should be defined"

// Attempt 2 — guessed nesting:
{"type": "replace_content_range", "replace_content_range": {"content": "...", "content_range": {"old_str": "...", "new_str": "..."}}}
// ❌ "body.replace_content_range.content_range should be defined"

// Attempt 3 — string range:
{"type": "replace_content_range", "replace_content_range": {"content": "...", "content_range": "2:5"}}
// ❌ "String not found: <pattern>2:5</pattern>"
```

**The reliable alternative is `replace_content`** (replace entire page content, works every time):

```bash
PAGE_ID="<page-uuid>"

curl -s -X PATCH "https://api.notion.com/v1/pages/$PAGE_ID/markdown" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "replace_content",
    "replace_content": {
      "new_str": "# Updated Title\n\nFull replacement of page content with corrected info."
    }
  }'
```

**Workflow for updating existing pages with `replace_content`:**

1. **Read** the current content: `GET /v1/pages/{id}/markdown` → save the `markdown` field
2. **Modify** in Python: `str.replace()` or regex substitution on the saved markdown string
3. **Write back** via `replace_content` with the full modified markdown

```python
import json, subprocess, os

NOTION_KEY = os.environ["NOTION_API_KEY"]
PAGE_ID = "..."

# Step 1: Read current content
result = subprocess.run([
    "curl", "-s", f"https://api.notion.com/v1/pages/{PAGE_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
current = json.loads(result.stdout)
md = current.get("markdown", "")

# Step 2: Apply replacements
replacements = [
    ("old_term", "new_term"),
    ("Old Name", "New Name"),
]
for old, new in replacements:
    md = md.replace(old, new)

# Step 3: Write back
payload = json.dumps({
    "type": "replace_content",
    "replace_content": {"new_str": md}
}, ensure_ascii=False)

result2 = subprocess.run([
    "curl", "-s", "-X", "PATCH",
    f"https://api.notion.com/v1/pages/{PAGE_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", payload
], capture_output=True, text=True, timeout=15)

resp = json.loads(result2.stdout)
success = resp.get("object") == "page_markdown"
print(f"{'✅' if success else '❌'} Update complete, new length: {len(resp.get('markdown',''))}")
```

This read-modify-write cycle is reliable and escapes shell quoting issues entirely.

### 7. Title property name mismatch after database creation

When you create a database via `/v1/databases`, the title property is always named `"Name"` internally even if you specified a different Korean/non-English name. To fix this, PATCH the data source afterward:

```bash
curl -s -X PATCH "https://api.notion.com/v1/data_sources/{data_source_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"Name": {"name": "제목"}}}'
```

This renames the title property without losing data.

### 8. Untitled pages are real items, not ghosts

Pages with empty title arrays appear in query results. They have a valid page ID and can be updated (set a title) or archived. Always check for them during workspace cleanup — they're often orphaned items from API tests or incomplete imports.

### 9. ⚠️ `replace_content` on a parent page with child pages requires `<page>` tags

When you PATCH `/v1/pages/{id}/markdown` with `replace_content` on a page that has existing `child_page` sub-pages (created via `parent: {"page_id": "..."}`), the API **refuses** with:

```
This operation would delete N child page(s) or database(s):
- page: "title" (id: ...)

To proceed, either:
1. Include these items in content using <page url="..."> tags, OR
2. Set allow_deleting_content: true to confirm deletion.
```

**Fix (Option A — safe):** Include `<page url="...">` tags for EVERY existing child page in the new markdown:

```python
child_pages = [("Title 1", "uuid1"), ("Title 2", "uuid2")]
new_md = "# New content\n\n"
for title, pid in child_pages:
    new_md += f'<page url="https://www.notion.so/{pid}">{title}</page>\n'
```

**Fix (Option B — detach):** Set `allow_deleting_content: true` in the PATCH payload to proceed without child page tags. This detaches (archives) the children.

**How to discover existing child pages:**

```python
result = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/blocks/{page_id}/children",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
blocks = json.loads(result.stdout)
for block in blocks.get("results", []):
    if block.get("type") == "child_page":
        pid = block["id"]
        title = block.get("child_page", {}).get("title", "")
```

The API returns all immediate children (inline content blocks + child_page/database blocks). Paginate with `start_cursor` if more than ~50 items. Child pages may appear at positions >20 after inline content.

### 10. Emoji icon validation — create without icon, then PATCH separately

Notion's `POST /v1/pages` validates the `icon.emoji` field against a canonical emoji list (~1800 entries). **Multi-codepoint emoji are rejected** — `"1️⃣1️⃣"`, ZWJ sequences, and non-standard variants all fail with a massive error listing all 1800+ allowed values. Even simple single emoji (💻, ⚡) can fail when bundled with complex markdown payloads.

**Safe two-step pattern:**

```python
# Step 1: Create page WITHOUT icon field
data = {
    "parent": {"page_id": parent_id},
    "properties": {"title": [{"text": {"content": title}}]},
    "markdown": md_content
}
# POST /v1/pages → get page_id

# Step 2: Set icon via separate PATCH
subprocess.run(["curl", "-s", "-X", "PATCH",
    f"https://api.notion.com/v1/pages/{page_id}",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", json.dumps({"icon": {"type": "emoji", "emoji": "💻"}})
], ...)
```

**Test icon validity** by PATCHing just the icon on any known page first — 200 = accepted, 422 = pick a simpler emoji.

### 11. Rate limiting under sequential batched operations

The API enforces ~3 req/s average. When archiving 14+ pages or creating many pages sequentially, "API token is invalid" errors appear around request ~10. These are **rate limit errors, not auth failures** — they self-resolve after ~30 seconds.

**Pattern:** Insert `sleep 0.3` between sequential requests, or prefer terminal-based shell loops with explicit delays over Python subprocess loops in `execute_code`:

```bash
for id in uuid1 uuid2 uuid3 ...; do
  curl -s -X PATCH "https://api.notion.com/v1/pages/$id" ... -d '{"archived": true}'
  sleep 0.3
done
```

### 12. ⚠️ `str.replace` with HTML tags matches ALL occurrences — use targeted replacement

When using the read-modify-write pattern with `str.replace` on markdown that contains **multiple HTML tables** (e.g., a parent page with both a "통합 포트폴리오" table and a "최종 성과 요약" table), `md.replace("</table>", new_row + "\n</table>")` inserts the new row into **every** table, not just the first one.

```python
# ❌ BAD — inserts into ALL tables
md = md.replace("</table>", f"{new_row}\n</table>")

# ✅ GOOD — target by position
first_table_end = md.find("</table>")
md = md[:first_table_end] + f"{new_row}\n</table>" + md[first_table_end + len("</table>"):]

# ✅ ALSO GOOD — use unique surrounding context
md = md.replace(
    "통합 포트폴리오 (4개)\\n</table>",
    "통합 포트폴리오 (5개)\\n" + new_row + "\\n</table>"
)
```

**Rule:** When the markdown contains structurally identical HTML tags, never use bare tag names as replacement anchors. Always include enough surrounding context (header text, preceding/following lines) to guarantee a unique match, or slice by position.

### 12. Korean text in `execute_code`: use real characters, not `\\uXXXX` escapes

When replacing Korean text in `execute_code` Python scripts, **use the actual Korean characters directly**, not Unicode escape sequences:

```python
# ❌ BAD — \\uXXXX creates literal backslash-u string, NOT Korean chars
old_dup = '\\uad6c\\uccb4\\uc801 \\ub9e4\\uce6d'  # This is literal "\\uad6c\\uccb4\\uc801", not "구체적"
md = md.replace(old_dup, '')                       # Won't match anything

# ✅ GOOD — use actual Korean text
old_dup = '구체적 매칭 엔진으로의 진화였다'
md = md.replace(old_dup, '')                        # Matches correctly
```

In Python `"..."` strings inside `execute_code`, `\\uad6c` is an escaped backslash (`\\` → literal `\`) followed by `uad6c`, producing the 8-character string `\uad6c` — NOT the Korean character `구`. Use the real UTF-8 Korean text instead.

**Exception:** Unicode escapes (`\\uXXXX`) are still needed in JSON strings passed via curl (`json.dumps` handles this correctly with `ensure_ascii=False`). The problem only affects direct Python string comparisons targeting Korean text.
