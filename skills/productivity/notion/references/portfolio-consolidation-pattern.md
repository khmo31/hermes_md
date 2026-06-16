# Portfolio Consolidation Pattern: Merging Multiple Child Pages into a Single Integrated Page

A recurring pattern: the user has multiple portfolio sub-pages (e.g., weeks 1-4, 5-8, 9-11, 12-14) plus a reflection page, and wants a **single integrated page** consolidating everything. Separately, there's a sibling document (final report) that needs fact-checking against the consolidated page.

## The Three-Phase Workflow

### Phase 1: Discover & Read Everything

1. **Search for the parent portfolio page** in Notion
2. **Get all children** of the parent via `GET /v1/blocks/{parent_id}/children` — paginate to find all `child_page` blocks
3. **Read each child page's markdown** via `GET /v1/pages/{page_id}/markdown` and save to local files

```python
import json, subprocess, os

NOTION_KEY = os.environ["NOTION_API_KEY"]
PARENT_ID = "page-uuid"

# Discover child pages
result = subprocess.run([
    "curl", "-s", f"https://api.notion.com/v1/blocks/{PARENT_ID}/children?page_size=100",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03"
], capture_output=True, text=True, timeout=15)
data = json.loads(result.stdout)

child_pages = []
for block in data.get("results", []):
    if block.get("type") == "child_page":
        title = block.get("child_page", {}).get("title", "Untitled")
        child_pages.append((title, block["id"]))

# Paginate if needed
while data.get("has_more"):
    cursor = data.get("next_cursor")
    result = subprocess.run([...f"?start_cursor={cursor}"...], ...)

# Read each child page's markdown
for title, pid in child_pages:
    result = subprocess.run([
        "curl", "-s", f"https://api.notion.com/v1/pages/{pid}/markdown",
        ...
    ], capture_output=True, text=True, timeout=15)
    md = json.loads(result.stdout).get("markdown", "")
    with open(f"/tmp/notion_{safe_name(title)}.md", "w") as f:
        f.write(md)
```

### Phase 2: Build the Integrated Page

Structure the integrated page as:

```
# 📋 Title — Author Name
> Project info (role, project name, GitHub, period)

## Project Overview
2-3 sentence summary + 3-axis evolution statement

## Integrated Timeline
Weekly table covering the entire period

## 1️⃣ First Section (e.g., Weeks 1-4)
> Period
Activity details (week-by-week narrative)

## 2️⃣ Second Section (Weeks 5-8)
...

## 💭 Reflection
Condensed to core insights only — NOT a re-summary of the sections above

## 🛠️ Technology Stack
Optional: add a tech stack table from the final report

## 📂 Project Structure
Optional: add directory tree from the final report

## 📊 Final Results
Metrics table
```

**Critical redundancy rule:** The Reflection section must NOT re-summarize content already in the weekly sections. Keep only:
- Unique insights not mentioned elsewhere
- Meta-lessons about decision-making
- The single-sentence thesis of the project

Everything else is a duplicate and should be removed.

### Phase 3 (if sibling report exists): Cross-Document Fact-Checking

If there's a separate final report (프로젝트 최종 보고서), run a fact-check pass AFTER creating the integrated page:

Read the report and compare specific claims against the portfolio:

| What to check | Why it diverges | How to fix |
|---|---|---|
| API/access status | Report may describe outcome more favorably | Use portfolio's factual accuracy |
| Technology format descriptions | Report may simplify or misremember technical details | Check original data source |
| Timeline event placement | Report may consolidate weeks into ranges and misplace events | Use week-by-week portfolio data |
| Problem definition wording | Report and portfolio may use different phrasings | Align to one canonical version |

Apply corrections to both documents in Notion via `replace_content`.

## Key Pitfalls

### 1. Reflection redundancy is the #1 problem
In a real session, the Reflection section was 80% identical to the weekly sections. The user wanted punchy insights, not a re-summary.

**Pattern for valid reflection content:**
- "데이터 소스의 교훈" — condensed to 1-2 sentences
- "방향 전환의 가치" — the meta-lesson, not the timeline
- "엔지니어링 의사결정" — what was learned about decision-making

### 2. Terminology drift across sections
The same concept may be called different names in different weekly sections (e.g., "Chroma DB" vs "Vector DB", "NCS Wiki" vs "Facet Wiki" vs "Facet Index").

**Fix:** Choose one canonical term per concept and use it consistently:
- First mention: full name with context: "Vector DB (Chroma DB)"
- After: uniform short form: "Vector DB"
- In reflection: use the FINAL term only (e.g., "Facet Index", never "NCS Wiki")

