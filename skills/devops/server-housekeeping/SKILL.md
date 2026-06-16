---
name: server-housekeeping
description: "Server maintenance automation — cron job scheduling with multi-platform delivery, and Docker container lifecycle management (cleanup, idle auto-stop, restart policies)."
version: 1.0.0
author: hermes
tags: [devops, cron, docker, automation, maintenance, cleanup, power-saving]
related_skills: [hermes-server-deployment, smart-home-deployment, server-migration]
---

# Server Housekeeping

Two core housekeeping domains for single-host Linux servers in one skill: **cron job automation** (script-based and agent-mode scheduling with multi-platform delivery) and **Docker container lifecycle management** (cleanup, idle auto-stop, restart policies).

## Triggers

**Cron triggers:**
- User says: "크론잡", "cron job", "스케줄", "scheduled task", "자동화", "cron delivery to discord/telegram"
- Setting up periodic data collection, reminders, or watchdog scripts

**Docker triggers:**
- User says: "안쓰는 컨테이너 자동종료", "컨테이너 정리", "Docker 청소", "전력 아끼기", "container cleanup", "auto-stop idle containers"
- Debugging disk-full alerts caused by Docker overlay / build cache
- Auditing a server's Docker footprint

---

# Section A: Cron Job Automation

Design and maintain durable cron jobs using scripts (`no_agent=true`) or agent-driven prompts, with proper delivery routing across Telegram, Discord, and local channels.

## Quick Reference

```bash
# List all jobs
cronjob action=list

# Create a no_agent script job
cronjob action=create script="my_script.py" no_agent=true deliver="telegram:CHAT_ID" schedule="0 22 * * *"

# Create an agent-mode job with skills
cronjob action=create prompt="..." skills=["my-skill"] schedule="0 9 * * *"
```

## Delivery Routing (Critical!)

Delivery targets control WHERE the output goes. Every cron job MUST specify a concrete target — a bare platform name causes a silent delivery failure.

### Correct patterns

