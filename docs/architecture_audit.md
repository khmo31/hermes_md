# Architecture Audit — 중복 정리 & Rule Registry

---

## 1. MEMORY ↔ SOUL.md 중복 정리 완료 보고

> 2026-06-13 실행. MEMORY는 `~/.hermes/` 내부 저장소로 이 레포에 포함되지 않음.

### 제거된 MEMORY 항목 (7건)

| 항목 | 사유 |
|------|------|
| Paperclip server + bot 중지 이력 | Stale — 더 이상 운영하지 않음 |
| Paperclip 제거 완료 + 역할 주입 v3.2.0 | Stale — 구버전 정보 |
| delegate_task model override 로컬 패치 이력 | Stale — 기능 안정화됨 |
| 매 세션 skill_view 자동 로드 | 중복 — System prompt가 이미 처리 |
| hermes-paperclip-adapter 설치 정보 | Stale |
| multi-agent-orchestration v3.0.0/v3.2.0 | Stale — v4.0.0이 최신 |

### SOUL.md로 병합된 USER 항목 (5건)

| 항목 | 원래 위치 | 병합 위치 |
|------|----------|----------|
| 글쓰기 스타일 | USER | SOUL.md §글쓰기 스타일 |
| 정확성/성향 | USER | SOUL.md §사용자 |
| 세션 리셋 session_search | USER | SOUL.md 규칙 #3 |
| v4-pro 분석 필수 | USER | SOUL.md §사용자 + AGENTS.md §2 |
| 시스템 설계 스타일 | USER | SOUL.md §사용자 |

### 정리 결과

| 저장소 | 정리 전 | 정리 후 |
|--------|---------|---------|
| MEMORY | 2,053/2,200 (93%) | 973/2,200 (44%) |
| USER | 1,176/1,375 (85%) | 156/1,375 (11%) |

---

## 2. SOUL.md ↔ AGENTS.md 역할 분리

SOUL.md와 AGENTS.md의 "중복"은 의도된 설계다. 핵심 원칙(SOUL)과 실행 절차(AGENTS)는 서로 다른 문서지만 상호 참조한다.

### 매핑 테이블

| SOUL.md 규칙 | AGENTS.md 섹션 | 관계 |
|-------------|---------------|------|
| #1 MUST delegate_task 분할 | §1 직접 처리 vs delegate_task 판단 | SOUL=원칙, AGENTS=절차 |
| #5 MUST model 파라미터 | §7 delegate_task model override | SOUL=금지, AGENTS=사용법 |
| #6 검증 루프 | §4 검증 루프 (Verification Protocol) | SOUL=원칙, AGENTS=구체적 검증 방법 |
| #7 MUST second_brain 탐색 | — (SOUL 전용) | — |
| #8 MUST 라우팅 준수 | §2 모델 라우팅 퀵 레퍼런스 | SOUL=금지, AGENTS=라우팅 테이블 |

### 충돌 해결 이력

| 충돌 | 해결일 | 방식 |
|------|--------|------|
| 규칙 #1(MUST 분할) vs #2(직접 처리 우선) | 2026-06-13 | #2 개정: 분할 트리거 충족 시 직접 처리 NEVER |
| 코드리뷰 라우팅 (Research vs coder.md) | 2026-06-13 | researcher.md로 단일화, coder.md 트리거에서 제거 |

---

## 3. Rule Registry

### 규칙 인덱스

| ID | 규칙 | 파일 | 우선순위 | 충돌_대상 | 예외 |
|----|------|------|---------|----------|------|
| R1 | MUST delegate_task 분할 | SOUL.md | P0 | R2에 우선 (트리거 충족 시 R2 무력화) | 단일 툴 호출, 1~2파일 |
| R2 | 분할 트리거 충족 시 직접 처리 NEVER | SOUL.md | P1 | R1 트리거 0개일 때만 적용 | 없음 |
| R3 | 세션 리셋 시 session_search() | SOUL.md | P0 | — | — |
| R4 | Subagent 자기보고 불신 | SOUL.md | P0 | — | 검증 완료된 경우 |
| R5 | MUST model 파라미터 | SOUL.md | P0 | — | — |
| R6 | 검증 루프 필수 | SOUL.md | P0 | — | — |
| R7 | MUST second_brain → session_search | SOUL.md | P0 | — | 독립 일상대화 |
| R8 | MUST 라우팅 테이블 준수 | SOUL.md | P0 | — | — |
| A1 | 분할 전 MUST 검증 3질문 | AGENTS.md | P0 | — | — |
| A2 | Decision Log 필수 기재 | AGENTS.md | P0 | — | — |
| M1 | Proposal write only | meta/AGENTS.md | P0 | — | — |
| M2 | Preflight Denylist | meta/AGENTS.md | P0 | — | — |

### 우선순위 체계

- **P0**: 위반 시 시스템 안전성/정합성 손상. 절대 위반 금지.
- **P1**: 품질/효율성 관련. 정당한 사유 시 예외 가능 (문서화 필수).
- **P2**: 권장사항. 상황에 따라 조정 가능.

### 확장 가이드

새 규칙 추가 시:
1. 다른 규칙과의 충돌 여부를 `conflicts_with` 필드에 명시
2. P0 규칙이 10개 초과 시 우선순위 재검토 (P0 남용 방지)
3. 각 규칙은 반드시 하나의 `owner_file`을 가짐 (SOUL.md 또는 AGENTS.md, 양쪽 중복 금지)
