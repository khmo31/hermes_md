# AGENTS.md — Hermes Agent 개발·의사결정 가이드

이 문서는 Hermes가 태스크를 처리하는 방식을 정의한다. SOUL.md가 "무엇을 해야 하는가"를 정의한다면, AGENTS.md는 "어떻게 결정하고 실행하는가"를 정의한다.

---

## 1. 직접 처리 vs delegate_task 판단 (MUST 준수)

### delegate_task로 분할해야 하는 경우 (하나라도 해당 시 MUST 분할)

| 조건 | 예시 |
|------|------|
| **독립적 서브태스크 2개 이상** | "A 기능 구현 + B 기능 테스트" → 각각 subagent |
| **툴셋이 다른 작업 혼합** | 웹 검색 + 코드 작성 → web vs terminal/file |
| **중간 결과가 컨텍스트 오염 우려** | 큰 파일 생성, API 응답 대량 포함 |
| **예상 턴 수 10턴 이상** | 복잡한 분석, 여러 파일 수정 |
| **사용자가 명시적으로 분할 요청** | "하위 에이전트 써서", "병렬로" |
| **서로 다른 모델 필요** | 분석(v4-pro) + 단순포맷팅(flash) |

위 조건 중 하나라도 해당하면 NEVER 직접 처리하지 말고 MUST delegate_task로 분할한다.

### 직접 처리 허용 (다음 모두 해당 시에만)

| 조건 | 예시 |
|------|------|
| **단일 툴 호출** | `web_search()`, `read_file()` |
| **이전 subagent 결과에 의존적** | A의 출력이 B의 입력이면 순차 처리 |
| **사용자에게 즉시 답변 필요** | "지금 몇 시야?", "이거 뜻이 뭐야?" |
| **1~2개 파일 생성/수정** | 단순 문서 편집 |
| **판단/승인이 필요한 작업** | "이거 해도 될까?" — subagent는 clarify 사용 불가 |

### 분할 전 MUST 검증 3가지 질문

delegate_task 호출 전에 반드시 자문할 것 (하나라도 NO면 순차 처리):

1. **서브태스크들이 정말 독립적인가?** — A의 결과 없이 B를 시작해도 되는가?
2. **각 subagent가 충분한 컨텍스트를 갖는가?** — context 필드에 모든 필요 정보가 들어있는가?
3. **병렬로 보내도 충돌하지 않는가?** — 같은 파일을 동시에 수정하려 하지 않는가?

3개 모두 YES → 병렬 MUST. 하나라도 NO → 순차 처리 또는 직접 처리.

분할이 필요하다고 판단되면 "직접 해도 되지 않을까?" 고민하는 것은 NEVER 허용된다.

---

## 2. 모델 라우팅 퀵 레퍼런스 (7그룹)

| 그룹 | 태스크 | 1순위 | 2순위 | 툴셋 |
|------|--------|-------|-------|------|
| 🔍 Research & Analysis | 리서치, 코드분석, 코드리뷰, 기획, 취약점분석 | `deepseek-v4-pro` | `kimi-k2.6` | file, web |
| ⚡ Development | 코드작성, 디버깅, 백엔드, 프론트, 테스트 | `deepseek-v4-pro` | `deepseek-v4-flash` | terminal, file |
| 📝 Writing & Docs | 문서, README, 번역, 한국어글쓰기, AI어투제거 | `qwen3.7-max` | `qwen3.7-plus` | file |
| 🎨 Creative | 스토리, 카피, 블로그, 광고 | `minimax-m3` | `qwen3.7-max` | file |
| 📄 Long Docs | 대용량문서(200K+), PDF분석 | `kimi-k2.6` | `kimi-k2.5` | file |
| 🔄 Automation | 크론, RSS, 뉴스, 모니터링, 알림 | `deepseek-v4-flash` | `big-pickle` 🆓 | web, terminal |
| 🪶 Light | 단순QA, 간단편집, 실험 | `deepseek-v4-flash` | `big-pickle` 🆓 | terminal, file |

### 역할 파일 기준 라우팅 (추가 참조)

| 트리거 키워드 | 역할 파일 | 1순위 모델 | 툴셋 |
|---|---|---|---|
| 노션, 문서, 작성, AI어투, 편집, 초안 | `technical-writer.md` | `qwen3.7-max` | file |
| 번역, 다국어, 영문화 | `technical-writer.md` | `qwen3.7-max` | file |
| 블로그, 카피, 스토리 | `technical-writer.md` | `minimax-m3` | file |
| 분석, 조사, 리서치, 비교, 트렌드 | `researcher.md` | `deepseek-v4-pro` | web, file |
| 기획, 설계, 아키텍처, 요구사항 | `researcher.md` | `deepseek-v4-pro` | file |
| 대용량 문서 처리 (200K+) | `researcher.md` | `kimi-k2.6` | file |
| 로그인, CRUD, API, DB, 백엔드, 서버 | `coder.md` | `deepseek-v4-pro` | terminal, file |
| UI, 프론트, CSS, 컴포넌트, React | `coder.md` | `deepseek-v4-pro` | terminal, file |
| 버그, 오류, 디버깅 | `coder.md` | `deepseek-v4-pro` | terminal, file |
| 테스트, 검증, QA | `coder.md` | `deepseek-v4-pro` | terminal, file |
| 코드리뷰, PR, 코드검토 | `researcher.md` | `deepseek-v4-pro` | file, web |

### 부모 모델 권고

- **오케스트레이션 시:** `deepseek-v4-pro` 권장. 분할 판단, 모델 선택, 검증 루프 등 일관된 의사결정을 위해 flash로는 부족하다. 부모 호출 횟수는 적어 비용 증가폭은 미미.
- **분석/리서치/코드리뷰:** 무조건 `deepseek-v4-pro` 사용. `deepseek-v4-flash`는 일반 대화/단순 작업 전용.
- **단순 응답 시:** `deepseek-v4-flash` 사용.

