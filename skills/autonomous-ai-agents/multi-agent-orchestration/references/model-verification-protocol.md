# Model Verification Protocol

모델에 대한 정보를 보고할 때 반드시 따를 것.  
"공식 문서에 GPT-5.5 있다고 써있음"만으로 "사용 가능"이라고 판단하지 말 것.

## 3-Step Verification

### Step 1: 공식 문서 확인

해당 플랫폼의 최신 문서에서 **플랜별 모델 접근 권한**을 반드시 확인:

| 플랫폼 | 문서 URL | 중요 포인트 |
|--------|---------|----------|
| GitHub Copilot | https://docs.github.com/en/copilot/reference/ai-models/supported-models | **Copilot Student ≠ Copilot Pro**. Student는 Free와 동일 수준. Pro 전용 모델(Opus, Fable, Goldeneye) 접근 불가. |
| OpenCode Go | https://opencode.ai/docs/ko/go | 구독에 포함된 모델 목록만 사용 가능. API로 조회되는 모든 모델이 Go 구독에 포함되는 것은 아님. |

**문서 추출 팁**: GitHub Docs는 JS 렌더링. HTML 소스에서 `<table>` 태그를 직접 파싱하거나, `curl` + Python으로 구조화된 데이터 추출:

```python
import re
tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
for t in tables:
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
    for r in rows:
        cells = re.findall(r'<(?:th|td)[^>]*>(.*?)</(?:th|td)>', r, re.DOTALL)
        # process cells
```

### Step 2: CLI/API로 실제 접근 가능 모델 조회

문서와 실제 접근 권한이 다를 수 있음. 반드시 실환경에서 조회:

```bash
# OpenCode Go
opencode models

# OpenCode Go API (직접)
curl -s "https://opencode.ai/zen/go/v1/models" \
  -H "Authorization: Bearer $API_KEY" | python3 -c "import json,sys; [print(m['id']) for m in json.load(sys.stdin)['data']]"

# Copilot Chat (VS Code 내)
# → `/models` 명령어 실행
# → CLI: gh copilot ... (설치된 경우)
```

### ⚠️ 중요: Discovery ≠ Execution (추가 레이어)

CLI나 API로 모델이 조회된다고 해당 모델로 **실제 태스크를 실행할 수 있는 것은 아니다.** 특히 third-party provider 통합(Copilot, 등)의 경우:

1. **integrator별 접근 제한**: Copilot API는 integrator(opencode, copilot-chat 등)별로 접근 가능한 모델 서브셋을 제한함. `opencode models`는 Copilot 전체 카탈로그를 보여주지만, `opencode` integrator는 그중 일부만 사용 가능.
2. **모델 ID 매핑 문제**: `github-copilot/claude-sonnet-4.6`같은 prefixed ID가 Copilot API가 기대하는 `claude-sonnet-4.6`와 다를 수 있음. opencode-copilot-auth 플러그인이 이 매핑을 담당하지만 불완전할 수 있음.
3. **API 버전 호환성**: 일부 Copilot 모델은 chat completions만 지원하고 streaming/tool-calling을 지원하지 않아 OpenCode에서 정상 작동하지 않을 수 있음.

**규칙**: Discovery 단계(CLI/API 조회)와 Execution 단계(`opencode run` 실제 테스트)를 항상 분리하여 보고.

### ⚠️ 중요: 환경별 실행 편차 (Desktop TUI vs Headless Server)

동일한 provider 통합 플러그인이어도 **실행 환경(TUI vs CLI)에 따라 모델 동작이 완전히 다를 수 있다.**

**실제 사례**: `opencode-copilot-auth` 플러그인

| 환경 | 실행 방식 | Copilot 실행 결과 |
|------|----------|:----------------:|
| **Desktop** | `opencode` TUI (대화형 세션) | ✅ **5개 모델 정상 응답** |
| **Headless Server** | `opencode run -m` (CLI) | ❌ **동일 5개 모델 빈 응답** |

**가설**: TUI 모드가 플러그인의 스트리밍 파이프라인과 모델 ID 매핑을 다르게 처리하거나, API 호출 시 다른 헤더/파라미터를 전송함.

**규칙**:
1. 모델 테스트는 **실제 운영 환경에서만** 실행할 것 (desktop TUI 결과 ≠ server CLI 결과)
2. Paperclip + opencode_local 조합으로 모델을 쓸 거라면, 서버에서 `opencode run -m`으로 먼저 검증
3. Desktop TUI에서만 확인된 모델을 서버에 적용하지 말 것

