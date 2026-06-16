# KIS OpenAPI Reference

Detailed endpoint reference for KIS (Korea Investment & Securities) OpenAPI — supporting the trading pipeline's data layer.

## Endpoint Summary

| Purpose | Path | TR_ID | Virtual? |
|---------|------|-------|----------|
| 현재가 시세 | `/uapi/domestic-stock/v1/quotations/inquire-price` | `FHKST01010100` | ✅ Yes |
| 일별 시세 | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemprice` | `FHKST01010400` | ❌ 404 |
| 종목명 조회 | `/uapi/domestic-stock/v1/quotations/search-stock-info` | `CTPF1002R` | ❌ "모의투자 TR이 아닙니다" |
| 종목명 조회 (alt) | same path | `CTPF1604R` | ❌ "모의투자 TR이 아닙니다" |

Tested against `openapivts.koreainvestment.com:29443` (모의투자/simulation).

## inquire-price Response Fields

| Field | Meaning | Type | Example |
|-------|---------|------|---------|
| `stck_prpr` | 현재가/종가 | int (string) | `"349000"` |
| `stck_oprc` | 시가 | int (string) | `"319500"` |
| `stck_hgpr` | 고가 | int (string) | `"354500"` |
| `stck_lwpr` | 저가 | int (string) | `"319500"` |
| `acml_vol` | 누적거래량 | int (string) | `"39345631"` |
| `prdy_vrss` | 전일대비 | int (string) | `"32000"` |
| `prdy_vrss_sign` | 1:상한 2:상승 3:보합 4:하한 5:하락 | int (string) | `"2"` |
| `prdy_ctrt` | 전일대비율(%) | float (string) | `"10.09"` |
| `w52_hgpr` | 52주 최고 | int (string) | `"354500"` |
| `w52_lwpr` | 52주 최저 | int (string) | `"56200"` |
| `per` | PER | float (string) | `"53.17"` |
| `pbr` | PBR | float (string) | `"5.45"` |
| `eps` | EPS | float (string) | `"6564.00"` |
| `lstn_stcn` | 상장주식수 | int (string) | `"5846278608"` |
| `hts_avls` | 시가총액(억) | int (string) | `"20403512"` |
| `d250_hgpr` | 250일 최고 | int (string) | `"354500"` |
| `d250_lwpr` | 250일 최저 | int (string) | `"53700"` |

**Parse caution:** Always use `int(float(str(value)))` — KIS sometimes returns `"50000.0"` instead of `"50000"`.

## Stock Name Lookup Table

For the 20 major KOSPI tickers scanned by `_scan_candidates()`. Used when the stock-name API is unavailable in virtual mode:

```python
KOREA_STOCK_NAMES = {
    "005930": "삼성전자", "000660": "SK하이닉스",
    "207940": "삼성바이오로직스", "005380": "현대차",
    "005490": "POSCO홀딩스", "035420": "NAVER",
    "068270": "셀트리온", "051910": "LG화학",
    "006400": "삼성SDI", "003550": "LG",
    "086790": "하나금융지주", "105560": "KB금융",
    "138930": "BNK금융지주", "017670": "SK텔레콤",
    "028300": "HLB", "012330": "현대모비스",
    "096770": "SK이노베이션", "018260": "삼성에스디에스",
    "010130": "고려아연", "032830": "삼성생명",
}
```

For unknown tickers, fall back to the ticker string itself.

## Error Code Recovery

| Code | Message | Cause | Recovery |
|------|---------|-------|----------|
| `EGW00201` | 초당 거래건수를 초과하였습니다 | Rate limit exceeded (>20 calls/sec) | Wait 1s, retry |
| `EGW02006` | 모의투자 TR이 아닙니다 | TR_ID not available in virtual mode | Fall through to yfinance |
| 404 (empty) | (empty body) | Endpoint doesn't exist in virtual | Fall through to fallback |

## Rate Limit Details

The 200ms minimum interval (5 calls/sec) maintains a 4× safety margin below the actual ~20 calls/sec limit. If `EGW00201` is still hit, enforce a 1-second cool-off before retrying.

## 실전 (Real) Mode

Switch by setting `KIS_IS_VIRTUAL=false` in `.env`. Base URL changes to `openapi.koreainvestment.com:9443`. All endpoints should work in 실전 mode.

## Token Cache

OAuth2 token path: `~/.tradingagents/kis_token.json`. Set permissions to 0600. Auto-refresh with 5min buffer before 24h expiry. Multiple broker instances should use file locking on authenticate() to avoid race conditions.
