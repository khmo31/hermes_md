# Session Distillation Pipeline (Pipeline B)

> cron: `second-brain-wiki-pipeline` Phase 2
> state: `session_distillation_state.json`, `distillation_metrics.jsonl`

## Architecture

```
state.db (WAL mode, read-only)
  → 완료 세션 조회 (end_reason=session_reset|cron_complete)
  → session_distillation_state.json 교차 참조 (미처리만)
  → Owner (deepseek-v4-flash, researcher.md) → 초안
  → Reviewer (deepseek-v4-pro, researcher.md) → PASS/FAIL
  → Harness (Python, max 3 loops) → 10_Wiki/ 커밋
  → metrics 기록 + git push
```

## State DB Access

```python
import sqlite3
conn = sqlite3.connect("file:~/.hermes/state.db?mode=ro", uri=True)
conn.execute("PRAGMA busy_timeout = 5000")
# WAL mode allows concurrent reads
```

## Context Packing

- Messages: user+assistant only (tool excluded)
- Per message: max 2000 chars with `[truncated]` marker
- Per session: max 30 messages, recent-first

## Decision Log (MUST)

Each delegate_task call in the pipeline logs:
```
## Decision Log — delegate_task
- split_trigger: [true/false]
- trigger_reason: [조건 해당 사항]
- model: [선택 근거]
- toolsets: [선택]
```