| Target | When to use |
|--------|-------------|
| `telegram:CHAT_ID` | DM to user (user's Telegram chat ID) |
| `telegram:-100GROUP_ID:TOPIC_ID` | Telegram group topic (group_id:topic_id) |
| `discord:CHANNEL_ID` | Discord channel ID |
| `discord:#channel-name` | Discord channel by name (resolved at fire time) |
| `origin` | Same chat as where the cron was created |
| `origin,all` | Current chat + all connected home channels |
| `local` | No delivery — save only |
| `platform:ID1,platform:ID2` | Multi-platform (comma-separated) |

### ❌ Wrong patterns

| Target | Result |
|--------|--------|
| `telegram` alone | ❌ `"no delivery target resolved for deliver=telegram"` — bare platform name fails silently |
| `discord` alone | Same — needs channel specifier |
| `origin` when user's home channel changed | Delivers to old channel |

**Rule:** Always use `platform:ID` format. Never just `platform`.

## Two Modes

### Mode A: `no_agent=true` (script-based, zero LLM cost)

Best for: deterministic output, data collection, watchdog patterns, daily reminders.

```bash
cronjob action=create \
  script="my_script.py" \
  no_agent=true \
  deliver="telegram:CHAT_ID" \
  schedule="0 22 * * *"
```

**Rules:**
- Script MUST be in `~/.hermes/scripts/`. Use just the filename (no path).
- Script's stdout is delivered verbatim. Empty stdout = silent (nothing sent).
- Non-zero exit / timeout = error alert to user.
- Script has ~120s hard timeout — LLM-heavy tasks will time out (use Mode B instead).
- Script runs with clean `env -i` — env vars from `~/.hermes/.env` are NOT inherited unless explicitly sourced.

#### Env var availability in no_agent scripts

Cron no_agent scripts run in a minimal environment. `~/.hermes/.env` is NOT automatically loaded. If your script needs API keys:

```python
# Explicitly read .env
import os
env_path = os.path.expanduser("~/.hermes/.env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
```

Alternatively, make a bash script wrapper source it before calling python.

### Mode B: agent-mode (with prompt, LLM-driven)

Best for: reasoning-heavy tasks, summarization, conditional logic, tasks needing >120s.

```bash
cronjob action=create \
  prompt="Your self-contained prompt here" \
  skills=["my-skill"] \
  schedule="0 9 * * *" \
  deliver="telegram:CHAT_ID" \
  enabled_toolsets=["web", "terminal"]
```

**Timeout:** ~3 minutes (agent-mode cron has higher timeout than no_agent).

## Script Placement & Lifecycle

```
~/.hermes/scripts/          # All no_agent scripts go here
  ├── my_script.py          # Python scripts (no shebang needed for .py)
  ├── my_script.sh          # Bash scripts (.sh extension)
  └── ...
```

- Scripts can be `.sh` (bash) or `.py` (Python).
- `python3` and standard library are available. Third-party packages need explicit install.
- Scripts persist across sessions. Update via `write_file` to the same path.
- To update a cron job's script: write the new file, then `cronjob action=update job_id=... script="new_script.py"`

## Common Error Diagnosis

### Check status

```bash
cronjob action=list
# Look for: last_status, last_delivery_error
```

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `no delivery target resolved for deliver=telegram` | Bare platform name, no chat ID | Add `:ID` suffix |
| `Script timed out after 120s` | Script exceeded 120s limit | Convert to Mode B (agent), or optimize script |
| `ModuleNotFoundError: No module named 'X'` | Python package not installed | `pip install X` — add script-level import guard with error message |
| `script failed` (exit code 1 on no_agent) | Runtime error in script | Check script stdout/stderr in output log |
| `openai.AuthenticationError: 401` | Expired or wrong API key | Update key in `.env` |

### Debug pattern

```bash
# Reproduce cron environment
env -i HOME=$HOME PATH=/usr/bin:/bin:/usr/local/bin bash /path/to/script.sh

# Check output logs
cat ~/.hermes/cron/output/<job_id>/latest_output.md
```

---

# Section B: Docker Container Lifecycle

Container lifecycle automation for single-host Docker deployments. Targets minimal resource waste: auto-stop idle containers, periodic system prune, and retention policies that respect intentionally-always-on services.

## Scripts

Two scripts in `~/.hermes/scripts/`:

### `docker_cleanup.sh` — Weekly deep clean

Run via cron (recommended: Sunday 03:00):

```bash
docker container prune -f --filter "until=24h"    # stopped containers, keep < 24h recent
docker image prune -f                              # dangling images
docker builder prune -f                            # build cache
docker volume prune -f                             # unused volumes
docker system prune -f --volumes                   # everything else
```

### `docker_idle_stop.sh` — 10-minute idle check

Stops + removes containers that have been idle for > 60 minutes:

| Criteria | Threshold | Rationale |
|----------|-----------|-----------|
| CPU usage | < 5% | Anything doing real work shows >5% occasionally |
| Memory | < 100 MB | Service containers usually allocate more |
| Uptime | > 60 min | Avoid stopping recently-started containers |
| Restart policy | != `always` | `restart=always` is intentional always-on |

### Cron registration

```bash
# Weekly cleanup (no_agent, run Sunday 03:00)
cronjob action=create schedule="0 3 * * 0" script="docker_cleanup.sh" no_agent=true deliver="local" name="docker-auto-cleanup"

# Idle monitor (every 10 min)
cronjob action=create schedule="*/10 * * * *" script="docker_idle_stop.sh" no_agent=true deliver="local" name="docker-idle-stop"
```

## Workflow

### Step 1: Audit current state

```bash
docker ps -a                              # all containers
docker system df                          # disk usage by type
docker images --filter "dangling=true"    # orphaned images
```

### Step 2: Stop & remove useless containers

Check for `tail -f /dev/null` patterns — these are pure resource waste:

```bash
docker inspect <container> --format '{{.Config.Cmd}}'
docker inspect <container> --format '{{.HostConfig.RestartPolicy.Name}}'
```

If a container runs only `tail -f /dev/null` and has `unless-stopped` policy:
- It was probably a dev environment left running
- Stop and remove it safely: `docker kill <name> && docker rm <name>`

### Step 3: Set restart policies consciously

| Policy | Meaning | When to use |
|--------|---------|-------------|
| `always` | Always restart, even after `docker stop` | Critical services |
| `unless-stopped` | Restart unless intentionally stopped | General services |
| `on-failure` | Only on non-zero exit | Batch jobs |
| `no` | Never restart | Ephemeral containers |

The idle monitor skips `restart=always` containers.

## Combined Pitfalls

### Cron pitfalls

1. **`set -e` in no_agent bash scripts** — A failing intermediate command (e.g., empty `export $(xargs)`) kills the entire script. Omit `set -e` or add `|| true` to non-critical lines.
2. **`source ~/.hermes/.env` does NOT export** — Variable assignments without `export` keyword stay as shell-local vars. Subprocesses (python3 subprocess) don't see them. Use `export $(grep -v '^#' ~/.hermes/.env | xargs)` instead.
3. **Script timeout != terminal timeout** — no_agent scripts have a ~120s hard limit. LLM-heavy workflows hit this easily. Either optimize the script or switch to agent-mode cron.
4. **Delivery to newly-added platforms** — A cron set to bare `deliver="telegram"` before Telegram was wired up fails permanently. Re-create the cron after the platform is connected with a proper `platform:ID` pair.
5. **Workdir changes behavior** — Setting `workdir` makes jobs run sequentially (not parallel) for directory isolation. Without it, jobs can run concurrently but have no project context.

### Docker pitfalls

1. **`docker stop` timeout on `tail -f /dev/null` containers.** The `tail` process doesn't respond to SIGTERM. Use `docker kill` instead of `docker stop` for these.
2. **`restart=always` containers survive `docker stop`.** You must `docker rm` AND explicitly stop/kill them. Even then Docker might restart them if the daemon restarts. Set the policy to `no` before removing if needed.
3. **Idle detection is heuristic.** A container doing periodic batch work (1-min spike every 30 min) may look idle. Consider `restart=unless-stopped` instead of `always` for such cases so the idle monitor won't cascade-kill them.
4. **Build cache can grow >5 GB silently.** Run `docker builder prune -f` at least weekly if you build images locally.

## Verification

```bash
# Check cron jobs
cronjob action=list

# Test no_agent script manually
bash ~/.hermes/scripts/docker_cleanup.sh

# Check Docker containers and disk usage
docker ps -a
docker system df
```

---

# Section C: System Package Updates (apt)

Automate Ubuntu/Debian package updates (`apt update && apt upgrade -y`) via cron. Keeps the server patched without manual intervention.

## Quick Reference

### One-shot update
```bash
sudo -n apt update && sudo -n apt upgrade -y
```

### Daily cron (recommended)
```bash
cronjob action=create \
  schedule="0 6 * * *" \
  prompt="Run 'sudo apt update && sudo apt upgrade -y' on the server. Summarize what was upgraded (package names and versions), or report 'No packages to upgrade.'" \
  skills=["server-housekeeping"] \
  deliver="discord:#채널" \
  name="daily-apt-update"
```

## Prerequisites: NOPASSWD sudo for apt

Daily apt cron runs unattended — must not prompt for password. Create a sudoers rule:

```bash
echo 'khmo31 ALL=(ALL) NOPASSWD: /usr/bin/apt update, /usr/bin/apt upgrade -y' | sudo tee /etc/sudoers.d/apt-auto
```

### ⚠️ Pitfall: sudoers exact-match does NOT allow flags

A rule like `NOPASSWD: /usr/bin/apt upgrade` matches ONLY `/usr/bin/apt upgrade` with NO arguments. Any flag (`-y`, `--assume-yes`, `-q`) causes sudo to prompt for password.

**✅ Correct** — include the `-y` flag explicitly:
```
NOPASSWD: /usr/bin/apt update, /usr/bin/apt upgrade -y
```

**❌ Wrong** — bare command without flags:
```
NOPASSWD: /usr/bin/apt upgrade
# sudo -n apt upgrade -y  →  password prompt!
```

**Alternative (less restrictive):** wildcard the command:
```
NOPASSWD: /usr/bin/apt *
```
But this allows any apt subcommand — use the explicit form when possible.

## Verification

```bash
# Test NOPASSWD works
sudo -n apt update

# Test upgrade (dry)
sudo -n apt upgrade -y

# Check cron jobs
cronjob action=list
```