---

## 3. 툴셋 선택 규칙

| 툴셋 | 사용 조건 |
|------|----------|
| `file` | 파일 읽기/쓰기/검색만 필요한 작업 (문서, 글쓰기, 분석) |
| `terminal` | 셸 명령 실행이 필요한 작업 (코딩, 빌드, 설치, git) |
| `web` | 웹 검색, URL fetch가 필요한 작업 (리서치, 데이터 수집) |
| `terminal, file` | 코드 구현, 디버깅, 테스트 |
| `web, terminal` | 자동화, 크론, 모니터링 |
| `web, file` | 리서치, 분석, 조사 |

---

## 4. 검증 루프 (Verification Protocol)

delegate_task 결과는 subagent의 **자기보고**이므로 반드시 검증한다.

### 파일 생성/수정 검증
```
result = delegate_task(...)
# subagent가 "파일을 작성했습니다"라고 보고 → 직접 read_file로 확인
content = read_file(path)
# 실패 시 직접 수정하거나 재위임
```

### 검색 결과 검증
- 결과의 구체성 확인 (실제 숫자/날짜/인용이 있는가?)
- 가능하면 원문 URL 직접 방문 확인
- 모호한 결과("~인 것으로 보입니다")는 신뢰하지 말고 직접 검색

### 주문/API 호출 검증
- subagent가 claim한 order_id/URL을 직접 호출하여 확인
- "주문 접수됨" ≠ "주문 체결됨"

### 충돌 해결
- 더 구체적인 증거를 제시한 쪽 우선
- 파일 변경은 각각 읽어보고 병합
- 페이지 전체 덮어쓰기 금지 — `patch` 사용

---

## 5. Subagent 제한사항

Subagent(=`delegate_task`로 생성된 Hermes 세션)는 다음 기능을 사용할 수 **없다**:

- ❌ `clarify` — 사용자에게 질문 불가. 모든 정보는 context에 명시적으로 포함해야 함
- ❌ `memory` — 부모의 대화 기록/메모리에 접근 불가. 필요한 정보는 context 필드에 직접 전달
- ❌ `send_message` — 디스코드/텔레그램 등 메시지 전송 불가
- ❌ `execute_code` — 별도 코드 실행 샌드박스 사용 불가 (terminal은 사용 가능)
- ❌ `cronjob` — 크론 작업 등록/수정 불가

context에 필요한 모든 정보를 명시적으로 포함시킬 것. "알잖아", "저번에 했던 것처럼" 금지.

---

## 6. 구조적 한계 (Architectural Limitations)

### 한계 1: 동기 실행
delegate_task는 동기적이다. 부모 턴이 끝나기 전에 모든 subagent가 완료되어야 한다. 10분 이상 작업은 `terminal(background=True, notify_on_complete=True)`로 위임.

### 한계 2: Subagent 간 통신 불가
병렬 배치로 보낸 subagent들은 서로의 진행 상황을 알 수 없다. 정보는 반드시 부모를 통해서만 흐른다.

### 한계 3: 컨텍스트 평탄화 손실
context 필드는 문자열. JSON/코드는 파일로 저장 후 경로 전달할 것. "분석 결과는 /tmp/analysis.json 참고" 형식.

### 한계 4: 부모 모델의 분해 품질
부모가 orchestrator 전용 모델을 별도로 지정할 수 없다. 분해가 잘못되면 모든 subagent가 잘못된 방향으로 작업한다. 의심스러우면 분할하지 말고 직접 처리.

### 한계 5: Subagent가 구조적 context를 받지 못함
AGENTS.md, SOUL.md, 메모리 등은 subagent에 전달되지 않는다. 역할 파일(`~/.hermes/roles/*.md`)을 context에 포함시키는 패턴을 사용한다.

---

## 7. delegate_task model override 사용법

```python
# 단일 task
delegate_task(
    model="deepseek-v4-pro",
    goal="코드 리뷰 분석",
    context="...",
    toolsets=["terminal", "file"],
)

# batch — per-task model override
delegate_task(tasks=[
    {"goal": "...", "model": "deepseek-v4-pro", "toolsets": ["file"]},
    {"goal": "...", "model": "deepseek-v4-flash", "toolsets": ["terminal"]},
])
```

### Model Resolution 우선순위
```
tasks[i].model (per-task)
     ↓  overrides
delegate_task(model=...) (top-level)
     ↓  overrides
config.yaml delegation.model
     ↓  fallback
parent session model
```

### Provider 제한
`model` 파라미터는 override 가능하지만 provider는 `config.yaml delegation.provider`(opencode-go)로 고정된다. provider 변경이 필요하면 config.yaml 수정 필요.

---

## 8. MCP Fallback

delegate_task 서브에이전트는 config.yaml의 MCP 설정을 신규 세션에서 로드한다. MCP가 상속되지 않으면 curl/python으로 REST API 직접 호출로 fallback (특히 Notion).

---

## 참조

- `~/.hermes/skills/autonomous-ai-agents/multi-agent-orchestration/SKILL.md` — 전체 오케스트레이션 스킬 (분할 기준, 라우팅 테이블, 검증 루프, 의존성 규칙, 역할 주입 시스템)
- `~/.hermes/skills/autonomous-ai-agents/orchestrator-delegation-strategy/SKILL.md` — 외부 에이전트 CLI 활용 전략
- `~/.hermes/SOUL.md` — 에이전트 정체성 및 글쓰기 스타일
- `~/.hermes/roles/` — 역할 정의 파일 (coder, researcher, technical-writer)
