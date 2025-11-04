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
    
    # Agent Service (port 8001)
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
```

