# Portfolio Content: Pivot Narrative Pattern

A pattern for structuring project portfolio content that emphasizes **decision-making and evolution** rather than just outcomes. Useful for capstone projects, side projects, and engineering portfolios.

## Core Idea

Instead of presenting the project as a linear "we planned → we built → it worked" story, frame it as **a series of well-reasoned pivots**. This demonstrates:
- Critical thinking under constraints
- Ability to evaluate and discard approaches
- Real-world engineering judgment

## The Three-Column Comparison Tables

Use comparison tables to show the evolution clearly. Each row = one attempt with columns: Attempted Approach → Result → Reason.

### Data Source Evolution Table (when data source changed)

```
| 단계 | 시도한 접근법 | 결과 | 전환 사유 |
|:----:|:-----------:|:----:|:---------:|
| 1차 | **DART 공시 API** → | ❌ 기각 | 데이터가 채용과 무관한 재무/경영 정보 위주 |
| 2차 | **사람인·잡코리아 API** → | ❌ 승인 거절 | 기업 측 API 접근 권한 미승인 |
| 3차 | **ALIO 공공기관 채용 API** → | ✅ 적용 | 오픈 API, 공공 채용 특화 |
```

### Architecture Evolution Table (when technical approach changed)

```
| 단계 | 초기 접근법 | 한계 | 최종 결정 |
|:----:|:----------:|:----:|:---------:|
| 1차 | **Vector DB** 유사도 매칭 | 설명 불가능 | ❌ 폐기 |
| 2차 | **NCS Wiki** 개념 | 추상적, 세분화 필요 | 🔄 발전 |
| 3차 | **Facet Index** (8개 축) | 구조화 + 설명 가능 | ✅ 채택 |
```

## When to Use This Pattern

Use this pattern when:
- The project had multiple false starts or dead ends
- You evaluated and rejected alternatives before settling on the final approach
- External constraints (API rejections, rate limits, policy issues) forced scope changes
- A professor/instructor values PROCESS over results

## Cross-Document Sync

When you expand portfolio content with pivot narratives, **propagate the same narrative improvements to all related project documents** — not just the portfolio.

### Documents to sync

| Document | What to add | Priority |
|----------|-------------|----------|
| **Final report** (프로젝트 최종 보고서) | Architecture evolution table, data source evolution table, phase-by-phase retrospective | 🔴 High |
| **Presentation slides** | Pivot story as key talking points, comparison tables as visual slides | 🔴 High |
| **README / Q&A** | Add related Q&A items explaining why pivots happened | 🟡 Medium |
| **Resume / career doc** | Reference the decision-making skills demonstrated | 🟢 Nice-to-have |

### Sync strategy

1. After expanding portfolio child pages with detail, identify the parent/summary documents
2. Check if they already exist; if so, **read** them first to understand their current structure
3. Inject the same narrative elements into each document, **adapted to its format**:
   - Portfolio = personal achievement narrative (1st person, weekly structure)
   - Final report = project documentation (3rd person, thematic structure)
   - Slides = visual highlights (bullet points, tables, diagrams)
4. Use consistent terminology across all documents — if you name a phase "Vector DB Era" in the portfolio, use the same name in the final report

#### Fact-checking: verifying accuracy between documents

Narrative sync is not enough — **factual claims** can diverge between a portfolio and a final report even when the narrative arc is the same. After syncing narrative, run a separate fact-check pass:

**Fact-check all specific claims across documents:**

| What to check | Example discrepancy from real session | Severity |
|---------------|---------------------------------------|----------|
| API key/access status | Portfolio says "거절" → Report says "발급받았으나" | 🔴 심각 |
| Technology format descriptions | Portfolio: API described accurately → Report: "PDF 기반 데이터" (wrong, DART API is XML/JSON) | 🔴 심각 |
| Timeline placement of events | Event happened in Week 2 → Report timeline places it in Weeks 5-8 | 🟡 중간 |
| Problem definition statements | Portfolio has concise problem → Report has verbose mission statement; readers won't know they describe the same thing | 🟡 중간 |

**Procedure:**

