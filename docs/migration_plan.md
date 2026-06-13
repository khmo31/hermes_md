# Wiki 파일 다축 Frontmatter 마이그레이션 계획

> 대상: `~/second_brain/10_Wiki/` 내 기존 105개 마크다운 파일
> 목표: 폴더 기반 단일축 → frontmatter 다축 분류 전환

---

## 1. 현황

| 항목 | 수치 |
|------|------|
| 총 Wiki 파일 | 105개 |
| 카테고리 분포 | topic 69, project 45, decision 13, guide 2, skill 1 |
| 폴더 구조 | `10_Wiki/{Decisions,Topics,Projects,Guides,Skills}/` |

---

## 2. 마이그레이션 원칙

1. **원본 보존**: 기존 파일을 먼저 백업. 실패 시 즉시 롤백 가능.
2. **점진적 적용**: 한 번에 전체가 아니라 배치 단위로 처리.
3. **수동 검수 필수**: 자동 삽입된 frontmatter는 반드시 사람이 확인.
4. **Idempotent**: 동일 파일에 재실행해도 중복 frontmatter 생성 금지.

---

## 3. 마이그레이션 단계

### Phase 1: Dry-run (영향도 평가)

```bash
cd ~/second_brain

# 1. 현재 상태 스냅샷
find 10_Wiki/ -name "*.md" | sort > /tmp/wiki_files_before.txt

# 2. frontmatter 이미 있는 파일 수
grep -rl "^---$" 10_Wiki/ | wc -l

# 3. 각 파일의 현재 폴더 기반 type 추출
for f in $(find 10_Wiki/ -name "*.md" -not -name "README.md"); do
    dir=$(dirname "$f" | xargs basename)
    echo "$f → type: $dir"
done > /tmp/type_mapping.txt
```

**성공 기준**: 모든 파일이 누락 없이 매핑됨.

### Phase 2: 자동 Frontmatter 삽입 (스크립트)

```python
#!/usr/bin/env python3
"""기존 Wiki 파일에 frontmatter 자동 삽입"""
import os, re, yaml
from pathlib import Path

BASE = os.path.expanduser("~/second_brain/10_Wiki")
DOMAIN_KEYWORDS = {
    "trading": ["트레이딩", "KIS", "주식", "매매", "trading", "auto_investment"],
    "ai-ml": ["LLM", "RAG", "임베딩", "프롬프트", "fine-tuning", "DSPy", "LangGraph"],
    "devops": ["Docker", "배포", "CI/CD", "서버", "nginx", "인프라"],
    "smarthome": ["Home Assistant", "MQTT", "HA", "OpenHue", "IoT"],
    "hermes": ["Hermes", "delegate_task", "cron", "SOUL", "AGENTS", "스킬"],
    "toeic": ["TOEIC", "토익", "LC", "RC", "Part 5", "Part 6", "Part 7"],
}

def infer_domain(content: str, filename: str) -> str:
    text = (content + filename).lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw.lower() in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"

def infer_status(content: str) -> str:
    if "DEPRECATED" in content or "deprecated" in content.lower():
        return "deprecated"
    return "draft"  # 기존 파일은 검증 전이므로 draft

def infer_type_from_path(path: str) -> str:
    folder = Path(path).parent.name.lower()
    mapping = {
        "decisions": "decision", "topics": "topic",
        "projects": "project", "guides": "guide", "skills": "skill"
    }
    return mapping.get(folder, "topic")

def add_frontmatter(filepath: str) -> bool:
    with open(filepath) as f:
        content = f.read()

    # 이미 frontmatter 있으면 건너뛰기
    if content.startswith("---"):
        return False

    fname = os.path.basename(filepath)
    ftype = infer_type_from_path(filepath)
    domain = infer_domain(content, fname)
    status = infer_status(content)

    # Extract title from first heading
    title_match = re.search(r'^#{1,2}\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else fname.replace(".md", "")

    # Extract date from filename or mtime
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', fname)
    date = date_match.group(1) if date_match else "2026-06-13"  # default

    frontmatter = f"""---
type: {ftype}
domain: {domain}
status: {status}
source: research
tags: []
date: {date}
# AUTO-GENERATED — 수동 검수 필요
---

"""
    with open(filepath, "w") as f:
        f.write(frontmatter + content)
    return True

# Main
count = 0
for root, dirs, files in os.walk(BASE):
    for f in files:
        if f == "README.md" or not f.endswith(".md"):
            continue
        fp = os.path.join(root, f)
        if add_frontmatter(fp):
            print(f"  +frontmatter: {fp}")
            count += 1

print(f"\nTotal: {count} files updated")
```

