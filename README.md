# Hermes Agent — Structured Markdown Files

이 레포는 Hermes Agent의 구조화된 설정 파일들을 버전 관리한다.

## 구조

```
hermes_md/
├── SOUL.md                           # Hermes Agent 정체성 및 핵심 규칙 (10개)
├── AGENTS.md                         # 의사결정 프레임워크 (분할/라우팅/검증)
├── MEMORY.md                         # 세션 간 지속 기억
├── USER.md                           # 사용자 프로필
├── config.yaml                       # 모델·툴셋 기본 설정
├── evaluation_criteria.md            # 구조화 설정 평가 항목 (8영역)
├── profiles/                         # 도메인별 격리 에이전트 프로필
│   ├── writer/                       # 한국어 기술 문서·AI어투 제거 전담 (qwen3.7-max)
│   ├── reviewer/                     # 코드리뷰·보안 감사 전담 (v4-pro)
│   ├── knowledge/                    # Wiki Pipeline·세션 증류 전담 (v4-pro+flash)
│   ├── meta-optimizer/               # Pipeline 품질 재귀 개선 전담 (v4-pro)
│   └── cad/                          # 파라메트릭 3D CAD 설계 전담 (kimi-k2.7-code)
├── roles/                            # Subagent 역할 정의 파일
│   ├── _harness.md                   # 행동 교정·검증 루프 (모든 역할에 공통)
│   ├── _gbrain.md                    # 계약 기반 설계·신뢰 경계 (모든 역할에 공통)
│   ├── coder.md                      # 코딩·구현·백엔드·프론트
│   ├── researcher.md                 # 리서치·분석·조사
│   ├── technical-writer.md           # 문서·글쓰기·AI어투 제거
│   └── cad-designer.md               # CAD 설계·파라메트릭 모델링·BOM·도면
├── skills/                           # 도메인별 스킬 정의
│   ├── autonomous-ai-agents/         # 멀티에이전트 오케스트레이션·모델 인벤토리
│   ├── devops/                       # 서버 관리·전력 모니터링
│   ├── discord/                      # Discord 통합 설정
│   ├── productivity/                 # Notion·Second Brain
│   ├── smart-home/                   # Home Assistant·OpenHue
│   ├── software-development/         # 코드리뷰·검증·서브에이전트 개발
│   └── trading/                      # 트레이딩 에이전트 파이프라인
├── scripts/                          # 실행 스크립트
│   └── verify_integrity.sh           # 파일 무결성 검증
└── docs/                             # 설계 문서
    ├── architecture_audit.md         # 아키텍처 감사
    ├── migration_plan.md             # 마이그레이션 계획
    ├── multiaxis_schema.md           # 다축 분류 스키마
    └── pipeline_spec.md              # Knowledge Distillation Pipeline 명세
```

## 파일 설명

| 파일 | 역할 | 적용 대상 |
|------|------|----------|
| `SOUL.md` | Hermes Agent의 정체성, 10개 MUST/NEVER 핵심 규칙, 글쓰기 스타일 | 모든 Hermes 세션 |
| `AGENTS.md` | delegate_task 분할 기준, 모델 라우팅(전체 그룹은 AGENTS.md §2 참조), 검증 루프, 구조적 한계 | 모든 Hermes 세션 |
| `evaluation_criteria.md` | 구조화 설정 평가 항목 (8영역 34항목 + 프로필 확장 정합성) | 정기 설정 감사 |
| `profiles/*/SOUL.md` | 도메인별 정체성·핵심 규칙 | 해당 프로필 세션 |
| `profiles/*/AGENTS.md` | 도메인별 의사결정 가이드 | 해당 프로필 세션 |
| `profiles/*/config.yaml` | 도메인별 모델·툴셋 설정 | 해당 프로필 세션 |

## 핵심 규칙 요약

1. **MUST delegate_task 분할** — 6개 조건 중 하나라도 충족 시 즉시 분할, 고민 NEVER
2. **분할 트리거 없을 때만:** 직접 처리 → 순차 분할 → 병렬 분할
3. 세션 리셋 시 session_search() 먼저
4. Subagent 자기보고 절대 신뢰 금지
5. Subagent model 파라미터 MUST 명시
6. 검증 루프 필수 (수행→검증→자동수정→보고)
7. **MUST second_brain → session_search 3단계** — 건너뛰기 NEVER
8. **MUST 라우팅 테이블 준수** — 태스크별 정확한 모델 지정 (전체 라우팅 테이블은 AGENTS.md §2 참조 — 그룹 수는 AGENTS.md가 단일 소스)

## 연관 프로젝트

- [Second Brain Knowledge OS](https://github.com/khmo31/second_brain) — 지식 저장소
- [Knowledge Distillation Pipeline](https://github.com/khmo31/hermes_md) — 세션 → 위키 정제 파이프라인
