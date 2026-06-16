---
name: server-power-monitoring
description: Set up RAPL-based power/energy monitoring on Linux home servers with monthly cost estimation and Discord reporting.
triggers:
  - user asks about power usage, electricity cost, energy monitoring
  - user wants to track server power consumption over time
  - user asks RAPL, intel-rapl, turbostat, powercap
  - setting up a home server monitoring dashboard
---

# Server Power Monitoring (RAPL-based)

Set up accurate power consumption tracking using Intel RAPL (Running Average Power Limit) kernel interface. Includes:

- CPU package + DRAM energy via RAPL
- Base system wattage estimate (motherboard, PSU loss, fans, SSD)
- Cumulative monthly kWh + cost estimation in KRW
- Daily report delivery to Discord
- Automatic month rollover (resets on the 1st)

## Architecture

```
┌─────────────────────┐     every 5 min      ┌───────────────────┐
│  RAPL energy_uj     │◄────────────────────│  monitor.py       │
│  /sys/class/powercap│   collect sample      │  (accumulate)     │
└─────────────────────┘                      └────────┬──────────┘
                                                       │
                                                       ▼
                                              ┌───────────────────┐
                                              │  data.json        │
                                              │  (daily + monthly) │
                                              └────────┬──────────┘
                                                       │ daily 06:30 KST
                                                       ▼
                                              ┌───────────────────┐
                                              │  report script    │
                                              │  → Discord        │
                                              └───────────────────┘
```

## Prerequisites

- Intel CPU with RAPL support (`/sys/class/powercap/intel-rapl:*` exists)
- Kernel module `intel_rapl_msr` and `intel_rapl_common` loaded
- `sudo` access for initial setup
- Hermes Agent with cronjob tool
- Discord channel target for reports

## Power Estimation Model

Total System Power = RAPL_package + RAPL_dram + base_system_watts

| Component | Source | Typical (idle) | Typical (load) |
|---|---|---|---|
| CPU package | RAPL (intel-rapl:0) | 2-5W | TDP (e.g. 15W) |
| DRAM | RAPL (intel-rapl:0:2) | 1-2W | 2-4W |
| Base system | Configured | 5-8W | 8-12W |
| **Total** | | **~12-15W** | **~25-30W** |

base_system_watts covers: motherboard chipset (PCH), SSD, fans, PSU conversion loss.

Korean electricity rate default: 100원/kWh (주택용 저압 1단계). Adjust in config.json.

## Setup Steps

### 1. Create monitoring directory and scripts

```
~/.power-monitor/
├── monitor.py         # Main Python script
├── rapl-reader.sh     # RAPL reading wrapper (needs sudo)
├── collect.sh         # Cron collection wrapper
├── report.sh          # Cron report wrapper
├── setup.sh           # One-time privileged setup
├── config.json        # Settings
└── data.json          # Persistent data
```

### 2. Set up sudoers for RAPL access

RAPL energy_uj files are root-owned (mode 400). Create a sudoers drop-in:

```bash
# /etc/sudoers.d/rapl-reader
khmo31 ALL=(root) NOPASSWD: /home/khmo31/.power-monitor/rapl-reader.sh
```

The setup.sh script handles this automatically — run once:

```bash
sudo bash ~/.power-monitor/setup.sh
```

### 3. Register cron jobs

**Collector** (every 5 min, silent):
- no_agent=true
- Script file must be in `~/.hermes/scripts/` (symlinks NOT allowed — copy files there)
- name: `power-monitor-collect`
- schedule: `*/5 * * * *`

**Report** (daily 06:30 KST = 21:30 UTC):
- no_agent=true
- deliver: `discord:#채널명`
- name: `power-monitor-report`
- schedule: `30 21 * * *`

### 4. Verify

```bash
# Check RAPL access
sudo ~/.power-monitor/rapl-reader.sh
# Expected: two large integers (microjoules)

# Test collection
cd ~/.power-monitor && python3 monitor.py

# Check accumulated data
cat ~/.power-monitor/data.json

# Test report generation
cd ~/.power-monitor && python3 monitor.py --report
```

## Data Schema (data.json)

```json
{
  "month": "2026-06",
  "month_start": "2026-06-01",
  "daily": {
    "2026-06-07": {
      "kwh": 0.345,
      "samples": 288,
      "total_watts": 3888.0,
      "min_watts": 11.2,
      "max_watts": 18.5
    }
  },
  "monthly_total_kwh": 10.5,
  "last_sample_uj_pkg": 1234567890,
  "last_sample_uj_dram": 987654321,
  "last_sample_time": 1717740000.0
}
```

## Pitfalls

- **RAPL files root-only**: Can't use `sudo -S` with piped passwords in cron. Must use sudoers NOPASSWD drop-in.
- **no_agent script path**: Cron scripts must be actual files in `~/.hermes/scripts/`. Symlinks that escape via `..` or `~` are rejected. Copy the file, don't symlink.
- **Sample interval accuracy**: 5-min cron means max 288 samples/day. If server sleeps/suspends, gaps are normal but kWh for that day will be under-reported.
- **Month rollover**: Handled automatically — when month changes, `data.json` resets `monthly_total_kwh` to 0. No need for a separate 1st-of-month job.
- **Counter wrap**: RAPL max_energy_range_uj is ~262 billion µJ (73 Wh). On a 15W system, that's ~5 hours. Script handles wrap-around correctly.
- **No RAPL on some hardware**: AMD Zen before Zen 4 or older Intel (pre-Sandy Bridge) lacks RAPL. Fall back to CPU utilization estimation.
- **PSU overhead**: Estimate base_system_watts conservatively. Actual PSU efficiency (80+ Bronze ≈ 85%) means total wall power is ~15% higher than software estimate. Adjust config.json if you have a physical meter.

## Cost Configuration

Edit `~/.power-monitor/config.json`:

```json
{
    "cost_per_kwh": 100,
    "base_system_watts": 6.0,
    "sampling_interval": 300
}
```

Korean residential electricity tiers (2024, 저압):
- 1단계 0~200kWh: 120원/kWh (기본요금 910원)
- 2단계 201~400kWh: 214.6원/kWh (기본요금 1,600원)
- 3단계 401kWh~: 307.3원/kWh (기본요금 7,300원)

For a home server pulling ~10-15 kWh/month, use 120원/kWh for accuracy. The config uses 100원/kWh as a conservative lower bound.
