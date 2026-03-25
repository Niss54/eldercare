# Observability & Monitoring Guide

## Overview

The Eldercare platform implements comprehensive observability through:
- **Metrics**: Prometheus for time-series data collection
- **Logs**: CloudWatch for centralized log aggregation
- **Traces**: Jaeger for distributed tracing
- **Dashboards**: Grafana for metric visualization
- **Alerting**: AlertManager for intelligent routing

## Table of Contents

1. [Architecture](#architecture)
2. [Metrics Collection](#metrics-collection)
3. [CloudWatch Setup](#cloudwatch-setup)
4. [Prometheus Configuration](#prometheus-configuration)
5. [Alerting & SLOs](#alerting--slos)
6. [Dashboards](#dashboards)
7. [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Applications                          │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────┐    │
│  │   API (8000) │  │ Web(3000)│  │ Worker/Sched   │    │
│  └───────┬──────┘  └─────┬────┘  └────────┬───────┘    │
└─────────┼──────────────────┼───────────────┼────────────┘
          │                  │               │
          ▼                  ▼               ▼
┌──────────────────────────────────────────────────────────┐
│              Metrics & Logs Export                        │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────┐     │
│  │ Prometheus   │  │ OpenTel. │  │  JSON Logs     │     │
│  │ exporter:9090│  │ library  │  │                │     │
│  └──────┬───────┘  └─────┬────┘  └────────┬───────┘     │
└─────────┼──────────────────┼───────────────┼─────────────┘
          │                  │               │
          ▼                  ▼               ▼
┌──────────────────────────────────────────────────────────┐
│            Central Collection & Aggregation              │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ Prometheus   │  │  Jaeger  │  │  CloudWatch  │       │
│  │  (Scraper)   │  │ (Traces) │  │  (Logs/Metrics)     │
│  └──────┬───────┘  └─────┬────┘  └────────┬──────┘       │
└─────────┼──────────────────┼───────────────┼──────────────┘
          │                  │               │
          ▼                  ▼               ▼
┌──────────────────────────────────────────────────────────┐
│                 Visualization & Alerting                 │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────┐     │
│  │   Grafana    │  │AlertManager│ │  PagerDuty   │      │
│  │ (Dashboards) │  │(Alerts)    │  │ (On-call)    │      │
│  └──────────────┘  └──────────┘  └────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

---

## Metrics Collection

### Application Instrumentation

The platform exports metrics via StatsD/Prometheus format:

```python
# apps/api/src/middleware/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table', 'success']
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Cache hits',
    ['cache_name']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Cache misses',
    ['cache_name']
)

# Queue metrics
queue_depth = Gauge(
    'queue_depth',
    'Queue depth',
    ['queue_name']
)

# Business metrics
app_transactions_total = Counter(
    'app_transactions_total',
    'Total business transactions',
    ['transaction_type', 'status']
)

app_transaction_errors_total = Counter(
    'app_transaction_errors_total',
    'Total business transaction errors',
    ['transaction_type', 'error_type']
)
```

### Middleware for Automatic Collection

```python
# apps/api/src/middleware/observability.py
from prometheus_client import Counter, Histogram
from datetime import datetime
import logging

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'Request duration',
            ['method', 'endpoint', 'status']
        )
    
    async def __call__(self, request, call_next):
        start = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            raise
        finally:
            duration = time.time() - start
            self.request_duration.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).observe(duration)
            
            logging.info({
                'timestamp': datetime.utcnow().isoformat(),
                'method': request.method,
                'path': request.url.path,
                'status_code': status_code,
                'duration_ms': duration * 1000,
                'user_id': getattr(request.state, 'user_id', None)
            })
        
        return response
```

---

## CloudWatch Setup

### Creating Log Groups

```bash
# Create log groups for services
aws logs create-log-group --log-group-name /ecs/prod-api-service
aws logs create-log-group --log-group-name /ecs/prod-web-service
aws logs create-log-group --log-group-name /ecs/prod-worker-service
aws logs create-log-group --log-group-name /ecs/prod-scheduler-service

# Set retention policy to 30 days
aws logs put-retention-policy \
  --log-group-name /ecs/prod-api-service \
  --retention-in-days 30

# Create metric filters for error tracking
aws logs put-metric-filter \
  --log-group-name /ecs/prod-api-service \
  --filter-name ErrorCount \
  --filter-pattern "[... status = ERROR]" \
  --metric-transformations \
      metricName=ErrorCount,metricNamespace=Eldercare,metricValue=1
```

### CloudWatch Dashboards

```bash
# Import pre-built dashboard
aws cloudwatch put-dashboard \
  --dashboard-name EldercareProdDashboard \
  --dashboard-body file://infra/monitoring/cloudwatch-dashboard.json
```

### CloudWatch Alarms (Examples)

```bash
# API Error Rate Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name api-error-rate-high \
  --alarm-description "Alert when API error rate exceeds 1%" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:prod-alerts

# API Latency Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name api-latency-high \
  --alarm-description "Alert when P99 latency exceeds 500ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic p99 \
  --period 300 \
  --threshold 0.5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3

# Database Connection Pool
aws cloudwatch put-metric-alarm \
  --alarm-name db-connection-pool-high \
  --alarm-description "Alert when DB connections exceed 80" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## Prometheus Configuration

### Kubernetes Deployment

```yaml
# infra/kubernetes/prometheus-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: storage
          mountPath: /prometheus
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1000m
            memory: 4Gi
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: storage
        persistentVolumeClaim:
          claimName: prometheus-storage
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s
      evaluation_interval: 30s
    
    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093
    
    rule_files:
      - '/etc/prometheus/rules/*.yml'
    
    scrape_configs:
    
    # Kubernetes API Server
    - job_name: 'kubernetes-apiservers'
      kubernetes_sd_configs:
      - role: endpoints
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
        action: keep
        regex: default;kubernetes;https
    
    # Kubernetes Nodes
    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
    
    # Application Services
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

### Scrape Configuration for Application Pods

```yaml
# Add to pod spec in Kubernetes manifests
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

---

## Alerting & SLOs

### Alert Manager Configuration

```yaml
# infra/monitoring/alertmanager-config.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

templates:
- '/etc/alertmanager/templates/*.tmpl'

route:
  receiver: 'default'
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  routes:
  
  # Critical alerts go to PagerDuty immediately
  - match:
      severity: critical
    receiver: 'pagerduty'
    group_wait: 0s
    continue: true
  
  # Warning alerts go to Slack
  - match:
      severity: warning
    receiver: 'slack-warnings'
  
  # Business metrics alerts
  - match:
      alertname: 'CriticalUserJourneyDegraded'
    receiver: 'pagerduty'
    group_wait: 0s

receivers:

- name: 'default'
  slack_configs:
  - channel: '#alerts'
    title: 'Alert: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

- name: 'slack-warnings'
  slack_configs:
  - channel: '#warnings'
    title: '⚠️  {{ .GroupLabels.alertname }}'

- name: 'pagerduty'
  pagerduty_configs:
  - service_key: '{{ .GroupLabels.pagerduty_key }}'
    description: '{{ .GroupLabels.alertname }}'
    details:
      firing: '{{ template "pagerduty.default.instances" .Alerts.Firing }}'

inhibit_rules:

# Inhibit warning alerts if critical alert firing
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'

# Inhibit info alerts if warning alert firing
- source_match:
    severity: 'warning'
  target_match:
    severity: 'info'
```

### SLO Targets

| Metric | Target | Error Budget |
|--------|--------|--------------|
| API Availability | 99.9% | 43 minutes/month |
| API P99 Latency | < 500ms | 3 hours/month @ threshold |
| API Error Rate | < 0.1% | – |
| Web Availability | 99.5% | 3.6 hours/month |
| Database Uptime | 99.99% | 4.3 minutes/month |
| Cache Hit Rate | > 90% | – |

---

## Dashboards

### Grafana Integration

```bash
# Add Prometheus data source
curl -X POST http://grafana:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true
  }'
```

### Key Dashboards

1. **Overview Dashboard**
   - Current error rate
   - P99 latency
   - Availability percentage
   - Success rate over time

2. **Service Details**
   - Request rate by endpoint
   - Error rate by endpoint
   - Latency percentiles (p50, p95, p99)
   - Failed request breakdown

3. **Infrastructure**
   - CPU and memory utilization
   - Network I/O
   - Disk usage
   - Container restart count

4. **Database**
   - Connection pool usage
   - Query latency
   - Transaction rate
   - Replication lag

5. **Caching**
   - Cache hit/miss ratio
   - Memory usage
   - Eviction rate
   - Throughput

---

## Troubleshooting

### No Metrics Appearing

```bash
# 1. Verify Prometheus scrape targets
curl http://prometheus:9090/api/v1/targets

# 2. Check if metrics endpoint is accessible
curl http://api:8000/metrics

# 3. Look for scrape errors
curl http://prometheus:9090/api/v1/query?query=up

# 4. Check Prometheus logs
kubectl logs -l app=prometheus -n monitoring
```

### High Memory Usage

```bash
# Reduce scrape interval
# In prometheus.yml, increase global.scrape_interval from 30s to 60s

# Reduce retention period
# In prometheus startup args, add: --storage.tsdb.retention.time=7d
```

### Alerts Not Firing

```bash
# Test alert query
curl 'http://prometheus:9090/api/v1/query?query=sli:error_rate:api'

# Check alert rules are loaded
curl http://prometheus:9090/api/v1/rules

# Verify AlertManager is configured
curl http://alertmanager:9093/api/v1/alerts
```

---

## Cost Optimization

- **Metric Retention**: Keep 30 days of high-frequency metrics, 1 year for daily summaries
- **Log Retention**: 30 days for application logs, 90 days for audit logs
- **Sampling**: Use sampling for high-volume endpoints (e.g., health checks)
- **CloudWatch**: Reserve 5TB/month base with on-demand overage

---

## Runbooks

When alerts fire, reference these runbooks:

- [API SLO Breach](runbooks/api-slo-breach.md)
- [Database Performance](runbooks/database-performance.md)
- [Cache Issues](runbooks/cache-issues.md)
- [Memory Leaks](runbooks/memory-leaks.md)

**Last Updated**: 2024-01-10
**Owned By**: DevOps & Platform Team
