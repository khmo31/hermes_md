# Multi-Profile Migration Methodology

기존 default 프로필의 책임을 여러 Hermes 프로필로 분할하는 체계적인 방법론.
`multi-agent-orchestration` 스킬의 "Multi-Profile Architecture" 섹션에서 참조한다.

---

## 1단계: 크론 전수 매핑

```bash
hermes cron list
```

모든 cron job을 다음 축으로 분류:

| 축 | 값 | 의미 |
|----|-----|------|
| mode | `no-agent` | 셸 스크립트만 실행, LLM/SOUL/MEMORY 관여 없음 → **분리 불필요** |
| mode | `LLM-driven` | Hermes Agent가 SOUL.md + MEMORY.md 로드 후 실행 → **분리 검토** |
| profile | `default` | default 프로필의 MEMORY.md 공유 → 오염 가능성 |
| profile | `meta-optimizer` 등 | 이미 분리됨 → 현상 유지 |
| deliver | Discord 채널 | 결과 전달 대상 확인 (프로필 분리 후에도 유지할지 결정) |

### 함정: no-agent 크론을 분리 대상으로 착각하지 말 것

```
trading-morning-analysis:
  Mode: no-agent (script stdout delivered directly)  ← LLM 개입 ZERO
  Script: run_morning.sh
  
→ 이 크론은 SOUL.md, MEMORY.md, SKILLS 어느 것도 사용하지 않는다.
→ 별도 프로필로 옮겨도 변화 없음. 오히려 설정 부채만 증가.
→ 그대로 둔다.
```

---

## 2단계: MEMORY.md 오염도 분석

1. 현재 MEMORY.md 전체를 읽는다
2. 각 항목을 도메인별로 태깅한다:

```
[default MEMORY.md]
- OpenCode Notion MCP config       → 도메인: Notion/Docs
- Second Brain auto-save ON        → 도메인: Knowledge
- Discord 채널 구조                 → 도메인: Infra/Discord
- trading-agent-pipeline           → 도메인: Trading
- 스마트홈 서버 주소                 → 도메인: SmartHome
- hermes_md 레포                    → 도메인: Development
- Knowledge Distillation Pipeline  → 도메인: Knowledge (중복)
- khmo31 지식 관리 철학             → 도메인: Knowledge
- 의사결정 스타일                    → 도메인: User Profile (유지)
```

3. 도메인별 점유율 계산:

```
Knowledge:  35%  ← 최대 오염원, 분리 1순위
Notion:     15%  ← 문서 도메인
Development: 20%  ← default 유지
Trading:    10%  ← 이미 no-agent, MEMORY.md 항목만 제거
SmartHome:   5%
User:       15%  ← 필수 유지
```

4. 오염도 20% 이상인 도메인 = **분리 검토 대상**

---

## 3단계: delegate_task 패턴 분석

세션 로그 또는 AGENTS.md의 delegate_task 호출 패턴을 분석한다:

```
반복되는 패턴:
  goal: "Notion AI어투 제거" / "문서 번역" / "16주차 정리"
  model: qwen3.7-max (매번 override)
  context: technical-writer.md 주입
  toolsets: file, notion
  
→ 모델 override가 매번 필요 → 프로필 기본 모델로 설정하면 생략 가능
→ 같은 역할 파일 매번 주입 → 프로필 SOUL.md에 내장하면 콜드 스타트 제거
→ Notion 구조 매번 재탐색 → MEMORY.md에 축적되면 3~5턴 절약
```

---

## 4단계: 승격 가치 평가 매트릭스

각 후보 도메인을 5개 축으로 평가 (각 1~5점):

| 축 | 평가 기준 |
|----|----------|
| **반복성** | 5: 매일 수회 delegate_task 호출 / 1: 연 1~2회 |
| **도메인 특수성** | 5: 완전히 격리된 지식 도메인 / 1: 범용 지식 |
| **콜드 스타트 비용** | 5: 매 태스크마다 5턴+ 낭비 / 1: 1턴 이내 |
| **모델 차별화** | 5: default와 완전히 다른 모델 필요 / 1: 동일 모델 |
| **컨텍스트 오염도** | 5: MEMORY.md 30%+ 점유 / 1: 5% 미만 |

