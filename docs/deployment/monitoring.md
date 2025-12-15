---
title: Monitoring
description: Observability and alerting setup
---

# Monitoring

This guide covers setting up monitoring and alerting for UAPK Gateway.

## Metrics Overview

UAPK Gateway exposes Prometheus-compatible metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `gateway_requests_total` | Counter | Total requests by endpoint |
| `gateway_request_duration_seconds` | Histogram | Request latency |
| `gateway_decisions_total` | Counter | Decisions by type (allow/deny/escalate) |
| `gateway_active_agents` | Gauge | Currently active agents |
| `gateway_pending_approvals` | Gauge | Pending approval count |
| `gateway_chain_verification` | Gauge | Last verification status |

## Prometheus Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  gateway:
    image: ghcr.io/uapk/gateway:latest
    environment:
      METRICS_ENABLED: "true"
    ports:
      - "8000:8000"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

volumes:
  prometheus_data:
  grafana_data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'gateway'
    static_configs:
      - targets: ['gateway:8000']
    metrics_path: /metrics

  - job_name: 'caddy'
    static_configs:
      - targets: ['caddy:9180']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - /etc/prometheus/alerts/*.yml
```

## Grafana Dashboards

### Gateway Overview Dashboard

```json
{
  "dashboard": {
    "title": "UAPK Gateway Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gateway_requests_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Decision Distribution",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (decision) (gateway_decisions_total)",
            "legendFormat": "{{decision}}"
          }
        ]
      },
      {
        "title": "Request Latency (p99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(gateway_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "title": "Pending Approvals",
        "type": "stat",
        "targets": [
          {
            "expr": "gateway_pending_approvals"
          }
        ]
      }
    ]
  }
}
```

## Alerting Rules

### alerts.yml

```yaml
groups:
  - name: gateway
    rules:
      - alert: GatewayDown
        expr: up{job="gateway"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Gateway is down"
          description: "Gateway has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: rate(gateway_requests_total{status="5xx"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanize }}%"

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(gateway_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p99 latency is {{ $value }}s"

      - alert: PendingApprovalsBacklog
        expr: gateway_pending_approvals > 10
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Pending approvals backlog"
          description: "{{ $value }} approvals pending for over 1 hour"

      - alert: ChainVerificationFailed
        expr: gateway_chain_verification == 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Log chain verification failed"
          description: "Audit log chain integrity check failed"

      - alert: HighDenyRate
        expr: rate(gateway_decisions_total{decision="deny"}[1h]) / rate(gateway_decisions_total[1h]) > 0.2
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High deny rate"
          description: "{{ $value | humanizePercentage }} of requests denied"

  - name: database
    rules:
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"

      - alert: HighConnectionCount
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection count"
```

## Alertmanager Configuration

### alertmanager.yml

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@yourdomain.com'

route:
  receiver: 'default'
  group_by: ['alertname']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    - match:
        severity: critical
      receiver: 'critical'
      repeat_interval: 1h

    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'

  - name: 'critical'
    email_configs:
      - to: 'oncall@example.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts-critical'

  - name: 'warning'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
```

## Health Checks

### Gateway Health Endpoint

```bash
# Basic health check
curl http://localhost:8000/api/v1/gateway/health

# Response
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "timestamp": "2024-12-14T10:00:00Z"
}
```

### Docker Health Checks

```yaml
services:
  gateway:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/gateway/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### External Health Monitoring

```bash
# Uptime monitoring script
#!/bin/bash

GATEWAY_URL="https://gateway.yourdomain.com"
SLACK_WEBHOOK="https://hooks.slack.com/services/..."

if ! curl -sf "$GATEWAY_URL/api/v1/gateway/health" > /dev/null; then
    curl -X POST "$SLACK_WEBHOOK" \
      -H 'Content-type: application/json' \
      -d '{"text": "⚠️ UAPK Gateway health check failed!"}'
fi
```

## Log Aggregation

### Loki Setup

```yaml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - ./promtail-config.yml:/etc/promtail/config.yml
```

### promtail-config.yml

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: gateway
    static_configs:
      - targets:
          - localhost
        labels:
          job: gateway
          __path__: /var/log/gateway/*.log

  - job_name: caddy
    static_configs:
      - targets:
          - localhost
        labels:
          job: caddy
          __path__: /var/log/caddy/*.log
```

## Key Metrics to Monitor

| Metric | Alert Threshold | Description |
|--------|-----------------|-------------|
| Request latency p99 | > 1s | User experience |
| Error rate | > 1% | Service health |
| Pending approvals | > 10 for 1h | Operator attention needed |
| Chain verification | Failed | Critical integrity |
| Database connections | > 80% | Capacity |
| CPU usage | > 80% | Performance |
| Memory usage | > 85% | Stability |

## Runbook

### High Error Rate

1. Check gateway logs: `docker compose logs gateway`
2. Check database connectivity: `docker compose exec db pg_isready`
3. Review recent deployments
4. Check external service dependencies

### High Latency

1. Check database query times
2. Review connection pool usage
3. Check for resource contention
4. Scale if necessary

### Chain Verification Failed

1. **Critical** - Follow incident response
2. Export affected logs immediately
3. Investigate potential tampering
4. Contact security team

## Related

- [Single VM](single-vm.md) - Deployment setup
- [Backups](backups.md) - Backup monitoring
- [Incidents](../operator/incidents.md) - Incident response
