# Cron Job Telegram Fix — 2026-06-12

## 문제

트레이딩 파이프라인 크론 잡 3종(`trading-swing-monitor-11`, `trading-swing-monitor-14`, `trading-morning-analysis`, `trading-execution-check`)이 `RuntimeError: TELEGRAM_CHAT_ID is not configured` 로 전부 실패.

## 원인

1. `/home/khmo31/auto_investment/trading_pipeline/.env` 파일에 `TRADINGAGENTS_TELEGRAM_BOT_TOKEN`과 `TRADINGAGENTS_TELEGRAM_CHAT_ID` 누락
2. `telegram/__init__.py`가 모듈 import 시점에 `RuntimeError`를 raise → 파이프라인 전체 import 불가

## 수정

### 1. `.env`에 Telegram 변수 추가
```
TRADINGAGENTS_TELEGRAM_BOT_TOKEN=*** .env에서 복사>
TRADINGAGENTS_TELEGRAM_CHAT_ID=7935882706
```

### 2. `telegram/__init__.py` lazy import guard
- `TELEGRAM_ENABLED` 플래그 도입
- import 시점 `RuntimeError` → `logging.warning()` 으로 변경
- `TelegramApproval` 클래스에 `self.enabled` 속성 추가
- `send_proposal()`, `send_result()`, `update_proposal_message()` 에 `if not self.enabled: return None/False` early return 추가

## 검증

- `run_monitor.sh` → `📭 보유 종목 없음` exit 0
- `run_execution.sh` → `📭 처리할 대기 매수가 없습니다.` exit 0
- `run_morning.sh` → 정상 시작 (LLM 파이프라인으로 인한 timeout, crash 없음)

### 3. Telegram Markdown → HTML 파싱 오류 수정 (추가 발견)

`.env` 설정 후 `send_proposal()`이 다음 오류로 실패:
```
Bad Request: can't parse entities: Can't find end of the entity starting at byte offset 65
```
원인: Telegram API의 `parse_mode: "Markdown"`은 한글+`**bold**` 조합에서 파싱 경계를 올바르게 찾지 못함.

수정: `telegram/__init__.py`의 `send_proposal()`, `send_result()`, `update_proposal_message()` 3개 메서드에서:
- `"parse_mode": "Markdown"` → `"parse_mode": "HTML"`
- `**text**` → `<b>text</b>`
- 마크다운 특수문자 제거 (HTML은 이스케이프 불필요)

## 교훈

- 크론 잡의 `no_agent: true` 모드는 환경변수가 상속되지 않음 → `script` 내에서 `.env`를 명시적으로 로드할 것
- 외부 의존성 모듈은 절대 import 시점에 crash시키지 말고 lazy guard + graceful degradation 패턴 사용
- Hermes `.env`와 trading pipeline `.env`는 별도 관리되므로 변수 복사가 필요함
- Telegram Bot API에서 한글 메시지 발송 시 `parse_mode`는 `HTML` 사용 권장. `Markdown`/`MarkdownV2`는 유니코드 경계 문제로 `**bold**` 파싱에 실패할 수 있음

## 추가: KIS Transient Failure 대응 (06-12 후속)

### 문제

수정 후 `trading-swing-monitor-14` (14:00 KST)에서 `❌ 잔고 조회 실패` 발생. 같은 코드의 `trading-swing-monitor-11` (11:00 KST)은 정상 작동.

### 원인

KIS 모의투자 API의 일시적 장애 (rate limit, 네트워크 순단). 수동 재실행 2회 모두 성공 → transient failure 확정.

### 수정

`daily_pipeline.py`의 `run_swing_monitor()`에 retry loop 추가 (`max_retries=2`):

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

### 교훈

- 오류 메시지에 실제 API 에러 상세를 포함시킬 것 (`{balance.get('error')}`) — `"❌ 잔고 조회 실패"`만으로는 디버깅 불가
- `max_retries`를 파라미터화하여 호출자가 제어 가능하게
- `continue`로 retry → `break`로 탈출 구조
