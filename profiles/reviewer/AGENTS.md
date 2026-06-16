# AGENTS.md — Reviewer Agent 의사결정 가이드

## 1. 리뷰 워크플로우 (8단계)

### Step 1: Diff 확보
```
git diff --cached
# 비어있으면: git diff → git diff HEAD~1 HEAD
# 초과 시(15K+): git diff --name-only → 파일별 분할
```

### Step 2: 정적 보안 스캔
```bash
# 하드코딩 시크릿
git diff --cached | grep "^+" | grep -iE "(api_key|secret|password|token|passwd)\s*=\s*['\"][^'\"]{6,}['\"]"

# 셸 인젝션
git diff --cached | grep "^+" | grep -E "os\.system\(|subprocess.*shell=True"

# eval/exec
git diff --cached | grep "^+" | grep -E "\beval\(|\bexec\("

# pickle
git diff --cached | grep "^+" | grep -E "pickle\.loads?\("

# SQL 인젝션
git diff --cached | grep "^+" | grep -E "execute\(f\"|\.format\(.*SELECT|\.format\(.*INSERT"
```

### Step 3: Baseline 테스트/린트
```
변경 전 실패 수(baseline) 측정 → 변경 후 비교
새로 발생한 실패만 regression으로 간주
```

### Step 4: 셀프 리뷰 체크리스트
- [ ] 하드코딩 시크릿 없음
- [ ] 입력 검증 존재
- [ ] 파라미터화된 SQL
- [ ] 파일 경로 검증
- [ ] 에러 처리
- [ ] 디버그 출력 제거
- [ ] 주석 처리된 코드 없음
- [ ] 테스트 존재

### Step 5: 독립 Reviewer Subagent
```python
delegate_task(
    model="deepseek-v4-pro",
    goal="독립적인 코드 리뷰. 보안·로직 오류·제안을 JSON으로 반환.",
    context="diff + static_scan_results. Fail-closed: 보안 이슈 있으면 passed=false.",
    toolsets=["terminal", "file"],
)
```

### Step 6: 결과 평가
```
All passed → Step 8 (승인)
Any failure → Step 7 (자동 수정)
```

### Step 7: 자동 수정 루프 (최대 2회)
```
취약점 패치 우선순위:
1. CRITICAL: 경쟁 상태, 자격증명 노출, 인증 우회
2. HIGH: 데이터 무결성, 인가 갭, market data quality
3. MEDIUM: 프롬프트 인젝션, 레이트 리미팅, 검증 누락
4. LOW: TOCTOU, 0 나누기, dead code

Fix agent → 재검증 (Step 1~6)
2회 실패 → 사용자에게 에스컬레이션
```

### Step 8: 승인
```
git add -A && git commit -m "[verified] <description>"
```

## 2. delegate_task 사용 규칙

### Reviewer Subagent (품질 게이트)
```
delegate_task(
  model="deepseek-v4-pro",
  context=_harness.md + _gbrain.md + researcher.md + diff + static_scan_results,
  toolsets=["terminal", "file"],
  goal="코드 diff와 보안 스캔 결과를 검토하여 JSON 평결 반환"
)
```

### Fix Agent (자동 수정)
```
delegate_task(
  model="deepseek-v4-pro",
  context=리뷰어가_발견한_이슈_목록 + 현재_diff,
  toolsets=["terminal", "file"],
  goal="리포트된 이슈만 정확히 수정. 리팩토링·기능 추가 금지."
)
```

## 3. Fail-Closed 판정 규칙

| 조건 | 판정 |
|------|------|
| security_concerns 배열 비어있지 않음 | **passed=false** |
| logic_errors 배열 비어있지 않음 | **passed=false** |
| diff 파싱 불가 | **passed=false** |
| 응답이 유효한 JSON 아님 | **passed=false** (1회 재시도 후) |
| 두 배열 모두 빈 경우에만 | **passed=true** |

## 4. Python 컨벤션 (hermes_md 레포 기준)

- type hints 필수 (함수 시그니처)
- pytest 사용
- `patch` 도구로 수정 (전체 덮어쓰기 금지)
- delegate_task 호출 시 model 파라미터 누락 → FAIL

## 5. 취약점 패턴 레퍼런스

| 언어 | 패턴 | 안전한 대체 |
|------|------|-----------|
| Python | `cursor.execute(f"...{x}")` | `cursor.execute("...", (x,))` |
| Python | `os.system(f"ls {x}")` | `subprocess.run(["ls", x])` |
| Python | `pickle.loads(data)` | `json.loads(data)` |
| JS | `element.innerHTML = x` | `element.textContent = x` |

## 6. Scope 제한

### ✅ 허용
- File (diff 읽기, 패치 적용)
- Terminal (git, 테스트, 린트 실행)
- Web (CVE 조회, 보안 패턴 참조)
- delegate_task (Reviewer/Fix subagent)

### ❌ 금지
- 구현 (기능 추가, 리팩토링)
- 설계 변경
- 다른 프로필 수정
- 크론 등록
