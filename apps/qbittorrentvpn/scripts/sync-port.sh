#!/bin/sh
set -eu

CONF="/config/qBittorrent/qBittorrent.conf"
PF="/gluetun/forwarded_port"
LAST="/config/.last_forwarded_port"
LAST_RESTART="/config/.last_restart_time"
TARGET="${TARGET_CONTAINER:-qbittorrentvpn-qbittorrent-1}"

COOLDOWN=120  # seconds between restarts

log() { echo "[port-sync] $*"; }

now() { date +%s; }

read_port() {
  [ -f "$PF" ] || { echo ""; return; }
  cat "$PF" 2>/dev/null | tr -d '\r\n' || true
}

get_last_port() {
  [ -f "$LAST" ] || { echo ""; return; }
  cat "$LAST" 2>/dev/null | tr -d '\r\n' || true
}

get_session_port() {
  [ -f "$CONF" ] || { echo ""; return; }
  grep '^Session\\Port=' "$CONF" 2>/dev/null | head -n1 | cut -d= -f2 | tr -d '\r\n' || true
}

set_conf_port() {
  PORT="$1"
  [ -f "$CONF" ] || { log "qBittorrent conf not found yet"; return 1; }

  sed -i "s/^Session\\\\Port=.*/Session\\\\Port=$PORT/" "$CONF" 2>/dev/null || echo "Session\\Port=$PORT" >> "$CONF"
  sed -i "s/^Session\\\\UseRandomPort=.*/Session\\\\UseRandomPort=false/" "$CONF" 2>/dev/null || echo "Session\\UseRandomPort=false" >> "$CONF"
  sed -i "s/^Connection\\\\PortRangeMin=.*/Connection\\\\PortRangeMin=$PORT/" "$CONF" 2>/dev/null || echo "Connection\\PortRangeMin=$PORT" >> "$CONF"
  sed -i "s/^Connection\\\\PortRangeMax=.*/Connection\\\\PortRangeMax=$PORT/" "$CONF" 2>/dev/null || echo "Connection\\PortRangeMax=$PORT" >> "$CONF"

  return 0
}

container_exists() {
  docker ps --format '{{.Names}}' | grep -qx "$TARGET"
}

can_restart() {
  NOW=$(now)
  LAST_TS=0
  [ -f "$LAST_RESTART" ] && LAST_TS=$(cat "$LAST_RESTART" 2>/dev/null || echo 0)

  if [ $((NOW - LAST_TS)) -ge "$COOLDOWN" ]; then
    return 0
  else
    log "Cooldown active ($((NOW - LAST_TS))s elapsed)"
    return 1
  fi
}

restart_target() {
  if container_exists && can_restart; then
    log "Restarting $TARGET"
    docker restart "$TARGET" >/dev/null
    now > "$LAST_RESTART"
    log "Restarted $TARGET"
  fi
}

log "Started. Target container: $TARGET"

while :; do
  PORT="$(read_port)"

  if [ -n "${PORT:-}" ]; then
    LAST_PORT="$(get_last_port)"
    CURRENT_PORT="$(get_session_port)"

    if [ "$PORT" != "$LAST_PORT" ] || [ "$CURRENT_PORT" != "$PORT" ]; then
      log "Reconciling: forwarded=$PORT last=$LAST_PORT session=$CURRENT_PORT"

      if set_conf_port "$PORT"; then
        echo "$PORT" > "$LAST"
        restart_target
      fi
    fi
  fi

  sleep 30
done

