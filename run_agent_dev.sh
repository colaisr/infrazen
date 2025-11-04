#!/bin/bash
# Development script to run Agent Service locally
# Prerequisites: virtual environment activated, dependencies installed

set -e

echo "🚀 Starting InfraZen Agent Service (Development Mode)"
echo "=================================================="

# Load environment
if [ -f config.agent.env ]; then
    echo "✓ Loading config.agent.env"
    export $(cat config.agent.env | grep -v '^#' | xargs)
else
    echo "⚠ config.agent.env not found, using defaults"
fi

# Check if port is available
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 8001 is already in use"
    echo "   Stop the process or use a different port"
    exit 1
fi

echo "✓ Port 8001 is available"
echo ""
echo "Agent Service will start on: http://127.0.0.1:8001"
echo "Health check: http://127.0.0.1:8001/v1/health"
echo "WebSocket echo: ws://127.0.0.1:8001/v1/chat/ws"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with uvicorn
cd "$(dirname "$0")"
python -m uvicorn agent_service.main:app --host 0.0.0.0 --port 8001 --reload

