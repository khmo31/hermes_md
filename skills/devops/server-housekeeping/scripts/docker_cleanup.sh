#!/bin/bash
# Docker Cleanup — weekly deep clean
# Schedule: 0 3 * * 0 (Sunday 03:00)
set -e
LOG="$HOME/docker_cleanup.log"
echo "=== Docker Cleanup: $(date) ===" >> "$LOG"

echo ">> Container prune (24h+)..." >> "$LOG"
docker container prune -f --filter "until=24h" >> "$LOG" 2>&1

echo ">> Image prune..." >> "$LOG"
docker image prune -f >> "$LOG" 2>&1

echo ">> Build cache prune..." >> "$LOG"
docker builder prune -f >> "$LOG" 2>&1

echo ">> Volume prune..." >> "$LOG"
docker volume prune -f >> "$LOG" 2>&1

echo ">> System prune..." >> "$LOG"
docker system prune -f --volumes >> "$LOG" 2>&1

echo "=== Done ===" >> "$LOG"
echo "" >> "$LOG"
echo "=== Docker Cleanup Report ==="
tail -20 "$LOG"
