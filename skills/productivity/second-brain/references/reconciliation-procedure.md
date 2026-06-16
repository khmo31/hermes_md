# State File Reconciliation Procedure

> Run this when the wiki pipeline reports "no new files" but you suspect state files
> are out of sync (desync). Performs a full 3-way cross-reference between disk files,
> `wiki_state.json`, and `processed_raw.json`.

## Quick Reference

### Three State Sources

| Source | Key Format | Location |
|--------|-----------|----------|
| Disk (01_Parsed/) | `YYYY-MM-DD/rest/of/path.md` | `~/second_brain/01_Parsed/` |
| wiki_state.json | `YYYY-MM-DD/rest/of/path.md` (no `01_Parsed/` prefix) | `~/second_brain/20_Meta/wiki_state.json` |
| wiki_state.json (raw flat files) | `YYYY-MM-DD.md` (bare filename, no prefix) | (same file as above) |
| processed_raw.json (parsed) | `01_Parsed/YYYY-MM-DD/rest/of/path.md` (full) | `~/second_brain/agent/processed_raw.json` |
| processed_raw.json (raw flat) | `00_Raw/YYYY-MM-DD.md` (with `00_Raw/` prefix) | (same file as above) |

> **Key format pitfall**: `wiki_state.json` stores 00_Raw flat file keys as bare filenames (e.g. `2026-05-18.md`), while `processed_raw.json` stores them with the `00_Raw/` prefix (e.g. `00_Raw/2026-05-18.md`). When cross-referencing, remember to add/strip the prefix appropriately.

### Three Desync Directions

| Direction | Symptom | Fix |
|-----------|---------|-----|
| **A** | Wiki entry exists on disk in `10_Wiki/`, but NOT in either state file | Add both `wiki_state.json` and `processed_raw.json` entries. Use `reconciled/Category/filename.md` as the synthetic source key. |
| **B** | Entry is in `wiki_state.json` (and wiki exists on disk), but NOT in `processed_raw.json` | Add `processed_raw.json` entry with file's SHA1, mtime, wiki path. |
| **C** | File is in `processed_raw.json`, but NOT in `wiki_state.json` | Add `wiki_state.json` entry using title extracted from existing wiki file. |

### Key Format Differences for Cross-Reference

When checking if a `01_Parsed/` file has been wiki-processed:
- `wiki_state.json` keys are **relative to `01_Parsed/`**: `2026-05-16/github/khmo31/README.md`
- `processed_raw.json` keys are **full paths**: `01_Parsed/2026-05-16/github/khmo31/README.md`
- `00_Raw` flat file keys in `wiki_state.json` are **just the filename**: `2026-05-18.md`
- `00_Raw` flat file keys in `processed_raw.json` are **`00_Raw/filename`**: `00_Raw/2026-05-18.md`

## Structural README Detection

A README.md is **structural noise** (skip) if it describes the wiki's own directory structure. A README.md is **content** (process) if it describes an external project/tool.

### All Structural README Paths

These paths describe the wiki's own directories and should be skipped:
- `10_Wiki/Decisions/README.md`
- `10_Wiki/Guides/README.md`
- `10_Wiki/Meetings/README.md`
- `10_Wiki/Postmortems/README.md`
- `10_Wiki/Projects/README.md`
- `10_Wiki/RFCs/README.md`
- `10_Wiki/Releases/README.md`
- `10_Wiki/Skills/README.md`
- `10_Wiki/Topics/README.md`
- `10_Wiki/README.md`
- `00_Raw/README.md`

### Regex for Detection

```python
import re
is_structural = bool(re.search(
    r'(?:^|/)10_Wiki/(?:Decisions|Guides|Meetings|Postmortems|Projects|RFCs|Releases|Skills|Topics)/README\.md$',
    path
)) or path == '00_Raw/README.md'
```

