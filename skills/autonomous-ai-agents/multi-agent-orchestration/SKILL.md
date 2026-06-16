---
name: multi-agent-orchestration
description: "자동 판단 기반 멀티에이전트 오케스트레이션 — Hermes가 직접 라우터 역할, delegate_task로 세분화 실행"
version: 3.5.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [orchestration, multi-agent, auto-split, autonomous]
    related_skills: [opencode, orchestrator-delegation-strategy]
---

# Hermes 네이티브 오케스트레이션 (v3.3)

Paperclip 제거. Hermes가 직접 00-라우터.

## 역할 주입 시스템

모든 delegate_task 서브에이전트는 다음 순서로 context 주입:

```
context = _harness.md + "\n---\n" + _gbrain.md + "\n---\n" + role_specific.md
```

### Base (모든 역할에 공통 주입)

| 파일 | 크기 | 출처 | 핵심 내용 |
|------|------|------|----------|
| `_harness.md` | 26KB | revfactory/harness | 행동 교정, 6단계 워크플로우, 검증 루프, QA 기준 |
| `_gbrain.md` | 27KB | garrytan/gbrain | 계약 기반 설계, trust boundary, two-axis mental model, anti-patterns |

### Role-Specific (역할별)

| 파일 | 크기 | 출처 | 대상 태스크 |
|------|------|------|-----------|
| `technical-writer.md` | 25KB | im-not-ai | 문서/글쓰기/AI어투 제거/Notion |
| `coder.md` | 25KB | awesome-copilot + oh-my-pi | 코딩/구현/백엔드/프론트 |
| `researcher.md` | 33KB | academic-research-skills + last30days-skill | 리서치/분석/조사 |

### 실행 예제

```python
def build_context(role_name):
    harness = read_file("~/.hermes/roles/_harness.md")["content"]
    gbrain = read_file("~/.hermes/roles/_gbrain.md")["content"]
    role = read_file(f"~/.hermes/roles/{role_name}.md")["content"]
    return harness + "\n---\n" + gbrain + "\n---\n" + role

delegate_task(tasks=[{
    "goal": "노션 문서 AI어투 제거해서 재업로드",
    "context": build_context("technical-writer"),
    "toolsets": ["file"]
}])
```

## 멀티프로필 아키텍처 (Multi-Profile Architecture)

delegate_task는 단일 프로필 내에서만 동작한다. 도메인별 MEMORY.md/SKILLS 격리가 필요하거나 LLM 크론이 MEMORY.md를 공유할 때는 프로필 분할이 필요하다. 전체 설계 패턴과 적용 사례는 `references/multi-profile-architecture.md` 참조.

## 태스크 분류 → 라우팅 테이블

> **중요:** `delegate_task`에 `model` 파라미터를 전달하면 subagent의 모델을 override할 수 있음. 포맷: `"provider/model"` (예: `"deepseek-v4-pro"`, `"openai/gpt-4o"`). 생략 시 우선순위: `per-task model > top-level model > delegation.model(config) > parent session model`.

### Subagent 툴셋 매핑

| 그룹 | 태스크 | 1순위 | 2순위 | 툴셋 |
|------|--------|-------|-------|------|
| 🔍 Research & Analysis | 리서치, 코드분석, 코드리뷰, 기획, 취약점분석 | `deepseek-v4-pro` | `kimi-k2.6` | file, web |
| ⚡ Development | 코드작성, 디버깅, 백엔드, 프론트, 테스트 | `kimi-k2.7-code` | `deepseek-v4-pro` | terminal, file |
| 📝 Writing & Docs | 문서, README, 번역, 한국어글쓰기, AI어투제거 | `qwen3.7-max` | `qwen3.7-plus` | file |
| 🎨 Creative | 스토리, 카피, 블로그, 광고 | `minimax-m3` | `qwen3.7-max` | file |
| 📄 Long Docs | 대용량문서(200K+), PDF분석 | `kimi-k2.6` | `kimi-k2.5` | file |
| 🔄 Automation | 크론, RSS, 뉴스, 모니터링, 알림 | `deepseek-v4-flash` | `big-pickle 🆓` | web, terminal |
| 🪶 Light | 단순QA, 간단편집, 실험 | `deepseek-v4-flash` | `big-pickle 🆓` | terminal, file |

