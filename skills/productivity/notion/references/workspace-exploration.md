# Workspace Exploration (Workspace Audit)

Pattern for auditing a complete Notion workspace — discovering structure, datasets, and content without prior knowledge.

## 1. Search the workspace (full reconnaissance)

```bash
curl -s -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100}'
```

Parse `.results[]` to see every page + data_source visible to the integration.

Key fields per result:

| JSON path | Meaning |
|-----------|---------|
| `.object` | `"page"` or `"data_source"` |
| `.parent.type` | `"workspace"` (root), `"page_id"`, `"database_id"`, `"data_source_id"` |
| `.id` | The object's own UUID |
| `.parent[.parent.type]` | The parent UUID |

## 2. Extract database (data_source) IDs

From search results, filter for `object == "data_source"`:

```python
for item in results:
    if item.get('object') == 'data_source':
        title = item.get('title', [{}])[0].get('plain_text', '(untitled)')
        ds_id = item['id']
        print(f"{title}: {ds_id}")
```

> **Important:** A `data_source` has both a `data_source_id` (= `.id`) and a `database_id` (found in `.parent.id` when `parent.type == "database_id"`). Pages are created under `database_id`; queries run against `data_source_id`.

## 3. Get database schema

```bash
curl -s "https://api.notion.com/v1/data_sources/{data_source_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

Parse `.properties` to see all field names, types, and select/status/multi-select options.

## 4. Query database items

```bash
curl -s -X POST "https://api.notion.com/v1/data_sources/{data_source_id}/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"page_size": 100}'
```

Each result has `.properties` — a map of field-name → typed-value objects. Extract titles and key fields:

```python
for item in results:
    props = item['properties']
    title = ''
    status = ''
    for key, val in props.items():
        if val['type'] == 'title':
            text_parts = val['title']
            title = text_parts[0]['plain_text'] if text_parts else ''
        elif val['type'] == 'status':
            status = (val.get('status') or {}).get('name', '')
```

## 5. Read page content (markdown — agent-friendly)

```bash
curl -s "https://api.notion.com/v1/pages/{page_id}/markdown" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

Returns Notion-flavored markdown — best format for LLMs. `block_id` and `page_id` are the same UUID.

## 6. Traverse page children (blocks)

```bash
curl -s "https://api.notion.com/v1/blocks/{page_id}/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03"
```

Check for `child_page` blocks (`.type == "child_page"`) to discover sub-pages not captured by search.

## 7. Typical audit flow

```
Search workspace → all objects visible to integration
  ├─ data_source: get schema → query items → read interesting pages
  ├─ page at workspace root: read markdown → check children
  │   └─ child_page found: recurse
  └─ page in database: extract properties → read markdown if needed
```

## Pitfalls