> **⚠️ Pitfall**: The regex must start with `(?:^|/)` not just `/` — the path does not have a leading `/` (it's `10_Wiki/Decisions/README.md`, not `/10_Wiki/Decisions/README.md`).

### Title Extraction — Handles Both `#` and `##` Headings

Wiki files may use either `# Title` (h1) or `## Title (timestamp)` (h2) for the document title. Always use:

```python
title_match = re.search(r'^#{1,2} (.+)$', content, re.MULTILINE)
file_title = title_match.group(1).strip() if title_match else filename.replace('.md', '').replace('_', ' ')
# Strip trailing timestamps or parenthetical suffixes
file_title = file_title.split(' (')[0].strip()
```

> **⚠️ Pitfall**: Some files use `##` (h2) heading format (e.g., `## AI 시대의 기술 변화와 피지컬 AI 혁신 (2026-05-17 21:00:16 UTC)`). Using `r'^# (.+)$'` alone misses these. Always use `r'^#{1,2} (.+)$'`.

### The `reconciled/` Key Prefix

When adding a wiki entry that exists on disk but has NO corresponding source file in `01_Parsed/` (Direction A with no source), use a synthetic key with the `reconciled/` prefix:

```python
ws_key = f"reconciled/{category}/{filename}"
pr_key = f"reconciled/{category}/{filename}"
```

Example: `reconciled/Decisions/AI시대의_바이브_코딩과_피지컬_AI_혁신.md`

This pattern:
- Is clearly identifiable as a reconciliation artifact (not sourced from a real pipeline run)
- Keeps the source file in a known searchable format
- Avoids key collisions with real pipeline entries

## Reconciliation Script

Run this from a cron pipeline context to detect and fix all three desync directions:

```python
import json, os, hashlib, re
from datetime import datetime, timezone

base = os.path.expanduser('~/second_brain')
now = datetime.now(timezone.utc).isoformat()

# Category mapping from wiki directory name to wiki_state category value
CATEGORY_MAP = {
    'Decisions': 'decision', 'Topics': 'topic', 'Projects': 'project',
    'Guides': 'guide', 'Skills': 'skill', 'Meetings': 'meeting',
    'Postmortems': 'postmortem', 'RFCs': 'rfc', 'Releases': 'release'
}
WIKI_CATEGORIES = list(CATEGORY_MAP.keys())

# Structural README patterns
STRUCTURAL_README_RE = re.compile(
    r'(?:^|/)10_Wiki/(?:Decisions|Guides|Meetings|Postmortems|Projects|RFCs|Releases|Skills|Topics)/README\.md$'
)

def extract_title(content, filename):
    """Extract wiki entry title from file content. Handles both # and ## headings."""
    title_match = re.search(r'^#{1,2} (.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # Strip trailing parenthetical timestamps
        title = title.split(' (')[0].strip()
        return title
    return filename.replace('.md', '').replace('_', ' ').strip()

def is_structural_readme(path):
    """Check if path is a structural README (wiki directory description)."""
    if path == '00_Raw/README.md':
        return True
    return bool(STRUCTURAL_README_RE.search(path))

def normalize_title(title):
    """Normalize title for cross-referencing between state files and disk filenames."""
    s = title.replace(' ', '_').lower().strip()
    s = re.sub(r'[^\\w\\uAC00-\\uD7AF]', '_', s)
    s = re.sub(r'_+', '_', s)
    return s

# 1. Load state files
with open(os.path.join(base, '20_Meta/wiki_state.json')) as f:
    ws = json.load(f)
with open(os.path.join(base, 'agent/processed_raw.json')) as f:
    pr = json.load(f)

# 2. Index all wiki entries on disk (10_Wiki/...)
disk_wiki_entries = {}  # {relative_path: (category, title)}
for cat in WIKI_CATEGORIES:
    cat_dir = os.path.join(base, '10_Wiki', cat)
    if not os.path.isdir(cat_dir):
        continue
    result = subprocess.run(['find', cat_dir, '-name', '*.md', '-type', 'f'],
                           capture_output=True, text=True)
    if not result.stdout.strip():
        continue
    for fpath in result.stdout.strip().split('\\n'):
        rel = fpath.replace(base + '/', '')
        if is_structural_readme(rel):
            continue
        with open(fpath) as f:
            content = f.read(5000)
        title = extract_title(content, os.path.basename(fpath))
        disk_wiki_entries[rel] = (cat, title)

print(f'Wiki entries on disk: {len(disk_wiki_entries)}')

# 3. Build lookups for state files
# wiki_state normalized titles
ws_titles = {}
for ws_key, ws_val in ws.get('processed', {}).items():
    norm = normalize_title(ws_val.get('title', ''))
    ws_titles[norm] = ws_key

# processed_raw wiki_paths
pr_wiki_paths = set()
for pr_val in pr.get('items', {}).values():
    wp = pr_val.get('wiki_path', '')
    if wp:
        pr_wiki_paths.add(wp)

# 4. Direction A: wiki entry exists on disk but NOT in any state file
added_a = 0
for wiki_rel, (cat, title) in sorted(disk_wiki_entries.items()):
    if wiki_rel in pr_wiki_paths:
        continue
    norm = normalize_title(title)
    if norm in ws_titles:
        continue
    
    filename = os.path.basename(wiki_rel)
    ws_cat = CATEGORY_MAP.get(cat, 'topic')
    mtime = os.path.getmtime(os.path.join(base, wiki_rel))
    fsize = os.path.getsize(os.path.join(base, wiki_rel))
    src_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    
    ws_key = f'reconciled/{cat}/{filename}'
    ws['processed'][ws_key] = {
        'at': now, 'title': title, 'category': ws_cat,
        'source_size': fsize, 'source_date': src_date
    }
    with open(os.path.join(base, wiki_rel)) as f:
        content = f.read()
    pr['items'][ws_key] = {
        'wiki_path': wiki_rel,
        'raw_sha1': hashlib.sha1(content.encode()).hexdigest(),
        'raw_mtime_ns': str(int(mtime * 1e9)),
        'last_processed': now,
        'policy_fingerprint': 'reconciliation-fix'
    }
    ws_titles[norm] = ws_key
    pr_wiki_paths.add(wiki_rel)
    added_a += 1
    print(f'  [Dir A] +{ws_cat} {title} -> {wiki_rel}')

print(f'Direction A additions: {added_a}')

# 5. Direction B: wiki_state has it, processed_raw doesn't
added_b = 0
for ws_key, ws_val in list(ws.get('processed', {}).items()):
    # Skip reconciled entries (already in both)
    if ws_key.startswith('reconciled/'):
        continue
    # Build the corresponding pr key
    if '/' not in ws_key:
        # Flat file key (e.g. 2026-05-18.md) — 00_Raw/
        pr_key = f'00_Raw/{ws_key}'
    else:
        pr_key = f'01_Parsed/{ws_key}'
    
    if pr_key in pr.get('items', {}):
        continue
    
    # Determine wiki_path from existing wiki file
    cat = ws_val.get('category', '')
    backward_map = {v: k for k, v in CATEGORY_MAP.items()}
    cat_dir = backward_map.get(cat, 'Topics')
    title = ws_val.get('title', '')
    title_norm = normalize_title(title)
    
    # Try to find matching wiki file on disk
    cat_path = os.path.join(base, '10_Wiki', cat_dir)
    found_wiki = None
    if os.path.isdir(cat_path):
        for fname in os.listdir(cat_path):
            if fname.endswith('.md') and title_norm in normalize_title(fname.replace('.md', '')):
                found_wiki = os.path.join('10_Wiki', cat_dir, fname)
                break
    
    if not found_wiki:
        continue  # wiki file doesn't exist on disk
    
    # Add to processed_raw
    src_path = os.path.join(base, '01_Parsed', ws_key) if '/' in ws_key else os.path.join(base, '00_Raw', ws_key)
    content = open(src_path, 'rb').read() if os.path.exists(src_path) else b''
    pr['items'][pr_key] = {
        'wiki_path': found_wiki,
        'raw_sha1': hashlib.sha1(content).hexdigest(),
        'raw_mtime_ns': str(os.stat(src_path).st_mtime_ns) if os.path.exists(src_path) else '0',
        'last_processed': now,
        'policy_fingerprint': '8a0e701e730250c67757758d088adcafac7c7f1f'
    }
    added_b += 1
    print(f'  [Dir B] +{pr_key} -> {found_wiki}')

print(f'Direction B additions: {added_b}')

# 6. Direction C: processed_raw has it, wiki_state doesn't
added_c = 0
for pr_key, pr_val in list(pr.get('items', {}).items()):
    # Determine corresponding ws key
    if pr_key.startswith('01_Parsed/'):
        ws_key = pr_key[len('01_Parsed/'):]
    elif pr_key.startswith('00_Raw/'):
        ws_key = os.path.basename(pr_key)
    elif pr_key.startswith('reconciled/'):
        continue  # already handled
    else:
        continue
    
    if ws_key in ws.get('processed', {}):
        continue
    
    wiki_rel = pr_val.get('wiki_path', '')
    if not wiki_rel or is_structural_readme(wiki_rel):
        continue
    
    # Extract title from wiki file on disk
    wiki_full = os.path.join(base, wiki_rel)
    title = ws_key.replace('.md', '').split('/')[-1]
    if os.path.exists(wiki_full):
        with open(wiki_full) as f:
            title = extract_title(f.read(2000), title)
    
    # Infer category from wiki path
    ws_cat = 'topic'
    for cat_dir, cat_val in CATEGORY_MAP.items():
        if wiki_rel.startswith(f'10_Wiki/{cat_dir}/'):
            ws_cat = cat_val
            break
    
    src_path = os.path.join(base, '01_Parsed' if '/' in ws_key else '00_Raw', ws_key)
    source_size = os.path.getsize(src_path) if os.path.exists(src_path) else 0
    source_date = ws_key.split('/')[0] if '/' in ws_key else ''
    
    ws['processed'][ws_key] = {
        'at': now, 'title': title, 'category': ws_cat,
        'source_size': source_size, 'source_date': source_date
    }
    added_c += 1
    print(f'  [Dir C] +{ws_cat} {title} (from {pr_key})')

print(f'Direction C additions: {added_c}')

# 7. Verify total_processed and write state files
expected = len(ws['processed'])
if ws.get('total_processed') != expected:
    print(f'  Fixing wiki_state total_processed: {ws.get(\"total_processed\")} -> {expected}')
    ws['total_processed'] = expected
    ws['last_run'] = now

with open(os.path.join(base, '20_Meta/wiki_state.json'), 'w') as f:
    json.dump(ws, f, indent=2, ensure_ascii=False)
with open(os.path.join(base, 'agent/processed_raw.json'), 'w') as f:
    json.dump(pr, f, indent=2, ensure_ascii=False)

print(f'\\nFinal: {len(disk_wiki_entries)} wiki entries on disk, '
      f'{len(pr[\"items\"])} in processed_raw, '
      f'{len(ws[\"processed\"])} in wiki_state')
```

## Concrete Example (from 2026-05-30 pipeline)

During the May 30 pipeline run, the 2026-05-21 Auto-Investment README had:
- ✅ Wiki entry on disk at `10_Wiki/Projects/Auto-Investment__AI_기반_한국_주식_자동매매_시스템.md`
- ✅ Entry in `wiki_state.json` (under `2026-05-21/github/khmo31_auto_investment/README.md`)
- ❌ **Missing** from `processed_raw.json`

Two other files had the same pattern:
- `TradingAgents/README.md` → `10_Wiki/Projects/TradingAgents__*.md`
- `moltbook_reports/README.md` → `10_Wiki/Projects/Moltbook_인텔리전스_트래커_*.md`

All three were added to `processed_raw.json` to bring state files into sync.

## Structural README Detection

| Path | Is Content? | Reason |
|------|------------|--------|
| `.../moltbook_reports/README.md` | ✅ Yes | Describes an external project |
| `.../TradingAgents/README.md` | ✅ Yes | Describes an external project |
| `.../auto_investment/README.md` | ✅ Yes | Describes an external project |
| `00_Raw/README.md` | ❌ No | Describes the wiki's raw data layer |
| `10_Wiki/Decisions/README.md` | ❌ No | Describes the wiki's Decisions directory |
| `10_Wiki/Projects/README.md` | ❌ No | Describes the wiki's Projects directory |

Test: *"Does this README explain what the wiki directory structure is for, or does it describe an external project/tool?"*

## Concrete Example (from 2026-05-31 pipeline — Direction C)

During the May 31 pipeline run, three files were in `processed_raw.json` but missing from `wiki_state.json`:

| Source File | wiki_path | Status |
|------------|-----------|--------|
| `01_Parsed/2026-05-30/youtube/youtube_...-OnM0ABAYzM.md` | `10_Wiki/Topics/youtube-playlist-item-ai-paperclip-openclaw-hermes-openai-claude-codex.md` | ✅ Wiki on disk, added to wiki_state |
| `01_Parsed/2026-05-30/youtube/youtube_...WZBMyztg2ts.md` | (same wiki file as above — merged) | ✅ Wiki on disk, added to wiki_state |
| `01_Parsed/2026-05-16/.../requirements.txt.md` | `10_Wiki/Topics/requirements-txt-2.md` | ✅ Wiki on disk (deprecated), added to wiki_state |

## Concrete Example (from 2026-06-01 pipeline — Direction B + total_processed count)

During the June 1 pipeline run, no new files needed processing. But two state-file desyncs were found:

| Source File | wiki_path | Desync | Fix |
|------------|-----------|--------|-----|
| `01_Parsed/2026-05-16/.../00_Raw/README.md` | `10_Wiki/Projects/00_Raw__불변_원천_데이터_계층.md` | ✅ In wiki_state, ❌ Missing from processed_raw (Direction B) | Added to processed_raw with SHA1, mtime |
| — | — | `wiki_state.total_processed` = 32 but actual `len(ws['processed'])` = 33 | Corrected to 33 |

Key lesson: **even structural READMEs tracked in `wiki_state.json` by the old pipeline need entries in `processed_raw.json`** for Direction B reconciliation. The state files record *what was processed*, not *what is active knowledge*. Skipping structural READMEs in Direction B creates a permanent desync that triggers on every pipeline run.

This required the title-matching fix above (the `normalize_match` function) — the `00_Raw: 불변 원천 데이터 계층` title contains a colon `:`, which leaves it as `00_Raw:_불변_…` after the old `replace(' ', '_')` logic, while the on-disk filename `00_Raw__불변_…` uses a double underscore. The aggressive `re.sub(r'[^\w\uAC00-\uD7AF]', '_', s)` + `re.sub(r'_+', '_', s)` normalizer collapses these to the same token.

## Concrete Example (from 2026-06-10 pipeline — Direction A, no source file)

During the June 10 pipeline run, the pipeline had no new `01_Parsed/` files but 20+ wiki entries existed on disk that were completely untracked in both state files. These were artifacts from earlier pipeline runs before proper state tracking was implemented.

The reconciliation added entries like:

| wiki_path | Category | Synthetic Key | Reason |
|-----------|----------|--------------|--------|
| `10_Wiki/Decisions/AI시대의_바이브_코딩과_피지컬_AI_혁신.md` | decision | `reconciled/Decisions/AI시대의_바이브_코딩과_피지컬_AI_혁신.md` | No source file in 01_Parsed/ |
| `10_Wiki/Projects/Copilot_개발_워크플로우_지침.md` | project | `reconciled/Projects/Copilot_개발_워크플로우_지침.md` | Same |
| `10_Wiki/Guides/하네스-엔지니어링.md` | guide | `reconciled/Guides/하네스-엔지니어링.md` | Same |
| ... and 17 more entries across 4 categories | | | |

Key lessons from this run:
- **Always scan ALL 10_Wiki/ subdirectories** (Decisions, Topics, Projects, Guides, Skills, Meetings, Postmortems, RFCs, Releases) — not just the 4 main ones
- **Structural README detection must use a regex**, not a hardcoded list, because there are 9 subdirectory READMEs plus `10_Wiki/README.md` and `00_Raw/README.md`
- **Some files use `##` instead of `#`** for their document title — the title extraction regex must handle both
- **The `reconciled/` key prefix** signal is a clear, searchable convention that won't collide with real pipeline entries
- A file with the same title may exist in both `Topics/` and `Decisions/` (duplicate placed in the wrong directory by a previous run) — add both with their correct category based on the actual path

## Pitfalls

### Deprecated wiki entries during reconciliation

A wiki entry on disk may be marked as `DEPRECATED` (e.g., `requirements-txt-2.md` was superseded by `requirements-txt.md`). **Still add it to `wiki_state.json`** — the state file records what was processed, not what's canonically active. Skipping it creates a persistent desync that re-appears on every pipeline run.

### Multiple source files merging into one wiki file

The ingestion pipeline may produce multiple `01_Parsed/` files that all map to the same wiki entry (e.g., two YouTube videos from the same playlist merged into a combined Topics entry). In this case:

- `processed_raw.json` correctly has separate items for each source, all pointing to the same `wiki_path`
- `wiki_state.json` should have a **separate `processed` entry per source file** — the state tracks processing completeness per source, not wiki-level dedup
- The reconciliation script handles this correctly: each `ws_key` is unique, so both sources get their own entry
