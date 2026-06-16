# Verification Patterns Reference

Expanded verification techniques per tool and scenario. Use these concrete commands instead of ad-hoc checks.

## File Operations

### File Created / Updated
```python
# Read back and confirm content
read_file("path/to/file")

# For structured files, parse and assert
terminal("python3 -c \"import json; data=json.load(open('file.json')); assert 'key' in data\"")
terminal("python3 -c \"import yaml; data=yaml.safe_load(open('config.yaml')); assert data['version'] == 2\"")
```

### File Deleted
```bash
# Confirm file is gone
test -f path/to/file && echo "EXISTS" || echo "GONE"
```

### Bulk Operations (many files written)
```bash
# Check specific files
ls -la path/to/new/files/
wc -l path/to/new/files/*.py
```

### Syntax Verification
```bash
# Python
python3 -m py_compile path/to/file.py

# JSON
python3 -m json.tool path/to/file.json > /dev/null

# YAML
python3 -c "import yaml; yaml.safe_load(open('path/to/file.yaml'))"

# Shell
bash -n path/to/script.sh
```

## Terminal Commands

### Installation
```bash
# APT
which <binary>
<binary> --version

# PIP
pip show <package>

# NPM
npm list -g <package>

# Binary from URL
ls -la /usr/local/bin/<binary>
<binary> --help | head -3
```

### Build
```bash
# Native
ls -la ./build/<binary>
./build/<binary> --version

# Docker
docker images | grep <image>
docker run --rm <image> <binary> --version
```

### Git
```bash
# Confirm commit
git log --oneline -3

# Confirm branch
git branch --show-current

# Confirm merge status
git log --oneline --merges -1
```

### Service / Daemon
```bash
# Systemd
systemctl status <service> 2>&1 | head -10

# PM2
pm2 list | grep <app>

# Docker
docker compose ps
docker ps --filter name=<container>
```

### Network / HTTP
```bash
# Port listening
ss -tlnp | grep :PORT
netstat -tlnp 2>/dev/null | grep :PORT

# HTTP response
curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT/health
curl -s http://localhost:PORT/ | head -20
```

## delegate_task Verification

### Pattern: After any delegate_task, verify results

```python
# Task: "Create a utility script"
result = delegate_task(
    goal="Create script.sh that does X",
    context="...",
    toolsets=['terminal', 'file']
)
# VERIFY: read_file("script.sh") to confirm it exists with expected content

# Task: "Test the API endpoint"
result = delegate_task(
    goal="Run tests on user endpoint",
    context="...",
    toolsets=['terminal']
)
# VERIFY: terminal("pytest tests/test_users.py -q") to re-run critical tests yourself
```

### Verification Checklist for delegate_task Claims

| Subagent claims | Verify by |
|----------------|-----------|
| "File created at X" | `read_file("X")` — confirm content, not just existence |
| "Tests pass" | Re-run the test suite yourself |
| "API call succeeded" | `curl` the endpoint / check state after mutation |
| "Git commit made" | `git log --oneline -1` — confirm SHA and message |
| "Package installed" | `which <binary>` or `pip show <package>` |
| "Config updated" | `read_file(path)` — confirm specific key changed |
| "Deployed to server" | SSH to server and confirm process is running |
| "Cron registered" | `cronjob(action='list')` — confirm job_id and schedule |

## Cronjob Verification

### After Creating a Job
```python
# List all jobs to confirm
cronjob(action='list')
# → Verify job_id exists with correct schedule, prompt, script path
```

### After Installing a Script
```bash
cat ~/.hermes/scripts/<job_name>.sh
# or
cat ~/.hermes/scripts/<job_name>.py
```

### Manual Test Run
```python
cronjob(action='run', job_id='<id>')
# Check output
```

## API / Platform Verification

### Discord
```python
# After creating a channel
discord_admin(action='list_channels', guild_id='...')
# → Search for channel name in results

# After sending a message
# Read back recent messages to confirm delivery
discord(action='fetch_messages', channel_id='...', limit=5)
```
### Browser / Visual Verification (Playwright MCP)

```python
# After frontend changes, use Playwright MCP to verify rendering:
# mcp_playwright_navigate(url="http://localhost:3000")
# → confirm page loads without errors

# Screenshot for visual proof:
# mcp_playwright_screenshot(full_page=True)
# → attach to report

# DOM assertion:
# mcp_playwright_evaluate(
#     script="document.querySelectorAll('.error').length"
# )
# → confirm 0 errors

# Console log check:
# mcp_playwright_evaluate(
#     script="window.__CONSOLE_ERRORS__ || []"
# )
# → confirm empty
```

### Smart Home State Verification

```python
# After any Home Assistant mutation (turn_on, turn_off, set):
# mcp_homeassistant_get_state(entity_id='light.X')
# → Confirm state matches intent

# After automation changes:
# mcp_homeassistant_get_state(entity_id='automation.X')
# → Confirm last_triggered or enabled state
```

### API / HTTP MCP Verification

```python
# After deployment:
# mcp_http_get(url="http://localhost:PORT/health")
# → Check 200 + {"status": "ok"}

# After creating a resource:
# mcp_http_get(url="http://localhost:PORT/api/resource/ID")  
# → Confirm expected fields in response
```

### send_message
```python
# Confirm target is correct before sending
# The tool sends immediately — verify destination parameters
# Double-check: platform, channel_id, thread_id all match intent
```

## Research / Web Content Verification

### URL Claims
```bash
# Confirm URL is accessible
curl -s -o /dev/null -w "%{http_code}" https://example.com/page

# Fetch and compare key claims
curl -s https://example.com/page | grep -c "specific claim"
```

### Data Synthesis
```python
# For each source used in a synthesis task:
# 1. Visit the source URL
# 2. Confirm the key numbers/claims actually appear in the source
# 3. Note any discrepancies
```

## Pro Tip: The "So What?" Test

After verification, ask: **"If this verification is wrong, will the user know?"**

If yes → strengthen verification (e.g., parse output, not just exit code)
If no → verification is probably sufficient
