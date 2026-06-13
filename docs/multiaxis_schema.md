# 다축 분류 시스템 — Schema & Taxonomy

> 적용 대상: Second Brain Wiki Pipeline (`second-brain-wiki-pipeline` cron)
> 모든 위키 노트는 frontmatter 기반 다축 분류를 따른다.

---

## 1. Frontmatter Schema

```yaml
---
type: decision|topic|guide|project|skill    # 필수: 콘텐츠 유형
domain: trading|ai-ml|devops|smarthome|hermes|toeic|general  # 필수: 지식 영역
status: draft|stable|deprecated            # 필수: 성숙도
source: session|research|external          # 자동: 출처
tags: [tag1, tag2]                         # 선택: 세부 태그
session: session_id                        # 자동: 세션 출처 (source=session일 때만)
date: YYYY-MM-DD                           # 필수: 생성일
---
```

### 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `type` | enum | ✅ | 콘텐츠의 본질적 유형 |
| `domain` | enum | ✅ | 지식이 속한 영역. 복수 도메인은 tags로 처리 |
| `status` | enum | ✅ | 노트의 생애주기 단계 |
| `source` | enum | 자동 | 파이프라인이 자동 판단 |
| `tags` | string[] | 선택 | 자유 형식 태그. 쉼표 구분 |
| `session` | string | 자동 | 원본 Hermes 세션 ID |
| `date` | date | ✅ | YYYY-MM-DD 형식 |

---

## 2. Type (콘텐츠 유형)

| 값 | 정의 | 포함 기준 | 예시 |
|----|------|----------|------|
| `decision` | 기술 선택, 아키텍처 결정, 트레이드오프 판단 | "A vs B 선택" 구조가 명확할 때 | "FastAPI vs Flask 선택", "PostgreSQL 마이그레이션 결정" |
| `topic` | 개념 설명, 기술 조사 결과, 학습 내용 | 설명/분석이 주된 목적일 때 | "RAG 아키텍처 정리", "LLM 평가 벤치마크 분석" |
| `guide` | 설정 방법, 워크플로우, 튜토리얼 | 단계별 지침이 포함될 때 | "Home Assistant MQTT 연동", "Hermes 크론 설정법" |
| `project` | 프로젝트 진행 상황, 작업 내역 | 특정 프로젝트의 상태/이력일 때 | "Moltbook 리포트 현황", "TradingAgent 개발 로그" |
| `skill` | 반복 가능한 작업 패턴, 자동화 워크플로우 | 재사용 가능한 절차일 때 | "multi-agent-orchestration 활용법" |

### Tie-breaker

1. 결정이 포함되어 있으면 → `decision` (다른 유형보다 우선)
2. 단계별 지침이면 → `guide`
3. 특정 프로젝트 추적이면 → `project`
4. 나머지는 → `topic`

---

## 3. Domain Taxonomy

### domain: trading

- **포함**: 트레이딩 시스템, KIS API, 자동매매, 주식/선물/옵션, 백테스팅, 포트폴리오
- **제외**: 일반 금융 이론 (→ ai-ml 또는 general)
- **경계선 예시**:
  - "KIS API 에러 핸들링" → trading
  - "Python retry 패턴" → general (도메인 독립적 패턴)

### domain: ai-ml

- **포함**: AI/ML 모델, LLM, 프롬프트 엔지니어링, 임베딩, 파인튜닝, 평가
- **제외**: Hermes Agent 설정 (→ hermes), AI 도구 사용법 (→ 해당 도메인)
- **경계선 예시**:
  - "RAG 파이프라인 설계" → ai-ml
  - "Hermes에 RAG 통합하기" → hermes

### domain: devops

- **포함**: 서버 관리, Docker, Kubernetes, CI/CD, 배포, 인프라, 네트워크
- **제외**: SmartHome Docker 설정 (→ smarthome)
- **경계선 예시**:
  - "Docker 컨테이너 최적화" → devops
  - "HA Docker 설정" → smarthome

### domain: smarthome

- **포함**: Home Assistant, MQTT, IoT 기기, OpenHue, 자동화
- **제외**: 일반 Docker/서버 설정 (→ devops)
- **경계선 예시**:
  - "HA 자동화 yaml" → smarthome
  - "MQTT 브로커 보안" → devops (프로토콜 레벨)

