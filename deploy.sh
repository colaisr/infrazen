#!/usr/bin/env bash
# InfraZen Production Deployment Script
# This script is NOT in Git - maintained only on production server

set -euo pipefail

APP_DIR=/opt/infrazen
VENV="$APP_DIR/venv"
SERVICE=infrazen.service
BRANCH="${BRANCH:-master}"
HEALTH_URL="http://127.0.0.1:8000/"

log() { 
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

cd "$APP_DIR"

log "Pulling latest from Git (branch: $BRANCH)"
# Discard local changes to log files (they're regenerated anyway)
git checkout -- server.log.* 2>/dev/null || true

git fetch --all --prune
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
  log "Switching branch $CURRENT_BRANCH -> $BRANCH"
  git checkout "$BRANCH"
fi
git pull --ff-only origin "$BRANCH"

log "Installing/updating Python dependencies"
. "$VENV/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

log "Checking config.prod.env exists"
if [ ! -f config.prod.env ]; then
  log "ERROR: config.prod.env not found"
  log "Please create config.prod.env with production credentials"
  exit 1
fi

log "Running database migrations"
python3 -m alembic upgrade head

log "Restarting service (zero-downtime)"
sudo systemctl try-reload-or-restart "$SERVICE"

log "Running health check"
ok=0
for i in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
  if [ "$code" = "200" ]; then
    ok=1
    break
  fi
  sleep 0.5
done

if [ "$ok" != "1" ]; then
  log "ERROR: Service health check failed"
  log "Last 80 log lines:"
  sudo journalctl -u "$SERVICE" -n 80 --no-pager || true
  exit 1
fi

log "✅ Deployment successful!"
log "Deployed commit: $(git rev-parse --short HEAD)"
log "Service status: $(sudo systemctl is-active $SERVICE)"

