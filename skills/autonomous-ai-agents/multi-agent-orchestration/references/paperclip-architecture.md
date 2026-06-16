# Paperclip 아키텍처 참고 (멀티에이전트 오케스트레이션 관점)

## 개요

Paperclip(paperclipai/paperclip, ⭐69.8k)은 **AI Agent Control Plane** — 여러 AI 에이전트를 회사 조직처럼 관리하는 플랫폼.

## 서버 설정

### 의존성 설치

```bash
cd ~/paperclip
pnpm install
```

pnpm은 isolated mode 사용. 실제 패키지는 `node_modules/.pnpm/` virtual store에 있고, `server/node_modules/`가 entry point.

### Config 파일

위치: `~/.paperclip/instances/default/config.json`  
(환경변수 PAPERCLIP_CONFIG 로 override 가능)

최적 설정 예시:

```json
{
  "$meta": {
    "version": 1,
    "updatedAt": "2026-06-10T00:00:00Z",
    "source": "configure"
  },
  "server": {
    "deploymentMode": "local_trusted",
    "exposure": "private",
    "host": "127.0.0.1",
    "port": 3100,
    "serveUi": true
  },
  "database": {
    "mode": "embedded-postgres",
    "backup": {
      "enabled": true,
      "intervalMinutes": 120,
      "retentionDays": 3
    }
  },
  "logging": {
    "mode": "file"
  },
  "auth": {
    "disableSignUp": true,
    "baseUrlMode": "auto"
  },
  "telemetry": {
    "enabled": false
  }
}
```

### ⚠️ Config Schema 핵심 주의사항

| 문제 | 설명 |
|------|------|
| **`$meta` ≠ `meta`** | 스키마 키는 `$meta` ($ prefix 필수). `meta`로 쓰면 파싱 실패 → 모든 값이 default로 fallback |
| **`logging` 필수** | `mode: "file"` 또는 `"cloud"` 필수. 기본값 없음. 빠뜨리면 파싱 실패 |
| **`local_trusted` + loopback 강제** | `local_trusted` 모드는 반드시 `127.0.0.1` 바인딩. `host: "0.0.0.0"` 또는 `bind: "lan"` 설정하면 서버 시작 시 에러 throw |
| **LAN 접속** | SSH 터널 (`ssh -L 3101:localhost:3100 -p <port> user@host`) 로 우회. 또는 `authenticated` 모드 필요 |

스키마 소스: `packages/shared/src/config-schema.ts`

### 서버 실행/종료

```bash
# 실행
cd ~/paperclip/server && PATH="$PWD/node_modules/.bin:$PATH" tsx src/index.ts

# 종료
pkill -f "tsx.*src/index"
```

로그: `~/.paperclip/instances/default/logs/server.log`

## 핵심 트리거 메커니즘

Paperclip의 Agent 실행 트리거는 heartbeat(polling)만 있는 게 아님.

### WakeupOptions (소스코드 기준)

```typescript
// server/src/services/heartbeat.ts
interface WakeupOptions {
  source: "timer" | "assignment" | "on_demand" | "automation";
  triggerDetail?: "manual" | "ping" | "callback" | "system";
}
```

| source | 설명 | 지연 |
|--------|------|------|
| `timer` | 주기적 heartbeat (설정된 interval) | 최대 interval 시간 |
| `assignment` | **Issue가 Agent에게 할당되는 순간 즉시 wakeup** | 거의 0 (enqueueWakeup 호출 → 바로 실행) |
| `on_demand` | API 호출 / UI "지금 깨우기" 버튼 | 거의 0 |
| `automation` | Routine/webhook 트리거 | 거의 0 |

### enqueueWakeup() 동작 방식

```typescript
enqueueWakeup(agentId, {
  source: "assignment",     // 즉시 트리거
  reason: "issue_assigned",
  contextSnapshot: {
    issueId: "DEV-42",
    taskId: "DEV-42", 
    taskTitle: "로그인 API 구현"
  }
})
```