### 3. Timeline table + weekly detail = double content
The timeline table at the top and the week-by-week detail below are structurally redundant. This is acceptable — the user expects both — but the weekly detail should PROVE the timeline, not just repeat it. Each weekly entry must include context, reasoning, and outcomes.

### 4. Missing content from the report
The final report often has structured info (tech stack table, directory tree, problem-solution tables) that the portfolio lacks. After consolidation, check the report for content worth porting over.

### 5. Page creation with `replace_content`
- New pages (no child pages) can use `replace_content` without `allow_deleting_content`
- Set the icon via a separate PATCH after creation (`POST /v1/pages` → then `PATCH /v1/pages/{id}` with icon)
- Verify by re-reading the markdown after write

## Phase 4: Submission Polish (Optional, After Integration)

When the user asks to prepare the integrated page (or report) for submission, apply these polish steps in order:

### 4a. Emoji Removal

Submission-ready documents typically need all emojis stripped from:

- **Page title** — PATCH the title property
- **Page icon** — set `icon: null` via PATCH
- **Content** — replace_content with emoji-free markdown

**Emoji removal technique (safe for Korean text):**

Use precise Unicode ranges to remove emojis without touching CJK/Hangul:

```python
import re

emoji_ranges = [
    (0x1F600, 0x1F64F),   # Emoticons
    (0x1F300, 0x1F5FF),   # Misc Symbols
    (0x1F680, 0x1F6FF),   # Transport
    (0x1F1E0, 0x1F1FF),   # Flags
    (0x2600,  0x26FF),    # Misc symbols
    (0x2700,  0x27BF),    # Dingbats
    (0xFE00,  0xFE0F),    # Variation Selectors
    (0x1F900, 0x1F9FF),   # Supplemental Symbols
    (0x1FA00, 0x1FA6F),   # Chess Symbols
    (0x1FA70, 0x1FAFF),   # Extended-A
    (0x200D,  0x200D),    # ZWJ
    (0x25FB,  0x25FE),    # Medium squares
    (0x2648,  0x2653),    # Zodiac
    (0x267F,  0x267F),    # Wheelchair
    (0x26A1,  0x26A1),    # High voltage
    (0x2705,  0x2705),    # Check mark
    (0x274C,  0x274C),    # Cross mark
    (0x2757,  0x2757),    # Exclamation
    (0x2763,  0x2764),    # Hearts
    (0x2795,  0x2797),    # Plus/minus/division
    (0x27B0,  0x27B0),    # Curly loop
    (0x2B50,  0x2B50),    # Star
    (0x3030,  0x3030),    # Wavy dash
    (0x3297,  0x3297),    # Congratulations
    (0x3299,  0x3299),    # Secret
    (0x23E9,  0x23F3),    # Double arrows, Play/Pause
    (0x231A,  0x231B),    # Watch, Hourglass
    (0x25AA,  0x25AB),    # Small squares
    (0x25B6,  0x25C0),    # Play/reverse buttons
    (0x2614,  0x2615),    # Umbrella, coffee
    (0x26AA,  0x26BE),    # Circles, sports
    (0x26C4,  0x26C5),    # Snowman, sun
    (0x26CE,  0x26D4),    # Misc
    (0x26EA,  0x26FD),    # Misc
    (0x2702,  0x270F),    # Scissors, envelope, pencil
    (0x2712,  0x2716),    # Nib, check, x marks
    (0x271D,  0x2728),    # Cross, star, sparkles
    (0x2733,  0x2734),    # Asterisks, snowflake, sparkle
    (0x274E,  0x274E),    # Cross mark
    (0x2753,  0x2755),    # Question marks
    (0x2B05,  0x2B07),    # Arrows
    (0x2B1B,  0x2B1C),    # Squares
    (0x2B55,  0x2B55),    # Circle
    (0x303D,  0x303D),    # Part alternation
]

chars = []
for lo, hi in emoji_ranges:
    for cp in range(lo, hi + 1):
        chars.append(chr(cp))

emoji_pattern = re.compile(f"[{''.join(chars)}]")
text = emoji_pattern.sub('', text)
```

**CRITICAL:** Do NOT use broad ranges like `\U000024C2-\U0001F251` — these overlap with CJK Unified Ideographs (U+4E00–U+9FFF) and will strip Korean/Chinese characters. Use only the specific emoji blocks listed above.

After removal, clean up:
- Double spaces → single space
- Leading spaces on lines
- Consecutive blank lines (3+ → 2)
- Headers with extra space like `##  text` → `## text`

### 4b. Tone/Style Conversion

