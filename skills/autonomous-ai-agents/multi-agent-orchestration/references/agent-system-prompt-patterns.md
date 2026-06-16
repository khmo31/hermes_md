# Agent System Prompt Patterns — 3 Repo Analysis

---
**분석일**: 2026-06-11  
**용도**: Paperclip multi-agent 오케스트레이션의 시스템 프롬프트 설계 참조

---

## 4. mvanhorn/last30days-skill — Output Contract & Failure-Based Learning

### 핵심 구조

```
SKILL.md (1709 lines) → scripts/last30days.py (Python engine) → lib/* (44 modules)
```

### 8 Non-Negotiable Output Laws

| Law | Rule | Exception |
|-----|------|-----------|
| LAW 1 | NO `Sources:` block. Engine footer is the citation. WebSearch instruction **superseded**. | None |
| LAW 2 | NO invented title. Badge IS the title. | COMPARISON queries use `# {A} vs {B}` |
| LAW 3 | NO em-dashes/en-dashes. Use ` - ` (hyphen+spaces). | Quoted content preserves source dashes |
| LAW 4 | NO `##`/`###` headers. Bold-lead-in paragraphs only. | COMPARISON: 5 named headers allowed |
| LAW 5 | ENGINE FOOTER PASS-THROUGH — copy verbatim. | None |
| LAW 6 | NO raw ranked evidence clusters. Transform to prose. | None |
| LAW 7 | YOU are the planner. `--plan` mandatory on named entities. | None |
| LAW 8 | EVERY citation = inline markdown link. No raw URLs. | Plain-text fallback only when no URL |

### 차용할 패턴

| Pattern | Description |
|---------|-------------|
| **Output Laws as hard constraints** | 8개의 불가침 출력 규칙. 예외까지 명시. |
| **Named failure modes** | 각 규칙 위반 시 실제 실패 사례를 날짜+이름으로 기록 |
| **Self-check at multiple points** | Pre-synthesis, post-LAW 8, pre-presentation 3중 검증 |
| **Output contract moved to top** | 가장 중요한 형식 규칙을 최상단에 배치 |
| **Worked examples (BAD vs GOOD)** | 추상적 규칙 대신 실제 예시 쌍 제시 |
| **Skill Contract preface** | Do NOT improvise — 모델 임의 행동 제약 |

---

## 5. epoko77-ai/im-not-ai — Role Locking & AI-tell Removal

### 핵심 구조

12개 에이전트 파이프라인. Fast Mode(monolith, 5K이하) / Strict Mode(5-agent pipeline, 8K이상).

### Persona Crafting with Role Locking

| 에이전트 | 금지사항 (Role Lock) |
|---------|--------------------|
| Detector | "윤문·판단 금지" |
| Rewriter | "내용 보강·사실 확인·새 주장 추가 금지" |
| Auditor | "문체·리듬·자연스러움 평가 금지" |
| Reviewer | "직접 수정 금지" |

### Prime Directives (철칙)

1. **의미 불변** — Facts, numbers, proper nouns, quotes 100% 보존
2. **근거 기반** — Every edit maps to a detected span
3. **장르 유지** — Column→column, not column→literature
4. **과윤문 금지** — Change rate 30% warning, 50% abort
5. **Register 보존** — Formal in → formal out

### 차용할 패턴

| Pattern | Description |
|---------|-------------|
| **Role Locking** | 각 에이전트에 Do-NOT 리스트를 명시적으로 선언. 금지사항으로 역할 고정. |
| **Change Rate Self-Monitoring** | 30% 경고 / 50% 강제 중단 — 에이전트 스스로 과수정 감지 |
| **Self-Verification Checklist** | 작업 완료 후 N개 항목 자가 검증 (proper nouns preserved? change rate ≤30%?) |
| **Tool Call Budget** | monolith: 3회로 제한. 느린 이유가 모델 탓이 아니라 tool call 체인 때문이라는 발견 |
| **Multi-Agent Pipeline Tiers** | Fast: 단일 monolith, Strict: 5-agent sequential + parallel review |
| **Knowledge Separation by Purpose** | Taxonomy(분류) / Playbook(처방) / Quick-Rules(경량) 분리 |

---



## 1. garrytan/gbrain — Two-Layer Prompt Architecture

### 핵심 구조
```
CLAUDE.md (always-loaded, thin router) → RESOLVER.md (routing) → skills/<name>/SKILL.md (on-demand)
```

### 개별 SKILL.md 프롬프트 템플릿
```markdown
---
name: <skill-name>
version: <semver>
description: <한 문장>
triggers:
  - "<trigger phrase>"
tools:
  - <allowed tool>
mutating: true|false
writes_pages: true|false
writes_to:
  - people/
  - companies/
---

# Title

## Contract
{3-5 bullet guarantees}

## Phases
{numbered workflow steps}

## Output Format
{exact markdown template}

## Anti-Patterns
{what NOT to do, explicit negative constraints}
```