### Step 3: 각 모델 간단 기능 테스트

모델이 실제로 명령을 따르는지 검증:

```bash
opencode run -m "opencode-go/deepseek-v4-pro" --dangerously-skip-permissions "Reply exactly 'ok'" --format json
```

**판정 기준**:
- `'ok'` 또는 `OK` 응답 → ✅ 통과
- exit code 0이나 응답 없음 → ⚠️ 불안정 (명령 미준수)
- exit code != 0 또는 timeout → ❌ 실패
- 응답 속도 20s+ → ⚠️ 느림, 단순 작업에는 부적합

## 인벤토리 업데이트 규칙

1. **테스트 통과한 모델만** 인벤토리에 포함
2. 실패/불안정 모델은 **명시적으로 제외 목록에 기록**
3. 각 모델의 **응답 속도**도 함께 기록 (fallback 우선순위 결정용)
4. 플랜 변경/모델 추가 시 **재테스트** 필수

## 실제 테스트 예시 (2026.06.10)

### OpenCode Go (18개 모델)

| 모델 | 결과 | 응답 시간 | 비고 |
|------|------|----------|------|
| deepseek-v4-pro | ✅ | 14s | |
| deepseek-v4-flash | ✅ | 13s | |
| qwen3.7-max | ✅ | 14s | |
| qwen3.7-plus | ✅ | 11s | |
| qwen3.6-plus | ✅ | 12s | |
| kimi-k2.6 | ✅ | 12s | |
| kimi-k2.5 | ✅ | 13s | |
| glm-5 | ✅ | 9s | 빠름 |
| mimo-v2.5-pro | ✅ | 23s | 느림 |
| minimax-m3 | ✅ | 10s | |
| minimax-m2.7 | ✅ | 13s | |
| minimax-m2.5 | ✅ | 11s | |
| big-pickle | ✅ | 10s | 🆓 |
| nemotron-3-ultra-free | ✅ | 27s | 🆓 느림 |
| hy3-preview | ❌ | - | 실행 실패 |
| mimo-v2-pro | ❌ | - | 실행 실패 |
| mimo-v2-omni | ❌ | - | 실행 실패 |
| qwen3.5-plus | ❌ | - | 실행 실패 |
| glm-5.1 | ⚠️ | 13s | 명령 미준수 |
| mimo-v2.5 | ⚠️ | 10s | 명령 미준수 |
| deepseek-v4-flash-free | ⚠️ | 10s | 명령 미준수 |
| mimo-v2.5-free | ⚠️ | 10s | 명령 미준수 |
| north-mini-code-free | ⚠️ | 9s | 명령 미준수 |

### Copilot Student (VS Code에서 확인 필요, 미테스트)

공식 문서 기준 Copilot Student = Copilot Free 수준.  
예상 모델: GPT-5 mini, GPT-5.4, GPT-5.4 mini, Claude Haiku 4.5, Claude Sonnet 4.6, MAI-Code-1-Flash, Raptor mini

### Copilot via OpenCode (2026.06.11, desktop TUI 실행 확인)

`opencode-copilot-auth` 플러그인 설치 + OAuth 인증 후 사용 가능.  
CLI 조회 시 25개 모델 확인. Desktop TUI에서 5개 모델 안정적 실행 확인.

| 모델 | Desktop TUI | Server CLI | 비고 |
|------|:-----------:|:----------:|------|
| `github-copilot/claude-haiku-4.5` | ✅ | ⚠️ 빈 응답 | 경량 서브 |
| `github-copilot/gemini-3-flash-preview` | ✅ | ⚠️ 빈 응답 | 문서/주석 |
| `github-copilot/gemini-3.1-pro-preview` | ✅ | ⚠️ 빈 응답 | 기획 메인 |
| `github-copilot/gpt-5-mini` | ✅ | ⚠️ 빈 응답 | 경량 범용 |
| `github-copilot/gpt-5.4-mini` | ✅ | ⚠️ 빈 응답 | 서브 디버깅 |
| 나머지 20개 | ❌ or 미테스트 | ❌ | API/model_not_supported 등 |

**Desktop TUI에서 안정적 실행 확인된 Copilot 모델 5개** — 6단계 오케스트레이션 서브로 배치하여 쿼터 관리.

**경고**: Desktop TUI 결과를 Headless Server의 Paperclip/opencode_local 연동에 그대로 적용하지 말 것. 서버 환경에서 `opencode run -m`으로 재검증 필수.
