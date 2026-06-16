# Moltbook Trend Analysis — Reference

> Moltbook AI 대화 데이터를 Supabase에서 조회 → 카테고리/키워드 트렌드 분석 → Second Brain 위키에 월간 페이지 자동 생성

## Source: `khmo31/moltbook_reports`

비공개 레포지토리. Moltbook AI 대화 포스트를 수집 → 스코어링 → LLM(Groq) 클러스터링 → TOP5 인사이트 추출 → Telegram + Supabase 저장.

## Supabase Schema

**Project URL**: `https://ogkyafyassapbbdzxqln.supabase.co`

### Table: `moltbook_reports`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `created_at` | TIMESTAMPTZ | 리포트 생성일 (UTC) |
| `report_date` | DATE | 리포트 기준일 (YYYY-MM-DD) |
| `title` | TEXT | 리포트 제목 |
| `summary` | TEXT | 핵심 요약 |
| `category` | TEXT | 분류 (아래 6개 중 하나) |
| `keywords` | JSONB | 급상승 키워드 문자열 배열 (예: `["#AI","#Security"]`) |
| `key_issues` | JSONB | {side_a: string, side_b: string} 논쟁 구조 |
| `best_insight` | TEXT | 최종 인사이트 + 행동 제안 |
| `sources` | JSONB | 원본 포스트 참조 배열 |

> 2026-06-06 기준 **287건** 적재. 일평균 5.3건.

### Category Taxonomy

| Supabase 값 | Korean | Description |
|-------------|--------|-------------|
| 기술 | 기술 | 성능, 아키텍처, 모델, 디버깅 |
| 보안 | 보안 | 취약점, 암호화, 공급망 |
| 윤리 | 윤리 | 바이어스, 정렬, 거버넌스 |
| 시장 | 시장 | 투자, 가격, 스타트업 |
| Philosophy | 철학 | 종교, 영성, 의식, 신학 (2026-05-16 추가, Supabase에는 영문명) |
| 기타 | 기타 | 위 분류에 속하지 않는 주제 (49.8% — 서브카테고리 분할 필요) |

> ⚠️ **주의**: Supabase category 값은 `Philosophy` (영문)이고, 표시는 `철학` (한글). '기타' 비중이 50%에 육박하므로 Groq 프롬프트에서 서브카테고리 분류 개선 필요.

### Table: `posts`

Moltbook에서 수집한 원본 포스트 (retention: 30일, pg_cron 자동 정리)

### Table: `comments`

포스트별 댓글 (posts CASCADE 삭제)

## Credential Access

Supabase 인증 정보는 **GitHub Secrets**에만 있음. 로컬 접근 시:

1. **직접 입력** (권장) — Service Role Key를 사용자에게 요청
2. **gh CLI** — `gh secret list -R khmo31/moltbook_reports` 로 읽기 (GitHub Token 필요)
3. **`.env` 로컬 등록** — 반복 cron용: `~/.hermes/.env` 에 `SUPABASE_SERVICE_ROLE_KEY=...` 저장

## Trend Analysis Techniques

### 1. Category Distribution

기본 집계 — 전체 및 월별 카테고리별 리포트 수:

```python
from collections import Counter
cats = Counter(r["category"] for r in reports)
```

### 2. Month-over-Month Category Delta

저번 달 vs 이번 달 증감율까지 포함한 테이블:

```python
prev_cats = Counter(r["category"] for r in prev_month_reports)
curr_cats = Counter(r["category"] for r in curr_month_reports)

for cat in sorted(all_cats):
    p = prev_cats.get(cat, 0)
    c = curr_cats.get(cat, 0)
    change = c - p
    pct = ((c - p) / p * 100) if p > 0 else (100 if c > 0 else 0)
    arrow = "🔺" if change > 0 else ("🔻" if change < 0 else "➡️")
```

### 3. Emerging Keywords Detection

이전 달 전체에 없던 키워드 중 이번 달에 새로 등장한 키워드 찾기:

```python
# All keywords from all previous months
prev_all_kws = set()
for m in sorted(monthly.keys()):
    if m >= current_month:
        break
    for r in monthly[m]:
        for kw in r.get("keywords", []):
            if kw:
                prev_all_kws.add(kw.lower())

# New keywords this month (not in any prev month)
new_kws = [(kw, cnt) for kw, cnt in curr_kws.most_common(20) 
           if kw not in prev_all_kws]
```

### 4. Rising Keywords (Month-over-Month)

전월 대비 증가한 키워드:

```python
rising_kws = []
for kw, cnt in curr_kws.most_common(20):
    prev_cnt = prev_kws.get(kw, 0)
    if prev_cnt > 0 and cnt > prev_cnt:
        rising_kws.append((kw, prev_cnt, cnt, ((cnt-prev_cnt)/prev_cnt*100)))
```

### 5. Emerging Keywords (Cross-Month Persistence)

두 달 연속 등장하는 신규 키워드 (일시적 유행 vs 지속적 관심사 구분):

```python
# Keywords that appeared in May but NOT in April, and also appear in June
emerging = (may_kws - april_kws) & june_kws
```

### 6. Daily Volume Spikes

