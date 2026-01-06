---
title: Backups
description: Database and configuration backup strategies
---

# Backups

Regular backups are critical for disaster recovery. This guide covers backup strategies for UAPK Gateway.

## What to Backup

| Component | Priority | Frequency |
|-----------|----------|-----------|
| PostgreSQL database | Critical | Daily |
| Signing keys | Critical | On change |
| Configuration | High | On change |
| Audit log exports | High | Weekly |

## Database Backups

### Simple Backup Script

```bash
#!/bin/bash
# /opt/uapk-gateway/backup.sh

set -e

BACKUP_DIR=/var/backups/uapk-gateway
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Database backup
echo "Backing up database..."
docker compose exec -T db pg_dump -U uapk uapk_gateway \
  | gzip > $BACKUP_DIR/db-$DATE.sql.gz

echo "Database backup: $BACKUP_DIR/db-$DATE.sql.gz"

# Cleanup old backups
find $BACKUP_DIR -name "db-*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

### Automated Daily Backups

```bash
# Add to crontab
# 0 2 * * * /opt/uapk-gateway/backup.sh >> /var/log/uapk-backup.log 2>&1
crontab -e
```

### Point-in-Time Recovery

Enable PostgreSQL WAL archiving for point-in-time recovery:

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: uapk_gateway
      POSTGRES_USER: uapk
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    command:
      - "postgres"
      - "-c"
      - "wal_level=replica"
      - "-c"
      - "archive_mode=on"
      - "-c"
      - "archive_command=cp %p /var/lib/postgresql/wal_archive/%f"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - wal_archive:/var/lib/postgresql/wal_archive
```

## Key Backups

### Backup Signing Key

```bash
#!/bin/bash
# Encrypt and backup signing key

BACKUP_DIR=/var/backups/uapk-gateway/keys
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Encrypt with GPG
gpg --symmetric --cipher-algo AES256 \
  -o $BACKUP_DIR/signing-key-$DATE.pem.gpg \
  /etc/uapk-gateway/keys/signing.pem

echo "Key backup: $BACKUP_DIR/signing-key-$DATE.pem.gpg"
```

### Store Passphrase Securely

!!! warning "Passphrase Storage"
    Store the GPG passphrase separately from the encrypted key. Use a password manager or secrets vault.

## Configuration Backups

```bash
#!/bin/bash
# Backup configuration

BACKUP_DIR=/var/backups/uapk-gateway/config
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup docker-compose and env
cp /opt/uapk-gateway/docker-compose.yml $BACKUP_DIR/docker-compose-$DATE.yml
cp /opt/uapk-gateway/Caddyfile $BACKUP_DIR/Caddyfile-$DATE

# Backup environment (redact secrets)
grep -v PASSWORD /opt/uapk-gateway/.env > $BACKUP_DIR/env-$DATE.txt

echo "Config backup completed"
```

## Audit Log Exports

### Weekly Export Script

```bash
#!/bin/bash
# Export audit logs weekly

BACKUP_DIR=/var/backups/uapk-gateway/logs
DATE=$(date +%Y%m%d)
WEEK_AGO=$(date -d "7 days ago" +%Y-%m-%dT00:00:00Z)
NOW=$(date +%Y-%m-%dT23:59:59Z)

mkdir -p $BACKUP_DIR

# Export logs for each agent
for AGENT in $(curl -s http://localhost:8000/api/v1/orgs/$ORG_ID/manifests \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[].uapk_id'); do

  curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/download \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"uapk_id\": \"$AGENT\", \"from\": \"$WEEK_AGO\", \"to\": \"$NOW\"}" \
    > $BACKUP_DIR/logs-$AGENT-$DATE.json

  # Verify export
  python verify_log_chain.py $BACKUP_DIR/logs-$AGENT-$DATE.json

done

echo "Log export completed"
```

## Remote Storage

### AWS S3

