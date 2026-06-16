# Home Assistant MCP Package Options

Two known MCP servers for Home Assistant, both on npm:

## 1. `home-assistant-mcp` (recommended — used in this setup)

| Property | Value |
|----------|-------|
| Package | `home-assistant-mcp` |
| Version | 1.0.4 (as of 2026-05) |
| Author | aniketbhondave |
| Binary | `home-assistant-mcp` |
| Dependencies | `@modelcontextprotocol/sdk`, `node-fetch`, `dotenv` |
| GitHub | https://github.com/aniketbhondave/Home-Assistant-MCP |

**Environment variables:**
- `HOME_ASSISTANT_URL` — required, e.g. `http://192.168.x.x:8123`
- `HOME_ASSISTANT_TOKEN` — required, long-lived access token from HA profile

**Hermes MCP config:**
```yaml
mcp_servers:
  homeassistant-mcp:
    command: "npx"
    args: ["-y", "home-assistant-mcp"]
    env:
      HOME_ASSISTANT_URL: "http://<ha-host>:8123"
      HOME_ASSISTANT_TOKEN: "<token>"
    timeout: 30
```

**Tools exposed** (typical): `get_states`, `call_service`, `get_entities`, `get_services`

## 2. `ha-mcp`

| Property | Value |
|----------|-------|
| Package | `ha-mcp` |
| Version | 0.1.6 (as of 2025-08) |
| Author | jgracey |
| Keywords | home-assistant, mcp, websocket, automation, agent |

Less mature version. Use `home-assistant-mcp` unless there's a specific reason to choose this one.

## MCP SDK Requirement

Hermes requires the `mcp` Python package installed to discover and use MCP servers:

```bash
pip install mcp
```

Without it, Hermes silently skips MCP discovery and MCP tools never appear.
