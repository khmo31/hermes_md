# Hermes 멀티프로필 아키텍처 설계 패턴

> **적용일:** 2026-06-16
> **대상:** Hermes Agent 프로필 분할 설계
> **관련 스킬:** multi-agent-orchestration, second-brain

---

## 1. 왜 프로필을 분리하는가

### 문제: MEMORY.md 오염

단일 프로필이 모든 도메인을 처리하면 MEMORY.md(2,200자 제한)에 모든 도메인의 기억이 뒤섞인다:

```
[트레이딩] [지식관리] [Notion] [스마트홈] [개발] [hermes_md] [TOEIC] ...
→ 코딩할 때 트레이딩 메모리가 주입됨 (토큰 낭비)
→ 2,200자 제한 때문에 계속 통합·삭제 압박
→ LLM 크론이 MEMORY.md를 공유하면 크론 실행마다 오염 확산
```

### 해결: 도메인별 프로필 분리

각 프로필이 자기 MEMORY.md와 SKILLS를 가짐 → 도메인 특화 지식만 축적.

---

## 2. 분리 판단 기준

| 기준 | 설명 | 가중치 |
|------|------|--------|
| **모델 차별화** | default와 다른 모델이 필요한가? | 🔴 핵심 |
| **MEMORY.md 오염도** | 현재 MEMORY.md에 이 도메인의 항목이 많은가? | 🔴 핵심 |
| **LLM 크론 공유** | LLM이 개입하는 크론이 default MEMORY.md를 쓰는가? | 🟡 중요 |
| **반복성** | 같은 유형의 태스크가 반복되는가? (스킬 축적 가치) | 🟡 중요 |
| **툴셋 격리** | 보안상 툴셋을 제한해야 하는가? | 🟢 부가 |

### 분리 1순위 신호

1. **모델이 다르다** — 문서=qwen3.7-max, 개발=kimi-k2.7-code 등
2. **LLM 크론이 MEMORY.md를 공유한다** — 가장 큰 오염원
3. **MEMORY.md가 80% 이상 찼다** — 정리 압박 해소

### 분리하지 않아도 되는 경우

1. **no-agent 크론** — LLM이 개입하지 않으므로 MEMORY.md 공유 무관
2. **사용 빈도 낮음** — 프로필 관리 오버헤드가 이득보다 큼
3. **단일 세션 태스크** — delegate_task로 충분

---

## 3. 표준 프로필 구조

```
~/.hermes/profiles/<name>/
├── SOUL.md          ← 정체성 + 핵심 규칙
├── AGENTS.md        ← 의사결정 가이드 + 워크플로우
├── USER.md          ← default에서 복사
├── MEMORY.md        ← 도메인 특화 기억만 포함
└── config.yaml      ← 모델·툴셋·프로바이더
```

### SOUL.md 작성 원칙: 발췌조립 (Extract-Adapt)

**절대 처음부터 쓰지 않는다.** 오픈소스 검증된 역할 파일(`~/.hermes/roles/*.md`)과 스킬에서:

1. Identity/정체성 섹션 → 프로필 정체성으로 발췌
2. Workflow/품질 게이트 → AGENTS.md로 발췌
3. 원본 구조를 훼손하지 않고 Hermes 프로필 포맷에 맞게 재배열

**금지:** 역할 파일 원본 수정. 원본은 default의 delegate_task context 주입용으로 계속 사용.

### config.yaml 템플릿

```yaml
model:
  default: <모델명>
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
  api_mode: chat_completions
toolsets:
- file
- <도메인 특화 툴셋>
terminal:
  backend: local
  auto_source_bashrc: true
```

---

## 4. khmo31 적용 사례 (2026-06-16)

### 4-프로필 아키텍처