`policy.wakeOnDemand`가 활성화되어 있어야 non-timer source가 동작함.

### Routine Webhook Trigger

```typescript
// server/src/services/routines.ts
source: "schedule" | "manual" | "api" | "webhook";
//                                ^^^^^^^ 외부 HTTP 요청으로 routine 실행 가능
```

Routine을 webhook 트리거로 설정하면, 외부 시스템(Discord, GitHub, Linear 등)에서 
`POST /api/routine-triggers/:publicId/fire` 로 호출하여 Agent를 실행할 수 있음.

### Plugin Webhook 시스템

```typescript
// server/src/routes/plugins.ts
POST /api/plugins/:pluginId/webhooks/:endpointKey
// 외부 시스템이 plugin에 webhook 전달
// → plugin이 issue 생성 + assignment → enqueueWakeup()으로 Agent 즉시 실행
```

## 멀티에이전트 동시 실행

### 격리 보장

Paperclip은 각 Agent를 **완전히 격리된 프로세스**로 실행:

```typescript
// 각 Agent의 hermes-paperclip-adapter가 별도 프로세스 spawn
hermes chat -q "..." -m opencode-go/deepseek-v4-pro --yolo --source tool
hermes chat -q "..." -m opencode-go/qwen3.7-max --yolo --source tool
// ↑ 같은 시점에 다른 모델로 실행 가능
```

### 동시성 제어

- Agent별 `maxConcurrentRuns` 설정 가능 (기본 1)
- Issue Tree Hold: Issue 트리 단위 실행 락 (race condition 방어)
- Assignee 시스템: 하나의 Issue는 한 Agent만 처리

### Org Tree 구성

Agent 생성 시 `reportsTo` 필드로 조직도 구성:

```bash
# CEO 역할 agent 생성
curl -X POST "/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{"name":"Lead (v4-pro)","adapterType":"hermes_local","role":"ceo","adapterConfig":{"model":"deepseek-v4-pro","provider":"opencode-go"}}'

# 하위 agent 생성 후 reportsTo 연결
curl -X PATCH "/api/agents/$WORKER_ID" \
  -H "Content-Type: application/json" \
  -d '{"reportsTo":"$LEAD_ID"}'
```

유효한 role 값: `ceo`, `cto`, `cmo`, `cfo`, `security`, `engineer`, `designer`, `pm`, `qa`, `devops`, `researcher`, `general`

각 agent는 서로 다른 `adapterType`과 `adapterConfig`를 가질 수 있어 모델/제공자별 분할 가능:
- `hermes_local`: Hermes CLI 사용. `adapterConfig.model`, `adapterConfig.provider` 설정
- `opencode_local`: OpenCode CLI 사용. `adapterConfig.model` 설정 (예: `opencode-go/deepseek-v4-pro`)
- `acpx_local`: ACP 프로토콜 사용. `adapterConfig.agent` = `claude` | `codex` | `custom`

## Hermes-Paperclip 연결 구조

### Adapter 타입

현재 master 브랜치 기준 built-in adapter 목록:

| 타입 | 용도 | CLI 필요 |
|------|------|----------|
| `hermes_local` | Hermes Agent spawn | `hermes` |
| `opencode_local` | OpenCode CLI spawn | `opencode` |
| `acpx_local` | ACP 프로토콜 (Claude Code/Codex/Custom) | `claude` / `codex` / custom |
| `claude_local` | Claude Code 직접 실행 | `claude` |
| `codex_local` | Codex CLI 직접 실행 | `codex` |

등록 상태 확인:
```bash
curl http://localhost:3100/api/adapters
```

### Hermes adapter 동작 방식

Paperclip이 `hermes chat -q "<prompt>" -Q` 명령어로 Hermes CLI를 **자식 프로세스로 spawn**:

1. 프롬프트 템플릿에 Paperclip API URL, Agent ID, 태스크 정보를 주입
2. Hermes Agent가 `curl`로 Paperclip API를 호출하며 작업 수행
3. 완료 후 Paperclip API로 결과 보고

