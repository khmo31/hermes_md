# AGENTS.md — Writer Agent 의사결정 가이드

## 1. AI 티 탐지 → 윤문 파이프라인

### Fast 모드 (디폴트, 5,000자 이하)

```
입력 텍스트
  → AI 티 탐지 (A~J 10대 분류 기준)
  → 패턴별 교정 (의미 불변, Span-Grounded)
  → 자체 검증 (변경률 확인)
  → 최종 출력
```

### Strict 모드 (8,000자+ 또는 사용자 요청 시)

```
입력 텍스트
  → [탐지] span·category·severity·suggested_fix JSON 리포트
  → [윤문] finding 기반 수술적 윤문 (변경률 모니터링)
  → [검증] 의미 동등성 감사 + 잔존 AI 티 재탐지
  → [판정] accept / rewrite(최대 3회) / hold_and_report
```

## 2. 10대 AI 티 분류 체계 (technical-writer.md §3 발췌)

| ID | 대분류 | 핵심 패턴 예시 |
|----|-------|---------------|
| A | 번역투 | "~를 통해", "~에 대해", "~되어진다", "그/그녀" |
| B | 영어 인용·용어 과다 | 과도한 괄호 병기, 비번역 영어 |
| C | 구조적 AI 패턴 | 기계적 "첫째/둘째/셋째", 과도한 불릿 |
| D | AI 특유 관용구 | "결론적으로", "시사하는 바가 크다" |
| E | 리듬·문장 길이 균일성 | 문장 길이 편차 낮음, 동일 종결어미 반복 |
| F | 과도한 수식·중복 | "매우", "정말", "혁신적인" |
| G | Hedging 남용 | "~할 수 있을 것으로 보인다" |
| H | 접속사 남발 | 문두 "또한/따라서/즉/나아가" 연속 |
| I | 형식명사 과다 | "것이다", "점", "수", "바" |
| J | 시각 장식 남용 | 과도한 **볼드**, "따옴표", 대시(—) |

## 3. Notion API 워크플로우

### 페이지 읽기 → 윤문 → 저장

```
1. mcp_notion_API_get_block_children(page_id) → 원문 블록 목록
2. rich_text 추출 → 평문 변환
3. AI 티 탐지 → 윤문
4. mcp_notion_API_update_a_block(block_id, 새 rich_text) → 블록별 PATCH
```

### 주의사항
- Notion API 블록 100개 제한 → 대용량 페이지는 페이지네이션
- `mcp_notion_API_patch_page`는 페이지 속성만, 본문은 블록 API 사용
- 레이트리밋: 3 req/sec → 블록 100개 이상 시 분할 처리

## 4. delegate_task 사용 (writer 프로필 내부)

복잡한 문서 처리 시 delegate_task로 분할:

```
# AI어투 탐지 (분석 집중)
delegate_task(
  model="qwen3.7-max",
  context=technical-writer.md §3 + 입력 텍스트,
  toolsets=["file"],
  goal="텍스트에서 AI 티 패턴(A~J) 탐지 및 JSON 리포트 생성"
)

# 윤문 적용
delegate_task(
  model="qwen3.7-max",
  context=탐지_리포트 + 입력_텍스트,
  toolsets=["file"],
  goal="탐지된 AI 티 패턴을 교정하여 자연스러운 한국어로 윤문"
)
```

## 5. Khmo31 문체 적응 규칙

### 필수 적용
- 종결어미: `~것이다` 체 우선
- "~입니다", "~합니다" → "~것이다" (기술 문서)
- "도움이 되셨길 바랍니다" → 삭제
- "~인 것으로 보입니다" → "~이다" (확정) 또는 "확인 필요" (불확실)
- "확실히 말씀드리자면" → 삭제 (군더더기)

### 보존 대상
- 기술 용어 (원어 그대로)
- 코드 블록, 명령어
- 수치, 날짜, 고유명사
- 인용문

## 6. Scope 제한

### ✅ 허용
- Notion API (읽기/쓰기)
- File (마크다운 파일 생성/수정)
- delegate_task (내부 subagent)

### ❌ 금지
- Terminal (문서 작업에 불필요)
- Web (Notion API로 충분)
- Cronjob 등록
- 다른 프로필/SOUL.md 수정
