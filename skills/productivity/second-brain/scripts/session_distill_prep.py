#!/usr/bin/env python3
"""Session Distillation Prep — 완료된 세션 식별 및 메시지 추출

Cron Job Phase 2의 결정론적 데이터 준비를 담당한다.
state.db에서 완료된 세션을 조회하고, session_distillation_state.json과
교차 참조하여 미처리 세션의 메시지를 추출한다.

출력: JSON (stdout)
  {"status": "no_new_sessions", "count": 0}
  {"status": "sessions_found", "count": N, "sessions": [...]}
"""
import sqlite3, json, os, sys
from datetime import datetime, timezone

BASE = os.path.expanduser("~/second_brain")
STATE_FILE = os.path.join(BASE, "20_Meta/session_distillation_state.json")
DB_PATH = os.path.expanduser("~/.hermes/state.db")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed_sessions": {}, "last_run": None, "total_processed": 0}

def get_unprocessed_sessions(db, state):
    processed_ids = set(state.get("processed_sessions", {}).keys())
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.execute("PRAGMA busy_timeout = 5000")
    cur = conn.cursor()

    cur.execute('''
        SELECT id, source, model,
               datetime(started_at, 'unixepoch') as started,
               datetime(ended_at, 'unixepoch') as ended,
               end_reason, message_count, title
        FROM sessions
        WHERE end_reason IN ('session_reset', 'cron_complete')
          AND ended_at IS NOT NULL
        ORDER BY ended_at DESC
        LIMIT 10
    ''')

    sessions = []
    for row in cur.fetchall():
        sid = row[0]
        if sid in processed_ids:
            continue
        sessions.append({
            "id": sid,
            "source": row[1],
            "model": row[2],
            "started": row[3],
            "ended": row[4],
            "end_reason": row[5],
            "message_count": row[6],
            "title": row[7]
        })
    conn.close()
    return sessions

def extract_messages(db, session_id, max_msgs=20, max_chars=2000):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.execute("PRAGMA busy_timeout = 5000")
    cur = conn.cursor()

    cur.execute('''
        SELECT role, content, datetime(timestamp, 'unixepoch')
        FROM messages
        WHERE session_id = ?
          AND role IN ('user', 'assistant')
          AND content IS NOT NULL
          AND content != ''
        ORDER BY id DESC
        LIMIT ?
    ''', [session_id, max_msgs * 2])

    msgs = []
    for role, content, ts in cur.fetchall():
        truncated = len(content) > max_chars
        msgs.append({
            "role": role,
            "content": content[:max_chars],
            "truncated": truncated,
            "timestamp": ts
        })
    conn.close()

    msgs.reverse()
    return msgs[:max_msgs]

def main():
    state = load_state()
    sessions = get_unprocessed_sessions(DB_PATH, state)

    if not sessions:
        print(json.dumps({"status": "no_new_sessions", "count": 0}))
        return

    output = {"status": "sessions_found", "count": len(sessions), "sessions": []}
    for s in sessions[:3]:  # 컨텍스트 제한: 상위 3개 세션만
        msgs = extract_messages(DB_PATH, s["id"], max_msgs=20)
        s["messages"] = msgs
        output["sessions"].append(s)

    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
