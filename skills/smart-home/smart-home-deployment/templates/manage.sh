#!/bin/bash
# SmartHome Stack Manager
# Usage: ./manage.sh {start|stop|restart|status|logs|update}

COMPOSE_DIR="$HOME/smarthome"

case "${1:-status}" in
  start)
    cd "$COMPOSE_DIR" && docker compose up -d
    echo "✅ SmartHome stack started"
    ;;
  stop)
    cd "$COMPOSE_DIR" && docker compose down
    echo "⏹️  SmartHome stack stopped"
    ;;
  restart)
    cd "$COMPOSE_DIR" && docker compose restart
    echo "🔄 Restarted"
    ;;
  status)
    cd "$COMPOSE_DIR" && docker compose ps
    ;;
  logs)
    cd "$COMPOSE_DIR" && docker compose logs --tail=50 -f
    ;;
  update)
    cd "$COMPOSE_DIR" && docker compose pull && docker compose up -d
    echo "🆙 Updated all images"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|update}"
    exit 1
    ;;
esac