> **부모 모델 권고:** 이 테이블의 복잡도를 감안하면 **부모는 v4-pro 권장**. Flash로는 일관된 판단이 어렵다. 부모 호출은 적어 비용 증가폭 미미.

> **Provider 제한:** 현재 로컬 패치는 `model` override만 지원. provider는 `config.yaml delegation.provider`(opencode-go)로 고정. Copilot model 분기는 provider 레벨 패치 필요.

### 역할 파일 라우팅

| 그룹 | 역할 파일 | 1순위 | 2순위 | 툴셋 |
|------|----------|-------|-------|------|
| Research | `researcher.md` | `v4-pro` | `kimi-k2.6` | web, file |
| Development | `coder.md` | `kimi-k2.7-code` | `v4-pro` | terminal, file |
| Writing | `technical-writer.md` | `qwen3.7-max` | `qwen3.7-plus` | file |
| Creative | `technical-writer.md` | `minimax-m3` | `qwen3.7-max` | file |
| Long Docs | `researcher.md` | `kimi-k2.6` | `kimi-k2.5` | file |
| Automation | directly | `v4-flash` | `big-pickle 🆓` | web, terminal |
| Light | directly | `v4-flash` | `big-pickle 🆓` | terminal, file |

> 키워드 트리거는 부모 모델의 자유 재량으로 판단. 위 테이블은 그룹 매핑 가이드.

## 의존성 관리: 병렬 vs 순차 처리 규칙

delegate_task의 가장 흔한 실수는 **의존성이 있는 태스크를 병렬로 보내는 것**. 다음 규칙으로 방지.

### 독립성 판단 질문

`tasks=[{"goal": "A"}, {"goal": "B"}]` 형태의 batch 전에:

| 질문 | 판정 |
|------|------|
| A의 결과 없이 B를 시작해도 되는가? | YES → 병렬 가능 |
| B가 A가 만든 파일을 읽어야 하는가? | NO → 순차 처리 |
| A와 B가 같은 파일을 수정하는가? | YES → 순차 처리 (충돌 방지) |
| A의 출력이 B의 입력인가? | YES → 순차 처리 |

### 순차 처리 패턴

```python
# 1. 첫 번째 태스크
result_a = delegate_task(
    model="deepseek-v4-pro",
    goal="레포 구조 분석",
    context=f"분석할 레포: {repo_path}",
    toolsets=["terminal", "file"],
)
# 2. 결과를 context에 담아 두 번째 태스크
repo_context = extract_useful_info(result_a)
result_b = delegate_task(
    model="deepseek-v4-pro",
    goal="취약점 분석",
    context=f"레포 정보:\n{repo_context}",
    toolsets=["file"],
)
# 3. 결과 병합
```

### 병렬 처리 패턴 (독립적일 때만)

```python
# 실제로 독립적인 작업들
delegate_task(tasks=[
    {"goal": "주식 A 분석", "context": "...", "toolsets": ["web"]},
    {"goal": "주식 B 분석", "context": "...", "toolsets": ["web"]},
    {"goal": "뉴스 수집", "context": "...", "toolsets": ["web"]},
], model="deepseek-v4-pro")
```

### 금지 패턴 (절대 금지)

```python
# ❌ B가 A의 출력을 필요로 하는데 병렬로 보냄
delegate_task(tasks=[
    {"goal": "데이터 수집"},
    {"goal": "수집된 데이터 분석"},  # A가 끝나기 전에 B 시작 — 실패
])

# ❌ 같은 파일을 동시 수정
delegate_task(tasks=[
    {"goal": "README.md 수정"},
    {"goal": "README.md에 섹션 추가"},  # git conflict
])
```

### Fallback: 부모가 직접 중개자 역할

병렬이 불가능할 때 부모가 순차적으로 처리:

```python
# 직접 순차 처리
r1 = delegate_task(goal="Step 1", ...)
key_info = extract(r1)
r2 = delegate_task(goal="Step 2", context=key_info, ...)
```

사용자가 `/new`로 세션을 리셋하는 경우가 많음. 새 세션에서 delegate_task를 호출하기 전에:

