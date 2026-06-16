# AGENTS.md — Knowledge Agent 의사결정 가이드

## 1. 파이프라인 실행 워크플로우

### Phase 1: Raw Data → Wiki (Pattern 3)

```
Pre-flight: 00_Raw/ flat files + 01_Parsed/ 전체 디렉토리 목록
  → state 파일(processed_raw.json, wiki_state.json)과 교차 참조
  → 미처리 파일 식별
  → README 구조 파일 필터링 (10_Wiki/*/README.md, 00_Raw/README.md 제외)
  → 외부 프로젝트 README는 콘텐츠로 처리
  → 분류 + 요약 → 10_Wiki/ 적절한 카테고리에 저장
  → state 파일 업데이트
```

### Phase 2: Session Distillation (Pattern 6)

```
session_distill_prep.py 실행 → unprocessed 세션 목록
  → 각 세션에 대해:
      Owner(delegate_task, flash, researcher) → 초안 마크다운 + 다축 frontmatter
      Reviewer(delegate_task, v4-pro, researcher) → 팩트체크 + PASS/FAIL
      FAIL 시 최대 3회 루프 → 3회 FAIL 시 메트릭 기록 + 스킵
      PASS → 10_Wiki/에 저장
  → distillation_metrics.jsonl 업데이트
  → session_distillation_state.json 업데이트
```

### Phase 3: Reconciliation

```
Direction A: wiki 파일은 있지만 state 파일에 없음 → reconciled/ 키로 추가
Direction B: wiki_state.json에는 있지만 processed_raw.json에 없음 → 추가
Direction C: processed_raw.json에는 있지만 wiki_state.json에 없음 → 추가
  → total_processed == len(processed) 검증
  → last_run 갱신
```

### Phase 4: Git Commit

```
cd ~/second_brain
git add -A
git commit -m "wiki: pipeline run $(date +%Y-%m-%d)"
git pull --rebase origin main
# 충돌 시: last_run/updated_at은 더 최신 타임스탬프 유지
git push
```

## 2. delegate_task 사용 규칙

### Owner Subagent
```
delegate_task(
  model="deepseek-v4-flash",
  context=_harness.md + _gbrain.md + researcher.md + 세션 메시지,
  toolsets=["file"],
  goal="세션에서 지식 추출 및 다축 frontmatter 초안 작성"
)
```

### Reviewer Subagent
```
delegate_task(
  model="deepseek-v4-pro",
  context=_harness.md + _gbrain.md + researcher.md + Owner 초안,
  toolsets=["file", "web"],
  goal="Owner 초안 팩트체크, 중복 검출, frontmatter 검증"
)
```

### 모델 선택 근거
- **Owner = flash**: 초안 작성은 속도가 중요, 팩트체크는 Reviewer가 담당
- **Reviewer = v4-pro**: 정확성과 누락 탐지가 핵심, flash로는 부족

## 3. 저가치 세션 필터링

다음 세션은 `verdict: SKIPPED` + `reason` 필드와 함께 `session_distillation_state.json`에 기록:

| 패턴 | reason |
|------|--------|
| cron 실행 로그 (apt update, docker cleanup, power monitoring) | "cron_execution_log" |
| 콘텐츠 전달 cron (TOEIC, 자기개발 루틴, 예약 보고서) | "content_delivery_cron" |
| wiki-pipeline 자체 실행 세션 (cron_1e76dfe1ca7b_*) | "pipeline_self_run" |
| ≤3 user+assistant 메시지 + 기술/의사결정 내용 없음 | "trivial_interaction" |

## 4. 주요 Pitfall (second-brain 스킬에서 발췌)

### State File Key Format
| Source | wiki_state.json key | processed_raw.json key |
|--------|-------------------|----------------------|
| `01_Parsed/YYYY-MM-DD/.../file.md` | `YYYY-MM-DD/.../file.md` | `01_Parsed/YYYY-MM-DD/.../file.md` |
| `00_Raw/YYYY-MM-DD.md` | `YYYY-MM-DD.md` | `00_Raw/YYYY-MM-DD.md` |
| `session/...md` | `session/...md` | `session/...md` |

### Owner Subagent Pitfall
- **잘못된 경로에 저장**: `~/.hermes/wiki/`, `~/job_wiki/` 등 → 반드시 `~/second_brain/10_Wiki/`로 이동
- **테이블 산술 오류**: 행 합계 ≠ 표시된 합계 → Reviewer가 독립 검증
- **frontmatter 오류**: `세션-기록`(→decision), `완료`(→stable) 등 잘못된 enum 값 → Reviewer가 수정

### Git 충돌
- `git pull --rebase` 먼저 실행
- `last_run`, `updated_at` 충돌 시 더 최신 값 유지
- `ingest_state.json` 충돌 시 자신의 출력 우선, 중복 커밋은 `git rebase --skip`

### find -newer 함정
- 파일 mtime과 wiki_state.json의 mtime이 다를 수 있음
- 항상 전체 디렉토리 목록(`find ... -name '*.md' | sort`)을 1차 체크로 사용

## 5. Scope 제한

### ✅ 허용
- `~/second_brain/` 전체 (읽기/쓰기)
- `~/.hermes/roles/` (읽기만, delegate_task context 주입용)
- `~/.hermes/state.db` (읽기만, session_distill_prep.py용)

### ❌ 금지
- `~/.hermes/SOUL.md`, `~/.hermes/AGENTS.md` (Hermes Agent 설정)
- `~/.hermes/profiles/meta-optimizer/` (Meta-Optimizer 영역)
- `~/.hermes/skills/` (스킬 직접 수정 금지 — Meta-Optimizer가 제안)
- 크론 job prompt 직접 수정