### 차용할 패턴
| Pattern | Description |
|---------|-------------|
| **Contract** | 검증 가능한 품질 보장. self-review 기준. |
| **Anti-Patterns** | 금지사항 명시. 부정적 제약 조건이 긍정 지시보다 효과적. |
| **Phased Workflow** | 단계별 사고 흐름으로 복잡도 분해. |
| **Iterative Protocol** | `test-before-bulk`: 작은 규모 검증 → 문제 수정 → 전체 실행. |
| **Conventions-as-Subprompts** | 공통 규칙을 별도 파일로 분리, 여러 skill이 참조. |

---

## 2. github/awesome-copilot — Agent Definition Standards

### .agent.md 프롬프트 구조
```yaml
# Required frontmatter
description: '<50-150 chars>'
# Recommended frontmatter
tools: [execute, read, edit, search, agent, web, todo]
model: 'Claude Sonnet 4'
# Optional frontmatter
user-invocable: true|false
disable-model-invocation: true|false
mode: primary|secondary
handoffs:
  - label: 'Plan'
    agent: 'plan-agent'
    prompt: 'Create plan'
```

### 차용할 패턴
| Pattern | Description |
|---------|-------------|
| **Identity-first** | 첫문장 정체성 선언 |
| **Principle of Least Privilege** | 필요한 도구만 허용 |
| **Coordinator/Worker 분리** | Orchestrator는 절대 직접 구현 안 함 |
| **Subagent Validation** | subagent self-report 절대 신뢰 금지 |
| **Handoff Chains** | VS Code handoffs로 순차 워크플로우 |

### Tool Aliases
| Alias | Purpose |
|-------|---------|
| `execute` / `shell` / `Bash` | Shell execution |
| `read` / `Read` / `view` | File reading |
| `edit` / `Edit` / `Write` | File editing |
| `search` / `Grep` / `Glob` | Code search |
| `agent` / `custom-agent` / `Task` | Invoke subagents |
| `web` / `WebSearch` / `WebFetch` | Web access |

---

## 3. dontriskit/awesome-ai-system-prompts — Real-World Prompt Collection

### Role Definition 패턴 (5가지)

| Pattern | Example | Source |
|---------|---------|--------|
| Identity + Creator | "You are v0, Vercel's AI-powered assistant." | v0 |
| Identity + Location | "You operate exclusively in Same..." | same.new |
| Identity + Capability Claim | "You are Devin, a software engineer..." | Devin |
| Identity + Persona | "You're a shipboard AI with the operational chops..." | Clawdbot |
| Identity + Task Scope | "You excel at: 1. Information gathering... 2. Data processing..." | Manus |

### Output Formatting 규칙

| 규칙 | 예시 |
|------|------|
| **XML/Markdown Sectioning** | `<tool_calling>`, `<communication>` tags |
| **Response Length Control** | "fewer than 4 lines", "Avoid introductions" |
| **Tool-Naming Prohibition** | "NEVER refer to tool names when speaking to the USER" |
| **Code Output Prohibition** | "NEVER output code to the USER, unless requested" |
| **No Emojis / Minimalism** | "Minimize emoji use" |

### Constraint Encoding 전략

| 전략 | 설명 |
|------|------|
| **Environment cap declaration** | "This environment cannot run pip/networking/Docker" upfront |
| **Approval tiers** | "Do without asking / Get approval before / Never do" |
| **Safety refusal protocol** | Explicit refusal templates for harmful requests |
| **Error loop limit** | "DO NOT loop more than 3 times on fixing linter errors" |
| **Working language enforcement** | "Default working language: English" |

### Task Decomposition 패턴

| System | Strategy |
|--------|----------|
| **Devin** | Planning mode vs Standard mode. Gather info → understand → suggest_plan → execute |
| **Manus** | Agent loop: Analyze → Select Tools → Wait → Iterate → Submit → Standby |
| **Cline** | PLAN MODE (ask questions) vs ACT MODE (implement). `plan_mode_respond` tool |
| **Trae** | 7-step: Understand → Explore → Reproduce → Debug → Implement → Verify → Summarize |

### 최고 참고 템플릿

1. **Manus Modules.md** — Modular multi-module agent prompt with Planner/Knowledge split
2. **Parahelp manager.md + planning.md** — Manager/worker orchestration with verification checklists
3. **Clawdbot (SOUL.md + IDENTITY.md)** — Persona-grounded multi-file prompt architecture
4. **Devin/system.md** — Comprehensive single-system prompt with mode switching + reasoning commands
5. **Cursor/Agent.md** — XML-sectioned prompt with maximize_context_understanding section

---

## 종합: Paperclip Prompt Architecture에 적용된 패턴

| Section | Origin | 목적 |
|---------|--------|------|
| **Core Identity** | awesome-ai-system-prompts | 첫문장 정체성 선언. 역할 즉시 인지 |
| **Contract** | gbrain | 검증 가능한 품질 기준. self-review 가능 |
| **Core Principles** | awesome-copilot | 행동 규칙. 의사결정 일관성 |
| **Workflow Phases** | gbrain + awesome-copilot | 단계별 사고 흐름. 복잡도 분해 |
| **Collaboration** | 신규 설계 (this session) | 형제 에이전트 간 업무 전달/에스컬레이션 |
| **Anti-Patterns** | gbrain + awesome-copilot | 부정적 제약 조건 |
| **Inference Level** | 신규 설계 (this session) | 작업 난이도 표시. 모델 기대치 설정 |
