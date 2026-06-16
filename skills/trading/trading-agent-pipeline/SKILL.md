---
name: trading-agent-pipeline
description: >-
  Multi-agent trading pipeline architecture — LangGraph orchestration, 
  KIS broker integration, risk management, order execution, 
  and vulnerability patterns specific to automated trading systems.
version: 1.4.0
author: Hermes Agent
platforms: [linux]
metadata:
  hermes:
    tags: [trading, pipeline, langgraph, agents, kis, risk-management, order-execution]
    related_skills: [work-verification, systematic-debugging]
---

# Trading Agent Pipeline

## Overview

Class-level patterns for building, maintaining, and auditing multi-agent trading pipelines. Covers the architecture of LangGraph-based agent teams, KIS (Korea Investment & Securities) OpenAPI integration, mechanical risk management, order execution verification, and the specific failure modes that occur in automated trading systems.

## Architecture Patterns

### Multi-Agent Debate Pipeline

```
Analysts (Market, Sentiment, News, Fundamentals)
    → Bull/Bear Researcher Debate
    → Research Manager (synthesis)
    → Trader (concrete proposal)
    → Risk Debate (Aggressive/Conservative/Neutral)
    → Portfolio Manager (final decision)
    → Mechanical RiskManager (hard stop-loss/take-profit)
    → Broker Execution (KIS or paper)
```

**Key design rules:**
- **Role-specific LLM tiers**: quick_llm (analysts, debaters) vs deep_llm (managers, final decision) vs trader_llm (mid-tier precision). Maps to Flash/Pro model distinction.
- **Debate rounds bounded**: max_debate_rounds and max_risk_discuss_rounds in config prevent runaway token consumption.
- **LangGraph conditional edges**: Each debate node routes to next speaker or to synthesis based on round count.
- **Message clearing**: "Msg Clear" intermediate nodes reset `messages[]` after each analyst to prevent context bloat.

### Dual Pipeline Pattern

| Pipeline | Purpose | Broker | Risk |
|----------|---------|--------|------|
| DailyPipeline | Paper/portfolio-only | None (local JSON) | RiskManager |
| DailyTradingPipeline | Real execution | KIS OpenAPI | RiskManager + SwingRuleEngine |

**Both use the same agent graph** — only the execution layer differs.

## KIS Integration Critical Patterns

### Authentication
- OAuth2 token with 24h expiry, cached to disk
- Use `authenticate()` before every API call (auto-refreshes if expired)
- Token cache: `~/.tradingagents/kis_token.json` — **set permissions to 0600**
- Multiple KISBroker instances can race on token cache → add file locking

### Order Execution Verification (CRITICAL)
**Placing an order is NOT the same as filling it.**
```python
# DON'T:
result = broker.buy(ticker, quantity, price)
if result.get("success"):
    portfolio.add_position(ticker, quantity, price)  # Wrong! Order may not fill

# DO:
result = broker.buy(ticker, quantity, price)
if result.get("success") and result.get("order_id"):
    confirm = broker.confirm_order(result["order_id"], ticker, quantity)
    filled = confirm.get("filled", 0) if confirm.get("confirmed") else 0
    if filled > 0:
        portfolio.add_position(ticker, filled, price)  # Only actual fills
```

### Data Fallback Chain
```
KIS daily OHLCV → inquire-price (today only) → yfinance (history) → today-only (last resort)
```

**Known failure modes by fallback:**
| Fallback | Failure | Impact |
|----------|---------|--------|
| KIS daily | 404 in virtual mode | Silently falls through |
| inquire-price | Returns 1 data point | RSI/SMA can't calculate |
| yfinance `.KS` | KOSDAQ tickers need `.KQ` | Returns empty for KOSDAQ |
| yfinance data | 15-20 min delay | Stale indicators |
| Today-only | 1 data point | No technical analysis |

### API Implementation Patterns

#### Endpoint Map

