# Server Power Monitoring Setup Reference

## Directory Structure

Files live at `~/.power-monitor/` on the target server.

### Core Scripts

**monitor.py** — Main Python script. Three modes:
- No args: collect a RAPL sample and accumulate to data.json
- `--report`: generate daily report text (stdout)
- `--status`: show current accumulation state

Key implementation details:
- Uses KST timezone (UTC+9) for daily/month rollover
- RAPL counter wrap handled via max_energy_range_uj (~262B µJ)
- Month rollover detected by comparing `data["month"]` to current `YYYY-MM`
- DRAM energy is optional — if RAPL dram domain unavailable, treats as 0

**rapl-reader.sh** — Minimal wrapper:
```bash
#!/bin/bash
cat /sys/class/powercap/intel-rapl:0/energy_uj
cat /sys/class/powercap/intel-rapl:0:2/energy_uj
```
Must run as root. Protect via sudoers drop-in.

**setup.sh** — One-time setup:
1. Writes `/etc/sudoers.d/rapl-reader` with NOPASSWD rule
2. Tests RAPL reading
3. Creates default config.json if missing
4. Makes scripts executable

### Config (config.json)
```json
{
    "cost_per_kwh": 100,
    "base_system_watts": 6.0,
    "sampling_interval": 300
}
```

### Data (data.json)
Accumulated energy data with automatic month rollover.

## Sudoers Rule

File: `/etc/sudoers.d/rapl-reader`
```
khmo31 ALL=(root) NOPASSWD: /home/khmo31/.power-monitor/rapl-reader.sh
```

Permissions: `chmod 440`, owned by `root:root`.

## Hardware-Specific Notes

### Intel i5-4200U (Haswell, 2C/4T, TDP 15W)
- RAPL domains available: package-0, core, uncore, dram
- Kernel modules: intel_rapl_msr, intel_rapl_common
- Idle CPU package: ~2-3W
- Full load CPU: ~15W
- Typical total system (idle): 12-15W
- `/dev/cpu/*/msr` devices exist but also root-only

### Checking RAPL availability
```bash
ls /sys/class/powercap/          # Should show intel-rapl
cat /sys/class/powercap/intel-rapl:0/name  # Should show "package-0"
lsmod | grep intel_rapl          # intel_rapl_msr + intel_rapl_common
```

## Discord Delivery

Report script outputs plain text with markdown formatting (**bold**). Discord renders basic markdown. The cronjob uses:
- `no_agent=true`
- `deliver="discord:#클로-보고"`
- Schedule: `30 21 * * *` (21:30 UTC = 06:30 KST)

## Error Recovery

- **RAPL read fails**: monitor.py skips the sample and prints "Skipping sample - RAPL read failed". Data corruption impossible, but kWh for that interval is lost.
- **Month boundary crossing**: On first run of new month, data resets automatically. Previous month's data in `daily` dict is discarded.
- **Crash mid-write**: JSON write is atomic-ish (json.dump + file write). If process dies mid-write, old data.json remains intact.
