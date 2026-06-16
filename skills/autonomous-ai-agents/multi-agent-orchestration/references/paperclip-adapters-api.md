# Paperclip Adapter Types & Plugin API

## Adapter Type Overview (2026.06.11 기준)

| Type | Source | 용도 |
|------|--------|------|
| `acpx_local` | builtin | Apple Xcode |
| `claude_local` | builtin | Claude Code CLI |
| `codex_local` | builtin | OpenAI Codex CLI |
| `cursor` | builtin | Cursor editor |
| `cursor_cloud` | builtin | Cursor Cloud |
| `gemini_local` | builtin | Gemini CLI |
| `grok_local` | builtin | Grok CLI |
| `hermes_local` | **external plugin** | Hermes CLI (모든 Hermes 툴) |
| `http` | builtin | HTTP endpoint |
| `opencode_local` | builtin | OpenCode CLI (기본값) |
| `pi_local` | builtin | Pi CLI |

## Adapter Plugin API (External)

외부 어댑터 플러그인 관리를 위한 REST API 엔드포인트:

### 설치
```bash
POST /api/adapters/install
{
  "packageName": "@henkey/hermes-paperclip-adapter",
  "isLocalPath": false,
  "version": "latest"  # optional
}
```

### 목록 조회
```bash
GET /api/adapters
```

### 단일 조회
```bash
GET /api/adapters/hermes_local
```

### 설정 스키마 조회
```bash
GET /api/adapters/hermes_local/config-schema
```

### 토글/비활성화
```bash
PATCH /api/adapters/hermes_local
{ "disabled": true }
```

### 재시작 없이 리로드
```bash
POST /api/adapters/hermes_local/reload
```

### 재설치
```bash
POST /api/adapters/hermes_local/reinstall
```

### 제거
```bash
DELETE /api/adapters/hermes_local
```

## hermes_local Capabilities (v0.4.3)

```json
{
  "supportsInstructionsBundle": false,
  "supportsSkills": true,
  "supportsLocalAgentJwt": true,
  "requiresMaterializedRuntimeSkills": false,
  "supportsModelProfiles": false
}
```

## Hermes Profile 격리 모델

Paperclip의 hermes_local 에이전트는 `adapterConfig.profile`로 Hermes profile을 선택한다.
각 profile은 독립된 config/memory/skill을 가짐:

| Profile | Config 위치 | 기본 모델 |
|---------|------------|----------|
| `default` | `~/.hermes/config.yaml` | (현재 설정) |
| `coder` | `~/.hermes/profiles/coder/config.yaml` | deepseek-v4-pro |
| `researcher` | `~/.hermes/profiles/researcher/config.yaml` | deepseek-v4-flash |
| `reviewer` | `~/.hermes/profiles/reviewer/config.yaml` | deepseek-v4-pro |

profile별 config는 모델/프로바이더/toolset을 독립적으로 설정 가능:
```yaml
# ~/.hermes/profiles/coder/config.yaml
model:
  default: deepseek-v4-pro
  provider: opencode-go
toolsets:
- hermes-cli
terminal:
  backend: local
```