```bash
#!/bin/bash
# Upload backups to S3

BACKUP_DIR=/var/backups/uapk-gateway
S3_BUCKET=s3://my-backup-bucket/uapk-gateway

# Sync backups
aws s3 sync $BACKUP_DIR $S3_BUCKET --sse AES256

# Lifecycle policy handles retention in S3
```

### S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "ExpireOldBackups",
      "Status": "Enabled",
      "Prefix": "uapk-gateway/",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

### Google Cloud Storage

```bash
#!/bin/bash
# Upload backups to GCS

BACKUP_DIR=/var/backups/uapk-gateway
GCS_BUCKET=gs://my-backup-bucket/uapk-gateway

gsutil -m rsync -r $BACKUP_DIR $GCS_BUCKET
```

## Restore Procedures

### Database Restore

```bash
#!/bin/bash
# Restore database from backup

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  exit 1
fi

# Stop gateway
docker compose stop gateway

# Restore database
zcat $BACKUP_FILE | docker compose exec -T db psql -U uapk -d uapk_gateway

# Start gateway
docker compose start gateway

# Verify
curl http://localhost:8000/api/v1/gateway/health
```

### Key Restore

```bash
#!/bin/bash
# Restore signing key

BACKUP_FILE=$1

gpg --decrypt $BACKUP_FILE > /etc/uapk-gateway/keys/signing.pem
chmod 600 /etc/uapk-gateway/keys/signing.pem

# Restart gateway to load new key
docker compose restart gateway
```

### Full Disaster Recovery

```bash
#!/bin/bash
# Full recovery procedure

# 1. Provision new server
# 2. Install prerequisites (Docker, etc.)

# 3. Restore configuration
cp config-backup/docker-compose.yml /opt/uapk-gateway/
cp config-backup/Caddyfile /opt/uapk-gateway/

# 4. Restore signing key
gpg --decrypt keys-backup/signing-key.pem.gpg > /etc/uapk-gateway/keys/signing.pem
chmod 600 /etc/uapk-gateway/keys/signing.pem

# 5. Start database
docker compose up -d db
sleep 10

# 6. Restore database
zcat db-backup/db-latest.sql.gz | docker compose exec -T db psql -U uapk -d uapk_gateway

# 7. Start gateway
docker compose up -d gateway

# 8. Verify
curl http://localhost:8000/api/v1/gateway/health

# 9. Verify log chain integrity
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/all \
  -H "Authorization: Bearer $TOKEN"
```

## Backup Verification

### Monthly Verification

```bash
#!/bin/bash
# Verify backup integrity

BACKUP_DIR=/var/backups/uapk-gateway

echo "Checking database backups..."
for f in $BACKUP_DIR/db-*.sql.gz; do
  if gzip -t "$f" 2>/dev/null; then
    echo "✓ $f"
  else
    echo "✗ $f - CORRUPTED"
  fi
done

echo "Checking log exports..."
for f in $BACKUP_DIR/logs/*.json; do
  if python verify_log_chain.py "$f" >/dev/null 2>&1; then
    echo "✓ $f"
  else
    echo "✗ $f - VERIFICATION FAILED"
  fi
done
```

### Test Restore

Periodically restore backups to a test environment:

```bash
# Create test environment
docker compose -f docker-compose.test.yml up -d

# Restore and verify
./restore-db.sh /var/backups/uapk-gateway/db-latest.sql.gz

# Run verification
curl http://localhost:8001/api/v1/gateway/health
```

## Retention Policy

| Backup Type | Retention | Storage Class |
|-------------|-----------|---------------|
| Daily DB | 30 days | Standard |
| Weekly logs | 1 year | Standard → Glacier |
| Monthly archive | 7 years | Glacier |
| Signing keys | Forever | Cold storage |

## Related

- [Single VM](single-vm.md) - Deployment setup
- [Monitoring](monitoring.md) - Backup monitoring
- [Key Management](../security/key-management.md) - Key backup procedures
