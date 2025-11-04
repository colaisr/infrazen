#!/bin/bash
# Stop both InfraZen App and Agent Service

PROJECT_DIR="/Users/colakamornik/Desktop/InfraZen"
cd "$PROJECT_DIR"

echo "🛑 Stopping InfraZen services..."
echo ""

# Try to read PIDs from file
if [ -f .infrazen.pids ]; then
    read APP_PID AGENT_PID < .infrazen.pids
    echo "Stopping processes from .infrazen.pids..."
    kill $APP_PID 2>/dev/null && echo "✓ Stopped app (PID: $APP_PID)" || echo "⚠ App already stopped"
    kill $AGENT_PID 2>/dev/null && echo "✓ Stopped agent (PID: $AGENT_PID)" || echo "⚠ Agent already stopped"
    rm .infrazen.pids
fi

# Fallback: kill by port
echo ""
echo "Ensuring ports are free..."
lsof -ti:5001 | xargs kill -9 2>/dev/null && echo "✓ Killed remaining processes on port 5001" || echo "✓ Port 5001 is free"
lsof -ti:8001 | xargs kill -9 2>/dev/null && echo "✓ Killed remaining processes on port 8001" || echo "✓ Port 8001 is free"

echo ""
echo "✅ All services stopped"

