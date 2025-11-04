# Systemd Service Configuration for Agent Service

Create a systemd service to run the Agent Service as a daemon.

## Service File

Create `/etc/systemd/system/infrazen-agent.service`:

```ini
[Unit]
Description=InfraZen Agent Service - Conversational FinOps Assistant
After=network.target
Wants=infrazen.service

[Service]
Type=simple
User=infrazen
Group=infrazen
WorkingDirectory=/opt/infrazen
Environment="PATH=/opt/infrazen/venv/bin"
EnvironmentFile=/opt/infrazen/config.agent.env

# Run with uvicorn
ExecStart=/opt/infrazen/venv/bin/python -m uvicorn agent_service.main:app --host 0.0.0.0 --port 8001

# Restart policy
Restart=always
RestartSec=10s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=infrazen-agent

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Environment File

Create `/opt/infrazen/config.agent.env`:

```bash
AGENT_PORT=8001
AGENT_ENV=prod
LOG_LEVEL=INFO
AGENT_INTERNAL_API_BASE=http://127.0.0.1:5001/internal
AGENT_SERVICE_JWT_SECRET=<your-secret-here>
LLM_PROVIDER=openrouter
LLM_MODEL_TEXT=openai/gpt-4o-mini
LLM_MODEL_VISION=openai/gpt-4o
OPENROUTER_API_KEY=<your-key-here>
REDIS_URL=redis://127.0.0.1:6379/0
VECTOR_STORE=chroma
```

## Setup Commands

```bash
# Copy service file
sudo cp agent_service/SYSTEMD_SERVICE.md /etc/systemd/system/infrazen-agent.service

# Reload systemd
sudo systemctl daemon-reload

# Enable (start on boot)
sudo systemctl enable infrazen-agent

# Start service
sudo systemctl start infrazen-agent

# Check status
sudo systemctl status infrazen-agent
```

## Management Commands

```bash
# Start
sudo systemctl start infrazen-agent

# Stop
sudo systemctl stop infrazen-agent

# Restart
sudo systemctl restart infrazen-agent

# View logs
sudo journalctl -u infrazen-agent -f

# View recent logs
sudo journalctl -u infrazen-agent -n 100
```

## Verify

```bash
# Check if service is running
sudo systemctl is-active infrazen-agent

# Check if port is listening
sudo lsof -i :8001

# Test health endpoint
curl http://127.0.0.1:8001/v1/health
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u infrazen-agent -n 50

# Check file permissions
ls -la /opt/infrazen/config.agent.env

# Validate Python environment
/opt/infrazen/venv/bin/python -m agent_service.main
```

### Port already in use
```bash
# Find process using port 8001
sudo lsof -i :8001

# Kill if needed
sudo kill <PID>
```

### Dependencies missing
```bash
# Reinstall requirements
/opt/infrazen/venv/bin/pip install -r /opt/infrazen/requirements-agent.txt
```

