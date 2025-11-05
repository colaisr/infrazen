# Nginx Configuration for Agent Service

Add this location block to your Nginx config to proxy `/agent/` to the Agent Service.

## Configuration Snippet

Add to your existing InfraZen Nginx site config (typically `/etc/nginx/sites-available/infrazen`):

```nginx
# Agent Service proxy (runs on port 8001)
location /agent/ {
    proxy_pass http://127.0.0.1:8001/;
    proxy_http_version 1.1;
    
    # WebSocket support
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeouts for long-running LLM requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # No buffering for streaming responses
    proxy_buffering off;
    proxy_cache off;
}
```

## Complete Example

```nginx
server {
    listen 80;
    server_name infrazen.team www.infrazen.team;
    
    # Flask app (port 5001)
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Agent Service WebSocket Chat (specific route with longer timeouts)
    location /agent/v1/chat/ {
        proxy_pass http://127.0.0.1:8001/v1/chat/;
        proxy_http_version 1.1;
        
        # WebSocket headers (critical!)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Standard headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Extended timeouts for long-running chat sessions
        proxy_connect_timeout 3600s;  # 1 hour
        proxy_send_timeout 3600s;     # 1 hour
        proxy_read_timeout 3600s;     # 1 hour
        
        # No buffering for real-time chat
        proxy_buffering off;
        proxy_cache off;
    }
    
    # Agent Service (other API routes)
    location /agent/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
        proxy_cache off;
    }
    
    # Static files
    location /static {
        alias /path/to/InfraZen/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Apply Configuration

```bash
# Test config
sudo nginx -t

# Reload (zero-downtime)
sudo systemctl reload nginx
```

## Verify

```bash
# Check if agent is accessible
curl http://127.0.0.1/agent/v1/health

# Should return: {"status":"healthy","service":"infrazen-agent",...}

# Check WebSocket endpoint (returns HTML page if accessed via HTTP)
curl http://127.0.0.1/agent/v1/chat/connections

# Should return: {"active_connections":0,"timestamp":"..."}
```

## WebSocket Chat Configuration Details

The `/agent/v1/chat/` location is specifically configured for long-running WebSocket chat sessions:

**Key Features:**
- **1-hour timeouts**: Allows users to keep chat open for extended periods
- **WebSocket upgrade headers**: Critical for WS protocol handshake
- **No buffering**: Ensures real-time message delivery
- **Separate location block**: Prevents shorter timeouts from affecting chat

**Why separate from main `/agent/` location:**
- Chat sessions can last hours (vs. seconds for API requests)
- Prevents nginx from closing idle WebSocket connections
- Allows different timeout policies for different endpoints

**Testing WebSocket through Nginx:**
```javascript
// In browser console on https://infrazen.team
const ws = new WebSocket('wss://infrazen.team/agent/v1/chat/rec/123?token=...');
ws.onopen = () => console.log('Connected via Nginx!');
ws.onmessage = (e) => console.log('Received:', e.data);
```