### 실제 평가 예시 (khmo31 케이스)

| 도메인 | 반복성 | 특수성 | 콜드스타트 | 모델차별 | 오염도 | 총점 | 판정 |
|--------|--------|--------|-----------|---------|--------|------|------|
| Writer (Notion/문서) | 5 | 4 | 4 | 5 (qwen) | 3 | **21** | ✅ 즉시 분리 |
| Knowledge (Wiki) | 4 | 5 | 2 | 3 | 5 | **19** | ✅ 즉시 분리 |
| Reviewer (코드리뷰) | 3 | 4 | 3 | 1 | 1 | **12** | 🟡 조건부 |
| SmartHome | 2 | 5 | 1 | 1 (flash) | 1 | **10** | 🟢 선택 |
| Trading | 0 (no-agent) | 5 | 0 | 0 | 2 | **7** | ❌ 이미 분리됨 |
| TOEIC/Study | 2 | 3 | 1 | 1 | 1 | **8** | ❌ 너무 작음 |

**판정 기준:**
- 17점 이상: ✅ 즉시 분리 가치 있음
- 12~16점: 🟡 조건부 (다른 분리 완료 후 재검토)
- 11점 이하: ❌ delegate_task + 역할 파일로 충분

---

## 5단계: 프로필 설계

분리 결정된 도메인별로 다음을 정의:

### 프로필 스펙 시트

```yaml
name: writer
role: "한국어 기술 문서 작성 전문가"
model: qwen3.7-max  # default(v4-pro)와 다른 모델 — 핵심 분리 사유
toolsets: [file, notion]  # terminal/web 불필요 → 최소 권한
discord_bot: optional  # 패턴 B(default 중개)로 시작, 필요 시 패턴 A로 승격
cron_jobs: []  # 온디맨드만 처리
```

### SOUL.md 방향

프로필의 정체성을 한 문장으로 정의하고, 그에 맞는 행동 규칙을 작성:

```
"너는 한국어 기술 문서 작성 전문가다.
AI어투(~입니다, ~것으로 보입니다, 도움이 되셨길) 탐지 및 제거가 주 임무다.
khmo31의 선호 문체: 직설적/간결체, ~것이다 체, 추정 표현 금지."
```

### MEMORY.md 이전 계획

default MEMORY.md에서 제거 → 새 프로필 MEMORY.md로 이동:

```
[default → writer]
- OpenCode Notion MCP config 등록 완료
- Notion: 백엔드 포트폴리오 (14주차 구조)
- AI어투 제거 완료된 페이지 목록

[default → knowledge]
- Second Brain auto-save ON
- Knowledge Distillation Pipeline (Owner/Reviewer/Harness)
- distillation metrics
- khmo31 지식 관리 철학 (axis+linking > RAG)
- Meta-Optimizer와의 관계
```

### 크론 이전

```bash
# 기존 크론의 profile을 변경
hermes cronjob update <job_id> --profile knowledge

# 또는 삭제 후 knowledge 프로필에서 재생성
# (profile 파라미터로 대상 프로필 지정)
```

---

## 6단계: 구현 순서

1. **가장 오염도가 높은 것부터** → default MEMORY.md 부담 즉시 경감
2. **의존성이 적은 것부터** → 다른 프로필과 얽히지 않은 독립 도메인
3. **모델 차별화가 큰 것부터** → 토큰 비용 절감 효과 즉시 체감

### 실제 구현 순서 (khmo31)

```
Phase 1: knowledge 프로필 생성 → wiki-pipeline 크론 이전 → MEMORY.md 정리
Phase 2: writer 프로필 생성 → Notion 태스크 delegate_task에서 model override 제거
Phase 3: reviewer 프로필 재활성화 → 코드리뷰 전문화
Phase 4: smarthome 프로필 생성 (선택) → 툴셋 제한 보안 격리
```

