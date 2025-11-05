#!/bin/bash
# Run both InfraZen App and Agent Service together for local development

set -e

PROJECT_DIR="/Users/colakamornik/Desktop/InfraZen"
cd "$PROJECT_DIR"

echo "🚀 Starting InfraZen - App + Agent Service"
echo "=========================================="
echo ""

# Load agent config
if [ -f config.agent.env ]; then
    export $(cat config.agent.env | grep -v '^#' | xargs)
fi

# Kill any existing processes on ports 5001 and 8001
echo "🧹 Cleaning up existing processes..."
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

# Start Redis (Docker)
echo "🔴 Starting Redis..."
docker run -d --name infrazen-redis -p 6379:6379 redis:7-alpine 2>/dev/null || docker start infrazen-redis 2>/dev/null || true
sleep 2
echo "   Redis running on port 6379"

# Start Agent Service (background)
echo "🤖 Starting Agent Service on port 8001..."
nohup "./venv 2/bin/python" -m uvicorn agent_service.main:app --host 0.0.0.0 --port 8001 > agent.log 2>&1 &
AGENT_PID=$!
echo "   Agent PID: $AGENT_PID"

# Wait a bit for agent to start
sleep 2

# Start Main App (background)
echo "🌐 Starting Main App on port 5001..."
nohup "./venv 2/bin/python" run.py > app.log 2>&1 &
APP_PID=$!
echo "   App PID: $APP_PID"

# Wait for both to be ready
sleep 3

echo ""
echo "✅ Services started!"
echo "=========================================="
echo ""
echo "📊 Main App:      http://127.0.0.1:5001"
echo "🤖 Agent Service: http://127.0.0.1:8001"
echo "🔴 Redis:         redis://127.0.0.1:6379"
echo "🧪 Test Page:     http://127.0.0.1:5001/agent-test"
echo ""
echo "📝 Logs:"
echo "   App:   tail -f app.log"
echo "   Agent: tail -f agent.log"
echo "   Redis: docker logs infrazen-redis"
echo ""
echo "🛑 To stop all services:"
echo "   ./stop_both.sh"
echo ""
echo "PIDs saved to .infrazen.pids"
echo "$APP_PID $AGENT_PID" > .infrazen.pids

