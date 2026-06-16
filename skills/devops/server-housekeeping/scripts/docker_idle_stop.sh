#!/bin/bash
# Idle Container Auto-Stop — 10-minute interval
# Stops containers idle >60 min (CPU<5%, MEM<100MB)
# Skips restart=always containers (intentionally always-on)
set -e
THRESHOLD_CPU=5.0
THRESHOLD_MEM_MB=100
IDLE_MINUTES=60
LOG="$HOME/docker_idle_stop.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking idle containers..." >> "$LOG"

while IFS= read -r container; do
    [ -z "$container" ] && continue

    restart_policy=$(docker inspect "$container" --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)
    [ "$restart_policy" = "always" ] && continue

    stats=$(docker stats "$container" --no-stream --format "{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null)
    [ -z "$stats" ] && continue

    cpu=$(echo "$stats" | cut -f1 | sed 's/%//')
    mem_raw=$(echo "$stats" | cut -f2 | awk '{print $1}')
    mem=$(echo "$mem_raw" | sed 's/MiB//;s/GiB/*1024/' | bc 2>/dev/null || echo 0)

    started=$(docker inspect "$container" --format '{{.State.StartedAt}}' 2>/dev/null)
    started_ts=$(date -d "$started" +%s 2>/dev/null)
    now_ts=$(date +%s)
    uptime_min=$(( (now_ts - started_ts) / 60 ))

    echo "  $container: CPU=${cpu}% MEM=${mem_raw} Uptime=${uptime_min}m Policy=${restart_policy}" >> "$LOG"

    if (( $(echo "$cpu < $THRESHOLD_CPU" | bc -l) )) && \
       (( $(echo "$mem < $THRESHOLD_MEM_MB" | bc -l) )) && \
       [ $uptime_min -gt $IDLE_MINUTES ]; then
        echo "  ⛔ STOPPING $container (idle > 1h)" >> "$LOG"
        docker stop "$container" >> "$LOG" 2>&1
        docker rm "$container" >> "$LOG" 2>&1
    fi
done < <(docker ps --format "{{.Names}}")

echo "" >> "$LOG"
