# Deployment Guide

Deploy UAPK Gateway to production.

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- Docker and Docker Compose
- Domain name with DNS configured
- 2GB+ RAM, 2+ CPU cores

## Quick Production Setup

### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/example/uapk-gateway.git
cd uapk-gateway

# Create production environment
cp .env.example .env.prod
```

Edit `.env.prod`:

```env
ENVIRONMENT=production
DEBUG=false
LOG_FORMAT=json
LOG_LEVEL=INFO

# REQUIRED: Generate with: openssl rand -hex 32
SECRET_KEY=your-secure-random-key-here

# REQUIRED: Strong database password
POSTGRES_PASSWORD=your-secure-db-password

# Your domain
DOMAIN=gateway.yourdomain.com
```

### 2. Configure Caddy

Edit `deploy/caddy/Caddyfile`:

```
gateway.yourdomain.com {
    reverse_proxy backend:8000
    # ... rest of config
}
```

### 3. Deploy

```bash
# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Verify

```bash
curl https://gateway.yourdomain.com/healthz
```

## Systemd Service

For automatic startup:

```bash
# Copy service file
sudo cp deploy/systemd/uapk-gateway.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/uapk-gateway.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable uapk-gateway
sudo systemctl start uapk-gateway

# Check status
sudo systemctl status uapk-gateway
```

## Backup

### Database Backup

```bash
# Manual backup
docker compose exec postgres pg_dump -U uapk uapk > backup.sql

# Automated backup (add to crontab)
0 2 * * * cd /opt/uapk-gateway && docker compose exec -T postgres pg_dump -U uapk uapk | gzip > /backups/uapk-$(date +\%Y\%m\%d).sql.gz
```

### Restore

```bash
cat backup.sql | docker compose exec -T postgres psql -U uapk uapk
```

## Monitoring

### Health Endpoints

- `/healthz` - Liveness (is the app running?)
- `/readyz` - Readiness (can it accept traffic?)

### Logs

```bash
# All logs
docker compose logs -f

# Backend only
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend
```

### Metrics (Future)

Prometheus metrics endpoint planned for v0.3.

## Security Checklist

- [ ] Strong SECRET_KEY (32+ random bytes)
- [ ] Strong POSTGRES_PASSWORD
- [ ] TLS enabled (Caddy handles this)
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular backups configured
- [ ] Log rotation configured
- [ ] Monitoring alerts set up

## Updating

```bash
# Pull latest
git pull

# Rebuild and restart
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Run migrations (when available)
# docker compose exec backend alembic upgrade head
```