| Purpose | Path | TR_ID | Virtual Support |
|---------|------|-------|-----------------|
| 현재가 시세 | `/uapi/domestic-stock/v1/quotations/inquire-price` | `FHKST01010100` | ✅ Full OHLCV + 52w range |
| 일별 시세 | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemprice` | `FHKST01010400` | ❌ 404 |
| 종목명 조회 | `/uapi/domestic-stock/v1/quotations/search-stock-info` | `CTPF1002R` | ❌ "모의투자 TR이 아닙니다" |

Base URLs: 실전=`https://openapi.koreainvestment.com:9443`, 모의투자=`https://openapivts.koreainvestment.com:29443`

#### Authentication

OAuth2 token with 24h expiry, cached to disk:

```python
# POST /oauth2/tokenP
payload = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
# Response: {"access_token": "...", "expires_in": 86400}

headers = {
    "authorization": f"Bearer {access_token}",
    "appkey": app_key, "appsecret": app_secret,
    "tr_id": tr_id, "custtype": "P",
}
```

- Token cache: `~/.tradingagents/kis_token.json` — **set permissions to 0600**
- Auto-refresh with 5min buffer before expiry
- Multiple KISBroker instances can race on token cache → add file locking

#### Rate Limiting

KIS limit ~20 calls/sec. Safe: **200ms minimum interval** (5 calls/sec).

```python
_LAST_CALL_TIME = 0.0
_MIN_CALL_INTERVAL = 0.2

def kis_rate_limit():
    global _LAST_CALL_TIME
    now = time.time()
    elapsed = now - _LAST_CALL_TIME
    if elapsed < _MIN_CALL_INTERVAL:
        time.sleep(_MIN_CALL_INTERVAL - elapsed)
    _LAST_CALL_TIME = time.time()
```

Call `kis_rate_limit()` before **every** API request. Note: module-level `_LAST_CALL_TIME` is per-process — concurrent cron jobs bypass it. Use file-based coordination or conservative per-process delays.

#### Response Caching

```python
_KIS_CACHE: Dict[str, Any] = {}
_KIS_CACHE_TTL = 300  # 5 minutes

def cache_get(key: str):
    entry = _KIS_CACHE.get(key)
    if entry and time.time() - entry[0] < _KIS_CACHE_TTL:
        return entry[1]
    return None
```

Cache granularity: per-ticker per-endpoint (e.g. `ohlcv:005930:20260601:20260601`).

#### KISBroker Base Class Pattern

```python
class KISBroker:
    TR_IDS = {
        "price": ("FHKST01010100", "FHKST01010100"),  # (virtual_tr, real_tr)
        "daily_ohlcv": ("FHKST01010400", "FHKST01010400"),
        "stock_name": ("CTPF1002R", "CTPF1002R"),
    }

    def _tr_id(self, key: str) -> str:
        virtual_tr, real_tr = self.TR_IDS[key]
        return virtual_tr if self.is_virtual else real_tr

    def _headers(self, tr_id: str) -> Dict:
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key, "appsecret": self.app_secret,
            "tr_id": tr_id, "custtype": "P",
        }

    def _get(self, path, tr_id, params=None):
        url = f"{self.base_url}{path}"
        resp = httpx.get(url, headers=self._headers(tr_id), params=params, timeout=10)
        return self._handle_response(resp)
```

#### Virtual Mode Fallback Cascade

```
KIS 일별시세 API → inquire-price (today) → yfinance (history) → today-only (last resort)
```

The inquire-price fallback returns only 1 data point (today). If pipeline code checks `len(ohlcv) >= 2` before scoring (RSI/SMA calculation), **all candidates are silently skipped** with zero output. Always layer yfinance as a secondary fallback.

**yfinance details:**
- KOSPI tickers: append `.KS` suffix (e.g. `005930.KS`)
- KOSDAQ tickers: append `.KQ` suffix (e.g. `...KQ`)
- Use `.iloc[0]` for single-element DataFrame rows to avoid pandas FutureWarning
- Data can be 15–20 min delayed; validate freshness (last record within 3 trading days)

#### Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| `EGW00201` | 초당 거래건수를 초과하였습니다 | Wait 1s, retry |
| `EGW02006` | 모의투자 TR이 아닙니다 | Switch to inquire-price or yfinance |
| 404 (empty) | Endpoint not available in virtual | Use fallback chain |

