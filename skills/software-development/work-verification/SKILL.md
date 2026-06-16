---
name: work-verification
description: "Verify every deliverable before reporting: execute → verify → auto-fix → report-final. All work, all tools, all contexts."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, quality-assurance, reporting, task-execution, workflow, closing-the-loop, source-authority]
    related_skills: [systematic-debugging, requesting-code-review, subagent-driven-development]
---

# Work Verification Protocol

## Core Principle

**Never report completion without verification.** Every output must be proven correct before it reaches the user. "Looks right" is not verification. The user sees only the final verdict: success with evidence, or failure with analysis.

## The Four-Step Flow

### 1. Execute
Do the work — code generation, file edits, script runs, API calls, research synthesis, config changes, any tool use.

### 2. Verify
Prove the work actually succeeded using **tool-specific verification techniques** (see below). Verification must be **objective and repeatable** — not "that looks right" but "file exists with expected content" / "command exited 0" / "API returned 200 with expected payload".

### 3. Auto-Fix
If verification failed:
- Diagnose the failure (follow `systematic-debugging` for complex issues)
- Fix the root cause, not the symptom
- Re-verify
- If 3+ attempts fail: **stop**, analyze the architecture/approach, and report to user

### 4. Report Final
Only now inform the user. Format:
- **Success** — concise statement of what was done + verification evidence
- **Failure** — what failed, why, and what alternative approach could work
- Never: "I'm working on it", "Let me check", "I'll try again", partial progress, or intermediate states

## Tool-Specific Verification Techniques

### File Operations (write_file, patch, read_file)

| Operation | Verification |
|-----------|-------------|
| write_file | `read_file(path)` → confirm content matches intent |
| patch | `read_file(path)` → confirm diff was applied correctly |
| search_files | For creation: search_files(pattern) for existence. For deletion: confirm file gone via terminal, not a guess |
| Bulk writes | Verify each critical file; spot-check the rest |

### Terminal Commands

| Operation | Verification |
|-----------|-------------|
| Install (apt, pip, npm) | `which <binary>` + `<binary> --version` |
| Build (make, go build) | Exit code 0 + binary exists |
| Script execution | Exit code 0 + expected output or side-effect |
| git commit | `git log --oneline -1` → confirm hash and message |
| docker/container | `docker ps` / `docker compose ps` → confirm running |

### delegate_task

**Self-reported success is NOT verification.** Subagents hallucinate success. Always follow up:

```python
# After delegate_task claiming "file created":
read_file("path/to/file")  # confirm exists with correct content

# After delegate_task claiming "API call succeeded":
terminal("curl -s <endpoint>")  # confirm side-effect

# After delegate_task claiming "test passed":
terminal("pytest <path> -q")  # re-run the test yourself
```

For critical operations (HTTP POST, remote writes, publishing), require the subagent to return a verifiable handle (URL, ID, absolute path, HTTP status) and verify it yourself.

**Post-delegate_task verification protocol (mandatory):**
1. Subagent returns self-report claiming success
2. Dispatch a **follow-up verification task** or use direct tools to prove the claim
3. Check: file exists? URL returns 200? DB has the expected record? Command output matches?
4. If verification is impossible (no way to check), disclose the limitation to the user — never claim verified success
5. For trading/broker operations specifically: use broker API polling to confirm order execution, not just order placement response

Example verification flow after a trading subagent:
```python
result = broker.buy(ticker, quantity, price)
if result.get("success") and result.get("order_id"):
    confirm = broker.confirm_order(result["order_id"])  # Poll until confirmed
    if not confirm.get("confirmed"):
        report.append("⚠️ Order submitted but not yet confirmed")
```

### Research / Synthesis

| Scenario | Verification |
|----------|-------------|
| Summarized a URL | Visit the URL yourself and confirm accuracy of key claims |
| Extracted data | Cross-check against original source |
| Compared options | Verify each option's claims independently |

## Provider / Model Integration Verification

**New AI provider or model integration requires two-stage verification — discovery ≠ execution.**

### Stage 1: Discovery Verification

Confirm the model/provider appears in the available list:

