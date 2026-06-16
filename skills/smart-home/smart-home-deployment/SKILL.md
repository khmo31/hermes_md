---
name: smart-home-deployment
description: "Deploy Home Assistant + Mosquitto in Docker, connect Hermes Agent via MCP, and add IoT devices. Covers the full stack from zero to controllable smart home."
version: 1.0.0
author: hermes
tags: [home-assistant, mqtt, mosquitto, docker, iot, smart-home, deployment]
prerequisites:
  commands: [docker, docker-compose]
  env: []
related_skills: [openhue, native-mcp, docker-container-management]
---

# Smart Home Infrastructure Deployment

Deploy a self-hosted smart home control stack on any Linux server with Docker. Hermes Agent controls everything via Home Assistant's REST API through an MCP server bridge.

## Triggers

- User says: "IoT", "스마트홈", "홈어시스턴트", "home assistant", "MQTT", "smart home", "집에 IoT"
- Setting up smart home control from scratch
- User asks you to control lights, temperature, sensors, or any home device
- User asks "환경만 구축해줘" for smart home setup

## Architecture

```
[IoT Devices] ──→ [Home Assistant] ←── [Hermes Agent]
  WiFi/Zigbee        (Docker)           (MCP client)
                     port 8123
                         ↑
[Mosquitto MQTT] ────────┘
  port 1883, 9001
```

Home Assistant uses **host networking** (required for mDNS/SSDP device discovery). Mosquitto runs on a bridge network with port mapping.

## Step-by-Step Setup

### 1. Create directory structure

```bash
mkdir -p ~/smarthome/{homeassistant,mosquitto/{config,data,log}}
```

### 2. Create `~/smarthome/docker-compose.yml`

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: always
    network_mode: host          # CRITICAL: needed for mDNS/SSDP discovery
    volumes:
      - ~/smarthome/homeassistant:/config
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=Asia/Seoul

  mosquitto:
    image: eclipse-mosquitto:latest
    container_name: mosquitto
    restart: always
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ~/smarthome/mosquitto/config:/mosquitto/config:ro
      - ~/smarthome/mosquitto/data:/mosquitto/data
      - ~/smarthome/mosquitto/log:/mosquitto/log
```

### 3. Create `~/smarthome/mosquitto/config/mosquitto.conf`

```
listener 1883
listener 9001
protocol websockets

allow_anonymous true

persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

### 4. Create minimal `~/smarthome/homeassistant/configuration.yaml`

```yaml
homeassistant:
  name: "Hermes SmartHome"
  time_zone: "Asia/Seoul"
  unit_system: metric
  country: "KR"
frontend:
api:
auth:
config:
logger:
  default: info
system_health:
sun:
```

### 5. Start the stack

```bash
cd ~/smarthome && docker compose up -d
```

### 6. Complete HA onboarding (MANUAL — browser required)

Open `http://<server-ip>:8123` in a browser and:
1. Create owner account (name, username, password)
2. Set location (optional, can skip)
3. **DO NOT configure MQTT in YAML** — modern HA requires it via UI
4. After onboarding, add MQTT: Settings → Devices → Add Integration → MQTT
   - Broker: `127.0.0.1`, Port: `1883`, No auth

### 7. Generate long-lived access token

In HA web UI:
1. Click user avatar (bottom-left) → **Your profile**
2. Scroll to **Long-Lived Access Tokens**
3. Create token with name e.g. "Hermes MCP"
4. **Copy the token immediately** — it won't be shown again

### 8. Connect Hermes via MCP

First ensure MCP SDK is installed:

```bash
pip install mcp
```

Then add to `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  homeassistant-mcp:
    command: "npx"
    args: ["-y", "home-assistant-mcp"]
    env:
      HOME_ASSISTANT_URL: "http://192.168.x.x:8123"
      HOME_ASSISTANT_TOKEN: "<the-long-lived-token>"
    timeout: 30
```

Restart Hermes gateway to pick up MCP tools:

