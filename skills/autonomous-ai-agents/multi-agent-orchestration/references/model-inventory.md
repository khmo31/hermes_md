# Model Inventory — 2026.06.10 기준 (공식 문서 기반)

⚠️ **이 파일은 공식 문서에서 직접 추출한 정보입니다.**
- OpenCode Go: https://opencode.ai/docs/ko/go
- Copilot Models: https://docs.github.com/en/copilot/reference/ai-models/supported-models

## OpenCode-go (14개 구독 모델 + 5 free, 월 $10 정액)

출처: https://opencode.ai/docs/ko/go

### 구독 모델

| 모델 | 컨텍스트 | 추천 도메인 | 비고 |
|------|---------|----------|------|
| `opencode-go/deepseek-v4-pro` | 128K | 복잡 개발, deep analysis, 코드리뷰 | **최우선 사용** |
| `opencode-go/deepseek-v4-flash` | 128K | 일상 코드, 요약, 리서치 | **2순위, 대부분 용도** |
| `opencode-go/qwen3.7-max` | 128K | 문서 작성, 한국어 글쓰기 | 문서 작업에 특화 |
| `opencode-go/qwen3.7-plus` | 128K | 보조 문서, 일반 QA | |
| `opencode-go/qwen3.6-plus` | 128K | 일반 QA | |
| `opencode-go/kimi-k2.6` | 200K+ | 대용량 문서 분석 | 가장 긴 컨텍스트 |
| `opencode-go/kimi-k2.7-code` | 128K | 코드 작성, CAD 설계 | kimi-k2.6 기반 코드 특화 |
| `opencode-go/kimi-k2.5` | 200K | 대용량 문서 | 구버전, k2.6 우선 |
| `opencode-go/glm-5.1` | 128K | 중국어 번역/처리 | Zhipu AI 최신 |
| `opencode-go/glm-5` | 128K | 중국어 처리 | 구버전 |
| `opencode-go/mimo-v2.5-pro` | ? | 범용 fallback | |
| `opencode-go/mimo-v2.5` | ? | 범용 경량 | |
| `opencode-go/minimax-m3` | ? | 크리에이티브, 스토리 | |
| `opencode-go/minimax-m2.7` | ? | 크리에이티브 | m3 우선 |
| `opencode-go/minimax-m2.5` | ? | 크리에이티브 | m3 우선 |

### Free Tier (비용 0)

| 모델 | 용도 | 제약 |
|------|------|------|
| `opencode/deepseek-v4-flash-free` | 간단 코드, 테스트 | 속도 제한 있을 수 있음 |
| `opencode/mimo-v2.5-free` | 범용 경량 | |
| `opencode/big-pickle` | 극단순 태스크 | 성능 낮음 |
| `opencode/nemotron-3-ultra-free` | NVIDIA 모델 | 실험적 |
| `opencode/north-mini-code-free` | 경량 코딩 | |

---

## GitHub Copilot (25개 모델, OpenCode OAuth 인증 후 사용 가능)

**상태**:
- ✅ 2026.06.10 — CLI 조회 완료 (모델 목록 확인)
- ✅ 2026.06.10 — Paperclip opencode_local adapter 감지 확인
- ✅ 2026.06.11 — **Desktop TUI 실행 확인 완료 (5개 모델)**
- ⚠️ 2026.06.11 — Headless Server CLI에서는 동일 5개 모델 빈 응답 (환경 의존적)
- ❌ `mai-code-1-flash`는 `opencode models` 목록에 없음

**인증 방법**: `opencode plugin opencode-copilot-auth -g` → `opencode providers login --provider github-copilot`

### CLI 조회 모델 목록 (opencode models CLI 출력 기준)

| 모델 | 제공사 | Desktop TUI | Headless Server | 비고 |
|------|--------|:-----------:|:---------------:|------|
| `github-copilot/claude-sonnet-4` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-sonnet-4.5` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-sonnet-4.6` | Anthropic | ❌ model_not_supported | ❌ | API 거부 |
| `github-copilot/claude-haiku-4.5` | Anthropic | ✅ **실행 확인** | ⚠️ 빈 응답 | 경량 서브 |
| `github-copilot/claude-opus-4.5` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.6` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.6-fast` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.7` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.7-fast` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.8` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/claude-opus-4.8-fast` | Anthropic | ❌ 미테스트 | ❌ | |
| `github-copilot/gpt-5-mini` | OpenAI | ✅ **실행 확인** | ⚠️ 빈 응답 | 경량 범용 |
| `github-copilot/gpt-5.2` | OpenAI | ❌ model_not_supported | ❌ | API 거부 |
| `github-copilot/gpt-5.2-codex` | OpenAI | ❌ 미테스트 | ❌ | |
| `github-copilot/gpt-5.3-codex` | OpenAI | ❌ 미테스트 | ❌ | |
| `github-copilot/gpt-5.4` | OpenAI | ❌ model_not_supported | ❌ | API 거부 |
| `github-copilot/gpt-5.4-mini` | OpenAI | ✅ **실행 확인** | ⚠️ 빈 응답 | 서브 디버깅 |
| `github-copilot/gpt-5.4-nano` | OpenAI | ❌ integrator 미허용 | ❌ | opencode 플랜 미포함 |
| `github-copilot/gpt-5.5` | OpenAI | ❌ model_not_supported | ❌ | API 거부 |
| `github-copilot/raptor-mini` | OpenAI | ❌ model_not_supported | ❌ | API 거부 |
| `github-copilot/gpt-4.1` | OpenAI | ⚠️ 미확인 | ⚠️ 빈 응답 | 불안정 |
| `github-copilot/gemini-2.5-pro` | Google | ❌ 미테스트 | ❌ | |
| `github-copilot/gemini-3-flash-preview` | Google | ✅ **실행 확인** | ⚠️ 빈 응답 | 문서/주석 |
| `github-copilot/gemini-3.1-pro-preview` | Google | ✅ **실행 확인** | ⚠️ 빈 응답 | **기획 메인** |
| `github-copilot/gemini-3.5-flash` | Google | ❌ 미테스트 | ❌ | |
| `github-copilot/kimi-k2.7-code` | Moonshot AI | ❌ 미테스트 | ❌ | 코드/CAD 특화 |

