# Notion + Cron Delivery Pipeline

Extension of the second-brain knowledge pipeline: after producing a substantive analysis/output, persist to Notion AND set up cron-based recurring delivery — all in one turn, without asking permission.

## When to Use

User says or implies: "이거 저장해줘 + 노션에 올려줘 + 매일/매주 보내줘" — a multi-part request covering creation, persistence across stores, and automation.

The user expects all three in one go. Do not sequence or ask permission between steps.

## Pattern: Analysis → Notion → Cron Delivery

### Step 1: Build the analysis/output

Use session_search to gather historical data. The user references "지난 대화" or "우리가 나눈 모든 대화" — gather 5+ sessions for breadth.

### Step 2: Save summary to memory

Memory is capped at 2,200 chars. If full:
- **Consolidate** less-critical entries into single lines using `replace`
- Priority order to keep: user preferences > environment facts > procedural notes
- Low-priority to merge/trim: specific tool-usage instructions, old project references

```python
# Consolidation trick: merge facts into compact one-liners
memory.replace(old_text="old title substring", content="Compact merged line with all key facts")
```

### Step 3: Upload full content to Notion

- Use Path B (curl, NOT ntn CLI) when ntn is not installed
- Create as a **child page** under an existing workspace-root page the integration can access
- Verify parent page appears in search results FIRST (pre-flight check)
- Include markdown content directly in the `POST /v1/pages` payload

```bash
# Workspace-root pages (parent.type == "workspace") reliably accept children
PARENT_ID="<workspace-root-page-uuid>"

curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"page_id": "'$PARENT_ID'"},
    "properties": {"title": [{"text": {"content": "Page Title"}}]},
    "markdown": "..."
  }'
```

- Use Python's `json.dumps()` with `ensure_ascii=False` to safely construct the payload with Korean characters
- Verify by reading back: `GET /v1/pages/{page_id}/markdown`

### Step 4: Create cron for recurring delivery

For daily tips/reminders (fixed rotation, no LLM needed):

```bash
hermes cron create \
  --name "descriptive-name" \
  --deliver "telegram" \
  --no-agent \
  --script path/to/script.py \
  "0 22 * * *"   # 07:00 KST = 22:00 UTC
```

Key choices:
- **`no_agent=true`**: Zero LLM tokens. The script's stdout IS the message. Only use when the output is deterministic and doesn't need reasoning.
- **`deliver="telegram"`**: Direct to user's Telegram home channel.
- **Script path**: Relative to `~/.hermes/scripts/` — just the filename.

### Step 5: Write the cycling script

Script pattern for daily rotation:

```python
#!/usr/bin/env python3
"""Docstring: what this rotates through."""
import datetime

ITEMS = [
    ("Title 1", "Target domain", "Description / reasoning"),
    ("Title 2", "Target domain", "Description / reasoning"),
    # ... up to N items
]

def main():
    today = datetime.date.today()
    idx = (today.timetuple().tm_yday - 1) % len(ITEMS)
    title, domain, desc = ITEMS[idx]
    dow_names = ['월','화','수','목','금','토','일']
    dow = today.isoweekday()
    
    print(f"🌅 Header — {today.month}월 {today.day}일 ({dow_names[dow-1]})\n")
    print(f"✅ {idx+1}. {title}\n")
    print(f"대상: {domain}\n")
    print(desc)
    print(f"\n💡 Context: why this matters for this user.")

if __name__ == "__main__":
    main()
```

- Use `day_of_year % len(ITEMS)` for deterministic cycling — no state file needed
- Each item should have: title, target domain, and a concrete "why this" line
- Match the user's tone: concise, No Slop, Korean

## Pitfalls

- **Memory full trap**: Always check `usage` before adding. Consolidate rather than remove if possible.
- **Pre-flight parent check**: Some parent pages accept writes but never appear in search → children become invisible forever. Test with a search first.
- **No agent means no LLM**: The script must be self-contained. No external API calls, no model queries. stdout is the entire message.
- **Day 366 edge case**: Leap years have 366 days, which cycles naturally through `% N` — works fine.
- **Workspace-root pages from bot integrations**: Cannot create new workspace-root pages directly. Always create as child of existing root page.
