#!/usr/bin/env python3
"""
Daily tip cron script — cycles through N items deterministically using day-of-year.
Designed for no_agent=true mode: stdout IS the Telegram message.

Usage:
  1. Copy this file to ~/.hermes/scripts/<name>.py
  2. Edit ITEMS list with your content
  3. Create cron: hermes cron create --deliver "telegram" --no-agent --script <name>.py "0 22 * * *"
"""
import datetime

# Each item: (title, target_domain, description)
ITEMS = [
    ("Item 1", "Domain 1", "Concrete description with reasoning. Why this matters."),
    ("Item 2", "Domain 2", "Concrete description with reasoning. Why this matters."),
    ("Item 3", "Domain 3", "Concrete description with reasoning. Why this matters."),
    # Add more items — cycle length is automatic
]

def main():
    today = datetime.date.today()
    idx = (today.timetuple().tm_yday - 1) % len(ITEMS)
    title, domain, desc = ITEMS[idx]
    dow_names = ['월', '화', '수', '목', '금', '토', '일']
    dow = today.isoweekday()

    print(f"🌅 오늘의 — {today.month}월 {today.day}일 ({dow_names[dow-1]})\n")
    print(f"✅ {idx+1}. {title}\n")
    print(f"대상: {domain}\n")
    print(desc)
    print(f"\n💡 {domain} — 오늘 한 번 실행해보세요.")

if __name__ == "__main__":
    main()