1. **`session_search()` 실행** — 최근 대화 맥락 확인 (진행 중인 작업, 최근 수정 파일, 열려있는 이슈)
2. **결과가 있으면** — context에 포함시켜 subagent에 전달
3. **결과가 없어도** — 사용자에게 "예전에 하던 건데요?"라고 묻지 말고 바로 진행

이 패턴은 memory에 의존하지 않고도 지속성을 유지하는 핵심 방법임.

## 분할 판단 기준 (Decomposition Trigger) — MUST 준수

부모 에이전트가 태스크를 받았을 때 "직접 처리 vs delegate_task로 분할"을 판단하는 기준. SOUL.md 핵심 규칙 #1과 #8에 의해 강제된다.

### 반드시 분할 — MUST delegate_task (하나라도 해당 시)

| 조건 | 예시 |
|------|------|
| **독립적 서브태스크 2개 이상** | "A 기능 구현 + B 기능 테스트" → 각각 subagent |
| **툴셋이 다른 작업 혼합** | 웹 검색 + 코드 작성 → web vs terminal/file |
| **중간 결과가 컨텍스트 오염 우려** | 큰 파일 생성, API 응답 대량 포함 |
| **예상 턴 수 10턴 이상** | 복잡한 분석, 여러 파일 수정 |
| **사용자가 명시적으로 분할 요청** | "하위 에이전트 써서", "병렬로" |
| **서로 다른 모델 필요** | 분석(v4-pro) + 단순포맷팅(flash) |