- **Search doesn't return all sub-pages.** Pages nested as `child_page` blocks only appear in the parent's blocks endpoint. Always call `blocks/{id}/children` to find them.
- **Database IDs ≠ Data Source IDs.** In API v2025-09-03, use `data_source_id` for queries/schema and `database_id` for page creation. Confusing the two returns 404.
- **Database entries may have empty body despite user saying content exists.** A data_source query returns page entries with properties only — the markdown body and block children may be 0-length even when the user has written content. This happens when the real content is in a **separate child page** under a different parent, not inside the DB entry itself. Search for pages with similar titles independently via `POST /v1/search` — they may exist as standalone child_page blocks under another parent.
- **"Shadow" copies of DB entries.** A database item might have a duplicate page (same or similar title) that exists as a `child_page` elsewhere. This duplicate is the one with actual content. The DB entry is just a metadata placeholder. When searching, check `parent.type`: `data_source_id` means it's a DB row (likely empty body), `page_id` means it's a real content page. If both exist, the `page_id` version has the content.
- **When user insists content exists but API returns empty, do not trust the API alone.** Search more broadly: query for partial titles, check blocks of the DB's parent page for child_page blocks, and look for standalone pages with matching names. The integration may have read access to DB metadata but not to the individual page's block content if it resides outside the DB.
- **Integration must be shared.** If the integration hasn't been manually connected to a page/DB, the API returns 404 even if search found it. User must click "Connect to" → integration name in Notion UI.
- **Rate limit ~3 req/s.** Space out sequential calls when querying many items.
- **Untitled pages.** Pages with no title appear as `"(untitled)"` with empty title array. Flag them for cleanup.
- **Cannot create workspace-root pages from bot integrations.** Bot/internal integrations cannot create pages at the workspace root. The error reads: "Internal integrations aren't owned by a single user, so creating workspace-level private pages is not supported." Workaround: create the page under an existing shared page, then tell the user to drag it where they want in the UI.
- **⚠️ Pre-flight parent accessibility check.** Before creating sub-pages under a parent page, VERIFY that parent appears in search results. Some parent pages accept content PATCH operations (you can update them) but never appear in POST /v1/search results. Pages created under such a parent are **invisible to search forever** — the creation API returns a valid page_id that you can still PATCH directly, but subsequent searches never return it. To test: run a search for the parent's title or ID. If it doesn't show up, pick a different parent (e.g., workspace-root pages reliably appear in search). If you must use an invisible parent, save the created page_id from the API response immediately — it's your only reference.
- **Can't "move" pages between databases.** There is no API endpoint to move a page from one DB to another. To relocate: create a new page in the target DB with the same properties + content, copy the markdown body, then archive the original. This is a multi-step operation.
- **Property updates via wrong endpoint silently fail.** PATCHing `/v1/databases/{id}` with new properties returns 200 but does nothing. Always PATCH `/v1/data_sources/{id}` for property changes.

## Workspace organization: naming & linking

You can rename a data source (database) to make its purpose clear in the UI:

```bash
curl -s -X PATCH "https://api.notion.com/v1/data_sources/{data_source_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"title": [{"text": {"content": "📂 My Project DB"}}]}'
```

To link DB entries to related standalone pages (e.g. when content lives in a child_page but the DB entry tracks metadata), add a `url` property to the database schema, then set it per-entry:

```bash
# 1. Add URL property to schema
PATCH /v1/data_sources/{ds_id}
  {"properties": {"관련 자료": {"url": {}}}}

# 2. Set URL on each DB entry
PATCH /v1/pages/{page_id}
  {"properties": {"관련 자료": {"url": "https://www.notion.so/page-title-<page_uuid>"}}}
```

Notion page URLs follow `https://www.notion.so/{slug}-{uuid}`. Verify via `GET /v1/pages/{id}` → `.url`.

To archive (trash) a completed/unused page:
```bash
PATCH /v1/pages/{page_id} {"archived": true}
```

Archived pages no longer appear in data_source queries.

## Restoration pattern (moving content across DBs)

When you need to consolidate content from child pages into a database:

1. Query source DB for items → get each item's page_id
2. For each item, read the markdown content: `GET /v1/pages/{page_id}/markdown`
3. Create a new page in the target DB with properties matching the target schema
4. Optionally include the markdown body via the `markdown` field
5. Archive the original page: `PATCH /v1/pages/{page_id}` with `{"archived": true}`

Note: You can't set the markdown body on pages created inside a database — only on free-form pages. For DB items, copy content manually into the page's rich_text / memo fields.

## Quick reference: finding DB IDs

```python
# After search results, extract both IDs:
db_info = {}
for item in results:
    if item['object'] == 'data_source':
        title = item['title'][0]['plain_text']
        data_source_id = item['id']
        # database_id is stored in parent if parent.type == 'database_id'
        parent = item.get('parent', {})
        db_id = ''
        if parent.get('type') == 'database_id':
            db_id = parent.get('database_id', '')
        elif parent.get('type') == 'page_id':
            db_id = parent.get('page_id', '')
        db_info[title] = {'ds_id': data_source_id, 'db_id': db_id}
```

## Attribution

This pattern was developed auditing a workspace containing a project tracker (P-Project DB, 12 items with status/field/date), a lecture notes DB (강의 노트, 5 items), and top-level hub pages with child_page sub-trees. Full API reference in the `notion` skill's SKILL.md.
