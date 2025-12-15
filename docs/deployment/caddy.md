---
title: Caddy Setup
description: HTTPS reverse proxy with automatic certificates
---

# Caddy Setup

Caddy provides automatic HTTPS with Let's Encrypt certificates, making it ideal for UAPK Gateway deployments.

## Why Caddy?

| Feature | Benefit |
|---------|---------|
| Automatic HTTPS | Let's Encrypt integration |
| Zero config TLS | Secure defaults |
| Simple syntax | Easy to maintain |
| HTTP/2 & HTTP/3 | Modern performance |
| Automatic renewal | No certificate expiry |

## Basic Configuration

### Caddyfile

```caddyfile
gateway.yourdomain.com {
    reverse_proxy localhost:8000
}
```

That's it! Caddy will automatically:

- Obtain a TLS certificate from Let's Encrypt
- Configure HTTPS with secure defaults
- Redirect HTTP to HTTPS
- Renew certificates automatically

## Production Configuration

### Full Caddyfile

```caddyfile
{
    email admin@yourdomain.com
    acme_ca https://acme-v02.api.letsencrypt.org/directory
}

gateway.yourdomain.com {
    # Proxy to gateway
    reverse_proxy localhost:8000 {
        # Health check
        health_uri /api/v1/gateway/health
        health_interval 30s
        health_timeout 5s

        # Headers
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Content-Security-Policy "default-src 'self'"
        -Server
    }

    # Rate limiting
    rate_limit {
        zone api {
            match path /api/*
            rate 100r/m
        }
    }

    # Logging
    log {
        output file /var/log/caddy/access.log {
            roll_size 100mb
            roll_keep 10
        }
        format json
    }

    # Compression
    encode gzip zstd
}

# Redirect www to non-www
www.gateway.yourdomain.com {
    redir https://gateway.yourdomain.com{uri} permanent
}
```

## Docker Compose Integration

### docker-compose.yml

```yaml
version: '3.8'

services:
  gateway:
    image: ghcr.io/uapk/gateway:latest
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://uapk:${DB_PASSWORD}@db:5432/uapk_gateway
      SECRET_KEY: ${SECRET_KEY}
    expose:
      - "8000"

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    depends_on:
      - gateway
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - /var/log/caddy:/var/log/caddy

volumes:
  caddy_data:
  caddy_config:
```

## Multiple Domains

### API and Dashboard

```caddyfile
# API endpoint
api.yourdomain.com {
    reverse_proxy localhost:8000

    header {
        Access-Control-Allow-Origin "*"
        Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        Access-Control-Allow-Headers "Authorization, Content-Type, X-API-Key"
    }
}

# Dashboard
dashboard.yourdomain.com {
    reverse_proxy localhost:8000 {
        # Only allow UI paths
        header_up X-Dashboard "true"
    }

    # Stricter CSP for dashboard
    header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'"
}
```

## Load Balancing

### Multiple Gateway Instances

```caddyfile
gateway.yourdomain.com {
    reverse_proxy gateway1:8000 gateway2:8000 gateway3:8000 {
        lb_policy round_robin
        health_uri /api/v1/gateway/health
        health_interval 10s

        # Sticky sessions (if needed)
        # lb_policy cookie
    }
}
```

## TLS Configuration

### Custom Certificates

```caddyfile
gateway.yourdomain.com {
    tls /path/to/cert.pem /path/to/key.pem

    reverse_proxy localhost:8000
}
```

### Internal CA

```caddyfile
{
    # Use internal CA for testing
    local_certs
}

gateway.internal {
    reverse_proxy localhost:8000
}
```

### Client Certificates (mTLS)

```caddyfile
gateway.yourdomain.com {
    tls {
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file /path/to/ca.pem
        }
    }

    reverse_proxy localhost:8000
}
```

## Security Hardening

### Rate Limiting Plugin

```bash
# Install rate limit plugin
xcaddy build --with github.com/mholt/caddy-ratelimit
```

```caddyfile
{
    order rate_limit before reverse_proxy
}

gateway.yourdomain.com {
    rate_limit {
        zone api {
            match path /api/*
            rate 100r/m
        }
        zone auth {
            match path /api/v1/auth/*
            rate 10r/m
        }
    }

    reverse_proxy localhost:8000
}
```

### IP Filtering

```caddyfile
gateway.yourdomain.com {
    @blocked {
        remote_ip 10.0.0.0/8
    }
    respond @blocked "Forbidden" 403

    reverse_proxy localhost:8000
}
```

### Basic Auth (for staging)

```caddyfile
staging.yourdomain.com {
    basicauth * {
        admin $2a$14$... # bcrypt hash
    }

    reverse_proxy localhost:8000
}
```

## Monitoring

### Metrics Endpoint

```caddyfile
{
    servers {
        metrics
    }
}

:9180 {
    metrics /metrics
}

gateway.yourdomain.com {
    reverse_proxy localhost:8000
}
```

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'caddy'
    static_configs:
      - targets: ['caddy:9180']
```

## Troubleshooting

### Check Certificate Status

```bash
# View certificate details
curl -vI https://gateway.yourdomain.com 2>&1 | grep -A 10 "SSL certificate"

# Check certificate expiry
echo | openssl s_client -servername gateway.yourdomain.com -connect gateway.yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Force Certificate Renewal

```bash
# Remove old certificate
docker compose exec caddy rm -rf /data/caddy/certificates

# Reload Caddy
docker compose exec caddy caddy reload
```

### Debug Mode

```caddyfile
{
    debug
}

gateway.yourdomain.com {
    reverse_proxy localhost:8000
}
```

### View Logs

```bash
# Caddy logs
docker compose logs caddy

# Access logs
tail -f /var/log/caddy/access.log | jq
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Certificate not issued | Check DNS, firewall ports 80/443 |
| 502 Bad Gateway | Check gateway service is running |
| Slow HTTPS | Enable HTTP/2 and compression |
| Rate limit too strict | Adjust rate_limit configuration |

## Related

- [Single VM](single-vm.md) - Complete deployment guide
- [Monitoring](monitoring.md) - Observability setup
- [Security](../security/index.md) - Security practices