```bash
systemctl --user restart hermes-gateway.service
```

MCP tools appear as `mcp_homeassistant_mcp_*` in the Hermes tool registry.

### 9. Install OpenHue (optional — for Philips Hue)

```bash
curl -sL https://github.com/openhue/openhue-cli/releases/latest/download/openhue-linux-amd64 -o ~/.local/bin/openhue && chmod +x ~/.local/bin/openhue
openhue          # first run: press button on Hue Bridge to pair
```

## Management Script

Save as `~/smarthome/manage.sh`:

```bash
#!/bin/bash
COMPOSE_DIR="$HOME/smarthome"
case "${1:-status}" in
  start)   cd "$COMPOSE_DIR" && docker compose up -d ;;
  stop)    cd "$COMPOSE_DIR" && docker compose down ;;
  restart) cd "$COMPOSE_DIR" && docker compose restart ;;
  status)  cd "$COMPOSE_DIR" && docker compose ps ;;
  logs)    cd "$COMPOSE_DIR" && docker compose logs --tail=50 -f ;;
  update)  cd "$COMPOSE_DIR" && docker compose pull && docker compose up -d ;;
  *)       echo "Usage: $0 {start|stop|restart|status|logs|update}" ;;
esac
```

## Adding IoT Devices

| Device type | How to add |
|-------------|-----------|
| **Philips Hue** | HA auto-discovers Hue Bridge on same network. Or use `openhue` CLI directly. |
| **WiFi plugs/switches** | Settings → Devices → Add Integration → Tuya/SmartThings/Kasa/TP-Link |
| **MQTT sensors** | Publish to MQTT; HA auto-discovers via MQTT discovery topic |
| **Zigbee devices** | Add a Zigbee coordinator (Sonoff ZBDongle, Conbee II) via USB → HA add-on ZHA |
| **ESPHome sensors** | Settings → Add Integration → ESPHome |

## Pitfalls

- **HA host networking is mandatory** for device discovery. Bridge networking breaks mDNS, SSDP, and UPnP — most smart home devices won't be found. You cannot run multiple HA instances on the same host with host networking.
- **Modern HA (2025+) removed YAML broker config for MQTT.** Do NOT put `mqtt: broker:` in configuration.yaml — it fails with "invalid option" errors. Add MQTT integration via the web UI only.
- **Mosquitto log permissions.** The container runs as `mosquitto` user (uid 1883). If the log directory is owned by `root` or another user, chmod to 777 or set correct ownership: `chown 1883:1883 ~/smarthome/mosquitto/log`
- **HA first boot requires browser interaction.** There's no CLI/API way to create the initial owner account. The user must open `http://<ip>:8123` and complete onboarding before Hermes can connect.
- **Long-lived token is shown once.** Generate it from Profile → Long-Lived Access Tokens and save immediately. If lost, revoke and create a new one.
- **`home-assistant-mcp` npm package** requires `HOME_ASSISTANT_URL` **and** `HOME_ASSISTANT_TOKEN` env vars both set. Without the URL it silently fails to connect.
- **OpenHue first pairing** requires physically pressing the button on the Hue Bridge within 30 seconds of running the CLI command.
- **Docker compose version.** Use `docker compose` (v2 plugin) not `docker-compose` (v1). Modern HA images require Compose v2.4+.

## Verification

```bash
# Check containers
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Check HA web UI responds
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8123
# Expect: 302 (redirects to onboarding or dashboard)

# Check MQTT port
timeout 3 bash -c 'echo "" | nc -w1 127.0.0.1 1883'

# Check HA version
curl -s http://127.0.0.1:8123 | grep -oP 'HA_VERSION = "\K[^"]+' || docker exec homeassistant python3 -c "from homeassistant.const import __version__; print(__version__)"
```

## Related Skills

- `smart-home/openhue` — Philips Hue CLI control
- `mcp/native-mcp` — MCP server configuration and troubleshooting
- `devops/docker-container-management` — Docker cleanup and idle-stop