### Copilot 모델 실행 상태 요약

| 카테고리 | 개수 | 설명 |
|---------|:----:|------|
| ✅ Desktop TUI 실행 확인 | 5 | user desktop에서 안정적 동작 확인 |
| ⚠️ Server CLI 빈 응답 | 5 | Desktop과 동일 모델, 서버에서 응답 없음 |
| ❌ 모델 미테스트/기타 | 15 | API 거부, integrator 미허용, 미테스트 |
| ✅ 실행 성공 (서버) | 0 | 서버 opencode run CLI로 안정적 실행 불가 |

### 환경별 Copilot 동작 편차 (중요)

같은 `opencode-copilot-auth` 플러그인이지만 실행 환경에 따라 결과가 완전히 다름:

| 환경 | 동작 모드 | Copilot 실행 | 설명 |
|------|----------|:-----------:|------|
| **Desktop** | opencode TUI (대화형) | ✅ **5개 정상** | 플러그인 스트리밍 정상 |
| **Headless Server** | `opencode run -m` (CLI) | ❌ **빈 응답** | 플러그인 스트리밍/ID 매핑 불완전 |

**규칙**: 서버 환경에서 Copilot 모델 사용이 필요하면 `opencode run -m <model> "Reply 'ok'"` 로 먼저 검증 후 적용. Desktop TUI 결과를 서버에 적용하지 말 것.

---

## 용도별 최적 모델 매트릭스 (실제 테스트 기반)

| 작업 종류 | 1순위 | 2순위 | 3순위 | 비고 |
|---------|-------|-------|-------|------|
| 백엔드 API 개발 | v4-pro | v4-flash | | OpenCode |
| 프론트엔드 개발 | v4-pro | v4-flash | | OpenCode |
| 디버깅 | v4-pro | v4-flash | | OpenCode |
| 코드리뷰 | v4-pro | v4-flash | | OpenCode |
| PR 작성 | v4-pro | v4-flash | qwen3.7-max | |
| 문서/README | qwen3.7-max | qwen3.7-plus | v4-pro | 한국어 최적 |
| 기술 리서치 | v4-pro | kimi-k2.6 | v4-flash | |
| 대용량 문서 | kimi-k2.6 | kimi-k2.5 | v4-pro | 200K+ ctx |
| RSS/뉴스 요약 | v4-flash | big-pickle 🆓 | | 저비용 우선 |
| 크론 자동화 | v4-flash | big-pickle 🆓 | | |
| 번역 | qwen3.7-max | glm-5 | | |
| 스토리/카피 | minimax-m3 | qwen3.7-max | minimax-m2.7 | |
| 단순 QA | v4-flash | glm-5 | big-pickle 🆓 | |
| 무료 테스트 | big-pickle 🆓 | nemotron-3-ultra-free 🆓 | | |
| 크리에이티브 | minimax-m3 | qwen3.7-max | minimax-m2.5 | |
| CAD 설계 | kimi-k2.7-code | v4-pro | | OpenCode/파라메트릭 3D |

> ⚠️ Copilot Student 모델은 VS Code에서 실제 확인 후 매트릭스에 추가 필요.
> 이 표는 OpenCode Go로 실제 테스트 완료된 모델만 포함함.

## 업데이트 이력

- 2026.06.10 v3: 실제 OpenCode Go 테스트 결과 반영. 실패/불안정 모델 제거. Copilot Student ≠ Copilot Pro 정정.
- 2026.06.10 v2: Copilot 모델 전면 수정. 공식 문서 기준으로 GPT-4o/Llama-405b 등 제거하고 GPT-5.5/Claude Opus 4.8 등 실제 모델로 대체.
- 2026.06.10 v1: 최초 작성 (오류 포함: Copilot 모델을 GitHub Models로 잘못 기재)
