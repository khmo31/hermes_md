# Role Injection System

## 아키텍처

```
~/.hermes/roles/
├── _harness.md           26KB  Base — 행동 교정/검증 루프 (revfactory/harness)
├── _gbrain.md            27KB  Base — 계약 기반 설계/trust boundary (garrytan/gbrain)
├── technical-writer.md   25KB  Role — 문서/AI어투 제거 (epoko77-ai/im-not-ai)
├── coder.md              25KB  Role — 코딩/구현 (awesome-copilot + oh-my-pi)
└── researcher.md         33KB  Role — 리서치/분석 (academic-research-skills + last30days-skill)
```

## Context Injection 순서

모든 delegate_task 서브에이전트는 다음 순서로 context 주입:

```python
def build_context(role_name):
    harness = read_file("~/.hermes/roles/_harness.md")["content"]
    gbrain = read_file("~/.hermes/roles/_gbrain.md")["content"]
    role = read_file(f"~/.hermes/roles/{role_name}.md")["content"]
    return harness + "\n---\n" + gbrain + "\n---\n" + role
```

## 각 레이어의 역할

### Layer 1: _harness.md (모든 에이전트 공통)
- **목적**: AI 에이전트의 행동을 교정하고 통제
- **출처**: [revfactory/harness](https://github.com/revfactory/harness)
- **핵심 섹션**:
  1. Core Behavioral Principles — why-first, progressive disclosure
  2. 6 Architecture Patterns — 2 execution modes, team size limits
  3. Behavior Correction — dedup gates, agent definition requirements
  4. Verification Loop — structural/execution/trigger verification
  5. Skill Writing Standards — description as trigger, data schemas
  6. QA Guidelines — boundary cross-comparison, read-both-sides

### Layer 2: _gbrain.md (모든 에이전트 공통)
- **목적**: 다중 에이전트 오케스트레이션 패턴, 계약 기반 설계
- **출처**: [garrytan/gbrain](https://github.com/garrytan/gbrain) (⭐21.9k)
- **핵심 섹션**:
  1. Two-Axis Mental Model — brain(분석/의사결정) + source(데이터/검증)
  2. Trust Boundary — fail-closed, permission model
  3. Contract Pattern — 선언적 계약 기반 에이전트 설계 (gbrain 핵심 차별점)
  4. Search Modes — 12가지 검색 모드
  5. Anti-Patterns — 금지 패턴

### Layer 3: role-specific.md (역할별)
- **목적**: 역할 정체성, 워크플로우, 품질 기준, 도메인 지식
- **technical-writer.md** — AI 티 분류 체계 A~J 10개, 4대 철칙, 탐지→윤문→검증 파이프라인
- **coder.md** — 에이전트 정의 포맷, 명령어/스킬/훅 구조, 개발 규칙, 품질 기준
- **researcher.md** — 6단계 리서치 파이프라인, 13가지 검색 소스, 데이터 무결성 게이트

## 새로운 역할 정의서 생성 방법

사용자가 새로운 GitHub 레포 링크를 제공하면:

1. **클론**: `git clone <url> ~/tmp/role-sources/<name>/`
2. **전체 탐색**: `find ~/tmp/role-sources/<name>/ -name "*.md" -type f` 로 모든 파일 확인
3. **핵심 파일 집중 읽기**: CLAUDE.md, AGENTS.md, README.md, SKILL.md, agents/*.md, references/*.md
4. **원문 충실도 유지**: 요약 금지, 원문 표현 그대로 인용
   - 수치·고유명사·인용문·기술용어 변경 금지
   - 코드 블록과 표 형식 원본 유지
5. **8섹션 구조로 정리**: Identity / Workflow / Rules / Quality Gates / Fidelity Rules / Anti-Patterns / References
6. **다중 레포 통합**: 상호 보완적이면 통합, 충돌 시 별도 표기

## 실행 예제

```python
# 대량 Notion 페이지 처리 패턴
# 1. Notion REST API로 페이지 블록 수집 → 파일 저장
# 2. delegate_task로 AI어투 제거 위임 (파일 기반, full role context 주입)
# 3. 결과를 Notion API PATCH로 업데이트

# MCP 없는 경우 Notion API 대체:
curl -s "https://api.notion.com/v1/blocks/{page_id}/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28"

# 블록 수정:
curl -X PATCH "https://api.notion.com/v1/blocks/{block_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Notion-Version: 2022-06-28" \
  -d '{"paragraph": {"rich_text": [{"type": "text", "text": {"content": "새 텍스트"}}]}}'
```
