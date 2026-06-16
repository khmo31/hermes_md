# Batch Page Creation Patterns

Creating multiple pages under one parent (e.g., weekly portfolios, chapter structure, product sub-pages).

## Common Use Cases

- Split a single page into weekly/monthly sub-pages
- Create a navigation index + detail pages
- Scaffold project folder structure

## Pattern: Create → Collect → Link

### Step 1: Create all child pages

Create pages under the parent. Use `POST /v1/pages` with `parent: {"page_id": "..."}`.

**Icon strategy:** Create without icon first, then PATCH icons in a second pass (see Pitfall #9). This avoids payload-size-dependent validation errors.

### Step 2: Collect child page IDs

```python
result = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/blocks/{parent_id}/children?page_size=50",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
blocks = json.loads(result.stdout)
child_pages = [(block["id"], block.get("child_page", {}).get("title", ""))
               for block in blocks.get("results", [])
               if block.get("type") == "child_page"]
```

**Note:** The IDs returned by this endpoint use `-` separators; the `https://www.notion.so/{id}` format accepts both UUID forms (with or without dashes).

### Step 3: Build index with proper `<page>` tags

```python
index_md = "# Table of Contents\n\n"
for pid, title in child_pages:
    index_md += f'<page url="https://www.notion.so/{pid}">{title}</page>\n'
```

These tags are required in the parent's markdown when doing `replace_content` (see Pitfall #8).

### Step 4: Update parent's content

Use `replace_content` with the full index markdown including all `<page>` tags.

## Performance Notes

- Rate limit: ~3 req/s. Batch creation of 14+ pages takes ~4-8 seconds.
- `GET /v1/blocks/{id}/children` returns max 50 results per page. Use `start_cursor` for pagination.
- `POST /v1/pages` with large markdown bodies: build payload via Python `json.dumps()`, not shell heredocs.