When the user requests a specific Korean writing style:

| Style | Description | Examples | When requested |
|-------|-------------|----------|----------------|
| **음슴체** | Plain factual tone, omits polite endings. Uses `~임`, `~함`, `~였음` instead of `~입니다`, `~했다`, `~였다`. | "시스템임" not "시스템입니다", "판단함" not "판단했다" | Submission documents, reports |
| **개조식** | Itemized bullet-point format. Breaks paragraph narratives into concise bullet points with hierarchical sub-bullets. | `-\n\t-` structure | Readability optimization, one-glance scanning |

**Conversion technique for 음슴체:**
- Rewrite sentences to end with verb stems: `~했다` → `~함`, `~였다` → `~였음`, `~이다` → `~임`
- Remove narrative connectors like "~했기 때문이다", "~할 수 있었다"
- Use `~임` particles directly: "제공하는 시스템임" not "제공하는 시스템이다"
- Quotes/catchphrases can keep their original style for emphasis

**Conversion technique for 개조식:**
- Each paragraph becomes a top-level bullet (`-`)
- Key details become indented sub-bullets (`\t-`)
- Sequential actions use arrow notation: `→`
- Format: `[action/decision]: [result/outcome]`

**Before/After example:**
```
Before (서술체, 두괄식):
공공데이터와 AI를 결합한 서비스를 구상했다. 채용 시장에서 
구직자가 경험과 직무를 연결하는 데 어려움을 겪는 점에 주목했다.

After (음슴체, 개조식):
- 공공데이터 + AI 결합 맞춤형 커리어 정보 서비스 구상
- 채용 시장에서 구직자의 경험-직무 연결 어려움에 주목
- 초기 데이터 소스로 DART(전자공시) API 검토
    - 사업보고서, 인력 현황 등 포함 → 채용 연계 가능성 판단
    - 실제 분석 결과: 재무/경영 정보 위주, 채용공고 관련 정보 소수
    - 부적합 판단 후 채용공고 API로 방향 전환
```

### 4c. Title & Icon Cleanup

After content is polished, update page metadata:

```bash
curl -s -X PATCH "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d '{"properties":{"title":[{"text":{"content":"New Title Without Emoji"}}]},"icon":null}'
```

## Phase 5 (if sibling report exists): Error Detection & Correction

When a separate final report (프로젝트 최종 보고서) exists alongside the portfolio, run a structured fact-check pass. The following error types recurred in real sessions:

### Common Error Patterns Found in Reports

| Error Type | Example (Wrong) | Correct | How to Catch |
|---|---|---|---|
| **API/Access status** | "사람인 API 키를 발급받았으나" | "사람인·잡코리아 모두 API 접근 승인 거절" | Cross-reference with portfolio's raw week-by-week data |
| **Tech format description** | "DART는 PDF 기반 데이터" | "DART API는 XML/JSON 구조화 데이터" | Check actual API documentation |
| **Timeline misplacement** | 사람인/잡코리아 검토 배치 → 5~8주차 | 실제는 2주차(3/10) | Compare against week-by-week portfolio timeline |
| **Problem definition drift** | Report uses solution-style mission statement; portfolio uses problem-style statement | Align to one canonical version | Compare the two problem definitions side by side |

### Correction Workflow

1. **Read both documents** — portfolio markdown + report markdown
2. **Identify mismatches** — check same topics for wording, timing, facts
3. **Apply corrections to report** via `replace_content` with targeted string replacement
4. **Verify on read-back** — re-read the report markdown and check each replacement
5. **Apply corrections to portfolio** if the portfolio was the one that was wrong

**Priority order for report fixes:**
- 🔴 Must fix — factual errors (API status, tech descriptions, timeline)
- 🟡 Should fix — consistency issues (problem definition alignment)
- 🟢 Nice to fix — additions (links, supplementary detail)

## Verification Checklist

After creating the integrated page:
- [ ] All N source pages' content represented (no omissions)
- [ ] Reflection section is <30% of total content and contains unique insights only
- [ ] Terminology is consistent throughout (Vector DB, Facet Index, etc.)
- [ ] Tech stack / project structure / results table added from report
- [ ] New page is verified in Notion (re-read markdown, check length)
- [ ] If report exists: fact-checked against portfolio, inconsistencies fixed in both

**After submission polish:**
- [ ] All emojis removed from title, icon, and content
- [ ] Tone converted (if requested: 음슴체, 개조식, etc.)
- [ ] No residual formatting artifacts (double spaces, empty headers, excessive blank lines)
- [ ] Report corrected for any factual errors found during cross-check