핵심 config 필드 (`adapterConfig`):
- `model`: 사용할 모델명 (예: `deepseek-v4-pro`)
- `provider`: 제공자 (예: `opencode-go`)
- `hermesCommand`: Hermes CLI 경로 override (기본: `hermes`)

### OpenCode + Copilot 연결

OpenCode CLI는 `opencode-copilot-auth` 플러그인으로 GitHub Copilot 사용 가능:

```bash
# 플러그인 설치 (global 권장)
opencode plugin opencode-copilot-auth -g

# 로그인 (device code OAuth — 브라우저 필요)
opencode providers login --provider github-copilot --method "Login with GitHub Copilot"
# → GitHub.com 선택 → 브라우저에서 device code 인증
```

플러그인이 인증되면 OpenCode에 Copilot 모델이 등록되고, Paperclip의 `opencode_local` adapter도 자동 감지.

## OpenCode 모델 인벤토리

Paperclip의 `opencode_local` adapter가 표시하는 모델들 (2026.06 기준):

- `opencode-go/deepseek-v4-pro` — 🏆 코딩/추론 최강
- `opencode-go/deepseek-v4-flash` — ⚡ 빠름
- `opencode-go/qwen3.7-max` — 한국어 글쓰기 최상
- `opencode-go/qwen3.7-plus` / `qwen3.6-plus`
- `opencode-go/kimi-k2.6` / `kimi-k2.5` — 긴 컨텍스트
- `opencode-go/glm-5` / `glm-5.1`
- `opencode-go/mimo-v2.5` / `mimo-v2.5-pro`
- `opencode-go/minimax-m3` / `m2.7` / `m2.5` — 크리에이티브
- `opencode/big-pickle` 🆓
- `opencode/deepseek-v4-flash-free` 🆓
- `opencode/nemotron-3-ultra-free` 🆓

## Discord → Paperclip 연동 파이프라인

```
Discord 메시지
    ↓ (Discord Webhook)
Routine Webhook or Plugin Webhook
    ↓
Issue 생성 + assigneeAgentId 지정
    ↓
enqueueWakeup(agentId, {source: "assignment"})
    ↓
Agent 즉시 실행 (heartbeat 대기 없음)
    ↓
작업 완료 → Issue 상태 변경
    ↓ (선택: Agent skill로 curl Discord Webhook)
Discord에 결과 알림
```

## Resource & Quota Management (6단계 밸런스형 오케스트레이션)

Paperclip에 6단계 밸런스형 오케스트레이션을 구성하려면 각 단계별로 별도 Agent를 생성하고, 태스크 성격에 맞게 수동 라우팅한다.

### 6개 에이전트 구성 예시

```bash
CID="your-company-id"

# S1: 기획/분석 — gemini-3.1-pro-preview
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S1-Planner",
    "adapterType": "opencode_local",
    "role": "pm",
    "adapterConfig": {"model": "github-copilot/gemini-3.1-pro-preview"}
  }'

# S2: 코드베이스 로딩 — kimi-k2.6
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S2-Scanner",
    "adapterType": "opencode_local",
    "role": "engineer",
    "adapterConfig": {"model": "opencode-go/kimi-k2.6"}
  }'

# S3/S5: 핵심 로직 + 디버깅 — deepseek-v4-pro
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S3-Core-Dev",
    "adapterType": "opencode_local",
    "role": "engineer",
    "adapterConfig": {"model": "opencode-go/deepseek-v4-pro"}
  }'

# S4: 보일러플레이트 양산 — deepseek-v4-flash
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S4-Mass-Producer",
    "adapterType": "opencode_local",
    "role": "engineer",
    "adapterConfig": {"model": "opencode-go/deepseek-v4-flash"}
  }'

# S6: 테스트/문서화 — qwen3.7-plus
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "S6-QA-Docs",
    "adapterType": "opencode_local",
    "role": "qa",
    "adapterConfig": {"model": "opencode-go/qwen3.7-plus"}
  }'

# Lead (orchestrator) — 모든 태스크 분기점
curl -s -X POST "http://localhost:3100/api/companies/$CID/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lead (orchestrator)",
    "adapterType": "hermes_local",
    "role": "ceo",
    "adapterConfig": {
      "model": "deepseek-v4-pro",
      "provider": "opencode-go",
      "hermesCommand": "/home/khmo31/.local/bin/hermes"
    }
  }'
```

