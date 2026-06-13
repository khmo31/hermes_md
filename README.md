# Hermes Agent — Structured Markdown Files

이 레포는 Hermes Agent의 구조화된 설정 파일들을 버전 관리한다.

## 구조

```
hermes_md/
├── SOUL.md                           # Hermes Agent 정체성 및 핵심 규칙 (8개)
├── AGENTS.md                         # 의사결정 프레임워크 (분할/라우팅/검증)
└── profiles/
    └── meta-optimizer/
        ├── SOUL.md                   # Meta-Optimizer 정체성 (Second Brain 개선 전담)
        ├── AGENTS.md                 # 분석 워크플로우, Scope 제한, 승인 게이트
        └── config.yaml               # 모델/툴셋 설정
```

## 파일 설명

| 파일 | 역할 | 적용 대상 |
|------|------|----------|
| `SOUL.md` | Hermes Agent의 정체성, 8개 MUST/NEVER 핵심 규칙, 글쓰기 스타일 | 모든 Hermes 세션 |
| `AGENTS.md` | delegate_task 분할 기준, 모델 라우팅(7그룹), 검증 루프, 구조적 한계 | 모든 Hermes 세션 |
| `profiles/meta-optimizer/SOUL.md` | Second Brain Pipeline 개선 전담 에이전트. Hermes 설정 수정 금지 | Meta-Optimizer cron |
| `profiles/meta-optimizer/AGENTS.md` | 메트릭 분석 워크플로우, Scope 제한, 승인 게이트 | Meta-Optimizer cron |

## 핵심 규칙 요약

1. **MUST delegate_task 분할** — 조건 충족 시 즉시 분할, 고민 NEVER
2. 우선순위: 직접 처리 > 순차 분할 > 병렬 분할
3. 세션 리셋 시 session_search() 먼저
4. Subagent 자기보고 절대 신뢰 금지
5. Subagent model 파라미터 MUST 명시
6. 검증 루프 필수 (수행→검증→자동수정→보고)
7. **MUST second_brain → session_search 3단계** — 건너뛰기 NEVER
8. **MUST 라우팅 테이블 준수** — 태스크별 정확한 모델 지정

## 연관 프로젝트

- [Second Brain Knowledge OS](https://github.com/khmo31/second_brain) — 지식 저장소
- [Knowledge Distillation Pipeline](https://github.com/khmo31/hermes_md) — 세션 → 위키 정제 파이프라인