#### KIS-Specific Pitfalls

- **`int()` on float strings**: KIS returns `"50000.0"` → parse with `int(float(str(value)))`.
- **Token truncation**: Full key is 67 chars for opencode-go (`sk-...`). Ensure `.env` exports the complete key.
- **`set -e` in shell scripts**: KIS auth failures trigger immediate exit. Wrap in error handlers for cron.
- **Order confirmation gap**: Broker `buy()` returning success means "order placed", NOT "order filled". Always poll `confirm_order()` before portfolio updates. Use only actually filled quantity.
- **Portfolio.json concurrent writes**: Multiple cron jobs can race. Use atomic writes (tempfile + os.replace) and `fcntl.flock`.
- **Holiday checks**: `is_market_open()` must check Korean public holidays (Seollal, Chuseok, 대체공휴일) via `holidays.KR()`, not just weekday+time.
- **Stop-loss sign validation**: Ensure `swing_stop_loss_pct` is negative and `swing_stop_loss_pct < swing_target_profit_pct`.
- **Data freshness**: After any yfinance or inquire-price data fetch, validate the last record is within 3 trading days.
- **Token/chat ID exposure**: Never hardcode bot tokens or chat IDs. Require environment variables with runtime validation.
- **LLM prompt injection**: News article titles/summaries injected into agent prompts. Truncate to 200 chars, strip special characters, add system guard instructions. ⚠️ **Common trap**: defining a `_sanitize_prompt_input()` function but never calling it — verify the sanitizer is wired into the actual data flow (_get_news_data, analyst prompt builders).
- **`sell_price=0` treated as falsy**: `sell_price or current_price` silently replaces a valid 0 price with current_price. Use `sell_price if sell_price is not None else p["current_price"]`.
- **Telegram callback offset persistence**: `getUpdates(offset=-100)` loses responses if backlog exceeds 100 updates. Store `last_update_id` in the pending_trades.json file and pass `offset=last_update_id + 1` on every poll. **clear_pending() destroys offset** — store offset in a separate tracking file, or save it before clearing pending trades.
- **Telegram Markdown parse failure with Korean**: `parse_mode: "Markdown"` + `**한글**` 조합에서 `Can't find end of the entity` 오류 발생. **반드시 `parse_mode: "HTML"` 사용하고 `<b>text</b>`로 bold 처리.** `send_proposal()`, `send_result()`, `update_proposal_message()` 3개 메서드 모두 해당. `MarkdownV2`도 유니코드 경계 이슈 있으므로 HTML이 가장 안전.
- **`is_market_open()` exception silent pass**: Wrapping market checks in `except Exception: pass` hides connectivity failures. Always log the exception.
- **Rate limiter NOT in _get()/_post() base**: `_kis_rate_limit()` is called in specific methods but NOT in base HTTP methods. `buy()`, `sell()`, `get_balance()` bypass it. Move rate limiting into `_get()`/`_post()`.
- **HTTP status code unchecked before JSON parse**: `resp.json()` called without checking `resp.status_code`. HTTP 429/5xx produce cryptic errors. Always check status first.
- **KISDataProvider.get_name() crashes on auth failure**: `get_stock_name()` raises RuntimeError before local name lookup fallback can reach. Wrap in try/except.
- **TrailingStopRule peak not persisted**: `position["peak_return_pct"] = ret` modifies a temporary merged dict in `get_sellable_positions()`. Changes lost on next eval -> trailing stop never activates. Write back to live portfolio position dict.

Detailed endpoint response fields, full stock name lookup table, and rate-limit recovery notes are in `references/kis-endpoints.md`.

## Risk Validation Chain

Three independent risk layers must ALL approve before execution:

1. **LLM Portfolio Manager** — semantic judgment (buy/hold/sell rating)
2. **RiskManager** — mechanical rules (stop-loss -5%, take-profit +15%, trailing stop 3%)
3. **SwingRuleEngine** — position-level rules (target profit, max hold days, trailing stop)

**Hard rules (never overridden by LLM):**
- Stop-loss: -5% individual position
- Take-profit: +15% individual position  
- Trailing stop: activates at +5%, trails at 3%
- Max position size: 20% of total portfolio
- Reserve ratio: 20% cash minimum

