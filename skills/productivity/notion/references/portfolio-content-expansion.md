# Portfolio Content Expansion: Batch-Updating Specific Sections Across Child Pages

A recurring pattern: a parent page has a table of contents linking to child pages, and the user asks to "expand" or "make more detailed" the body content within each child page.

## The Mistake to Avoid

When the user says "각 통합된 내용을 좀 더 자세하게 적어줘" for a portfolio with:
- **Parent page**: table summary (구분/기간/주제/링크)
- **Child pages**: detailed content under specific sections (활동 상세/Activity Details)

→ **Expand the child page body sections, NOT the parent table summary.**
The parent table's "주제" column should remain a concise one-line label. The expansion work belongs in the child pages' detailed sections.

If unsure whether the user wants titles expanded or body content expanded, **clarify first** before making changes.

## Batch Expansion Workflow

### 1. Discover child pages from parent content

Read the parent page markdown and extract child page IDs from `<page>` tags:

```python
import re, json

# Read parent markdown
result = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/pages/{PARENT_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
parent_md = json.loads(result.stdout).get("markdown", "")

# Extract child page IDs from <page url="..."> tags
child_ids = re.findall(r'<page url="[^/]+/([a-f0-9]+)"', parent_md)
```

### 2. Read each child page and identify target sections

```python
result = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/pages/{CHILD_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
child_md = json.loads(result.stdout).get("markdown", "")
```

### 3. Expand specific sections with context-depth structure

Apply the **배경/문제 → 구체적 방법 → 결과/성과** (Background → Method → Result) structure to each bullet point:

| Original | Expanded |
|---|---|
| `- ALIO API 분석` | `- ALIO OpenAPI recruitment.api 서비스 엔드포인트 분석, pageNo/pageSize 파라미터 식별, 응답 데이터 매핑 테이블 작성 및 정합성 검증 방안 수립` |
| `- 기술 조사: CrewAI` | `- CrewAI 멀티에이전트 오케스트레이션 평가: 응답 지연·디버깅 불가·추론 일관성 부족 확인 → CrewAI 포기 결정의 근거로 활용` |

### 4. Write back each child page (read-modify-write)

**CRITICAL**: Use the full read-modify-write cycle:
1. Read the ENTIRE current markdown
2. Apply Python `str.replace()` on the specific sections
3. Write the ENTIRE modified markdown back with `replace_content`

```python
# Full read-modify-write per child
payload = json.dumps({
    "type": "replace_content",
    "replace_content": {"new_str": modified_full_md}
}, ensure_ascii=False)

# Save to file to avoid shell quoting issues
with open("/tmp/payload.json", "w") as f:
    f.write(payload)

subprocess.run([
    "curl", "-s", "-X", "PATCH",
    f"https://api.notion.com/v1/pages/{child_id}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", "@/tmp/payload.json"
], capture_output=True, timeout=15)
```

### 5. Pagination and rate limiting

When processing 4+ child pages sequentially:
- Insert `time.sleep(0.5)` between API calls to avoid rate limits (~3 req/s)
- Pages without child_page children can use `replace_content` freely (no `<page>` tag constraint)
- Verify each write by checking `resp.get("object") == "page_markdown"`

## ⚠️ Critical: Verify Each Page After Every Write

Do NOT batch-update all pages and then verify at the end. **Verify each page immediately after writing it.** This prevents a buggy write from corrupting multiple pages before detection.

```python
# After each PATCH call:
resp = json.loads(result.stdout)
if resp.get("object") != "page_markdown":
    print(f"❌ Write FAILED for {child_id}")
    # Stop and investigate before continuing
    break

# Then re-read and confirm content has the expected sections:
verify = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/pages/{child_id}/markdown",
    ...
], capture_output=True, text=True, timeout=15)
verify_md = json.loads(verify.stdout).get("markdown", "")

# Check key indicators:
assert "활동 상세" in verify_md, "Lost 활동 상세 section!"
assert len(verify_md) > 2000, f"Content too short: {len(verify_md)}"
```

### What can go wrong (based on real session failures):

| Failure mode | Symptom | Root cause |
|---|---|---|
| Wrong page overwritten | 9~11주차 shows 5~8주차 content | Previous write used wrong page ID or replace operations failed silently |
| Content merged from wrong source | Target section has text from different page | `str.replace` with too-short anchor matched wrong content |
| Duplicate sentences | Same paragraph appears twice | Partial replacement broke sentence, leaving duplicate fragment |
| Table row duplicated | Row appears in wrong table | `str.replace("</table>", ...)` matched all tables, not just the target |

## Verification

After all writes, do a final audit pass:
- ✅ Target section exists (e.g., "활동 상세" present in markdown)
- ✅ Each page has distinct, page-appropriate content (not a copy of another page)
- ✅ Content length increased significantly (baseline ~900-1400 chars → expanded ~2300-3400 chars)
- ✅ No duplicate sentences, fragments, or merged text from other pages
- ✅ No content was accidentally truncated or lost