1. **Read both documents in full** — don't assume they match just because they cover the same project
2. **Extract specific factual claims** from each document (API names, dates, counts, outcomes, technical formats)
3. **Compare line by line** — especially for: API approval status, tool/library roles, timeline positions, numerical values (counts, percentages, weights)
4. **Resolve using original source data** — if the portfolio and report disagree, check the weekly-level raw data (original 1~4주차 pages, meeting notes, or the user's own recollection) as the authoritative source
5. **Apply corrections to both documents** — one incorrect fact often has a matching correct version in the other document; fix both to match the truth
6. **Report findings prioritized** in severity order (🔴 → 🟡 → 🟢) so the user can triage

The user will notice if a number, date, or API detail differs between portfolio and report — this undermines trust more than any narrative gap. **Always fact-check after sync.**

## Why this matters

A professor who reads BOTH the portfolio AND the final report will notice if the narrative is inconsistent. Pivot narratives are the most distinctive signal of PROCESS thinking — if they appear in one document but not the other, it looks like an oversight. **Sync before considering the task complete.**

## Integrating Pivot Narratives into a Final Report

Final reports (프로젝트 최종 보고서) have a different structure from portfolios, but the same pivot narratives can be woven in naturally:

### Where to place them in a report

| Report section | How to inject pivot narrative |
|----------------|-------------------------------|
| **Introduction / Background** | Add a timeline table showing major phases and milestones across the project period |
| **Architecture / System Design** | Instead of showing only the final architecture, add a "Design Evolution" subsection with 3-phase comparison (attempt → problem → resolution) |
| **Key Decisions** | Dedicate one subsection per major decision. Each should include: the attempted approach, the problem that prompted the pivot, and the resolution. This is the natural home for architecture evolution and data source evolution stories. |
| **Problem Solving** | Add decisions that don't fit in "Key Decisions" here — operational challenges like rate limits, API rejections, tool limitations |
| **Lessons Learned / Retrospective** | Expand from a single paragraph to a **phase-by-phase retrospective** covering each major project period. Include concrete technical lessons AND decision-process insights. The strongest ending is a single-sentence thesis that encapsulates the project's core engineering lesson. |

### Report retrospective structure

A phase-by-phase retrospective is the most effective way to demonstrate PROCESS thinking:

```
### Phase-by-Phase Retrospective

**Weeks 1–4 (Phase name):**
What happened → what was learned → how it influenced later decisions.

**Weeks 5–8 (Phase name):**
...repeat for each phase...

**Overall lesson:**
One sentence that ties all phases together — the meta-lesson about engineering judgment.
```

## Feature Evolution Pattern (within-feature refinement)

For describing how a single feature or algorithm evolved through iterative improvement — distinct from architectural pivots between different approaches.

### The structure: 문제 → 한계 → 해결

Use a **problem → limitation → solution** arc rather than listing the final configuration as a flat fact:

1. **Initial approach** — what was tried first, and what values/config were chosen
2. **Limitation discovered** — why the initial approach wasn't sufficient; what specific gap emerged
3. **Improved approach** — what was added or changed to address the limitation
4. **Why it works** — why the improvement solves the original problem

### Example (scoring algorithm evolution)

Instead of a flat bullet:
```
PROFILE_TERM_WEIGHT 3.0 / CORE_TERM_WEIGHT 6.0 / SUPPLEMENTAL_TERM_WEIGHT 1.0
```

Write a narrative arc:
```
점수화: PROFILE_TERM_WEIGHT 3.0 → CORE_TERM_WEIGHT 6.0 추가

초기에는 사용자 경험 키워드(PROFILE_TERM)에 가중치 3.0, 보조 키워드
(SUPPLEMENTAL_TERM)에 가중치 1.0을 부여하는 단순 점수화를 적용함. 그러나
이 방식만으로는 사용자가 실제로 원하는 직무를 정확히 파악하는 데 한계가 있음을
발견함. 사용자 경험 텍스트에는 다양한 경험과 역량이 혼재되어 있어, 모든 경험에
동일한 가중치를 적용하면 직무 적합성을 제대로 평가할 수 없었기 때문임. 이 문제를
해결하기 위해 해당 직무와 직접 연관된 핵심 역량 키워드(CORE_TERM)를 별도로
분류하고 가중치 6.0을 부여하는 방식으로 점수화 알고리즘을 개선함.
```

### When to use this pattern

| Use it when... | Don't use it when... |
|---|---|
| A single algorithmic/config decision evolved over multiple iterations | The change was a bug fix or simple config correction |
| Final config is a superset (added more categories, changed values) | Final config is a complete replacement of the initial one |
| The evolution reveals engineering judgment (identified a gap and filled it) | The evolution was forced by an external requirement |
| The improvement is about **precision / intelligence** | The improvement is about performance optimization only |

Use the **Pivot Narrative** (architecture comparison tables above) when switching between fundamentally different approaches (e.g., Vector DB → Facet Index). Use the **Feature Evolution** pattern when refining a single approach that stayed conceptually the same but grew more sophisticated.

## Common Pitfalls

1. **Don't hide failures** — the pivot IS the story. A project that worked on the first try is less impressive than one where you recognized a problem and corrected course.
2. **Include real constraints** — API rejections, budget limits, time pressure. These make the story authentic.
3. **Explain WHY each pivot happened** — not just "we changed to X" but "we changed to X because Y was a problem."
4. **Use consistent framing** — if you present data source evolution AND architecture evolution, use the same table format for both.
5. **Keep terminology synchronized** between portfolio and final report. If the portfolio says "Phase 1: Vector DB Era", don't say "Initial Approach Using Embeddings" in the report. Name things once and reuse them.
6. **Don't let report sections become orphans** — if the "Key Decisions" section covers a pivot narrative, make sure the "Architecture" and "Retrospective" sections acknowledge it too. Cross-references make the report feel cohesive, not repetitive.