## Vulnerability Patterns (from audits)

### Critical — Fixed (v1 & v2)
| Pattern | Fix | Session |
|---------|-----|---------|
| Portfolio.json concurrent writes | Atomic write + fcntl.flock | v1 (06-09) |
| Token hardcoded in source | Remove defaults, require env vars | v1 (06-09) |
| `_sanitize_prompt_input()` defined but never called | Connect sanitize to every news/title flow into prompts | v2 (06-11) |
| Telegram getUpdates `offset=-100` — response loss on backlog | Persistent update_id tracking in pending_trades.json | v2 (06-11) |

### Critical — Unpatched (identified in deep analysis)
| Pattern | Fix |
|---------|-----|
| llm_client.py references missing config fields (`deepseek_api_key`, etc.) | Add to TradingConfig |
| ZeroDivisionError in price change calc (`/ last['open']`, `/ closes[-2]`) | Guard every division |
| pipeline.py execute_decision() never calls KIS broker | Add KIS buy/sell or deprecate pipeline.py |
| Portfolio.load() has no file lock | Add fcntl.flock(LOCK_SH) |
| TrailingStopRule peak_return_pct change never persisted to portfolio | Write back to live position dict + save |
| Dockerfile runs as root (no USER) | Add `USER nobody` |

### High — Fixed (v1 & v2)
| Pattern | Fix | Session |
|---------|------|---------|
| Korean holiday check missing | Use `holidays.KR()` library | v1 (06-09) |
| Portfolio updated before order confirmed | Only record filled quantity | v1 (06-09) |
| yfinance KOSDAQ suffix | `.KQ` lookup table | v1 (06-09) |
| Morning sell doesn't update portfolio | Always update portfolio after sell | v1 (06-09) |
| Token cache race condition | File locking on authenticate() | v1 (06-09) |
| No market-open check in execute | Check before any trade decision | v1 (06-09) |
| Sell order portfolio update before confirmation | Move pf.remove_position+save inside confirmed block | v2 (06-11) |
| Korean shortened trading days (단축장) | Add half-day calendar (Dec 24, Dec 31 → 12:00 end) | v2 (06-11) |
| KIS account_no length not validated | Raise ValueError if < 8 chars | v2 (06-11) |

### High — Fixed (v3, 06-12)
| Pattern | Fix | Session |
|---------|-----|---------|
| KIS API transient failure crashes cron monitor | Retry loop in `run_swing_monitor(max_retries=2)` with detailed error messages | v3 (06-12) |

### High — Unpatched (identified in deep analysis)
| Pattern | Fix |
|---------|-----|
| _injection_guard() only on 2/12 agent nodes | Add to all downstream 10 nodes |
| _sanitize_prompt_input allows markdown injection | Strip ##, ```, ---, ** patterns |
| KISDataProvider.get_name() crashes on auth failure | Wrap in try/except, use name lookup fallback |
| Rate limiter not in _get()/_post() base | Move _kis_rate_limit() into base methods |
| No KIS API failure fallback (cache, retry, degrade) | Cache-first balance, exponential backoff |
| HTTP status code never checked | Inspect resp.status_code before parsing JSON |
| Telegram clear_pending() destroys update_id offset | Store last_update_id outside pending_trades.json |

### Medium — Validated Fixes
| Pattern | Fix | Session |
|---------|-----|---------|
| News injection into LLM prompts | Truncate + sanitize + system guard | v1 (06-09) |
| Process-local rate limiter bypass | Cross-process coordination | v1 (06-09) |
| Unbounded debate history | Truncate at 8000 chars | v1 (06-09) |
| Config validation missing | Validate stop_loss < 0 < target_profit | v1 (06-09) |
| confirm_order() blocks process 60s | Reduce to max_retries=3, retry_interval=5 (max 15s) | v2 (06-11) |
| Static cache TTL too long during market hours | Dynamic TTL: 20s intraday, 300s off-hours | v2 (06-11) |
| _find_text_reply() accepts ANY chat message | Require reply_to_message.message_id == target_mid | v2 (06-11) |
| Portfolio save failure after successful KIS order | Atomic write retry (3 attempts) + logging | v2 (06-11) |