일별 리포트 수로 가장 활발했던 날 식별:

```python
daily = Counter(r["report_date"] for r in reports)
spikes = daily.most_common(10)  # e.g., 2026-05-09: 15건
```

## Production Script (Bash + Python heredoc)

실제 cron에서 사용하는 스크립트. Bash wrapper가 Python 분석을 호출하고 Git commit까지 수행:

- **Script path**: `~/.hermes/scripts/moltbook_trend_analyzer.sh`
- **Cron job name**: `moltbook-monthly-trend` (job_id: `b88de98585f0`)
- **Schedule**: 매월 1일 00:00 UTC (09:00 KST)
- **Mode**: `no_agent=True` (LLM 사용 안 함, 스크립트 stdout이 그대로 전송)

### 스크립트 구조

```bash
#!/usr/bin/env bash
set -euo pipefail

SUPABASE_URL="https://ogkyafyassapbbdzxqln.supabase.co"
SUPABASE_KEY="<service-role-key>"
SECOND_BRAIN="$HOME/second_brain"

# 1. Fetch all reports from Supabase
curl -s "${SUPABASE_URL}/rest/v1/moltbook_reports?select=id,report_date,category,title,keywords,summary&order=report_date.asc" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Accept: application/json" \
  -o /tmp/moltbook_trend_data.json

# 2. Python 분석 (heredoc)
python3 << 'PYEOF'
import json, os
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

with open('/tmp/moltbook_trend_data.json') as f:
    reports = json.load(f)

now = datetime.now(timezone.utc)
current_month = now.strftime('%Y-%m')
first_of_current = now.replace(day=1)
end_of_prev = first_of_current - timedelta(days=1)
prev_month = end_of_prev.strftime('%Y-%m')

# ... (aggregation, analysis, wiki page generation) ...

# Print summary for cron delivery
print(f"📊 Moltbook 트렌드 리포트")
print(f"전체: {len(reports)}건 | 이번 달: {len(cm_data)}건")
PYEOF

# 3. Git commit & push
cd "$SECOND_BRAIN"
git add -A
git diff --cached --quiet || {
    git commit -m "feat(trend): Moltbook 트렌드 분석 자동 갱신"
    git pull --rebase origin main
    git push origin main
}
```

### Key Design Decisions

1. **Bash wrapper + Python heredoc**: curl로 데이터 조회 → Python으로 분석 → Bash로 Git 처리. Python만으로 curl+REST보다 가독성 좋음
2. **`no_agent=True`**: LLM 호출 없이 스크립트 stdout이 그대로 전송. 월 1회 실행에 적합 (토큰 비용 0)
3. **Git pull --rebase before push**: state file 충돌 방지. `git diff --cached --quiet`로 빈 커밋 방지
4. **Wiki page overwrite**: 기존 `Moltbook_트렌드_분석.md`를 매번 갱신 (최신 데이터로 교체)

### Cron Registration

```bash
hermes cron create \\
  --name "moltbook-monthly-trend" \\
  --schedule "0 0 1 * *" \\
  --script "moltbook_trend_analyzer.sh" \\
  --no-agent \\
  --deliver "origin"
```

> ⚠️ **Credential in script**: Service Role Key가 bash 스크립트에 평문 노출됨. GitHub Secrets 대안보다 빠른 실행이 우선인 경우 선택. 보안 강화 필요시 `~/.hermes/.env`에서 읽도록 개선.

## Query Examples

```bash
# 특정 기간 카테고리별 집계
curl -s "$SUPABASE_URL/rest/v1/moltbook_reports?select=category&created_at=gte.2026-04-01&created_at=lt.2026-05-01" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"

# 전체 키워드 히스토그램 (pg view가 있다면)
curl -s "$SUPABASE_URL/rest/v1/rpc/keyword_frequencies?since=2026-04-01" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

## Pitfalls

- **Timezone**: Supabase timestamps in UTC, user in KST(UTC+9). 월간 롤업시 KST 기준으로 날짜 계산 필요
- **No gh CLI**: `khmo31` 서버에 GitHub CLI 미설치. Secret 직접 입력 우선
- **보존 정책**: `moltbook_reports` 는 영구 보관 대상, `posts`/`comments`는 30일 retention
- **키워드 JSONB 타입**: keywords 컬럼이 `["#AI", "#Security"]` 문자열 배열. 소문자 변환(`kw.lower()`) 후 Counter 필수 (대소문자 중복 방지)
- **`report_date` vs `created_at`**: 트렌드 분석은 `report_date` (리포트 기준일) 사용, `created_at` (Supabase 적재일) 아님. 두 값이 다를 수 있음
- **월초 prev_month 계산**: `now.replace(day=1) - timedelta(days=1)`로 전월 계산. 직접 월 뺄셈(`month - 1`)은 1월에서 12월로 갈 때 연도 처리 필요
- **category 필드 철자**: Supabase에 저장된 값은 `Philosophy` (영문). 검색/필터시 한글('철학')이 아닌 영문으로 쿼리해야 함
- **기타 카테고리 50%**: Groq 카테고리 분류가 광범위함. 서브카테고리(생산성/운영/커뮤니케이션) 도입 필요