---

## 주의: 분리하지 말아야 할 것

### no-agent 스크립트 크론

```
trading-morning-analysis:
  Mode: no-agent
  → 분리 불필요. LLM이 개입하지 않으므로 MEMORY.md/SKILLS 무관.
```

### 1회성·저빈도 작업

```
moltbook-monthly-trend (월 1회 no-agent)
TOEIC 알림 (크론 1개, LLM 관여 최소)
→ 프로필 생성·관리 오버헤드가 이득보다 큼
```

### default 정체성의 핵심인 도메인

```
개발·코딩·디버깅:
  default의 핵심 정체성. 분리 시 "코딩해줘"라는 
  자연스러운 대화 흐름이 끊김.
  → delegate_task + coder.md 역할 파일로 충분
```

---

## 핵심 원칙: 기존 구조 보존 + 오픈소스 검증 우선

프로필 생성 시 SOUL.md/AGENTS.md를 **새로 작성하지 않는다.** 다음 계층 구조를 따른다:

| 레벨 | 대상 | 변경 허용 | 이유 |
|------|------|----------|------|
| L0 | `~/.hermes/roles/*.md` (5개) | ❌ 절대 수정 금지 | 오픈소스에서 검증된 구조. 한 글자도 바꾸지 않음 |
| L1 | delegate_task context 주입 패턴 | ❌ 유지 | `_harness + _gbrain + role` 조합 그대로 사용 |
| L2 | 새 프로필의 SOUL.md/AGENTS.md | 📋 발췌조립만 | L0·L1에서 발췌 → 프로필 포맷에 맞게 재배열. 내용은 원본 그대로 |
| L3 | default MEMORY.md | ✂️ 트리밍만 | 도메인 무관 항목 제거만, 사용자 특성 항목 유지 |
| L4 | 새 프로필 config.yaml | 🆕 신규 | 모델·툴셋만 정의 |

### 발췌조립(📋) 방법

1. 원본(역할 파일 또는 스킬)에서 해당 프로필에 필요한 섹션만 **발췌**
2. Hermes 프로필 포맷(SOUL.md: 정체성 → 규칙 → 스타일 / AGENTS.md: 워크플로우 → 규칙 → Scope)에 맞게 **재배열**
3. 원본 내용은 **한 글자도 바꾸지 않는다** — 수치·고유명사·기술 용어 보존
4. 프로필 특화 정보(Notion API 패턴 등)는 **별도 섹션으로 분리**하여 원본 구조를 오염시키지 않음

### 함정: "내가 더 잘 쓸 수 있을 것 같다"는 착각

오픈소스 역할 파일은 수백 시간의 실제 사용과 검증을 거친 구조다. 새로 작성하면:
- 일관성 상실 (기존 delegate_task와 새 프로필 간 불일치)
- 검증되지 않은 규칙으로 인한 품질 저하
- 기존 subagent 컨텍스트와의 호환성 문제

**원칙: 발췌조립으로 충분하지 않은 경우에만 신규 작성. 90% 이상은 발췌조립으로 해결된다.**

---

## 검증 체크리스트

프로필 분리 완료 후:

- [ ] 새 프로필의 gateway가 정상 실행되는가? (`hermes gateway status --profile <name>`)
- [ ] 크론이 새 프로필에서 정상 실행되는가? (다음 실행 시점까지 대기 또는 수동 trigger)
- [ ] 이전된 MEMORY.md 항목이 default에서 제거되었는가?
- [ ] default MEMORY.md 글자 수가 목표치 이하로 감소했는가?
- [ ] 새 프로필의 Discord 봇이 필요한 경우 정상 응답하는가?
- [ ] default에서 writer/reviewer delegate_task 호출 시 model override가 정상 동작하는가?