### Medium — Unpatched (identified in deep analysis)
| Pattern | Fix |
|---------|-----|
| "reduce"/"trim" in sell pattern false positive | Remove from sell regex or add partial-reduce action |
| Double sanitization of news data | Let _get_news_data() handle it once |
| Excessive KISBroker instantiation (12-15× per run) | Module-level provider cache (singleton pattern) |
| SQLite checkpoint WAL mode + timeout not set | PRAGMA journal_mode=WAL; timeout=5 |
| requirements.txt all `>=` versions | Pin to `==` or `~=` with known-good upper bound |
| CLI missing input validation (ticker, date, negative values) | Apply _validate_ticker, IntRange, strptime |
| morning_sell without order confirmation | Add confirm_order() after sell in morning path |
| get_sellable_positions relies on KIS stale return_pct | Calculate from portfolio's own avg_buy/current price |

### Low
| Pattern | Fix | Session |
|---------|-----|---------|
| Backtest stub missing date validation | Add YYYY-MM-DD regex check | v2 (06-11) |
| sell_price=0 falsy in `or` expression | Use `is not None` check | v2 (06-11) |
| is_market_open() exception silently passed | Log logger.warning() instead of bare `pass` | v2 (06-11) |
| Telegram token plain string (not SecretStr) | Use pydantic.SecretStr | deep |
| Duplicate import yfinance inside function | Remove local import | deep |
| Provider boilerplate across 10+ nodes | Extract _get_ticker_info(state) helper | deep |
| config_show leaks telegram_bot_token | Add "token"/"secret" to key mask | deep |
| _find_text_reply target_mid=0 accepts all messages | Default to negative sentinel or raise early | deep |

## LLM Output Parsing

Never use naive substring matching (`"buy" in text`) — too many false positives:
- `"buy"` matches `"busy"`, `"buyout"`, `"goodbye"`
- `"sell"` matches `"cell"`, `"seller"`, `"umbrella"`

**Use word-boundary regex instead** (`\bbuy\b`). Reference implementation: `parse_utils.py` with `extract_rating()` and `extract_action()`.

## Multi-Agent Parallel Fix Workflow

When applying vulnerability fixes to the trading pipeline, use **parallel sub-agents** grouped by file ownership (not by severity):

```python
# Good grouping: 3 tasks, no file conflicts
Task 1: agents.py + telegram/__init__.py   # Security & Telegram
Task 2: broker/kis.py + daily_pipeline.py + pipeline.py  # Broker & Logic
Task 3: portfolio_manager.py + cli.py      # Minor fixes
```

**Rules:**
- Group by file — no two tasks touch the same file.
- Each subagent gets `toolsets=["terminal", "file"]`.
- Pass explicit context: exact file paths, line numbers, and the old→new pattern for each fix.
- After all complete, run `python3 -m py_compile` on every modified file.
- Verify each fix by re-reading the changed lines.

**Common pitfalls:**
- Subagents re-read files the parent loaded — note "re-read before editing" in summary.
- `patch()` with fuzzy matching works well for small targeted changes.
- Never use `write_file` for full rewrites on production files; use `patch()` to preserve unrelated code.

## Verification Protocol (Trading-Specific)

Every trading operation follows this chain:
1. Execute (place order, write file, update state)
2. **Verify** (confirm_order, read_file, check state)
3. Auto-fix if verification fails
4. Report only verified result

The `work-verification` skill covers the general protocol. Trading pipeline adds:
- **Order confirmation** is mandatory before portfolio update
- **Data freshness** validate before technical analysis
- **Risk gate** every trade passes through all 3 layers
- **Portfolio consistency** cross-check local vs broker state daily

## Cron Job Environment Setup

트레이딩 파이프라인 크론 잡 3종(`run_monitor.sh`, `run_execution.sh`, `run_morning.sh`)은 `no_agent: true` watchdog 패턴이다. Hermes cron scheduler 환경은 interactive shell과 달라 `.env` 파일에 모든 의존성이 명시되어야 한다.