```bash
# CLI discovery
opencode models | grep <provider>

# Paperclip adapter discovery
curl /api/companies/:cid/adapters/<adapter>/models | jq '.[].id'

# API discovery (raw)
curl -H "Authorization: Bearer $KEY" $API_BASE/v1/models | jq '.data[].id'
```

Report only as: `[provider] 모델 목록 CLI 조회 완료 (N개)`.  
Do NOT report as "사용 가능" or "connected" based on discovery alone.

### Stage 2: Execution Verification

For each model intended for use, run a minimal functional test:

```bash
opencode run -m "<provider>/<model>" "Reply exactly 'ok'" 2>&1
```

**⚠️ 중요 — 환경별 실행 편차를 반드시 고려할 것:**
- **Desktop TUI**에서 실행한 결과와 **Headless Server CLI**에서 실행한 결과가 다를 수 있음
- `opencode-copilot-auth` 플러그인 사례: Desktop TUI에서 5개 Copilot 모델 정상 동작했으나, Headless Server의 `opencode run -m` CLI에서는 동일 모델이 빈 응답 반환
- **규칙**: 모델 검증은 반드시 최종 운영 환경에서 실행. Desktop에서만 확인된 모델을 서버 Paperclip에 연결하지 말 것.

**Result categories**:

| Observation | Status | Meaning |
|------------|--------|---------|
| `ok` or `OK` in output | ✅ Pass | Model executes and follows instructions |
| Exit 0, no response body | ⚠️ Unstable | Model starts but produces no output (ID mapping / API mismatch) |
| `model_not_supported` | ❌ Fail | API rejected the model name |
| `model_not_available_for_integrator` | ❌ Fail | Provider restricts model per integrator tier |
| `Model not found` | ❌ Fail | The prefixed ID doesn't match the API's expected name |
| Timeout / connection error | ❌ Fail | Network or auth issue |

### Stage 3: Paperclip/Platform Integration Verification

If the model passes execution, verify platform integration:

1. Create a Paperclip agent with the model via API
2. Assign a simple task to the agent
3. Check that the task gets picked up and completed
4. Verify the output

### Reporting Rule

**Separate discovery from execution in every report.** Never combine:

```python
# ❌ WRONG — discovery ≠ execution
"Copilot 통합 완료! 25개 모델 사용 가능"

# ✅ RIGHT — separated stages with honest status
"Copilot 모델 discovery 완료: CLI 25개 확인. "
"실행 테스트: 5개 모델 테스트 — 0개 통과, 3개 API 거부, 2개 응답 없음. "
"아직 안정적 실행 불가, 플러그인 업데이트 대기."
```

**Also separate execution environment in every report.** Desktop TUI ≠ Headless Server:

```python
# ❌ WRONG — 환경 무시
"Copilot 5개 모델 사용 가능 확인 완료"

# ✅ RIGHT — 환경 구분
"Desktop TUI에서 Copilot 5개 모델 실행 확인: "
"  claude-haiku-4.5, gemini-3-flash-preview, gemini-3.1-pro-preview, "
"  gpt-5-mini, gpt-5.4-mini ✅\n"
"Headless Server CLI에서는 동일 5개 모델 빈 응답 ⚠️\n"
"Paperclip + opencode_local 서버 연동은 추가 검증 필요."
```

### Cronjob Operations

| Scenario | Verification |
|----------|-------------|
| Created a job | `cronjob(action='list')` → confirm job_id, schedule, script exist |
| Script install | `cat <script_path>` or run dry-run |
| Context chain | Verify upstream jobs exist and produce expected output |

### API / MCP Tool Calls

| Operation | Verification |
|-----------|-------------|
| turn_on / turn_off | Follow-up `get_state` or list_devices |
| send_message | Confirm target and content are correct before sending |
| Any state mutation | Read back state after mutation |

## MCP-Based Verification (Harness Engineering Pattern)

The most powerful verification technique from the "harness engineering" playbook: **use MCP tools as an automated verification layer** so AI can directly confirm its own work outcomes instead of relying on self-reports.

### When to Use MCP for Verification

