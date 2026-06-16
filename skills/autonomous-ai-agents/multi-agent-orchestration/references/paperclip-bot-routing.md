# Paperclip Bot Routing 패턴 — Content-based Agent Routing

`bot.py`의 `resolve_agent()` 구현. 접두사 매칭 + 점수 기반 키워드 매칭.

## 라우팅 파이프라인

```python
# 3-Stage Routing Pipeline
#
# [Discord Message]
#   │
#   ├─ Stage 1: Prefix Match (startswith)
#   │   ├─ "03 API 구현" → 03-핵심로직 (v4-pro)
#   │   └─ No match → Stage 2
#   │
#   ├─ Stage 2: Content Score Match
#   │   ├─ 각 route의 keyword와 메시지 내 일치 개수 계산
#   │   ├─ 최고 점수 route 선택 (동점 시 CONTENT_ROUTES 순서 우선)
#   │   ├─ "노션 문서 AI어투 수정" → 글쓰기 (score: 6)
#   │   └─ Score 0 → Stage 3
#   │
#   └─ Stage 3: Fallback
#       └─ 00-라우터 (orchestrator)
```

## CONTENT_ROUTES 테이블 설계

```python
CONTENT_ROUTES = [
    # 빈도 높은 route 우선 배치
    (["노션", "문서", "작성", "편집", "AI어투", "어투", "느낀점",
      "회고", "블로그", "포스트", "레터", "뉴스레터", "카피", "초안"], "글쓰기"),
    (["번역", "다국어", "영문화", "한국어로", "영어로"], "번역"),
    (["분석", "조사", "리서치", "검색", "찾아줘", "알아봐", "트렌드",
      "시장", "동향", "비교", "장단점"], "웹서치"),
    (["기획", "설계", "아키텍처", "요구사항", "스펙", "명세"], "01-기획"),
    (["버그", "오류", "에러", "안됨", "고장", "수정해줘", "고쳐줘",
      "디버깅", "실패", "장애"], "05-디버거"),
    (["API", "CRUD", "DB", "데이터베이스", "백엔드", "서버",
      "엔드포인트", "라우트", "sql", "SQL"], "03-핵심로직"),
    (["UI", "프론트", "화면", "CSS", "컴포넌트", "React", "디자인"], "04-양산"),
    (["테스트", "검증", "QA", "유닛테스트", "통합테스트"], "06-테스트"),
    (["코드리뷰", "리뷰", "PR", "코드검토"], "02-코드스캔"),
]
```

## resolve_agent() — 핵심 로직

```python
def resolve_agent(content: str) -> tuple[str, str, str, bool | str]:
    """
    Returns: (agent_id, agent_name, cleaned_title, matched)
    matched=True  → prefix match (explicit)
    matched='content' → content score match
    matched=False → fallback to 00-라우터
    """
    content = content.strip()
    sorted_prefixes = sorted(AGENT_PREFIX_MAP.keys(), key=len, reverse=True)

    # Stage 1: Prefix match
    for prefix in sorted_prefixes:
        if content.startswith(prefix):
            rest = content[len(prefix):].strip().lstrip(" :,.-")
            if rest:
                entry = AGENT_PREFIX_MAP[prefix]
                return entry["id"], entry["name"], rest, True

    # Stage 2: Content score match
    scores = {}
    for keywords, agent_pattern in CONTENT_ROUTES:
        score = sum(1 for kw in keywords if kw in content)
        if score > 0:
            scores[agent_pattern] = scores.get(agent_pattern, 0) + score

    if scores:
        best_pattern, best_score = max(scores.items(), key=lambda x: x[1])
        best = _find_best_agent(best_pattern)
        if best:
            return best["id"], best["name"], content, "content"

    # Stage 3: Fallback
    router = AGENT_PREFIX_MAP.get("00-라우터 (orchestrator)")
    if router:
        return router["id"], router["name"], content, False
    return "", "00-라우터 (orchestrator)", content, False
```

## agent lookup helper

```python
def _find_best_agent(pattern: str) -> dict | None:
    """Find the best matching agent entry for 'pattern in name'."""
    best = None
    for key, entry in AGENT_PREFIX_MAP.items():
        if pattern in key and key.endswith(")"):
            return entry  # exact match with full name
        if pattern in key and best is None:
            best = entry
    return best
```

## 키워드 설계 주의사항

1. **짧은 키워드 = 모호**: `"수정"`은 글쓰기("문서 수정")와 디버거("버그 수정") 모두에 포함됨
   - 해결: `"수정해줘"`(longer form)만 디버거에 추가하고 `"수정"` 단독은 제거
   - 점수 기반 매칭: "문서 수정" → 글쓰기 2점 vs 디버거 0점 → 글쓰기 ✅
   - "버그 수정 로그인 안됨" → 글쓰기 1점 vs 디버거 3점 → 디버거 ✅

2. **대문자/소문자 구분**: `"sql"`과 `"SQL"` 둘 다 리스트에 포함시킬 것 (파이썬의 `in`은 대소문자 구분)

3. **빈도 기준 정렬**: 가장 자주 매칭될 route(글쓰기)를 상단에 배치 — 동점 시 상단 우선이므로

## 메시지 응답 포맷

```python
# Prefix match → 즉시 할당, watching 불필요
await channel.send(f"✅ **{issue_id}** → `{agent_name}`\n└─ {title}")

# Content match → watching 필요
label = "자동 분류"
await channel.send(f"🔀 **{issue_id}** → `{agent_name}` ({label})\n└─ {title}\n작업 완료 시 자동으로 결과를 알려드립니다.")

# Fallback → watching 필요
label = "분류 대기"
await channel.send(f"🔀 **{issue_id}** → `{agent_name}` ({label})\n└─ {title}\n작업 완료 시 자동으로 결과를 알려드립니다.")
```

`matched is True`만 `if matched:`에서 즉시 할당 처리.
`matched == "content"`와 `matched is False`는 모두 watching 처리 (완료 시 Discord 알림).