### 필수 `.env` 항목

모든 스크립트는 `/home/khmo31/auto_investment/trading_pipeline/.env`를 `source`/`load_dotenv`로 로드한다. 누락 시 import 단계에서 실패하지 않도록 telegram 모듈이 lazy import guard를 적용했으나, **실제 Telegram 기능을 사용하려면** 다음 변수가 반드시 필요하다:

```bash
# ── Telegram (TRADINGAGENTS_ prefix는 pydantic BaseSettings 호환) ──
TRADINGAGENTS_TELEGRAM_BOT_TOKEN=*** .env의 TELEGRAM_BOT_TOKEN과 동일>
TRADINGAGENTS_TELEGRAM_CHAT_ID=7935882706

# ── KIS ──
KIS_APP_KEY=...
KIS_APP_SECRET=...
K...n
# ── LLM ──
TRADINGAGENTS_LLM_PROVIDER=openai
TRADINGAGENTS_DEEP_THINK_LLM=deepseek-v4-pro
TRADINGAGENTS_QUICK_THINK_LLM=deepseek-v4-flash
OPENAI_API_KEY=*** `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`(prefix 없는 버전)는 pydantic `config.telegram_bot_token` / `config.telegram_chat_id`가 None/empty일 때의 fallback으로 사용된다. prefix 있는 `TRADINGAGENTS_*` 버전이 1순위.

### Lazy Import Guard (Anti-Crash)

`telegram/__init__.py`는 v1.x에서 모듈 import 시점에 `RuntimeError`를 발생시켜 Telegram 설정이 없으면 파이프라인 전체가 import조차 불가능했다. **이 패턴은 크론 잡을 전멸시키므로 금지.** v3 패치로 변경:

```python
# ✅ 올바른 패턴 (v3): import 시점에 경고만, disabled 상태로 진행
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
if not TELEGRAM_ENABLED:
    logging.getLogger(__name__).warning("Telegram disabled: ...")

class TelegramApproval:
    def __init__(self, ...):
        self.enabled = TELEGRAM_ENABLED  # 모든 메서드가 이걸 먼저 체크

    def send_proposal(self, ...):
        if not self.enabled:
            return None  # 크론 잡이 죽지 않고 진행됨
```

**교훈**: 외부 의존성이 있는 Python 모듈은 절대 import/module 로드 시점에 `raise`하지 말 것. `ENABLED` 플래그 + 메서드별 early return으로 graceful degradation 할 것.

### KIS API Transient Failure 대응 (Retry Pattern)

크론 모니터링 스크립트에서 KIS API 일시적 장애(rate limit, 네트워크 순단)로 `get_balance()` 실패 시 전체 잡이 죽는 문제를 retry loop로 방어:

```python
def run_swing_monitor(self, max_retries: int = 2) -> str:
    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            if not self.broker.authenticate():
                last_error = "KIS 인증 실패"
                continue
            balance = self.broker.get_balance()
            if not balance.get("success"):
                last_error = f"잔고 조회 실패: {balance.get('error', 'unknown')}"
                continue
            last_error = ""
            break
        except Exception as e:
            last_error = f"KIS 예외: {e}"

    if last_error:
        return f"❌ {last_error}"
    # ... 정상 처리 계속
```

**포인트:**
- 오류 메시지에 실제 API 에러를 포함시켜 디버깅 가능하게 할 것 (`{balance.get('error')}`)
- `continue`로 retry → `break`로 탈출 구조
- `max_retries`를 파라미터화하여 호출자가 제어 가능하게

## References

- `references/vulnerability-audit-2026-06-09.md` — Full 23-finding audit report from v4-pro deep analysis (first pass)
- `references/vulnerability-audit-2026-06-11.md` — 12 additional findings from second pass, all fixed via parallel sub-agent workflow
- `references/vulnerability-audit-2026-06-11-deep.md` — 40+ additional findings from 3-subagent deep re-analysis (includes unpatched CRITICAL/HIGH items and priority ordering)
- `references/kis-endpoints.md` — KIS API response fields, stock name lookup table, error code reference
- `work-verification` skill — General cross-domain verification protocol