| Scenario | MCP Approach | Why |
|----------|-------------|-----|
| Web app changes | `mcp_playwright_*` / `mcp_browser_*` — navigate, screenshot, assert DOM | AI sees the actual rendered output, not just code |
| API changes | `mcp_http_*` — curl the endpoint, check response | Confirms runtime behavior, not just compile |
| File changes | `mcp_filesystem_*` — read back, check content | More structured than raw terminal |
| Smart home | `mcp_homeassistant_*` — get_state after set | Confirms actual device state |
| GitHub | `mcp_github_*` — verify PR/issue after creation | Confirms remote state |

### Verification Pattern: Browser-Based (Chrome DevTools / Playwright MCP)

For frontend/coding tasks, add a **browser MCP** (Playwright or Puppeteer) and use it to verify that rendered output matches expectations:

```python
# After coding a feature, use browser MCP to verify:
# 1. Navigate to the page
# 2. Take a screenshot
# 3. Assert specific elements exist
# 4. Confirm no JS console errors

# Example: verify a web app feature
# mcp_playwright_navigate(url="http://localhost:3000")
# mcp_playwright_screenshot() → visible proof
# mcp_playwright_evaluate(script="document.querySelector('.result').textContent")
```

### Verification Pattern: HTTP / API MCP

```python
# After deploying an API or webhook:
# mcp_http_get(url="http://localhost:PORT/health")
# → confirm 200 + expected response body

# After creating a resource via API:
# mcp_http_get(url="http://localhost:PORT/api/resource/ID")
# → confirm resource exists with expected fields
```

### Home Assistant MCP (existing — enhanced)

```python
# After turn_on:
# mcp_homeassistant_get_state(entity_id='light.X')
# → Confirm state == 'on'

# After automation setup:
# mcp_homeassistant_get_automation(automation_id='X')
# → Confirm triggers and actions
```

## Source Authority Verification

When providing **technical specifications** (model lists, API capabilities, pricing, version numbers):

1. **Official website FIRST** — When the user asks about a platform's capabilities, open the official website/docs in a browser or `curl` the URL before consulting CLI tools or API endpoints. CLI output often shows a subset or uses different naming conventions.
2. **If user says "this is wrong"** → immediately visit the **official source URL** and re-verify. Do NOT try a different CLI flag or API call first — the official website is the source of truth.
3. **Cross-reference documentation with actual behavior** — Docs may list models that aren't available on your specific plan. Always verify by running an actual test command against the available API.
4. **Preferred sources by domain:**
   | Domain | Official Source |
   |--------|----------------|
   | GitHub Copilot models | `docs.github.com/en/copilot/reference/ai-models/supported-models` |
   | OpenCode models/pricing | `opencode.ai/docs/ko/go` |
   | Docker images | `hub.docker.com` |
   | Python packages | `pypi.org` |
   | Node packages | `npmjs.com` |

4. **Do NOT** infer model lists from CLI `--list-models` output alone — CLI may show only a subset or use different naming
5. **Do NOT** assume similarity between different API providers (e.g., GitHub Models ≠ Copilot Pro)

## Behavior Correction Protocol (하네스 엔지니어링 핵심)

When AI repeatedly makes the same mistake (hallucinates file creation, sets wrong font sizes, ignores instructions), use the **Behavior Correction Protocol** from the harness engineering playbook:

### Step 1: Detect the Pattern
During auto-fix (step 3), if you encounter the **same failure more than once**, stop and ask: *"Is this a recurring behavioral problem?"*

### Step 2: Record the Correction
Save the behavioral rule where the AI will read it next time:

```python
# Option A: Memory (for user-level, cross-session behavior)
memory(action='add', target='memory', content='When doing X, always Y. Do NOT Z.')

# Option B: Skill (for task-specific, reusable protocol)
# Add to the relevant skill's pitfall or instruction section:
# "When doing X: always verify Y first. Never skip Z."
```

### Step 3: Create/Update a Correction Rule
Format: **Context + Trigger + Forbidden Behavior + Correct Behavior**

```
[Context: PowerPoint generation]
[Trigger: AI creates slides with font sizes]
[Forbidden: Setting body font < 18pt or heading font < 28pt]
[Correct: Body=20pt, Heading=32pt minimum]

[Context: delegate_task claiming success]
[Trigger: Subagent reports "task complete"]
[Forbidden: Accepting without file/content verification]
[Correct: Always read_file() or curl to confirm side-effects]
```

