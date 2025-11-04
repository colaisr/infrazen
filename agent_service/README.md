# InfraZen Agent Service

Conversational FinOps Assistant with LLM-powered recommendations.

## Quick Start (Local Development)

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements-agent.txt
```

### 2. Configure Environment

```bash
# Copy sample config
cp config.agent.env.sample config.agent.env

# Edit config.agent.env and set at least:
# - OPENROUTER_API_KEY (or another LLM provider key)
# - AGENT_SERVICE_JWT_SECRET (any secure random string)
```

### 3. Run Agent Service

```bash
# From project root
./run_agent_dev.sh
```

Agent will start on http://127.0.0.1:8001

### 4. Test Connectivity

1. Start the main InfraZen app (port 5001)
2. Navigate to http://127.0.0.1:5001/agent-test
3. Run tests:
   - Health check
   - WebSocket echo
   - Full test suite

## API Endpoints

- `GET /v1/health` - Health check
- `GET /v1/readiness` - Readiness check with dependency validation
- `WS /v1/chat/ws?session=<id>` - WebSocket chat (echo mode)
- `POST /v1/chat/start` - Create chat session

## Directory Structure

```
agent_service/
├── main.py              # FastAPI application
├── api/                 # API routes
│   ├── health.py        # Health checks
│   └── chat.py          # Chat endpoints
├── core/                # Core utilities
│   └── config.py        # Configuration
├── tools/               # Data access tools (future)
├── llm/                 # LLM provider abstraction (future)
└── schemas/             # Pydantic schemas (future)
```

## Configuration

See `config.agent.env.sample` for all available options.

Key settings:
- `AGENT_PORT`: Service port (default: 8001)
- `AGENT_ENV`: dev|prod
- `LLM_PROVIDER`: openrouter|openai|anthropic|ollama|gigachat
- `LLM_MODEL_TEXT`: Text model for recommendations
- `LLM_MODEL_VISION`: Vision model for image analysis

## Development Status

✅ **Milestone 1 (In Progress)** - Skeleton + Local Validation
- [x] FastAPI skeleton with health & WebSocket endpoints
- [x] Configuration management
- [x] Test UI page
- [ ] Nginx proxy configuration
- [ ] systemd service setup
- [ ] Server deployment

🔜 **Milestone 2** - CI/CD
🔜 **Milestone 3** - LLM Recommendation Text Generator
🔜 **Milestone 4** - Recommendation Chat
🔜 **Milestone 5** - Analytics Chat
🔜 **Milestone 6** - AI Report Generator

See `Docs/agent_service_master_description.md` for full roadmap.