위 조건 중 하나라도 해당하면 NEVER 직접 처리하지 말고 MUST delegate_task로 분할한다.
"직접 처리할까?" 고민하는 것 자체가 NEVER 허용된다 (SOUL.md #1).

### 직접 처리 허용 (다음 모두 해당 시에만)

| 조건 | 예시 |
|------|------|
| **단일 툴 호출** | `web_search()`, `read_file()` |
| **이전 subagent 결과에 의존적** | A의 출력이 B의 입력이면 순차 처리 |
| **사용자에게 즉시 답변 필요** | "지금 몇 시야?", "이거 뜻이 뭐야?" |
| **1~2개 파일 생성/수정** | 단순 문서 편집 |
| **판단/승인이 필요한 작업** | "이거 해도 될까?" — subagent는 clarify 사용 불가 |

### 분할 전 MUST 검증 질문 3가지

delegate_task를 호출하기 전에 반드시 스스로에게 물을 것 (하나라도 NO면 순차 처리):

1. **"서브태스크들이 정말 독립적인가?"** → A의 결과 없이 B를 시작해도 되는가?
2. **"각 subagent가 충분한 컨텍스트를 갖는가?"** → context 필드에 모든 필요 정보가 들어있는가?
3. **"병렬로 보내도 충돌하지 않는가?"** → 같은 파일을 동시에 수정하려 하지 않는가? (git conflict)

3개 모두 YES면 병렬 MUST. 하나라도 NO면 순차 처리 또는 직접 처리.

### Subagent 모델 분류 — MUST 라우팅 테이블 준수 (SOUL.md #8)

delegate_task 호출 시 반드시 태스크 유형에 따라 정확한 모델을 지정한다:
- 분석/리서치/코드리뷰 → `deepseek-v4-pro`
- 코드작성/디버깅/테스트 → `deepseek-v4-pro`
- 문서/번역/글쓰기 → `qwen3.7-max`
- 자동화/모니터링 → `deepseek-v4-flash`
- 단순 작업/실험 → `deepseek-v4-flash`

model 파라미터 생략은 NEVER 허용. 태스크에 부적합한 모델 사용은 NEVER 허용.
"이 정도는 아무 모델이나 써도 되겠지"라는 판단은 NEVER 허용된다 (SOUL.md #8).

### 우선순위: 분할 트리거 충족 시 직접 처리 NEVER (SOUL.md #2)

규칙 #1의 분할 조건이 1개 이상 충족되면 "직접 처리"는 NEVER 선택할 수 없다. 분할 트리거가 0개일 때만 직접 처리를 고려한다. 의존성이 있으면 병렬 대신 순차 분할.

### MUST: delegate_task 호출 전 Decision Log

delegate_task 호출 전에 반드시 다음 로그를 생성한다 (누락 시 실행 금지, SOUL.md #1 + AGENTS.md §1):

```
## Decision Log — delegate_task
- split_trigger: [true/false]
- trigger_reason: [6개 조건 중 해당하는 것 모두 나열]
- model: [선택한 모델과 근거 — 라우팅 테이블 참조]
- toolsets: [선택한 툴셋]
- context_includes: [subagent에 전달한 정보 목록]
```

split_trigger=false인 경우에만 직접 처리를 허용하며, true인데 직접 처리하는 것은 NEVER 허용된다.

## delegate_task model override — 지원됨 (로컬 패치 v3.3.0)

### 패치 개요

`delegate_task`의 `DELEGATE_TASK_SCHEMA`와 함수 시그니처에 `model` 파라미터를 추가하여 subagent model override를 가능하게 함.

**적용 일자:** 2026-06-11
**적용 파일:** `~/.local/lib/python3.12/site-packages/tools/delegate_tool.py`

### 사용법

```python
# 단일 task — model 지정
delegate_task(
    model="deepseek-v4-pro",
    goal="코드 리뷰 분석",
    toolsets=["terminal", "file"],
)

# batch — per-task model override
delegate_task(tasks=[
    {"goal": "...", "model": "deepseek-v4-pro"},
    {"goal": "...", "model": "deepseek-v4-flash"},
])
```

### Model Resolution 우선순위

```
tasks[i].model (per-task)
      ↓  overrides
delegate_task(model=...) (top-level caller)
      ↓  overrides
config.yaml delegation.model
      ↓  fallback
parent session model
```

### 공식 레포 현황 (참고)

| 이슈/PR | 상태 | 내용 |
|---------|------|------|
| #31155 | OPEN | "delegation.model override ignored" — 우리가 겪은 문제 |
| #34472 | OPEN | 함수 파라미터만 추가 (스키마 누락) — 불완전 |
| #12794 | OPEN | 가장 큼 (3405줄), 스키마+함수+plugin |
| #35033 | OPEN | per-task + latent bug fix (356줄) |
| 병합된 PR | **0건** | 아직 공식 릴리스 안 됨 |

로컬 패치는 #34472의 함수 파라미터 접근 + #12794의 스키마 접근을 결합하여 5개 지점 수정.

### 적용된 패치 5개

| # | 위치 | 변경 |
|---|------|------|
| 1 | `DELEGATE_TASK_SCHEMA` properties | `model` (`type: string`) 프로퍼티 추가 |
| 2 | `DELEGATE_TASK_SCHEMA` tasks[].items.properties | per-task `model` (`type: string`) 프로퍼티 추가 |
| 3 | `delegate_task()` 시그니처 | `model: Optional[str] = None` 파라미터 추가 |
| 4 | creds resolve 직후 | `if model: creds = {**creds, "model": model}` caller override |
| 5 | `_build_child_agent()` 호출부 | `effective_task_model` per-task 처리 |
| 보너스 | `_build_top_level_description()` | MODEL OVERRIDE 설명 섹션 추가 |

### 검증 방법

```python
delegate_task(
    model="deepseek-v4-pro",
    goal="간단한 문법 체크",
    context="print('hello')",
    toolsets=["terminal"],
)
# subagent 결과에서 model 필드 확인
```

### config.yaml delegation 설정 (부가 제어 수단)

```yaml
delegation:
  model: deepseek-v4-pro       # 기본 subagent 모델
  provider: opencode-go        # provider
```

### 알려진 제한사항

1. `model`만 지정하고 `provider`는 별도로 넘길 수 없음 (현재 패치 범위 밖). provider 변경이 필요하면 config.yaml `delegation.provider` 또는 PR #12794의 provider 파라미터가 머지될 때까지 대기.
2. OpenRouter slug 사용 시 (예: `"openai/gpt-4o"`) provider 매핑이 config와 충돌할 수 있음. 이 경우 config.yaml의 `delegation.provider`가 `openrouter`여야 슬러그가 올바르게 라우팅됨.

### Provider per-task override — 미지원 (향후 과제)

현재 로컬 패치는 `model` override만 지원. `provider`는 `config.yaml delegation.provider`로 전역 고정.

**per-task provider override가 필요한 이유:**
- `github-copilot` provider의 코딩 특화 모델(`gpt-5.4-mini`, `gpt-4.1`)이 개발 태스크에 더 효율적
- Copilot Student 구독은 무료이므로 비용 절감 가능
- `animath` provider의 `claude-opus-4.8` 등 추론 특화 모델을 분석에 활용 가능

**구현 방안 (추후):**
1. `delegate_task()` 시그니처에 `provider: Optional[str]` 추가
2. `DELEGATE_TASK_SCHEMA`에 `provider` 프로퍼티 추가
3. `_build_child_agent()`에 `override_provider`로 전달 (이미 인자 있음)
4. 로컬 패치 범위로 충분히 구현 가능 (model override 패치와 동일 패턴)

## 구조적 한계 (Architectural Limitations)

이 시스템의 근본적인 한계. 인지하고 우회 전략을 사용할 것.

### 한계 1: 동기 실행 (Synchronous)

delegate_task는 **동기(synchronous)**: 부모 턴이 끝나기 전에 모든 subagent가 완료되어야 함.
- 사용자가 중간에 메시지를 보내면 모든 subagent 취소됨
- 10분 이상 걸리는 작업은 cronjob(delegate_task 아님) 사용
- 긴 작업은 `terminal(background=True, notify_on_complete=True)`로 위임

### 한계 2: Subagent 간 실시간 통신 불가

병렬 배치로 보낸 subagent들은 서로의 진행 상황을 알 수 없음.
- 정보는 반드시 부모를 통해서만 흐름
- A의 발견을 B가 실시간으로 활용하는 것은 불가능
- 의존성이 있는 태스크는 순차 처리 필수

### 한계 3: 컨텍스트 평탄화 손실

context 필드는 문자열. 구조화된 정보(코드, JSON, 표 등)가 자연어로 평탄화되면서 손실 발생.
- 가능하면 원본 파일 경로를 context에 포함시켜 subagent가 직접 읽게 할 것
- JSON/코드는 문자열로 임베드하지 말고 파일로 저장 후 경로 전달
- "분석 결과는 /tmp/analysis.json 참고" 형식

### 한계 4: 부모 모델의 분해 품질

현재 Hermes는 orchestrator 역할에 특화된 모델을 별도로 지정할 수 없음. 부모도 범용 모델 사용.
- 분해가 잘못되면 모든 subagent가 잘못된 방향으로 작업
- 분할 전 "검증 질문 3가지"를 반드시 거칠 것
- 의심스러우면 분할하지 말고 직접 처리

### 한계 5: Subagent가 구조적 context를 받지 못함

AGENTS.md, SOUL.md, 메모리 등은 subagent에 전달되지 않음.
- context에 필요한 모든 정보를 명시적으로 포함시킬 것
- "알잖아" / "저번에 했던 것처럼" 금지
- 역할 파일(`~/.hermes/roles/*.md`)을 context에 포함시키는 패턴 사용

### Subagent 결과의 model 필드 신뢰성

`delegate_task` 결과 딕셔너리의 `model` 필드는 `_run_single_child()` → `getattr(child, "model", None)` 값을 반환한다. 로컬 패치(v3.3.0) 적용 + gateway 재시작 후 `model="deepseek-v4-pro"` 지정 시 subagent 결과에 `"model": "deepseek-v4-pro"`가 정상적으로 표시되는 것을 확인함 (2026-06-11 테스트).

**주의**: 패치 후에도 gateway를 재시작하지 않으면 Python 모듈은 시작 시점의 코드를 메모리에 유지하므로 변경사항이 적용되지 않는다. 패치 후 반드시 `systemctl --user restart hermes-gateway` 또는 `hermes gateway restart`를 실행할 것.

**검증 방법:** subagent에게 직접 모델 식별을 요청하는 task를 보내거나, subagent 결과의 `model` 필드 + `tokens` 사용량을 교차 검증할 것.

### delegate_tool.py 패치 후 gateway 재시작 필요

`~/.local/lib/python3.12/site-packages/tools/delegate_tool.py`를 직접 수정한 경우, Hermes gateway 프로세스가 **시작할 때 메모리에 로드**한 코드를 계속 사용함. `.py` 파일을 수정해도 gateway를 재시작하기 전까지는 변경 사항이 적용되지 않음.

```bash
systemctl --user restart hermes-gateway
# 또는
hermes gateway restart
```

### `delegation.model` config이 무시되는 현상

config.yaml의 `delegation.model`이 설정되어 있어도 subagent가 parent의 모델을 상속받는 버그가 공식 레포에 보고됨 (#31155). 로컬 패치(v3.3.0)로 `model` 파라미터를 명시적으로 전달하면 우회 가능하지만, config 값만으로는 적용되지 않을 수 있음.

## Multi-Profile Architecture — delegate_task의 한계를 넘어

delegate_task의 구조적 한계(동기 실행, 메모리 공유, 스킬 미축적)가 임계점을 넘으면 **별도 Hermes 프로필**로 분리해야 한다. 이 섹션은 "언제 delegate_task로 충분하고, 언제 별도 프로필이 필요한가"를 판단하는 프레임워크다.

### delegate_task vs 별도 Hermes 프로필

| 특성 | delegate_task (임시 서브에이전트) | 별도 Hermes 프로필 (영구 에이전트) |
|------|----------------------------------|-----------------------------------|
| **생명주기** | 태스크 종료 시 소멸 | 24/7 독립 실행 (자체 gateway) |
| **MEMORY.md** | **부모와 공유** → 도메인 간 오염 | 프로필별 완전 격리 |
| **SKILLS** | 축적 불가 (매번 초기화, 콜드 스타트) | 도메인 특화 스킬 자동 축적 (Closed Learning Loop) |
| **모델** | 호출 시 model override | 프로필 config.yaml 기본값 사용 (항상 올바른 모델) |
| **툴셋** | 호출 시 toolsets 지정 | config.yaml로 고정 → **보안 격리 가능** (예: smarthome은 terminal/file 제외) |
| **사용자 접근** | 부모를 통해서만 (clarify 불가) | 자체 Discord 봇으로 직접 호출 가능 |

### 분리 판단 4단계 방법론

> 상세한 단계별 실행 가이드는 `references/multi-profile-migration-methodology.md` 참조.

**1단계: 크론 매핑** — 모든 cron job을 mode(no-agent vs LLM)와 실행 프로필별로 분류

**2단계: MEMORY.md 오염도 분석** — 현재 MEMORY.md 항목을 도메인별로 분류. 서로 다른 도메인의 기억이 한 파일에 섞여 토큰 낭비 + 자가 정리 압박을 유발하는지 측정

**3단계: delegate_task 패턴 분석** — 반복 호출되는 (역할, 모델, 컨텍스트) 조합 식별. 매번 동일한 역할 파일·모델 override를 반복하는 패턴이 승격 후보

**4단계: 승격 가치 평가** — 5개 축으로 점수화:

| 축 | 가중치 | 설명 |
|----|--------|------|
| 반복성 | 🔴 핵심 | 같은 유형의 태스크가 자주 delegating되는가? |
| 도메인 특수성 | 🔴 핵심 | 쌓이는 지식이 다른 도메인과 섞이면 안 되는가? |
| 콜드 스타트 비용 | 🟡 중요 | 매번 "처음부터" 배우는 데 드는 토큰 낭비가 큰가? |
| 모델 차별화 | 🟡 중요 | default와 다른 모델이 더 효율적인가? (예: writer=qwen, default=v4-pro) |
| 컨텍스트 오염도 | 🟢 부가 | 이 도메인의 메모리가 default MEMORY.md의 몇 %를 점유하는가? |

### 분리 가치가 없는 패턴 (함정 — MUST 확인)

**함정 1: 이미 no-agent script로 완전 분리된 크론**
- `Mode: no-agent (script stdout delivered directly)` → LLM이 전혀 개입하지 않음
- MEMORY.md, SOUL.md, SKILLS 어느 것도 사용하지 않음
- **프로필로 분리해도 아무 변화 없음** — 헛된 설정 부채만 증가
- 예: 트레이딩 스크립트, docker cleanup, power monitor

**함정 2: 1회성·저빈도 delegate_task**
- 연 1~2회 호출되는 패턴은 프로필 생성·관리 오버헤드가 더 큼
- 역할 파일 주입으로 충분

**함정 3: 도메인이 너무 작은 경우**
- 크론 1개 + 연간 수회 질문 수준 → 프로필 분리보다 MEMORY.md 항목 정리로 충분
- 예: TOEIC 알림 (크론 1개, LLM 관여 최소)

### 프로필 간 상호작용 모델

> **⚠️ 핵심 원칙: 기존 구조 절대 파괴 금지.** 새 프로필의 SOUL.md/AGENTS.md는 반드시 기존 역할 파일(`~/.hermes/roles/*.md`)에서 **발췌조립**한다. 오픈소스 검증된 역할 파일 구조는 한 글자도 수정하지 않는다. 새로 작성하는 것보다 검증된 원본을 재배열하는 것이 항상 더 나은 결과를 낸다. 상세 방법론은 `references/multi-profile-migration-methodology.md`의 "핵심 원칙: 기존 구조 보존 + 오픈소스 검증 우선" 섹션 참조.

현재 Hermes는 영상에서 언급된 `/meeting` 커맨드나 프로필 간 직접 통신을 지원하지 않는다. 다음 패턴으로 우회:

**패턴 A — Discord 라우팅 (사용자 주도)**
```
사용자 → #문서 채널 → writer 프로필 (자체 봇)
사용자 → #코드리뷰 채널 → reviewer 프로필 (자체 봇)
사용자 → #일반 채널 → default 프로필 (기존 봇)
```
장점: 각 프로필이 자기 MEMORY.md/SKILLS 축적. 단점: 여러 Discord 봇 관리 필요.

**패턴 B — default 중개 (delegate_task 유지)**
```
사용자 → default → delegate_task(model="qwen3.7-max", context=technical-writer.md)
```
장점: 단일 진입점, 기존 워크플로우 유지. 단점: 전문 프로필의 MEMORY.md/SKILLS 축적 불가.

**패턴 C — 크론 전달 (백그라운드 전용)**
```
knowledge 프로필 → cron 실행 → deliver to #클로-보고
meta-optimizer 프로필 → cron 실행 → deliver to #클로-보고
```
백그라운드 프로필은 Discord 봇 불필요. 결과만 채널로 deliver.

**권장 하이브리드:** 기본은 패턴 B(default 중개)로 시작. 반복성이 임계점을 넘으면 패턴 A로 승격. 크론 전용은 패턴 C.

### 실제 분리 사례 (khmo31 아키텍처)

| 프로필 | 분리 사유 | 모델 | 상호작용 |
|--------|----------|------|----------|
| `knowledge` | wiki-pipeline이 default MEMORY.md 30%+ 점유, LLM 크론으로 매일 실행 | v4-pro+flash | 패턴 C (크론 → #클로-보고) |
| `writer` | 모델 차별화(qwen3.7-max), Notion 문서화 반복성 최고 | qwen3.7-max | 패턴 B (default가 delegate_task) |
| `reviewer` | 코드리뷰 패턴 축적, dormant 프로필 재활성화 | v4-pro | 패턴 B (default가 delegate_task) |
| `smarthome` | 툴셋 제한 보안 격리 (terminal/file 미허용) | flash | 패턴 A (자체 봇, #스마트홈) |
| `meta-optimizer` | pipeline 최적화는 default 설정 변경 금지 규칙으로 격리 필수 | v4-pro | 패턴 C (크론 → #클로-보고) |

## 검증 루프 (Verification Protocol)

delegate_task 결과는 subagent의 **자기보고(self-report)** 이므로 반드시 검증해야 함. 다음 규칙을 지킬 것:

### 1. 파일 생성/수정 검증

subagent가 "파일을 작성했습니다"라고 보고하면:

```python
# subagent 결과를 받은 후
result = task_result["summary"]
# 직접 확인
content = read_file(path)["content"]
assert "expected content" in content  # 또는 search_files로 검증
# 실패 시 → 직접 수정하거나 재위임
```

### 2. 검색 결과 검증

subagent가 "검색 결과를 찾았습니다"라고 보고하면:

- 결과의 구체성 확인 (실제 숫자/날짜/인용이 있는가?)
- 가능하면 원문 URL 직접 방문 확인
- 모호한 결과("~인 것으로 보입니다")는 신뢰하지 말고 직접 검색

### 3. 주문/API 호출 검증

KIS 주문, Notion API 호출 등 외부 상태 변경:

- subagent가 claim한 URL/ID(order_id 등)를 직접 호출하여 확인
- "주문 접수됨" ≠ "주문 체결됨" — 반드시 confirm까지 확인

### 4. 여러 subagent 결과 충돌 시

- 더 구체적인 증거를 제시한 쪽 우선
- 파일 변경은 각각 읽어보고 병합
- 페이지 전체 덮어쓰기 금지 — patch(find/replace) 사용

### 5. subagent 결과 신뢰성 등급

| 등급 | 조건 | 후속 조치 |
|------|------|----------|
| ✅ 확실 | 검증 가능한 증거 포함 (파일 경로, URL, 숫자) | 신뢰 |
| ⚠️ 의심 | 증거 없이 "했습니다"만 보고 | 직접 확인 필수 |
| ❌ 불신 | 기존 사실과 모순, 모호한 표현 다수 | 재위임 또는 직접 수행 |

## MCP 미탑재 Fallback 패턴

delegate_task 서브에이전트는 config.yaml에 등록된 MCP를 신규 세션에서 로드한다. 하지만 **현재 세션이 config 변경 전에 시작된 경우** MCP가 상속되지 않을 수 있음.

**감지 방법**: subagent가 MCP 툴을 찾지 못하면 fallback 실행.

**Fallback 절차 (Notion 예시)**:

```
1. NOTION_API_KEY 환경변수 확인
2. curl/python으로 Notion REST API 직접 호출
   - POST /v1/search (페이지 탐색)
   - GET /v1/blocks/{id}/children (내용 읽기)
   - PATCH /v1/blocks/{id} (블록 수정)
3. 원문을 파일로 저장 (~/tmp/notion_input.txt)
4. delegate_task로 AI어투 제거 위임 (파일 기반)
5. 결과를 Notion API로 업데이트 (PATCH)
```

**MCP 없이 사용 가능한 Notion API 엔드포인트:**

| 작업 | 메서드 | 엔드포인트 |
|---|---|---|
| 페이지 검색 | POST | `/v1/search` |
| 블록 읽기 | GET | `/v1/blocks/{id}/children` |
| 블록 수정 | PATCH | `/v1/blocks/{id}` |
| 페이지 속성 수정 | PATCH | `/v1/pages/{id}` |

**env**: `NOTION_API_KEY` (ntn_...), `Notion-Version: 2022-06-28`

## 역할 정의서(role file) 구축 방법론

사용자 요청사항: **"각 레포를 하나도 빠짐없이 꼼꼼하게 읽고, 필요한 내용을 수정하지 말고 그대로 가져와서 역할로 정의"**

**6단계 워크플로우:**

1. **클론** — `git clone <url> ~/tmp/role-sources/<name>/`
2. **전체 탐색** — `find`로 모든 파일 목록, `search_files`로 내용 검색
3. **핵심 파일 집중 읽기** — CLAUDE.md, AGENTS.md, README.md, SKILL.md, 모든 agent 정의, 참조 문서
   - 빈 파일 / 단순 링크 파일 스킵
   - 각 파일의 핵심 내용을 구조화하여 정리
4. **원문 충실도 유지** — 내용을 '요약'하지 말고, 원문 표현을 그대로 살릴 것. 
   - 수치·고유명사·인용문·기술 용어 변경 금지
   - 코드 블록과 표 형식은 원본 그대로 유지
   - "~했다" 체의 원문은 유지, 불필요한 재가공 금지
5. **역할 정의서 구조**:
   - Identity / Workflow / Quality Gates / Rules / Anti-Patterns / References
   - 각 섹션은 원문의 핵심 내용을 그대로 인용
6. **교차 검증** — 생성된 역할 정의서 다시 읽고 누락 확인

**다중 레포 통합 원칙**:
- 상호 보완적이면 통합 (충돌 시 별도 표기)
- 충돌 시 원문 우선, 통합 시 출처 표기

## Notion MCP 대기 시간 관리

Notion MCP + delegate_task 조합 사용 시 주의:
- Notion MCP는 `inherit_mcp_toolsets: true` 설정으로 subagent에 상속
- 서브에이전트는 fresh Hermes session에서 config.yaml을 새로 읽으므로 MCP 사용 가능 (현재 세션이 config 변경 전에 시작된 경우에도 적용됨)
