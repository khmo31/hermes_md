# GBrain — Multi-Agent Orchestration & Knowledge System

> **소스:** https://github.com/garrytan/gbrain (⭐21.9k)
> **제작자:** Garry Tan (President & CEO of Y Combinator)
> **철학:** "Search gives you raw pages. GBrain gives you the answer."
> **규모:** 146,646 pages, 24,585 people, 5,339 companies, 66 cron jobs (Garry's production deployment)

GBrain은 개인 지식 브레인 및 GStack mod로, agent platform 위에서 동작한다. PGLite (WASM 내장 Postgres) 또는 Postgres + pgvector 하이브리드 검색을 지원한다. CLI와 MCP 서버 모두 단일 `src/core/operations.ts`에서 생성되는 contract-first 설계 방식이다.

GStack이 agent에게 코딩을 가르친다면, GBrain은 그 외의 모든 것——brain ops, signal detection, content ingestion, enrichment, cron scheduling, reports, identity, access control——을 가르친다.

---

## 1. Two-Axis Mental Model: Brain + Source

GBrain 지식은 **두 개의 직교 축**으로 구성된다. 사용자와 에이전트 모두 이 구조를 이해해야 하며, 그렇지 않으면 쿼리가 자동으로 잘못 라우팅된다.

### Brain (DB 축)
- **Brain = 데이터베이스.** PGLite 파일, 자체 호스팅 Postgres, 또는 Supabase.
- 각 brain은 고유의 `pages` 테이블, `chunks` 테이블, `embeddings` 등을 가진다.
- **`host`** — 기본 brain (`~/.gbrain/config.json`에 설정). **`mounts`** — 추가 brain (`~/.gbrain/mounts.json`에 등록, `gbrain mounts add <id>`).
- 라우팅: `--brain <id>` → `GBRAIN_BRAIN_ID` → `.gbrain-mount` dotfile → mount path 최장 일치 → fallback: `'host'`

### Source (Repo 축, v0.18.0+)
- **Source = brain 내부의 명명된 콘텐츠 repo.** 모든 `pages` 행은 `source_id`를 가진다.
- Slug는 전역이 아니라 source 기준으로 유일하다. 같은 slug가 `source=wiki`와 `source=gstack` 아래에 각각 존재할 수 있다.
- 라우팅: `--source <id>` → `GBRAIN_SOURCE` → `.gbrain-source` dotfile → registered `local_path` match → `sources.default` config → `sole_non_default` auto-route (v0.41.13) → fallback: `'default'`

### 축 선택 기준

| 상황 | 조정 대상 |
|---|:---:|
| 같은 brain 내에서 다른 repo 작업 (wiki → gstack) | `--source` |
| 팀이 공개한 brain 조회 | `--brain` |
| 특정 주제를 개인 검색에서 격리 | `--source` + `federated=false` |
| brain을 팀과 공유 | `--brain` (mount team brain) |
| 개인 brain에 새 repo 추가 | `--source` via `gbrain sources add` |
| 팀 brain 추가 | `--brain` via `gbrain mounts add` |

**경험 법칙:** 데이터 소유자가 바뀌면 brain 경계. 소유자는 같은데 주제/repo가 바뀌면 source 경계.

### Topology 예시

**개인 brain + 여러 source:**
```
host brain (~/.gbrain)
├── source: wiki      (federated=true)   — personal notes, people, companies
├── source: gstack    (federated=true)   — gstack plans, learnings
├── source: openclaw  (federated=true)   — openclaw docs, memos
└── source: essays    (federated=false)  — draft essays, isolated on purpose
```

**CEO-class 다중 팀 멤버십:**
```
host brain (개인 DB)          mount: media-team      mount: policy-team      mount: portfolio
├── wiki                      ├── wiki               ├── wiki                 ├── companies
├── essays                    ├── pipeline            ├── research             ├── deals
├── gstack                    └── enriched            └── letters              └── diligence
└── openclaw
```

Cross-brain 쿼리는 **latent-space federation** 방식——agent가 brain 목록을 보고 필요시 재조회. SQL federation이 아니다.

---

## 2. Trust Boundary — 신뢰 경계 설계

GBrain은 **신뢰된 로컬 CLI 호출자**와 **신뢰되지 않은 원격 에이전트 호출자**를 구분한다.

### OperationContext.remote (v0.27+, F7b hardening)

```typescript
export interface OperationContext {
  engine: BrainEngine;
  config: GBrainConfig;
  logger: Logger;
  dryRun: boolean;
  auth?: AuthInfo;
  remote: boolean;  // REQUIRED — 타입 시스템의 첫 방어선
  jobId?: number;
  subagentId?: number;
  viaSubagent?: boolean;
  // ...
}
```

| 출처 | `remote` 값 | 신뢰 수준 |
|---|:---:|---|
| `src/cli.ts` (로컬 CLI) | `false` | **Trusted** — OS 수준 신뢰 |
| `src/mcp/server.ts` (MCP stdio/HTTP) | `true` | **Untrusted** — agent-facing |
| 미래의 제3자 transport | `undefined` 가능 | **Fail-closed** — untrusted로 간주 |

### Trust is Fail-Closed (핵심 불변 규칙 #1)

- `OperationContext.remote`은 타입에 **REQUIRED** 필드.
- `strictly false`가 아니면 모두 remote/untrusted로 처리.
- `ctx.remote === false` → trusted-only site 허용
- `ctx.remote !== false` → untrust-unless-explicit-false
- undefined/falsy 기본값으로 설정하지 말 것 (타입 우회 캐스트에 대비한 defense-in-depth)

### 보안 민감 작업

- `file_upload`: `remote=true`일 때 `root` 디렉토리로 파일 시스템 제한, 심볼릭 링크 차단, 경로 탐색 방지. `remote=false`일 때는 완화된 검증.
- `submit_job`: PROTECTED_JOB_NAMES (synthesize/patterns/consolidate)는 `ctx.remote === false`일 때만 허용. MCP는 제출 불가.
- `think`의 `--save`/`--take` 플래그: 원격 호출자에 대해 비활성화.

### Source Isolation

모든 읽기 작업은 `sourceScopeOpts(ctx)`를 통해 라우팅된다:
- 우선순위: `federated array (ctx.auth.allowedSources)` > `scalar (ctx.sourceId)` > 없음
- 소스 필터링을 수동 구현하지 말 것——누락된 스레드는 cross-source 데이터 누출이다.
- MCP/원격 호출자는 `ctx.auth.sourceId` / `ctx.auth.allowedSources`를 통해 제한됨. 서버 프로세스의 CLI source 컨텍스트를 상속받지 못함.

### AuthInfo (OAuth 2.1)

```typescript
export interface AuthInfo {
  clientId: string;
  scopes: string[];  // 'read' | 'write' | 'admin' | 'sources_admin' | 'users_admin'
  userId?: string;
  sourceId?: string;           // 쓰기 권한 (단일 source)
  allowedSources?: string[];   // 읽기 권한 (federation)
}
```

v0.34.1 (#876)에서 `federated_read` 추가: OAuth 클라이언트는 `sourceId`(쓰기)와 독립적인 `allowedSources`(읽기)를 가질 수 있다. 빈 배열 `[]` = "sourceId 외에는 연합 읽기 없음". undefined = "v60 백필이 아직 안 됨" — 하위 호환성 위해 scalar sourceId로 폴백.

### Protected Operations (Trusted Local Only)

```typescript
const PROTECTED_JOB_NAMES = [
  'synthesize',  // dream cycle synthesis (영향: 모든 합성 페이지 생성)
  'patterns',    // dream cycle patterns (영향: 패턴 인식)
  'consolidate', // dream cycle consolidation (영향: 메모리 통합)
] as const;
```

원격 호출자가 protected job name으로 `submit_job`을 시도하면 `permission_denied` 에러 반환.

---

## 3. Search Modes (v0.32.3)

GBrain은 세 가지 named search mode를 제공한다. 설치 시점에 선택하며, 모든 경로는 `src/core/search/mode.ts`를 통해 해석된다.

### Mode Configuration

| Knob | `conservative` | `balanced` | `tokenmax` |
|---|:---:|:---:|:---:|
| `cache.enabled` | true | true | true |
| `cache.similarity_threshold` | 0.92 | 0.92 | 0.92 |
| `cache.ttl_seconds` | 3600 | 3600 | 3600 |
| `intentWeighting` | true | true | true |
| `tokenBudget` | **4000** | **12000** | **off** |
| `expansion` (LLM multi-query) | false | false | **true** |
| `relationalRetrieval` (v0.42.34) | false | **true** | **true** |
| `searchLimit` default | 10 | 25 | 50 |

### Cost Matrix (Mode × Downstream Model)

Chunk ~400 tokens 기준. 월 10K 쿼리 기준 (일반 단일 사용자), 전체 검색 페이로드, 캐시 미적용:

| Mode \ Downstream | Haiku 4.5 ($1/M) | Sonnet 4.6 ($3/M) | Opus 4.7 ($5/M) |
|---|:---:|:---:|:---:|
| conservative (~4K) | **$40/mo** | $120/mo | $200/mo |
| balanced (~10K) | $100/mo | $300/mo | $500/mo |
| tokenmax (~20K) | $200/mo | $600/mo | **$1,000/mo** |

**코너 간 25x spread.** 자연스러운 매칭은 약 4x 범위:
- tokenmax + Opus → ~$700/mo (최고 품질)
- balanced + Sonnet → ~$430/mo (sweet spot)
- conservative + Haiku → ~$170/mo (비용 민감)

캐시 히트는 모든 비용을 약 50% 절감. Anthropic prompt caching 적용 시 추가 50-80% 할인.

### Resolution Chain

```
per-call SearchOpts → per-key config (search.cache.enabled, ...) →
  MODE_BUNDLES[search.mode] → MODE_BUNDLES.balanced (fallback)
```

### Relational Retrieval (v0.42.34.0)

`balanced`/`tokenmax`에서 활성화. seed entity를 확인하고 typed-edge graph를 탐색하여 (`src/core/search/relational-recall.ts`), edge 기반 답변을 RRF에 주입. 동일 source 내에서 결정론적이며, 멘션은 기본적으로 제외. 비관계형 쿼리에는 no-op.

### knobs_hash Cache Key

검색 캐시 키는 의도치 않은 크로스-모드 캐시 히트를 방지하기 위해 설정 knob들의 해시를 포함. v=2→3에서 embedding 컬럼명 포함, v=9→10에서 relationalRetrieval knob + depth 포함. 업그레이드 시 일회성 miss spike 발생.

### CLI Surface

```
gbrain search modes              # 현재 모드 + knob attribution 확인
gbrain search modes --reset      # search.* override 제거
gbrain search stats [--days N]   # cache hit rate, intent mix, budget drops
gbrain search tune [--apply]     # data-driven recommendations
```

---

## 4. Cross-Cutting Invariants

시스템 전반의 불변 규칙. 어떤 파일을 수정하든 절대 위반하지 말 것.

### 1. Trust is Fail-Closed
- `OperationContext.remote`는 REQUIRED. undefined/falsy 기본값 금지.
- `ctx.remote === false`만 trusted. 나머지는 모두 untrusted.

### 2. Source Isolation
- 모든 read-side op는 `sourceScopeOpts(ctx)`를 통해 라우팅.
- 우선순위: `allowedSources[]` > `sourceId` > 없음.
- 수동 source 필터링 금지.

### 3. JSONB: Never JSON.stringify into a ::jsonb cast
- postgres.js는 이중 인코딩; PGLite는 버그를 숨김.
- raw object를 `engine.executeRaw`에 전달하거나 `executeRawJsonb` 사용.
- `scripts/check-jsonb-pattern.sh`가 CI에서 검증.

### 4. Engine Parity (Lockstep)
- `postgres-engine.ts`와 `pglite-engine.ts`는 함께 움직임.
- 새 method/SQL은 두 엔진 모두에 추가. `test/e2e/engine-parity.test.ts`로 고정됨.
- 전방 참조 컬럼/인덱스는 bootstrap probe set에 포함.

### 5. Contract-First
- `src/core/operations.ts`가 단일 진실 공급원; CLI + MCP가 여기서 생성됨.
- 모든 op는 `scope: 'read'|'write'|'admin'|'sources_admin'|'users_admin'` + 선택적 `localOnly`를 가짐.
- HTTP dispatch는 handler 실행 전에 scope/localOnly를 강제.

### 6. Migrations
- Schema DDL은 `src/core/migrate.ts`의 `MIGRATIONS` 배열에 위치.
- `CREATE INDEX CONCURRENTLY`는 `transaction: false` 필요.
- PGLite용 `sqlFor.pglite` 분기 제공.

### 7. Multi-Source
- Slug uniqueness는 `(source_id, slug)` 복합 키 기준.
- Key batch ops와 reverse-writes는 복합 키를 사용.
- `validateSourceId`를 모든 `source_id` 경로 결합 전에 호출.

### 8. Canonical Pricing (Chat Pricing)
- 모든 유료 클라우드 채팅/완성 가격은 `src/core/model-pricing.ts`의 `CANONICAL_PRICING` + `canonicalLookup`에 한 번만 위치.
- 다른 모든 테이블은 DERIVED VIEW. 가격 표류가 구조적으로 불가능.
- Embeddings 가격은 별도로 `embedding-pricing.ts` (다른 단위).

---

## 5. Evaluation & Benchmarks

### 핵심 벤치마크

| 벤치마크 | 성능 | 비교 |
|---|:---:|:---:|
| BrainBench | **P@5 49.1%, R@5 97.9%** | 240페이지 고급 코퍼스 |
| BrainBench vs graph-disabled | **+31.4점 P@5** | 그래프 비활성화 + BM25+벡터 RAG 대비 |
| LongMemEval | **Recall@5 97.60%** | 이전 SOTA 96.6% 돌파 |

### Eval Methodology

**데이터셋:**
- **LongMemEval** — public split, n=500 questions. Hugging Face에서 다운로드, 특정 commit에 고정.
- **Replay captures** — NDJSON from gbrain-evals repo, n=200 queries.
- **BrainBench v1** — n=1240 documents / n=350 qrels (binary relevance judgments).

**통계 규율:**
- **Paired bootstrap** — 10,000 resamples per metric. Question-level pairs 사용.
- **Bonferroni correction** — 12 comparisons (3 modes × 4 metrics)에 대해 적용.
- **95% CI** — bootstrap distribution에서 계산. CI가 0을 포함하거나 adj. p > 0.05이면 "not significant".

**Metric Glossary:** 모든 `gbrain eval *` 또는 `gbrain search stats` 명령어가 출력하는 metric은 `src/core/eval/metric-glossary.ts`를 통해 사람이 읽을 수 있는 설명 제공. JSON 출력에는 `_meta.metric_glossary` 블록 포함. `docs/eval/METRIC_GLOSSARY.md`는 CI에 의해 최신 상태 유지.

### Eval Loop (4-Command)

```bash
# ① Capture (contributor mode 필요)
export GBRAIN_CONTRIBUTOR_MODE=1

# ② Snapshot baseline
gbrain eval export --since 7d > baseline.ndjson

# ③ Code change

# ④ Replay against baseline
gbrain eval replay --against baseline.ndjson
```

**Output metrics:**
| Metric | 의미 | 건강 범위 |
|---|---|---|
| Mean Jaccard@k | 현재와 캡처된 slug 세트 간 평균 중복 | ≥0.85 neutral |
| Top-1 stability | #1 결과가 동일한 쿼리 비율 | ≥85% |
| Mean latency Δ | 현재 - 캡처 지연시간 | ±50ms 이내 |

### Eval Gate (v0.41+)

```bash
gbrain eval gate --baseline X.baseline.ndjson --qrels Y.qrels.json
```

- **Regression gate** (`--baseline`): 리팩터링이 검색을 망가뜨렸는지 감지.
- **Correctness gate** (`--qrels`): 알려진 정답 쿼리로 recall@K 측정.
- **Privacy posture:** 공개 baseline은 hermetic-synthetic 전용. 실제 사용자 캡처는 로컬 `~/.gbrain/baselines/`에 고립.

### Search Mode Methodology

`gbrain eval run-all --modes conservative,balanced,tokenmax --suites longmemeval,replay --seed 42` 스윕으로 비교. 모든 결과는 커밋된 NDJSON에서 재현 가능. Pre-registered expectations 문서화 (haters-immune methodology).

---

## 6. Company Brain Capabilities — 조직 단위 지식 관리

개인 brain을 회사 brain으로 확장하면 세 가지가 추가된다:

### 1. Multi-Source with OAuth Scoping
- 각 팀원은 고유한 OAuth credential을 가짐.
- `--source` = 쓰기 권한 (단일 source에 한정).
- `--federated-read` = 읽기 권한 (여러 source로 연합).
- SQL 계층에서 cross-source 읽기를 차단, 데이터베이스가 격리를 강제.

### 2. Per-Person Folders, Crons, and Skills
```bash
# 소스 기반 (Model A — 진정한 multi-user, 다양한 AI 클라이언트)
gbrain auth register-client alice-example \
  --grant-types client_credentials \
  --scopes read,write \
  --source customers \
  --federated-read customers,shared
```

```bash
# 디렉토리 기반 (Model B — one-agent-serves-everyone)
# 한 source 내 partners/<slug>/ 규약 사용
```

### 3. Access Models

**Model A (권장 — 진정한 multi-user):**
- 각 팀원이 자신의 OAuth 클라이언트를 가짐.
- 각자 자신의 AI 클라이언트(Claude Code, Cursor, OpenClaw 등)를 사용.
- 격리가 데이터베이스에서 강제됨.

**Model B (단순 — one agent serves everyone):**
- 단일 source, `partners/<slug>/` 디렉토리 규약.
- 에이전트가 강제하는 격리 (관례 기반).
- 한 에이전트가 Telegram 등으로 모두를 서빙할 때 적합.

### Example Per-Source Structure
```
customers/
├── alice-example/
│   ├── customers/acme-co.md
│   └── meetings/2026-05-21-acme-renewal.md
├── bob-example/
│   └── customers/orbit-bio.md
└── shared-customers/
    └── all-active-deals.md
```

### Company Brain Scope Isolation

- Alice가 "performance review" 검색 → `customers`와 `shared`만 조회. `internal`의 리뷰는 볼 수 없음.
- Bob이 같은 검색 → `internal`과 `shared` 조회. `customers`의 데이터는 볼 수 없음.
- **제로 누출 보장** — 모든 읽기 경로에서 fuzz-test 완료.

### Botmaster Onboarding Pattern
1. **Pre-populate** — 팀원의 슬라이스에 USER.md, concepts, sources, 예시 brain entries 시드 (약 20분).
2. **Walk through wow flows** — 합성 시연, gap 분석, write-back 흐름 (약 15분).
3. **Graduate to DM** — wow moment가 정착된 후 credential 제공.

---

## 7. Contract Pattern — 선언적 계약 기반 에이전트 설계

> **이것이 gbrain의 핵심 차별점이다.** 단일 `operations.ts` 파일이 CLI, MCP, tools-json의 단일 진실 공급원이다.

### Operation Interface

```typescript
export interface Operation {
  name: string;           // 예: 'get_page', 'query', 'search'
  description: string;    // 에이전트가 읽는 설명
  params: Record<string, ParamDef>;  // { name: { type, required, description } }
  handler: (ctx: OperationContext, params: Record<string, unknown>) => Promise<unknown>;
  mutating?: boolean;     // 쓰기 작업 표시
  scope?: 'read' | 'write' | 'admin' | 'sources_admin' | 'users_admin';
  localOnly?: boolean;    // 원격 호출자에게 노출 금지
  cliHints?: {
    name?: string;        // CLI 명령어 이름
    aliases?: string[];   // 대체 CLI 명령어 (v114/#1941)
    positional?: string[];// 위치 인자
    stdin?: string;       // stdin에서 읽기
    hidden?: boolean;     // tools-json에서 숨기기
  };
}
```

### Contract-First 원칙

1. **단일 진실 공급원 (Single Source of Truth)**
   - `src/core/operations.ts`는 ~47개 공유 operation을 정의.
   - CLI와 MCP 서버가 이 하나의 소스에서 생성됨.
   - operation을 추가 = CLI 플래그 + MCP 툴 + JSON 스키마가 모두 한 번에 생김.

2. **Scope Enforcement**
   - 모든 Operation은 `scope`를 가짐: `'read' | 'write' | 'admin' | 'sources_admin' | 'users_admin'`
   - 계층 구조: `admin`이 모든 것을 포함, `write`가 `read`를 포함, `sources_admin`과 `users_admin`은 형제 (서로 포함하지 않음).
   - 로컬 CLI 호출자 (ctx.remote === false)는 scope enforcement 우회 (OS가 trust boundary).
   - MCP/HTTP transport는 scope를 엄격히 적용.

3. **localOnly Guard**
   - `localOnly: true`인 operation은 원격 호출자에게 거부됨.
   - thin-client 설치 시 `refuseThinClient()`가 pinpoint hint 테이블과 함께 거부 메시지 출력.

4. **Error Handling**
   - `OperationError`는 `code`, `message`, `suggestion`, `docs` 필드를 가짐.
   - ErrorCode는 OPEN union (`(string & {})`) — 전방 호환 가능.
   - ErrorCode 예: `'page_not_found' | 'invalid_params' | 'embedding_failed' | 'storage_error' | 'permission_denied' | 'rate_limited' | 'extraction_failed' | 'fact_not_found'`

5. **CLI + MCP 동시 생성**
   - Operation을 정의하면 CLI 명령어 (`gbrain query`)와 MCP 툴 (`tools/call`)이 동시에 생김.
   - `cliHints`로 CLI 전용 메타데이터 (별칭, 위치 인자, stdin)를 추가.
   - MCP transport (`src/mcp/server.ts`)는 operation 목록에서 tools-json을 생성.

### Thin-Client Routing (v0.29.2+)

thin-client 설치는 로컬 DB 없이 원격 `gbrain serve --http`에 연결:
- `isThinClient(cfg)`가 `connectEngine()` 전에 감지.
- `localOnly` op는 `refuseThinClient()`로 거절 (pinpoint hint 테이블 포함).
- 원격 호출은 `callRemoteTool(config, toolName, args, opts)`로 라우팅.
- Error는 `RemoteMcpErrorReason` stable union으로 정규화 (timeout / aborted / unreachable).
- `--timeout=Ns` 플래그로 per-op 타임아웃 설정 가능.

### Skill Routing (Resolver Pattern)

```markdown
# skills/RESOLVER.md — Dispatcher
# skills/conventions/brain-routing.md — Decision table
# skills/conventions/quality.md — Citation format
# skills/conventions/brain-first.md — Check brain before external APIs
```

**Routing-table compression (v0.32.3.0):** `skills/functional-area-resolver/` — 2계층 dispatch 패턴. 하나의 행을 functional area 항목으로 대체, 각 area는 `(dispatcher for: ...)` 절에 서브 스킬 선언. 25KB → 13KB에 +13 to +17pp 정확도 향상.

---

## 8. Anti-Patterns — 금지 패턴

### Brain Routing Anti-Patterns

1. **Silent brain jumping** — 사용자가 명확히 host를 의미했는데 "답을 찾기 위해" 조용히 brain을 전환. 감사 추적 구멍이 생김.
2. **Writing to host when data is team-owned** — "팀의 계획이 이제 개인 brain에 있습니다" = 나쁜 놀라움.
3. **Cross-brain federation without citations** — 단일 쿼리에서 source brain을 명시하지 않고 여러 brain에서 가져오기. 사용자가 답변을 추적 불가.
4. **Ignoring dotfiles** — `.gbrain-mount` / `.gbrain-source` dotfile 무시. 이들은 사용자가 설정한 중요한 컨텍스트.

### 테스트 Anti-Patterns

5. **Piping test output through tail/head** — `bun test 2>&1 | tail -10`. exit code가 `tail`의 것(항상 0)이 되고, 실패 세부사항이 잘림. 대신 파일로 리다이렉트 후 tail.
6. **Version drift** — VERSION, package.json, CHANGELOG.md가 불일치. CI version-gate가 차단.
7. **Hand-rolling ship operations** — `/ship` 스킬이 있는데 수동으로 git commit + push + gh pr create. VERSION bump, CHANGELOG, document-release, test coverage audit, adversarial review를 모두 건너뜀.

### 설계 Anti-Patterns

8. **Fat harness, thin skills** — 40+ tool 정의가 context window 절반 차지. God tool에 2-5초 MCP round-trip. REST API wrapper로 모든 엔드포인트를 tool로 변환. 3배 토큰, 3배 지연시간, 3배 실패율.
9. **Deterministic problem in latent space** — LLM이 800명 좌석배치를 생성하게 하는 것. SQL/코드가 해야 할 일을 LLM이 환각하도록 강제.
10. **Search-first instead of direct get** — slug를 알고 있을 때도 `gbrain search` 또는 `gbrain query` 실행. `gbrain get <slug>`가 즉시 전체 페이지를 반환하는데 불필요한 검색 오버헤드.
11. **Tokenbudget mismatch** — tokenmax + Haiku (저렴한 모델에 과도한 컨텍스트) 또는 conservative + Opus (비싼 모델에 부족한 컨텍스트). 두 경우 모두 지출 대비 품질 낭비.

### 보안 Anti-Patterns

12. **Defaulting `remote` to falsy** — `ctx.remote`가 REQUIRED인데 falsy 기본값을 사용. 타입 시스템을 `as` 캐스트로 우회할 경우 untrusted 호출자가 trusted로 잘못 간주됨.
13. **Hand-rolling source filtering** — `sourceScopeOpts(ctx)` 대신 수동 source 필터링. 누락된 스레드는 cross-source 데이터 누출로 이어짐.
14. **JSON.stringify into ::jsonb cast** — postgres.js 이중 인코딩 버그. PGLite에선 숨겨져 발견 늦어짐.
15. **Exposing attack surface in release notes** — "10개 테이블이 anon key로 공개됨, X, Y, Z 포함" 대신 "Security hardening pass"로 설명. CHANGELOG가 공격자를 위한 정찰 목록이 되어서는 안 됨.
16. **Real names in public artifacts** — CHANGELOG, docs, PR에 실제 사람/회사/펀드명 사용. 검색 엔진 인덱싱, cross-reference, 배포 시 누출.

### Skill Design Anti-Patterns

17. **One huge CLAUDE.md** — 모든 것을 `CLAUDE.md`에 넣는 패턴 (592KB / 147K 토큰이 된 사례). CLAUDE.md는 orientation만 담고, detail은 on-demand 참조 문서로 분리.
18. **Appending release history to reference docs** — `**vX.Y.Z (#NNN):**` 절을 KEY_FILES.md 등에 추가. CHANGELOG.md와 git에 위임하고, 참조 문서는 현재 상태만 기술.
19. **Searching without first checking brain** — 외부 API 조회 전에 brain 확인 건너뜀. brain-first 규칙 위반.

---

## Schema Packs (v0.38+)

Brain의 형태를 정의하는 동적 스키마. 어떤 디렉토리가 있고, 어떤 타입이 있으며, path에서 타입을 어떻게 추론할지, 어떤 링크 동사가 무엇을 연결하는지 정의.

### Bundled Packs

- **`gbrain-base`** (default) — pre-v0.38 하드코딩 동작을 byte-for-byte 재현. person, company, deal, meeting, project, place, concept 등.
- **`gbrain-recommended`** — 13개 추가 디렉토리 (deal, meeting, concept, project, source, daily, personal, civic, original, place, trip, conversation, writing).

### Resolution Chain (7 Tiers)

| Tier | Source | Notes |
|---:|---|:---:|
| 1 | Per-call `schema_pack` opt | CLI only (ctx.remote === false) |
| 2 | `GBRAIN_SCHEMA_PACK` env | Process scope override |
| 3 | Per-source DB config key | `schema_pack:source:<id>` |
| 4 | Brain-wide DB config key | |
| 5 | `gbrain.yml schema:` section | Repo-checked |
| 6 | `~/.gbrain/config.json` schema_pack | `gbrain schema use`가 작성 |
| 7 | Default: `gbrain-base` | 항상 존재 |

### Schema Pack이 Agent에게 의미하는 것

- **`parseMarkdown`** — 활성 pack의 `page_types[].path_prefixes`에서 page type을 추론.
- **`whoknows` / `find_experts`** — `expert_routing: true` 타입으로 범위 제한.
- **`extract_facts`** — `extractable: true` 타입에서만 실행.
- **Search cache** — pack name + version을 knobsHash에 포함 (cross-pack 오염 방지).

---

## 추가 개념

### Take Pattern (v0.35+)
- **Takes** = statement of opinion/judgment ("My take on X: ...").
- **Facts** = structured metric/attribute data (`## Facts` fence).
- **Takes fence:** `## Takes` 섹션에서 `## Backed by`로 인용 추적.
- **Facts fence:** 구조화된 `metric:`, `value:`, `unit:`, `period:` 컬럼.
- `gbrain eval trajectory <entity-slug>` — chronological fact history.
- `gbrain founder scorecard <entity-slug>` — 4-signal JSON rollup.

### Dream Cycle (24/7 Autonomous)
- Ingest → enrich → consolidate을 24/7 자동 실행.
- Subagent-based (minion orchestration).
- 세 가지 protected phase: synthesize, patterns, consolidate.
- 원격 호출자는 dream cycle phase를 트리거할 수 없음.

### Sync Resumability (v0.42.x, #1794)
- `gbrain sync`는 pool exhaustion + repeated kill에서도 수렴.
- Checkpoint는 `op_checkpoint_paths` table에 append-only로 기록.
- `GBRAIN_SYNC_CHECKPOINT_EVERY`, `GBRAIN_SYNC_CHECKPOINT_SECONDS`, `GBRAIN_LOCK_STEAL_GRACE_SECONDS` 등 5개 env knob.

### Pricing Canonical Table
- 모든 채팅 모델 가격: `src/core/model-pricing.ts` (CANONICAL_PRICING + canonicalLookup).
- 모든 다른 가격 테이블은 DERIVED VIEW. 가격 표류가 구조적으로 불가능.
- Embeddings 가격: 별도 `embedding-pricing.ts`.

---

> **참고:** 이 문서는 gbrain 저장소의 원본 문서를 최대한 보존하면서 gbrain 고유 패턴에 집중합니다. _harness.md와 중복되는 일반적인 에이전트 개념은 생략되었습니다. gbrain의 핵심 차별점은 **Contract Pattern** (단일 operations.ts에서 CLI+MCP 생성), **Trust Boundary** (fail-closed remote 구분), **Two-Axis Mental Model** (brain+source), 그리고 **Schema Packs** (동적 스키마 관리)입니다.