### Step 4: Verify the Correction Works
- Re-run the task
- Confirm the AI now follows the corrected behavior
- If still failing, the rule needs to be more specific or placed in a higher-priority location (SKILL.md > memory > AGENTS.md)

### When to Use Each Correction Location

| Location | Best For | Priority |
|----------|----------|----------|
| `SKILL.md` | Task-specific recurring pitfalls | Highest — loaded on skill use |
| `memory` | User preferences, environment facts | High — loaded every session |
| `AGENTS.md` / `CLAUDE.md` | Project-specific conventions | Medium — project-root level |
| System prompt override | Fundamental behavior issues | Highest — but hard to maintain |

## Verification by Work Type

### Single-file, Simple Task (e.g. one write_file)
- Verify the file exists with `read_file`
- Quick content scan for correctness
- **Report** — "Done. Created `path/to/file` with [brief summary]."

### Multi-step, Multi-file (e.g. feature implementation)
- Verify each step as you go
- At the end: full test suite, git diff review
- **Report** — "Feature X complete. Tests: 45/45 pass. Files: A, B, C modified. Summary of changes."

### Recurring / Cron (e.g. scheduled report)
- Run it once manually to verify output
- Confirm cron entry exists with correct schedule
- **Report** — "Scheduled daily at 09:00 KST. Test run produced correct output. [attach sample if notable]."

### Installation / Setup (e.g. package, service)
- Verify binary exists (`which`)
- Verify version (`--version`)
- Verify expected files exist in expected locations
- **Report** — "Installed X v1.2.3. Binary at /usr/bin/X. Service running on port 8080."

### Remote / Deploy (e.g. git push, server deploy)
- Verify remote state matches intent (SSH back, curl endpoint)
- Confirm CI/CD pipeline initiated (if applicable)
- **Report** — "Deployed to production. `curl https://...` returns 200. Git SHA: abc123."

## Pitfalls

- **"Looks right" syndrome** — Don't read the file you just wrote and say "looks good". Prove it. Check syntax. Run the tool that consumes it.
- **"Discovery = Execution" fallacy** — A model appearing in `opencode models` or a Paperclip adapter's model list does NOT mean it can execute tasks. Always run `opencode run -m <model> "Reply exactly 'ok'"` to confirm actual execution. Concrete example from this session: Copilot 25개 모델이 CLI에 조회되었고 Paperclip adapter도 반환했으나, 실제 실행 테스트에서 5개 Desktop TUI 통과, 나머지 전멸. 환경(Desktop TUI vs Headless Server)에 따라 결과가 달라질 수 있으므로 최종 운영 환경에서 검증할 것.
- **Silent command failures** — A command can exit 0 but do nothing (e.g. `pip install` of a non-existent package that resolves locally). Verify the side-effect, not just the exit code.
- **delegate_task trust trap** — Subagents always claim success. Always follow up. File not found? URL 404? The subagent was wrong.
- **Over-verification** — Don't verify every character. The goal is not perfection, it's proving the intended outcome happened. Proportion effort to risk.
- **Verification itself had a bug** — If verification says FAIL but the work is correct, check your verification method. Is the file path right? Is the test command right?
- **False positive verification** — Reading a file and seeing what you expect to see, when the file actually contains something subtly different. Use diff or structured parsing when exactness matters.
- **Reporting partial progress** — If verification found an issue, fix it before reporting. "I tried X but Y failed and I'm now trying Z" is not final.
- **Forgetting to verify non-file outputs** — Did you `send_message` to the right channel? Did the cron fire? Did the lights turn on? Verify platform-specific effects too.

## Integration with Other Skills

**systematic-debugging** — When auto-fix fails (step 3), use systematic-debugging's 4-phase approach to find root cause before trying again.

**requesting-code-review** — For git changes, run the full pre-commit verification pipeline instead of ad-hoc checks.

**subagent-driven-development** — After each subagent task, apply verification before marking todo complete.

## References

- **`references/verification-patterns.md`** — Expanded catalog of verification techniques per tool and scenario, with concrete commands.
- **`references/harness-engineering.md`** — The three-level Harness Engineering framework (L1 agent-mod, L2 MCP/Skill, L3 prompt/config) with tradeoff guide. From the YouTube 하네스 엔지니어링 deep-dive.