### Copilot 쿼터 관리 전략

- **Copilot 에이전트(S1-Planner)는 필요할 때만 활성화** — 항상 켜두면 쿼터 증발
- **OpenCode 에이전트(S2~S6)는 상시 대기** — rate limit이 넉넉함
- 순차 태스크가 아닌 병렬 태스크는 쿼터 소모 2~3배 급증하므로 주의
- Copilot 모델 사용 전 서버에서 `opencode run -m <model> "Reply 'ok'"`로 실행 가능 여부 반드시 검증

## 리소스 요구사항

| 항목 | 예상 |
|------|------|
| 서버 프로세스 (Express + UI) | ~200 MB RAM |
| PGLite (내장 DB) | ~50 MB RAM |
| Agent 1개 (Hermes chat -q) | ~90 MB RAM (별도 프로세스) |
| node_modules | ~500 MB - 1 GB 디스크 |
| 포트 | 3100 (기본) |

## Paperclip으로 할 수 있는 것 vs 없는 것

### ✅ 가능
- Issue assignee 변경 시 Agent 즉시 wakeup
- Routine webhook으로 외부 트리거 수신
- 다중 Agent 동시 실행 (각각 다른 모델/컨텍스트)
- Agent 작업 durability (Hermes 세션과 무관하게 지속)
- 비용/예산 트래킹

### ❌ 불가능 (우리가 직접 해야 함)
- 태스크 자동 분류 (Paperclip엔 Classifier 없음 — 사람이 assign)
- 결과 검증 (Verification Layer 없음 — Agent self-report)
- 모델별 라우팅 (Adapter는 고정 — 모델 전환은 Agent config 변경)
- 외부 알림 push (Plugin/Skill로 직접 구현 필요)

## 참고: 소스코드 검증 방법

Paperclip의 실제 동작 방식을 이해하려면 **공식 문서만 보지 말고 소스코드를 직접 확인**할 것.

```bash
# Config 스키마
packages/shared/src/config-schema.ts
  → `$meta` required, `logging` required (no default)

# Network bind 검증
packages/shared/src/network-bind.ts
  → `local_trusted` + `bind != loopback` → 에러

# Heartbeat/wakeup 시스템
server/src/services/heartbeat.ts
  → WakeupOptions, enqueueWakeup()

# Issue assign wakeup  
server/src/routes/issues.ts
  → assignmentWakeSkipped, assignee 변경 시 wakeup 로직

# Routine webhook
server/src/services/routines.ts
  → source: "webhook", webhookSecret, fire endpoint

# Plugin webhook
server/src/routes/plugins.ts
  → webhookDeps, POST /api/plugins/:id/webhooks/:key

# Adapter registry
server/src/adapters/registry.ts
  → built-in adapter 등록 목록 (13개 + external plugin loader)

# Hermes adapter execute
node_modules/.pnpm/hermes-paperclip-adapter@0.2.0/.../dist/server/execute.js
  → prompt template, CLI flag 구성

# OpenCode adapter execute
packages/adapters/opencode-local/src/server/execute.ts
  → model/provider 파싱, CLI spawn

# ACPX adapter
packages/adapters/acpx-local/src/server/execute.ts
  → agent: "claude" | "codex" | "custom"
```

## 관련 링크

- Repo: https://github.com/paperclipai/paperclip
- Docs: doc/SPEC-implementation.md, doc/GOAL.md, doc/PRODUCT.md
- Hermes adapter: https://github.com/NousResearch/hermes-paperclip-adapter
- AGENTS.md: 프로젝트 루트의 AGENTS.md에 전체 가이드 있음
- OpenCode Copilot plugin: https://npmjs.com/package/opencode-copilot-auth
