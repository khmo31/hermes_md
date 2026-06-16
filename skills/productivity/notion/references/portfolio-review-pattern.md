# Portfolio Review Pattern: Cross-Week Overlap Check & Targeted Precision Edits

A recurring pattern: the user asks you to review multiple related portfolio pages (e.g., different weeks of a capstone project) for **content overlap, narrative inconsistencies, or timeline contradictions**, and then make targeted additions/corrections.

This is distinct from `portfolio-content-expansion.md` (which covers bulk expanding sections with detail). This pattern is about **audit + precision surgery**.

## The Workflow

### Phase 1: Discover & Map

Before reading content, understand the portfolio structure:

```python
# Step 1: Search for relevant pages
search_result = subprocess.run([
    "curl", "-s", "-X", "POST", "https://api.notion.com/v1/search",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", '{"query": "캡스톤"}'
], capture_output=True, text=True, timeout=15)
results = json.loads(search_result.stdout).get("results", [])
```

**Key insight**: Weekly pages may be **consolidated** into ranges (e.g., "5~8주차 통합", "9~11주차 통합"). Always search for both individual week numbers and consolidated range titles.

```python
# Build a map of pages
pages_map = {}
for r in results:
    title = (r.get("properties", {}).get("title", {}).get("title", [{}])[0]
             .get("text", {}).get("content", "")
             or r.get("properties", {}).get("Name", {}).get("title", [{}])[0]
             .get("text", {}).get("content", ""))
    page_id = r.get("id", "")
    if "통합" in title or any(w in title for w in ["1주차","2주차","3주차"]):
        pages_map[page_id] = title
```

### Phase 2: Read All Pages in Parallel

Read every relevant page's markdown **before** analyzing:

```python
page_contents = {}
for pid, title in pages_map.items():
    result = subprocess.run([
        "curl", "-s", f"https://api.notion.com/v1/pages/{pid}/markdown",
        "-H", f"Authorization: Bearer {NOTION_KEY}",
        "-H", "Notion-Version: 2025-09-03"
    ], capture_output=True, text=True, timeout=15)
    md = json.loads(result.stdout).get("markdown", "")
    page_contents[pid] = {"title": title, "md": md}
```

### Phase 3: Analyze for Overlap & Inconsistencies

Cross-compare pages looking for these specific patterns:

| Signal | What to check | Example from real session |
|--------|---------------|---------------------------|
| **Same narrative in different weeks** | Does the same decision/feedback appear in multiple weeks' "활동 상세"? | "Vector DB는 설명할 수 없다" feedback appeared in both 7주차 and 9주차 |
| **Timeline leap** | Does a week announce a conclusion that wasn't reached until later? | 7주차 says "Facet Wiki 전환의 계기" but actual transition happened in 9-10주차 |
| **Source attribution mismatch** | Is the same event attributed to different people/groups? | 7주차 = "팀원 피드백" vs 9주차 = "교수님 피드백" |
| **Weight/value inconsistency** | Do numerical values (weights, counts, percentages) shift between weeks without explanation? | Profile term weights 3 → later core term weights 6 |

Implementation:

```python
def check_overlap(contents_a: str, contents_b: str, phrases_to_check: list[str]) -> list[dict]:
    """Check if specific narrative phrases appear in multiple pages."""
    findings = []
    for phrase in phrases_to_check:
        in_a = phrase in contents_a
        in_b = phrase in contents_b
        if in_a and in_b:
            findings.append({
                "phrase": phrase,
                "pages": ["A", "B"],
                "severity": "duplicate_narrative"
            })
    return findings
```

### Phase 4: Report Findings to User

Present findings in a structured format:

```
## 🔍 중복 분석

**7주차** vs **9주차** — "Vector DB 블랙박스" 피드백이 양쪽에 등장

| 항목 | 7주차 | 9주차 |
|------|-------|-------|
| 피드백 출처 | "팀원" | "교수님" |
| 서사 위치 | "→ Facet Wiki 전환의 계기" | "7주차 피드백과 연결됨" |
| 문제 | 7주차가 전환을 **이미 결정**처럼 서술했으나, 실제 전환은 9-10주차 | ❓ 출처 불일치 |

❓ 처리 방안 제안 (A/B/C 옵션)
```

Always propose concrete resolution options — don't just dump findings.

### Phase 5: Precision Edit (Targeted Content Addition)

When adding new information (not expanding), use **exact string replacement** anchored in surrounding context:

```python
# Read current content
result = subprocess.run(["curl", "-s",
    f"https://api.notion.com/v1/pages/{PAGE_ID}/markdown",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
md = json.loads(result.stdout).get("markdown", "")

# Anchor replacement with enough context for uniqueness
old = """- 점수화: PROFILE_TERM_WEIGHT 3.0 / SUPPLEMENTAL_TERM_WEIGHT 1.0
\t사용자 경험(Profile Term)과 채용공고 직무 내용(Supplemental Term) 간의 매칭 정확도를 높이기 위해"""

new = """- 점수화: PROFILE_TERM_WEIGHT 3.0 / CORE_TERM_WEIGHT 6.0 / SUPPLEMENTAL_TERM_WEIGHT 1.0
\t사용자 경험(Profile Term)과 채용공고 직무 내용(Supplemental Term) 간의 매칭 정확도를 높이기 위해"""

if old not in md:
    # Try finding just the key identifier
    idx = md.find("PROFILE_TERM_WEIGHT")
    if idx >= 0:
        print(f"Old string not found. Anchor at {idx}:")
        print(repr(md[idx-30:idx+150]))
else:
    md = md.replace(old, new)
```

**Rules for safe replacement:**
1. Include 2-3 lines of surrounding text for uniqueness
2. Use `str.replace` (not regex) for predictable behavior
3. Verify the old string exists BEFORE modifying
4. If not found, print debug context around a known anchor point
5. After write-back, verify by re-reading and checking expected content exists

## Verification After Precision Edit

Always verify after a targeted edit:

```python
# Write back
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

# Verify the new content is present
new_md = resp.get("markdown", "")
assert "CORE_TERM_WEIGHT 6.0" in new_md, "❌ New content not found after write!"
assert "PROFILE_TERM_WEIGHT 3.0" in new_md, "❌ Existing content was lost!"
```

## When to Use This vs. Portfolio Content Expansion

| Pattern | `portfolio-review-pattern.md` (this file) | `portfolio-content-expansion.md` |
|---------|------------------------------------------|----------------------------------|
| Trigger | "겹치는것 같은데 확인", "비교해줘", "수정해줘" | "더 자세하게 적어줘", "보강해줘" |
| Action | Audit + Compare + Precision edit | Bulk expand sections |
| Scope | Multiple related pages | Single page or section |
| Output | Findings report + minimal targeted edits | Large content additions |
| Risk | Corrupting existing content via wrong replacement | Overshooting content boundaries |
