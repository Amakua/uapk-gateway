---
title: Single VM Deployment
description: Deploy UAPK Gateway on a single virtual machine
---

# Single VM Deployment

This guide covers deploying UAPK Gateway on a single virtual machine, suitable for small to medium deployments.

## Prerequisites

- Ubuntu 22.04 LTS or Debian 12
- 4+ GB RAM, 2+ CPU cores
- 50+ GB SSD storage
- Domain name pointing to server IP
- SSH access

## Step 1: Initial Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y curl git ufw fail2ban

# Configure firewall
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Create service user
sudo useradd -r -s /bin/false uapk
```

## Step 2: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Install Docker Compose
sudo apt install -y docker-compose-plugin
```

## Step 3: Configure PostgreSQL

```bash
# Create data directory
sudo mkdir -p /var/lib/uapk-gateway/postgres
sudo chown 999:999 /var/lib/uapk-gateway/postgres

# Generate database password
DB_PASSWORD=$(openssl rand -base64 32)
echo "Database password: $DB_PASSWORD"
```

## Step 4: Generate Signing Key

```bash
# Create keys directory
sudo mkdir -p /etc/uapk-gateway/keys
sudo chown uapk:uapk /etc/uapk-gateway/keys

# Generate Ed25519 key pair
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

private_key = Ed25519PrivateKey.generate()

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
print(private_pem.decode())
" | sudo tee /etc/uapk-gateway/keys/signing.pem

sudo chmod 600 /etc/uapk-gateway/keys/signing.pem
sudo chown uapk:uapk /etc/uapk-gateway/keys/signing.pem
```

## Step 5: Create Docker Compose File

```bash
sudo mkdir -p /opt/uapk-gateway
cd /opt/uapk-gateway

# Create docker-compose.yml
cat <<EOF | sudo tee docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: uapk_gateway
      POSTGRES_USER: uapk
      POSTGRES_PASSWORD: \${DB_PASSWORD}
    volumes:
      - /var/lib/uapk-gateway/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U uapk -d uapk_gateway"]
      interval: 10s
      timeout: 5s
      retries: 5

  gateway:
    image: ghcr.io/uapk/gateway:latest
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://uapk:\${DB_PASSWORD}@db:5432/uapk_gateway
      SECRET_KEY: \${SECRET_KEY}
      GATEWAY_SIGNING_KEY_FILE: /keys/signing.pem
      GATEWAY_ENV: production
      LOG_LEVEL: INFO
    volumes:
      - /etc/uapk-gateway/keys:/keys:ro
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/gateway/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    depends_on:
      - gateway
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
EOF
```

## Step 6: Create Caddyfile

```bash
# Replace gateway.yourdomain.com with your domain
cat <<EOF | sudo tee /opt/uapk-gateway/Caddyfile
gateway.yourdomain.com {
    reverse_proxy gateway:8000

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }

    log {
        output file /var/log/caddy/access.log
    }
}
EOF
```

## Step 7: Create Environment File

```bash
# Generate secret key
SECRET_KEY=$(openssl rand -base64 32)

# Create .env file
cat <<EOF | sudo tee /opt/uapk-gateway/.env
DB_PASSWORD=${DB_PASSWORD}
SECRET_KEY=${SECRET_KEY}
EOF

sudo chmod 600 /opt/uapk-gateway/.env
```

## Step 8: Start Services

```bash
cd /opt/uapk-gateway

# Start services
sudo docker compose up -d

# Check status
sudo docker compose ps

# View logs
sudo docker compose logs -f gateway
```

## Step 9: Initialize Gateway

```bash
# Wait for services to be healthy
sleep 10

# Create initial organization
curl -X POST http://localhost:8000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Organization",
    "slug": "my-org",
    "admin_email": "admin@example.com",
    "admin_password": "secure-password-here"
  }'

# Save the org_id from response
```

## Step 10: Set Up Systemd Service

```bash
# Create systemd service
cat <<EOF | sudo tee /etc/systemd/system/uapk-gateway.service
[Unit]
Description=UAPK Gateway
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/uapk-gateway
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable uapk-gateway
sudo systemctl start uapk-gateway
```

## Step 11: Set Up Log Rotation

```bash
cat <<EOF | sudo tee /etc/logrotate.d/uapk-gateway
/var/log/caddy/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

## Step 12: Configure Backups

```bash
# Create backup script
cat <<'EOF' | sudo tee /opt/uapk-gateway/backup.sh
#!/bin/bash
set -e

BACKUP_DIR=/var/backups/uapk-gateway
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U uapk uapk_gateway | gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Backup keys
cp -r /etc/uapk-gateway/keys $BACKUP_DIR/keys-$DATE

# Keep last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /opt/uapk-gateway/backup.sh

# Add to crontab
echo "0 2 * * * /opt/uapk-gateway/backup.sh >> /var/log/uapk-backup.log 2>&1" | sudo crontab -
```

## Verification

```bash
# Check services
sudo docker compose ps

# Check gateway health
curl https://gateway.yourdomain.com/api/v1/gateway/health

# Check TLS certificate
curl -vI https://gateway.yourdomain.com 2>&1 | grep "SSL certificate"
```

## Updating

```bash
cd /opt/uapk-gateway

# Pull latest image
sudo docker compose pull

# Restart with new image
sudo docker compose up -d

# Verify health
sudo docker compose ps
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo docker compose logs gateway

# Check database
sudo docker compose exec db psql -U uapk -d uapk_gateway -c "SELECT 1"
```

### TLS Certificate Issues

```bash
# Check Caddy logs
sudo docker compose logs caddy

# Force certificate renewal
sudo docker compose exec caddy caddy reload
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check database connections
sudo docker compose exec db psql -U uapk -d uapk_gateway \
  -c "SELECT count(*) FROM pg_stat_activity"
```

## Related

- [Caddy Setup](caddy.md) - Detailed Caddy configuration
- [Backups](backups.md) - Backup strategies
- [Monitoring](monitoring.md) - Setting up monitoring