**실행**:
```bash
cd ~/second_brain
cp -r 10_Wiki 10_Wiki_backup_$(date +%Y%m%d)  # 백업
python3 add_frontmatter.py > /tmp/migration_log.txt
```

**성공 기준**: 105개 중 90% 이상에 frontmatter 삽입, 중복 생성 0건.

### Phase 3: 수동 검수 (필수)

1. `grep -r "AUTO-GENERATED" 10_Wiki/` → 수동 검수 대상 목록
2. 파일별로 `type`, `domain`, `status`, `tags` 확인 및 수정
3. `# AUTO-GENERATED — 수동 검수 필요` 라인 삭제
4. 수정 완료 시 `status: draft` → 적절한 값으로 변경

**검수 기준**:
- `type`이 폴더 위치와 일치하는가?
- `domain`이 내용과 일치하는가? (부정확하면 직접 수정)
- `status`가 적절한가? (명백히 stable한 노트는 draft→stable로 변경)

### Phase 4: 검증

```bash
# 1. frontmatter 없는 파일 확인 (0이어야 함)
find 10_Wiki/ -name "*.md" -not -name "README.md" | while read f; do
    head -1 "$f" | grep -q "^---$" || echo "MISSING: $f"
done

# 2. domain/type 유효성 검증
grep -rh "^domain:" 10_Wiki/ | sort | uniq -c
grep -rh "^type:" 10_Wiki/ | sort | uniq -c

# 3. status 분포
grep -rh "^status:" 10_Wiki/ | sort | uniq -c

# 4. migrated vs failed
wc -l /tmp/wiki_files_before.txt  # before
find 10_Wiki/ -name "*.md" -not -name "README.md" | wc -l  # after (같아야 함)
```

**성공 기준**: frontmatter 누락 0건, 파일 수 불변, domain/type/status가 허용된 enum 값만 사용.

### Phase 5: Git Commit + 평탄화

```bash
cd ~/second_brain
git add -A
git commit -m "migration: 다축 frontmatter 추가 (105개 Wiki 파일)"
git push

# 평탄화: 폴더 구조 제거 (선택적 — 검증 완료 후)
# 모든 파일을 10_Wiki/ 루트로 이동
```

---

## 4. 롤백 계획

```bash
# 전체 롤백
cd ~/second_brain
rm -rf 10_Wiki
cp -r 10_Wiki_backup_$(date +%Y%m%d) 10_Wiki
git add -A && git commit -m "rollback: migration reverted" && git push

# 부분 롤백 (특정 파일만)
cp 10_Wiki_backup_20260613/Decisions/some_file.md 10_Wiki/Decisions/
```

---

## 5. 마이그레이션 후 평탄화

frontmatter가 모든 파일에 추가된 후, 폴더 구조를 제거하고 `10_Wiki/` 루트로 평탄화한다:

```bash
cd ~/second_brain/10_Wiki
for dir in Decisions Topics Projects Guides Skills; do
    mv $dir/*.md . 2>/dev/null
    rmdir $dir 2>/dev/null
done
git add -A && git commit -m "refactor: Wiki 평탄화 (폴더→frontmatter)"
```

이후 검색은 frontmatter 필드로만 수행. 폴더 구조는 deprecated.

---

## 6. 마이그레이션 체크리스트

- [ ] Phase 1: dry-run 완료, 모든 파일 매핑 확인
- [ ] Phase 2: 자동 frontmatter 삽입 실행, 로그 확인
- [ ] Phase 3: 105개 파일 수동 검수 완료
- [ ] Phase 4: 유효성 검증 통과 (누락 0, enum 검증)
- [ ] Phase 5: git commit + push
- [ ] 평탄화: 폴더 구조 제거 (선택적)
- [ ] wiki-pipeline cron이 새 frontmatter 포맷으로 정상 작동 확인