```
default (v4-pro)          ← 주 인터페이스 + 개발 + delegate_task 오케스트레이션
    │
    ├─ delegate_task → writer (qwen3.7-max)
    │   역할: Notion 문서, AI어투 제거, 번역
    │   MEMORY.md: AI어투 패턴, Notion 페이지 구조
    │
    ├─ delegate_task → reviewer (v4-pro)
    │   역할: 코드 리뷰, 보안 스캔, 품질 게이트
    │   MEMORY.md: 레포 컨벤션, 취약점 패턴, 반복 이슈
    │
    ├─ delegate_task → 코딩 (kimi-k2.7-code)
    │   역할: 코드 작성, 디버깅, 테스트
    │   (default 프로필 내 delegate_task, 별도 프로필 아님)
    │
    └─ 크론 전용 (독립 실행, default와 MEMORY.md 미공유)
        ├─ knowledge (v4-pro)    ← wiki-pipeline + distillation
        └─ meta-optimizer (v4-pro) ← pipeline 최적화 (격리)
```

### 분리 결정 근거

| 프로필 | 분리 근거 | 모델 |
|--------|----------|------|
| writer | **모델 다름** (qwen3.7-max ≠ v4-pro) + 반복성 최고 | qwen3.7-max |
| knowledge | **LLM 크론이 MEMORY.md 오염** (최대 원인) | v4-pro |
| reviewer | 반복적 PR 리뷰 패턴 + dormant 프로필 재활용 | v4-pro |
| meta-optimizer | 이미 분리 완료, Scope 격리 필수 | v4-pro |

### 분리하지 않은 것

| 항목 | 사유 |
|------|------|
| 트레이딩 (4개 크론) | **no-agent** 스크립트 → LLM 무관, MEMORY.md 공유 안 함 |
| docker/power 스크립트 | no-agent, LLM 무관 |
| 코딩 (kimi-k2.7-code) | default에서 delegate_task로 충분, 도메인 혼재가 심하지 않음 |

### default MEMORY.md 변화

```
Before: 3,194 bytes (20줄)
  [Notion MCP] [Second Brain] [Discord] [Notion 포트폴리오] [서버]
  [Discord 채널] [Distillation Pipeline] [Meta-Optimizer]
  [hermes_md] [지식관리 철학] [의사결정 스타일]

After: 1,601 bytes (13줄, 50% 감소)
  [Notion MCP 참조] [Discord 채널] [서버] [Discord 토큰]
  [멀티프로필 구조] [hermes_md] [의사결정 스타일]
```

---

## 5. 조심해야 할 함정

### 함정 1: 크론이 no-agent인데 프로필 분리하는 것
**증상:** "트레이딩 크론 X개 있으니 트레이딩 프로필 만들자"
**현실:** no-agent 모드는 Hermes LLM 세션을 전혀 생성하지 않으므로 MEMORY.md/SKILLS를 사용하지 않는다. 분리해도 아무 변화 없음.

### 함정 2: 역할 파일 직접 수정
**증상:** "writer 프로필용으로 technical-writer.md를 수정하자"
**현실:** 역할 파일은 default의 delegate_task context 주입에 사용된다. 수정하면 모든 delegate_task에 영향. 새 프로필은 역할 파일을 **참조만** 하고 자기 SOUL.md/AGENTS.md를 따로 만든다.

### 함정 3: delegate_task를 프로필 간 위임으로 착각
**증상:** "default가 writer 프로필에 delegate_task로 위임한다"
**현실:** delegate_task는 **같은 프로필 내**에서만 동작한다. 다른 프로필로 위임하려면 Discord 채널 경유나 별도 API가 필요. 현재 아키텍처에서는 default가 사용자 요청을 받고 delegate_task로 model override + 역할 주입으로 처리.

### 함정 4: 프로필마다 Discord 봇 등록
**증상:** "각 프로필이 자기 Discord 봇을 가지면 좋겠다"
**현실:** 봇 여러 개 관리 부담이 크다. default가 단일 진입점이고, delegate_task가 백엔드 분산을 처리하는 구조가 더 실용적. 스마트홈처럼 즉시 응답이 중요한 도메인만 예외.

---

## 6. 크론 프로필 이전 방법

```bash
# 기존 크론의 프로필 변경
hermes cron update <job_id> --profile <new_profile>

# 확인
hermes cron list | grep <job_id>
# → "profile": "<new_profile>" 확인
```

크론은 다음 실행부터 새 프로필의 SOUL.md/AGENTS.md/MEMORY.md를 사용한다.
