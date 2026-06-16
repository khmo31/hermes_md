# Knowledge Distillation Pipeline — 설계 명세

> cron job: `second-brain-wiki-pipeline` (매일 21:00 UTC)
> skill: `second-brain`
> model: `deepseek-v4-pro` (orchestrator)

---

## 1. 아키텍처 개요

```
Phase 1 (Pipeline A)          Phase 2 (Pipeline B)
외부데이터 → 00_Raw/01_Parsed  state.db 세션 → 10_Wiki
        ↓                              ↓
   wiki_state.json              Owner-Reviwer-Harness 루프
        ↓                              ↓
    10_Wiki/                     10_Wiki/ (다축 frontmatter)

                    Phase 3
              State Reconciliation
              (3방향 A/B/C 정합성)
                    ↓
              Git commit + push
```

Phase 1과 Phase 2는 **순차 실행**되지만 **독립적**이다. Phase 1 실패가 Phase 2를 막지 않는다.

---

## 2. Owner-Reviewer-Harness 상태기계

```
START
  │
  ▼
[Owner: 세션 분석 → 초안 작성]  ←──────────────┐
  │ (deepseek-v4-flash, researcher.md)        │
  ▼                                            │
[Reviewer: 팩트 체크 + 중복 검증]               │ 수정 요청
  │ (deepseek-v4-pro, researcher.md)          │ (최대 2회)
  ├── PASS → [커밋]                            │
  ├── FAIL + loop < 3 → [Owner 재수정] ────────┘
  └── FAIL + loop ≥ 3 → [최고 점수 버전 채택 → 커밋]
```

### Harness (크론 에이전트 자신) 책임

```python
MAX_LOOPS = 3
loop_count = 0
best_version = None
best_score = 0

while loop_count < MAX_LOOPS:
    draft = delegate_task(owner_goal, owner_context, model="deepseek-v4-flash")
    verdict = delegate_task(reviewer_goal, reviewer_context, model="deepseek-v4-pro")
    score = calculate_score(verdict)  # PASS=1, FAIL with fixes=0.5, FAIL vague=0

    if score > best_score:
        best_version = draft
        best_score = score

    if verdict == "PASS":
        break  # 수락

    loop_count += 1
    # Reviewer의 수정 지침을 Owner context에 추가

# 종료: best_version 또는 마지막 draft를 커밋
commit_to_wiki(best_version or draft)
```

### 결정론적 통제

- 루프 상한: Harness가 `loop_count`로 통제. LLM에게 위임 금지.
- 타임아웃: 각 delegate_task는 300초 제한. 초과 시 현재 best_version 채택.
- 토큰 제한: Owner 출력 4000자 초과 시 truncate + 경고.

---

## 3. Context Packing

### 세션 메시지 → Owner 전달

```python
MAX_MSG_CHARS = 2000  # 메시지당 상한
MAX_TOTAL_MSGS = 30   # 세션당 최대 메시지 수

for msg in reversed(messages):  # 최근 메시지 우선
    if msg['role'] in ('user', 'assistant'):
        packed.append({
            'role': msg['role'],
            'content': msg['content'][:MAX_MSG_CHARS],
            'truncated': len(msg['content']) > MAX_MSG_CHARS
        })
    if len(packed) >= MAX_TOTAL_MSGS:
        break
```

### 전달 규칙

- tool 메시지는 제외 (노이즈)
- 최근 메시지 우선 (시간 역순)
- 2000자 초과 시 절단 + `[truncated]` 마커
- 절단된 메시지가 있으면 Reviewer에게 "원문 일부 손실 가능성"을 context로 전달

> **MVP 기본값. metrics 기반으로 조정 예정.**

---

## 4. state.db 동시성 정책

### 현재 환경

- `~/.hermes/state.db`: SQLite 3, WAL 모드 활성화
- Hermes Agent: 읽기/쓰기
- Pipeline cron: **읽기 전용**

### WAL 안전성

SQLite WAL 모드는 동시 읽기를 허용한다. Pipeline cron이 읽는 동안 Hermes가 쓰기 가능.

```python
import sqlite3
conn = sqlite3.connect("file:/path/to/state.db?mode=ro", uri=True)  # 읽기 전용
conn.execute("PRAGMA busy_timeout = 5000")  # 5초까지 대기
conn.execute("PRAGMA journal_mode = WAL")   # WAL 확인
```

### 실패 시 대응

1. DB locked → 5초 busy_timeout 후 retry
2. 3회 retry 실패 → "DB 접근 불가" 로그 + 이번 실행 건너뛰기
3. 다음 cron 실행에서 미처리 세션 재시도 (session_distillation_state.json 기반 idempotent)

---

## 5. Pipeline A/B 통합 정책

### 실행 순서

```
Phase 1 (Pipeline A): Raw Data 처리
  → 실패 시: Phase 2로 진행 (독립적)
Phase 2 (Pipeline B): Session Distillation
  → 실패 시: Phase 3으로 진행
Phase 3: Reconciliation + Metrics + Git
```

### Idempotency

- Phase 1: `processed_raw.json` + `wiki_state.json`으로 중복 처리 방지
- Phase 2: `session_distillation_state.json`으로 처리된 세션 ID 추적
- Phase 3: Direction A/B/C reconciliation으로 정합성 복구

### Timeout Budget

Pipeline A와 Pipeline B는 **별도 cron으로 분리**한다. 단일 cron 통합은 context overflow로 Phase 2가 silent-skip 되는 문제가 확인되었다.

