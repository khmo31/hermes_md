# Second Brain State File Schemas

## `20_Meta/wiki_state.json`

Tracks what files have been wiki-processed (01_Parsed/ → 10_Wiki/).

```json
{
  "last_run": "2026-05-27T21:02:34.316632Z",
  "processed": {
    "2026-04-16/local/LOCAL_7a0319aa43eb_지성학.md": {
      "at": "2026-05-17T21:04:02.398Z",
      "title": "AI 시대의 기술 변화와 피지컬 AI 혁신",
      "category": "topic",
      "source_size": 835,
      "source_date": "2026-04-16"
    }
  },
  "total_processed": 29
}
```

- **processed keys**: 
  - For `01_Parsed/` files: path relative to `01_Parsed/` (e.g. `2026-04-16/local/FILE.md` — note: NO `01_Parsed/` prefix in the key)
  - For `00_Raw/` flat files processed directly: just the filename (e.g. `2026-05-18.md`)
- **category**: one of `topic`, `decision`, `project`, `guide`, `skill`
- On each pipeline run, add new entries + bump `last_run` + increment `total_processed`

## `agent/processed_raw.json`

Maps parsed files to their wiki output paths. Schema v2:

```json
{
  "schema_version": 2,
  "items": {
    "01_Parsed/2026-04-16/github/khmo31_moltbook_reports/docs/plan.md": {
      "wiki_path": "10_Wiki/Projects/plan.md",
      "raw_sha1": "0c1d4a6f5b7fc1017cf7099a13a7c508a12d7fa7",
      "raw_mtime_ns": "xxxxxxxxxxxxxxxxx221",
      "last_processed": "2026-05-15T13:05:04.330114+00:00",
      "policy_fingerprint": "8a0e701e730250c67757758d088adcafac7c7f1f"
    }
  }
}
```

- **wiki_path**: target path relative to `~/second_brain/`
- **raw_sha1**: SHA1 of the raw source file (for dedup)
- **policy_fingerprint**: identifies which processing policy was used
- Multiple parsed files may map to the same wiki_path (dedup/merge scenario)

## `20_Meta/ingest_state.json`

Tracks the ingest.py pipeline progress (00_Raw → 01_Parsed). Conflicts here are common during parallel pipeline runs.

```json
{
  "last_confirmed_offset": 0,
  "updated_at": "2026-05-27T20:28:36.835835+00:00",
  "cursors": {
    "github:khmo31/auto_investment:main": "0facdd2e603ad1425774dad7863504b9a639747c"
  },
  "raw_hash_index": {
    "503a42e8f168e78c7aab2baf7c5ac77b4170fcbe": "00_Raw/2026-04-18/original/github/khmo31_moltbook_reports/config/groq_report_prompt.md"
  }
}
```

## Check Order in Pipeline

1. `00_Raw/` flat `.md` files → check `wiki_state.json` "processed" keys (raw-path-based, bare filename)
2. `01_Parsed/` directory files → check both `processed_raw.json` "items" (by full Parsed path) and `wiki_state.json` (by relative key)

## Desync Reconciliation

Over time, `wiki_state.json` and `processed_raw.json` can fall out of sync — e.g., one gets updated on a pipeline run but not the other. This happens because different pipeline runs may update different state files.

**When you find a file in one state file but not the other:**

1. Verify the wiki entry actually exists on disk at the path specified in `processed_raw.json`'s `wiki_path` (or, for files only in `wiki_state.json`, check that the corresponding wiki file exists)
2. If the wiki entry exists, add the missing entry to the other state file
3. If the wiki entry doesn't exist and the file is meaningful content, process it into the wiki first, then update both state files
4. If the wiki entry doesn't exist and the file is structural noise (README.md describing a wiki directory), skip it entirely

**Example reconciliation scenarios:**
- File in `processed_raw.json` but NOT in `wiki_state.json` → Add `wiki_state.json` entry with the same title/category
- File in `wiki_state.json` but NOT in `processed_raw.json` → Add `processed_raw.json` entry with the wiki_path from the on-disk file
