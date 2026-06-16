# Output Contract Pattern (from last30days-skill + im-not-ai)

비코딩 에이전트(글쓰기, 리서치, 번역)의 시스템 프롬프트에 적용할 Output Contract 패턴.
두 레포에서 발췌하여 Paperclip 비코딩 에이전트에 맞게 일반화.

## 핵심: 8 Non-Negotiable Output Laws (last30days-skill 패턴)

출력의 매 줄마다 적용되는 불가침 규칙을 **이름(failure case)과 함께** 명시.
"이 규칙을 어기면 이렇게 망했다"는 실제 사례를 함께 기록해야 모델이 기억함.

### 패턴 템플릿

```markdown
## OUTPUT CONTRACT (Non-Negotiable)

| # | Rule | When to Break |
|---|------|---------------|
| 1 | **[RULE]** — reason for this rule | exception cases |
| 2 | **[RULE]** — reason | exception |
```

예시 (글쓰기 에이전트용):

```markdown
## OUTPUT CONTRACT

| # | Rule | Exception |
|---|------|-----------|
| 1 | **NO AI-isms** — 'Certainly', 'I'd be happy to', 'In conclusion', 'It's worth noting'. These are AI tells your reader detects instantly. | Reproducing a direct quote that contains them |
| 2 | **NO em-dashes (—)** — Use hyphens with spaces ( - ) instead. Em-dashes are a GPT signature. | Quoted content where the source used one |
| 3 | **NO introduction/apology** — Start with the content, not 'Here is your article...' or 'I hope this helps...'. | None |
| 4 | **NO bullet points in prose** — Only use bullets for actual lists. Narrative paragraphs use sentences. | When the user explicitly asks for a list |
| 5 | **EVERY claim has evidence** — If you state a fact, you must be confident it's true. 'Seems like' is not evidence. | Widely-known common knowledge |
```

### Text, not structure (Writer-specific)

```markdown
- Paragraphs, not sections. No `##` headers in the body.
- Bold lead-in for emphasis, not headers.
- One blank line between paragraphs. No extra spacing.
```

### Self-Check Before Emit

프롬프트 마지막에 실행할 자가 검증 5-7항목:

````markdown
## PRE-EMIT SELF-CHECK

Before outputting, scan your response for:

- [ ] Any AI-ism phrases present? → Remove them
- [ ] Any em-dashes? → Replace with hyphen-spaces
- [ ] Does the first line start with the content (not an introduction)?
- [ ] Are there `##` headers in the body? → Remove, use bold lead-in
- [ ] Is every factual claim supported?
- [ ] If Korean text: check for 번역투, 영어 직역, 과도한 연결어
````

## Role Locking Pattern (im-not-ai 패턴)

각 에이전트가 **무엇을 하지 말아야 하는지**를 하는 것보다 먼저 명시.
이는 에이전트가 역할 범위를 넘어서는 행동(self-review, code generation, routing 등)을 방지.

### 템플릿

```markdown
## Role Boundaries (MANDATORY)

You MUST:
- [positive scope: what you DO]

You MUST NOT:
- [negative scope 1: e.g., 'Write code']
- [negative scope 2: e.g., 'Suggest alternatives not asked for']
- [negative scope 3: e.g., 'Modify the original text']
```

### 적용 예시

| 에이전트 | Must NOT |
|----------|----------|
| 글쓰기 | Write code, add meta-commentary, use AI-isms |
| 웹서치 | Make up sources, report unverified claims, produce off-scope research |
| 번역 | Summarize, add explanations, change proper nouns |
| 00-라우터 | Implement anything, route to itself, ignore ambiguity |

## Failure Name Pattern (named real-world regressions)

"이 규칙을 왜 만들었냐"면 구체적인 사례를 제시:

```markdown
**KNOWN FAILURE CASE (YYYY-MM-DD):** [brief description of what went wrong]
→ Fix: [what the rule enforces]
```

예시:
```
KNOWN FAILURE CASE (2026-06-10): Writing agent output started with 'Here is the article you requested'
→ FIX: Output Contract Rule #3 — NO introduction, start with content immediately
```