```
Cron 1: Pipeline A + Phase 3 (21:00 UTC, 예상 10분)
  Phase 1 (Pipeline A): Raw Data 처리
    → 실패 시: Phase 3으로 진행 (독립적)
  Phase 3: Reconciliation + Metrics + Git

Cron 2: Pipeline B + Phase 3 (21:20 UTC, 예상 35분)
  Phase 2 (Pipeline B): Session Distillation
    → 실패 시: Phase 3으로 진행
  Phase 3: Reconciliation + Metrics + Git
```

- Cron 2는 `scripts/session_distill_prep.py`의 출력이 `{"status": "no_new_sessions"}`이면 Phase 3만 실행 후 조기 종료
- Phase 3은 양 cron에서 모두 실행하여 state file 정합성을 유지 (idempotent)

초과 시 처리된 것까지만 커밋하고 다음 실행에 나머지 위임.

---

## 6. 모델 선택 근거 (MVP 가설)

| 역할 | 모델 | 선택 이유 | 예상 비용/세션 |
|------|------|----------|--------------|
| Owner | `deepseek-v4-pro` | 초안 품질이 Reviewer의 교정 부담과 루프 횟수를 결정. flash의 분류 오류(domain 오분류, invalid frontmatter, table 합계 불일치)로 인한 재작업 비용이 flash의 단가 이점을 상쇄함. | ~$0.01 |
| Reviewer | `deepseek-v4-pro` | 팩트 체크 + 중복 검증은 정확도가 필수. | ~$0.01 |
| Orchestrator | `deepseek-v4-pro` | 분할 판단, 컨텍스트 구성, 루프 제어는 고품질 추론 필요. | ~$0.005 |

> **Owner 모델 downgrade 조건:** 다음 조건이 모두 충족되면 `deepseek-v4-flash`로 재전환 검토.
> 1. metrics.jsonl 50건 이상 누적
> 2. pro Owner 기준 avg_loops ≤ 1.2
> 3. Reviewer PASS rate (1차 통과율) ≥ 80%
> 위 조건 충족 시 flash로 A/B 테스트 (25건씩) → 통계적 유의미성 확보 후 전환.

---

## 7. Meta-Optimizer Profile 격리 검증

### 설계

Meta-Optimizer는 `hermes --profile meta-optimizer`로 실행되며, 루트 `~/.hermes/SOUL.md`/`AGENTS.md` 대신 `~/.hermes/profiles/meta-optimizer/`의 파일만 로드한다.

### 검증 절차

```bash
# 1. profile context dump
hermes --profile meta-optimizer --print-context > /tmp/meta_context.txt

# 2. 루트 SOUL/AGENTS 미포함 확인
grep -c "Hermes Agent — 핵심 정체성" /tmp/meta_context.txt
# 기대값: 0 (루트 SOUL.md의 정체성 문구가 없어야 함)

grep -c "Meta-Optimizer" /tmp/meta_context.txt
# 기대값: ≥ 1 (profile SOUL.md의 정체성만 있어야 함)

# 3. instruction merge 정책 확인
# Profile이 명시적으로 root의 instruction을 상속하지 않도록 config.yaml에 설정
# merge_strategy: replace (기본값)
```

### Cron 실행 시 격리

cron job `meta-optimizer-weekly`는 `profile="meta-optimizer"`로 등록되어 있어, cron 스케줄러가 자동으로 해당 profile의 SOUL/AGENTS/config를 로드한다. 루트 설정과의 혼합은 발생하지 않는다.

---

## 8. Phase 4: Legacy Folder Migration (1회성)

기존 folder-based Wiki 파일(105개)을 flat + multi-axis frontmatter로 변환하는 일회성 작업.

### 변환 대상
- `10_Wiki/{Decisions,Topics,Projects,Guides,Skills,Meetings,Postmortems,RFCs,Releases}/` 아래 모든 `.md`

### 폴더 → type 매핑
| Legacy Folder | `type` 값 |
|---------------|----------|
| `Decisions/` | `decision` |
| `Topics/` | `topic` |
| `Projects/` | `project` |
| `Guides/` | `guide` |
| `Skills/` | `skill` |
| `Meetings/` | `meeting` |
| `Postmortems/` | `postmortem` |
| `RFCs/` | `rfc` |
| `Releases/` | `release` |

### 변환 로직 (`scripts/migrate_legacy_to_flat.py`)
- `domain`: 파일명/내용 키워드 기반 휴리스틱 분류 + `general` fallback
- `status`: mtime > 90일 → `deprecated`, 그 외 → `stable` (수동 검토 대상 마킹)
- `source`: `legacy-migration`
- `date`: 파일의 git 최초 커밋일
- 출력: flat `10_Wiki/<원본파일명>.md` + frontmatter 삽입
- 원본 legacy 폴더는 `.legacy_backup/`로 이동 (삭제 아님)

### 실행 절차
```bash
# Step 1: Dry-run — 변환 대상 확인 (파일 이동 없음)
python3 scripts/migrate_legacy_to_flat.py --dry-run

# Step 2: 실제 변환 실행
python3 scripts/migrate_legacy_to_flat.py --execute

# Step 3: 검증 — grep으로 모든 파일에 frontmatter 존재 확인
missing=$(find ~/second_brain/10_Wiki/ -name '*.md' -type f \
  -not -path '*/README.md' \
  -exec sh -c 'head -1 "$1" | grep -q "^---$" || echo "$1"' _ {} \;)
if [ -n "$missing" ]; then
  echo "ERROR: Missing frontmatter in: $missing"
  exit 1
fi
```

### Post-Migration
- frontmatter 누락 파일 0건 확인
- `wiki_state.json`의 모든 legacy 경로를 새 flat 경로로 업데이트
- git commit + push
- legacy 폴더 구조를 `.legacy_backup/`에서 30일 후 삭제