### domain: hermes

- **포함**: Hermes Agent 설정, 스킬, 크론, delegate_task, profile, SOUL/AGENTS
- **제외**: LLM 일반 이론 (→ ai-ml)
- **경계선 예시**:
  - "delegate_task model override" → hermes
  - "LangGraph supervisor pattern" → ai-ml

### domain: toeic

- **포함**: 영어 학습, 토익 전략, LC/RC 팁, 오답 분석
- **제외**: 일반 영어 문법 (→ general)

### domain: general

- **포함**: 위 6개 도메인에 명확히 속하지 않는 모든 것
- **제한**: `general` 사용 빈도가 20%를 초과하면 도메인 정의 재검토 필요

---

## 4. Status Lifecycle

```
draft ──(검증 완료)──▶ stable ──(정보 노후화)──▶ deprecated
  │                        │
  └──(방치 90일)──▶ deprecated
```

| 전환 | 조건 | 액션 |
|------|------|------|
| `draft → stable` | Reviewer 2회 연속 PASS + 생성 7일 경과 | status: stable, 검증일 갱신 |
| `stable → deprecated` | 내용이 더 이상 정확하지 않음 + 대체 노트 존재 | status: deprecated, superseded_by 링크 추가 |
| `draft → deprecated` | 90일 이상 방치 + 검증 시도 없음 | status: deprecated, reason: "stale" |
| `deprecated → stable` | 불가. 새로운 노트로 재작성 | — |

### 추가 메타데이터 (stable 전환 시)

```yaml
verified_date: YYYY-MM-DD
verified_by: reviewer_session_id
superseded_by: "[[다른 노트 제목]]"  # deprecated일 때만
deprecation_reason: "stale|superseded|inaccurate"
```

---

## 5. 검색 효율 비교

### 폴더 기반 (현재)

```bash
# "트레이딩 관련 결정" 검색
grep -ril "트레이딩\|trading" ~/second_brain/10_Wiki/Decisions/
# → Decisions/ 폴더 전체 스캔 후 내용 grep → 2 pass
```

### Frontmatter 기반 (변경 후)

```bash
# "트레이딩 도메인의 모든 결정" 검색
grep -rl "domain: trading" ~/second_brain/10_Wiki/ | xargs grep -l "type: decision"
# → frontmatter 먼저 필터 → 내용 grep → 결과 수 최소화

# "stable 상태의 AI-ML topic 중 RAG 관련"
grep -rl "domain: ai-ml" ~/second_brain/10_Wiki/ | \
  xargs grep -l "type: topic" | \
  xargs grep -l "status: stable" | \
  xargs grep -il "RAG"
# → 축 따라 순차 필터링 → 정확도 ↑
```

### 정량 비교 (가상)

| 시나리오 | 폴더 기반 | Frontmatter 기반 |
|----------|----------|-----------------|
| "trading 결정" | Decisions/ 45개 전수 grep | frontmatter 필터 후 12개 grep |
| "AI-ML stable topic" | Topics/ 69개 전수 grep | 3축 필터 후 8개 grep |
| "deprecated 노트 찾기" | 전체 폴더 grep "DEPRECATED" (비정형) | `grep -rl "status: deprecated"` (정형) |

---

## 6. 예시 노트

```markdown
---
type: decision
domain: trading
status: stable
source: session
tags: [kis-api, error-handling, retry-logic]
session: 20260611_122817_5533c405
date: 2026-06-12
---

# KIS API 잔고 조회 실패 시 재시도 로직 적용

## 결정 내용
KIS API 일시적 장애에 대비해 run_swing_monitor에 최대 3회 재시도 로직을 추가.

## 배경
trading-swing-monitor-14(14:00 KST)의 잔고 조회가 KIS API 일시적 오류로 실패.
동일 스크립트를 쓰는 11:00 모니터는 정상 작동.

## 적용
- max_retries=2 (최대 3회 시도)
- 에러 메시지 구체화: `❌ 잔고 조회 실패: {e}`

## 관련
- [[KIS API 인증 토큰 관리]]
- [[trading-pipeline 아키텍처]]
```
