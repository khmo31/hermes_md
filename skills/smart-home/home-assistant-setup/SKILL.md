---
name: home-assistant-setup
description: "Setup Home Assistant + Mosquitto MQTT on Docker with Hermes Agent MCP integration"
version: 1.0.0
author: Hermes Agent
platforms: [linux]
prerequisites:
  commands: [docker, docker compose]
---

# Home Assistant IoT Infrastructure Setup

Full setup of Home Assistant + Mosquitto MQTT + Hermes Agent integration on a Linux server.

## Architecture

```
IoT Devices → Home Assistant (Docker) → Hermes Agent (via MCP)
                              ↓
                    Mosquitto MQTT (Docker)
```

## Directory Structure

```bash
~/smarthome/
├── docker-compose.yml      # HA + Mosquitto
├── manage.sh               # start/stop/status/logs/update
├── ha_api.sh               # Direct HA REST API calls
├── ha_token_wizard.py      # Generate long-lived HA token
├── homeassistant/           # HA config (mount)
│   ├── configuration.yaml
│   └── .storage/            # HA state (auto-created)
└── mosquitto/
    ├── config/mosquitto.conf
    ├── data/
    └── log/
```

## Setup Steps

### 1. Docker Compose

```yaml
# ~/smarthome/docker-compose.yml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: always
    network_mode: host                # Required for mDNS/SSDP device discovery
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
      - "1883:1883"      # MQTT TCP
      - "9001:9001"      # MQTT WebSocket
    volumes:
      - ~/smarthome/mosquitto/config:/mosquitto/config:ro
      - ~/smarthome/mosquitto/data:/mosquitto/data
      - ~/smarthome/mosquitto/log:/mosquitto/log
```

### 2. Mosquitto Config

```conf
# ~/smarthome/mosquitto/config/mosquitto.conf
listener 1883
listener 9001
protocol websockets
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

### 3. HA Initial Config

```yaml
# ~/smarthome/homeassistant/configuration.yaml
homeassistant:
  name: "Hermes SmartHome"
  latitude: 37.5665
  longitude: 126.9780
  time_zone: "Asia/Seoul"
  country: "KR"
  unit_system: metric
  currency: KRW
frontend:
api:
auth:
config:
system_health:
sun:
```

### 4. First Run & Onboarding

HA needs an owner account. If no browser available, use REST API:

```bash
# Create account
curl -X POST http://localhost:8123/api/onboarding/users \
  -H "Content-Type: application/json" \
  -d '{"client_id":"http://localhost:8123/","name":"khmo","username":"khmo31","password":"...","language":"ko"}'

# Login flow for token
FLOW_ID=$(curl -s -X POST http://localhost:8123/auth/login_flow \
  -H "Content-Type: application/json" \
  -d '{"client_id":"http://localhost:8123/","redirect_uri":"http://localhost:8123/","handler":["homeassistant",null]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['flow_id'])")

AUTH_CODE=$(curl -s -X POST "http://localhost:8123/auth/login_flow/$FLOW_ID" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"http://localhost:8123/","username":"khmo31","password":"..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])")

ACCESS=$(curl -s -X POST http://localhost:8123/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$AUTH_CODE&client_id=http://localhost:8123/" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Complete onboarding
curl -s -X POST http://localhost:8123/api/onboarding/core_config -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"latitude":37.5665,"longitude":126.978,"elevation":38,"time_zone":"Asia/Seoul","unit_system":"metric","currency":"KRW","country":"KR"}'
curl -s -X POST http://localhost:8123/api/onboarding/analytics -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"privacy":{"usage":false,"statistics":false}}'
```

### 5. Get Long-Lived Access Token

```python
# Requires: pip install websockets
async with websockets.connect("ws://localhost:8123/api/websocket") as ws:
    await ws.recv()  # auth_required
    await ws.send(json.dumps({"type":"auth","access_token":"<short_lived_token>"}))
    await ws.recv()  # auth_ok
    await ws.send(json.dumps({
        "id": 1,
        "type": "auth/long_lived_access_token",
        "client_name": "hermes-mcp",
        "lifespan": 3650
    }))
    result = json.loads(await ws.recv())
    long_lived_token = result["result"]  # 183-char JWT
```

### 6. Hermes MCP Integration

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  homeassistant:
    command: "npx"
    args: ["-y", "home-assistant-mcp"]
    env:
      HOME_ASSISTANT_URL: "http://192.168.x.x:8123"
      HOME_ASSISTANT_TOKEN: "${HA_TOKEN}"
    timeout: 30
```

Add to `~/.hermes/.env`:
```
HA_TOKEN=<long_lived_access_token>
```

Restart Hermes gateway to pick up MCP tools. MCP tools appear as `mcp_homeassistant_*`.

### 7. Direct API Access (no MCP)

```bash
# ~/smarthome/ha_api.sh GET /api/states
# ~/smarthome/ha_api.sh POST /api/services/light/turn_on '{"entity_id":"light.living_room"}'
```

## Management

```bash
~/smarthome/manage.sh start   # Start stack
~/smarthome/manage.sh stop    # Stop
~/smarthome/manage.sh status  # Container status
~/smarthome/manage.sh logs    # Tail logs
~/smarthome/manage.sh update  # Pull & restart
```

## Adding Devices

1. Connect device to HA via Settings → Devices & Services
2. For MQTT devices: Add MQTT integration in HA GUI (broker: 127.0.0.1, port: 1883)
3. Hermes discovers all entities automatically via MCP

## Ports Used

| Port | Service |
|------|---------|
| 8123 | Home Assistant Web UI |
| 1883 | MQTT TCP |
| 9001 | MQTT WebSocket |

## Pitfalls

- **HA files owned by root** after Docker runs (normal — container runs as root)
- **MQTT config error** in HA config YAML: recent HA versions removed `broker`/`port`/`discovery` options from YAML. Configure MQTT via GUI instead
- **Token expiry**: Short-lived tokens expire in 30 min. Always use long-lived tokens (WebSocket API)
- **Permission on Mosquitto logs**: Container user `mosquitto` (uid 1883) needs write access to log dir. Use `chmod 777` on mosquitto/log or set correct ownership
- **Host networking**: HA uses `network_mode: host` for mDNS/SSDP discovery. This means port mapping in docker-compose is ignored for HA
