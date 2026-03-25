# Incident Runbooks

## API SLO Breach Runbook

### Alert Details
- **Condition**: API availability <99.9% for 5+ minutes
- **Impact**: Users unable to use applications or experiencing errors
- **On-Call Escalation**: Page on-call engineer immediately

### Step 1: Assess Severity (2 minutes)

```bash
# 1a. Check current metrics
curl https://grafana.eldr.care/api/datasources/proxy/1/api/v1/query \
  --data-urlencode 'query=sli:availability:api' | jq '.data.result[0].value'

# 1b. Check if single service or platform-wide
curl https://api.eldr.care/api/v1/health -v
curl https://eldr.care/health -v

# 1c. Get error distribution
kubectl logs -l app=api -n eldercare-prod --since=5m | grep ERROR | tail -20

# 1d. Check recent deployments
kubectl rollout history deployment/api -n eldercare-prod
```

### Step 2: Determine Root Cause (5 minutes)

**Check these in order:**

A. **Database issues**
```bash
# Check database connection
kubectl exec -it postgres-0 -n eldercare-prod -- \
  psql -U postgres -d eldercare -c "\conninfo"

# Check slow queries
kubectl exec -it postgres-0 -n eldercare-prod -- \
  psql -U postgres -d eldercare -c "SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Check connection pool
kubectl exec -it api-pod -c api -- \
  curl localhost:8000/debug/db-connections
```

B. **Resource constraints**
```bash
# CPU/Memory
kubectl top nodes
kubectl top pod -n eldercare-prod

# Disk space
kubectl exec -it api-pod -c api -- df -h /

# Network
kubectl exec -it api-pod -c api -- netstat -tuln | grep ESTABLISHED | wc -l
```

C. **Recent deployment issues**
```bash
# Rollout status
kubectl rollout status deployment/api -n eldercare-prod

# Compare current vs previous image
kubectl describe deployment api -n eldercare-prod | grep -A 5 "Image:"

# Check events
kubectl get events -n eldercare-prod --sort-by='.lastTimestamp' | tail -20
```

D. **External dependencies**
```bash
# Check Redis
kubectl exec -it api-pod -c api -- redis-cli -h redis ping

# Check message queue
kubectl get pod -l app=redis -n eldercare-prod -o wide

# Check SSL certificates (if public)
echo | openssl s_client -servername api.eldr.care -connect api.eldr.care:443 2>/dev/null | \
  openssl x509 -noout -dates
```

### Step 3: Execute Remediations

**If database slow:**
```bash
# Kill long-running queries
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE query_start < now() - interval '5 minutes';"

# Restart database
kubectl rollout restart statefulset/postgres -n eldercare-prod
```

**If resource constrained:**
```bash
# Scale up API replicas
kubectl scale deployment api --replicas=5 -n eldercare-prod

# If memory issue, restart pods
kubectl delete pod -l app=api -n eldercare-prod

# Check if HPA is enabled
kubectl get hpa -n eldercare-prod
```

**If recent deployment:**
```bash
# Rollback to previous version
kubectl rollout undo deployment/api -n eldercare-prod

# Monitor rollback
kubectl rollout status deployment/api -n eldercare-prod -w
```

**If Redis issue:**
```bash
# Flush keys if memory critical
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli MEMORY PURGE

# Restart Redis cluster
kubectl rollout restart deployment/redis -n eldercare-prod
```

### Step 4: Verify Recovery (3 minutes)

```bash
# 4a. Check health endpoints
for i in {1..5}; do
  curl https://api.eldr.care/api/v1/health
  sleep 2
done

# 4b. Run smoke tests
kubectl run test-pod -it --rm \
  --image=python:3.13-alpine \
  --env="API_URL=https://api.eldr.care" \
  --env="USER_EMAIL=test@test.com" \
  --env="USER_PASSWORD=TestPass123" \
  -n eldercare-prod \
  -- python -m pytest /smoke-tests -v

# 4c. Check error metrics
curl https://grafana.eldr.care/api/datasources/proxy/1/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m])'
```

### Step 5: Post-Incident (If applicable)

```bash
# 5a. Gather logs for analysis
kubectl logs -l app=api -n eldercare-prod --since=30m > api-logs-incident.txt
kubectl describe nodes > nodes-incident.txt

# 5b. Create incident report
# Use PagerDuty/Datadog to document:
# - Timeline of events
# - Root cause analysis
# - Actions taken
# - Prevention measures
```

---

## Database Performance Degradation Runbook

### Alert Details
- **Condition**: Database P95 query latency > 1 second
- **Impact**: API requests timeout, poor user experience
- **On-Call Escalation**: Page database DBA

### Step 1: Emergency Measures (1 minute)

```bash
# Kill long-running queries immediately
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE usename != 'postgres' AND query_start < now() - interval '30 seconds';"

# Drop unnecessary connections
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE application_name LIKE 'unused-%';"
```

### Step 2: Diagnose (5 minutes)

```bash
# Check active connections
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT datname, usename, count(*) as connections FROM pg_stat_activity GROUP BY datname, usename;"

# Check slow query log
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT query, calls, mean_time, max_time FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;"

# Check table sizes
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
   FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') 
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"

# Check missing indexes
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT schemaname, tablename, attname, n_distinct, correlation 
   FROM pg_stats WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"
```

### Step 3: Remediation

**If connection pool exhausted:**
```bash
# Restart application servers (recycles connections)
kubectl rollout restart deployment/api -n eldercare-prod

# Monitor connection recovery
kubectl exec -it postgres-0 -n eldercare-prod -- \
  watch -n 2 "psql -U postgres -d eldercare -c \
  'SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;'"
```

**If table bloat detected:**
```bash
# Run VACUUM on specific table
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "VACUUM ANALYZE table_name;"

# If still slow, do REINDEX
kubectl exec -it postgres-0 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "REINDEX TABLE table_name;"
```

**If replication lag detected:**
```bash
# Check replica status
kubectl exec -it postgres-1 -n eldercare-prod -- psql -U postgres -d eldercare -c \
  "SELECT now() - pg_last_wal_receive_lsn() AS replication_lag;"

# Promote replica if primary is down
# (This is manual failover - only if primary truly unavailable)
```

### Step 4: Monitor Recovery

```bash
# Watch query latency
kubectl port-forward -n eldercare-prod svc/prometheus 9090:9090 &
# Navigate to http://localhost:9090/graph
# Query: histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))
```

---

## Cache Crisis Runbook

### Alert Details
- **Condition**: Redis memory >85% or eviction rate high
- **Impact**: Cache misses increase, database load spikes
- **On-Call Escalation**: Page infrastructure team

### Step 1: Immediate Actions (2 minutes)

```bash
# Reduce TTL on non-critical caches
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli << 'EOF'
# Clear session cache entries > 30 mins old
EVAL "local keys = redis.call('KEYS', 'session:*'); \
      for i, key in ipairs(keys) do \
        if redis.call('TTL', key) > 1800 then redis.call('DEL', key) end \
      end \
      return #keys" 0

# Clear temporary caches
EVAL "local keys = redis.call('KEYS', 'temp:*'); \
      for i, key in ipairs(keys) do redis.call('DEL', key) end \
      return #keys" 0
EOF

# Or aggressive flush if critical
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli MEMORY PURGE
```

### Step 2: Assess Memory Usage

```bash
# Check memory breakdown
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli INFO memory

# Check key distribution
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli MEMORY DOCTOR

# Identify large keys
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli --bigkeys
```

### Step 3: Execute Solution

**Option A: Increase Redis memory**
```bash
# Update StatefulSet resource limits
kubectl patch statefulset redis -n eldercare-prod --type merge -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"redis","resources":{"limits":{"memory":"8Gi"}}}]}}}}'

# Restart pod to apply
kubectl delete pod redis-0 -n eldercare-prod
```

**Option B: Enable eviction policy**
```bash
# Set LRU eviction (if not already set)
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli \
  CONFIG SET maxmemory-policy allkeys-lru

# Make persistent
kubectl exec -it redis-0 -n eldercare-prod -- redis-cli \
  CONFIG REWRITE
```

**Option C: Scale Redis cluster**
```bash
# If using multi-node setup
kubectl scale statefulset redis --replicas=3 -n eldercare-prod
```

### Step 4: Verify

```bash
# Monitor eviction rate
kubectl exec -it redis-0 -n eldercare-prod -- \
  redis-cli INFO stats | grep evicted_keys

# Confirm memory under control
kubectl top pod redis-0 -n eldercare-prod
```

---

## Memory Leak Runbook

### Alert Details
- **Condition**: Steady memory increase without load change
- **Impact**: Pods eventually OOMKilled, service disruption
- **Timeline**: 24-48 hours from alert to critical

### Step 1: Confirm Memory Leak (5 minutes)

```bash
# Get memory trend for last hour
kubectl get pod api-xxx -n eldercare-prod \
  --watch=false -o json | jq '.status.containerStatuses[].state.running'

# Use Prometheus to see trend
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
# Query: container_memory_usage_bytes{pod="api-xxx"} (over 1 hour)
# Look for constant increase despite no load change
```

### Step 2: Identify Leaking Component (10 minutes)

```bash
# Get detailed memory stats
kubectl exec -it api-pod -n eldercare-prod -c api -- \
  python -c "import tracemalloc; tracemalloc.start(); \
  # Access problematic code path
  import gc; gc.collect(); \
  snapshot = tracemalloc.take_snapshot(); \
  top_stats = snapshot.statistics('lineno'); \
  for stat in top_stats[:10]: print(stat)"

# Or use memory_profiler
kubectl exec -it api-pod -n eldercare-prod -c api -- \
  python -m memory_profiler src/main.py

# Check for circular references
kubectl exec -it api-pod -n eldercare-prod -c api -- \
  python -c "import sys; sys.getsizeof(gc.get_objects())"
```

### Step 3: Immediate Mitigation

```bash
# Option 1: Increase memory limit (short-term)
kubectl set resources deployment api \
  -n eldercare-prod \
  --limits=memory=2Gi

# Option 2: Restart pods on schedule
# Add CronJob to restart pods at off-peak
kubectl apply -f - << 'EOF'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: restart-api
  namespace: eldercare-prod
spec:
  schedule: "2 2 * * *"  # 2:02 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kubectl
            image: bitnami/kubectl:latest
            command: ["kubectl", "rollout", "restart", "deployment/api", "-n", "eldercare-prod"]
          restartPolicy: OnFailure
EOF
```

### Step 4: Fix (Next sprint)

```bash
# Create data structure audit
# Identify:
# - Unbounded caches (implement LRU)
# - Unclosed connections (ensure proper cleanup)
# - Listener accumulation (unsubscribe on shutdown)
# - Large objects in scope (use generators/streaming)

# Add memory monitoring to CI/CD
# Run memory profiler on every merge request
pytest --profile=memory tests/
```

---

## Complete Platform Outage Runbook

### If everything is down (5 minutes)

```bash
# 1. Check Kubernetes cluster status
kubectl get nodes
kubectl get pod -A --sort-by=.metadata.creationTimestamp

# 2. Check service endpoints
kubectl get endpoints -A

# 3. Check ingress/load balancer
kubectl describe ingress -n eldercare-prod

# 4. Check DNS
nslookup eldr.care
nslookup api.eldr.care
```

### Recover in order:

1. **Database** (if down)
   ```bash
   kubectl rollout restart statefulset/postgres -n eldercare-prod
   # Wait for master election
   sleep 60
   ```

2. **Cache** (if down)
   ```bash
   kubectl rollout restart statefulset/redis -n eldercare-prod
   # Data in Redis is lost, that's OK (it's a cache)
   ```

3. **Application** (if crashed)
   ```bash
   kubectl rollout restart deployment/api -n eldercare-prod
   kubectl rollout restart deployment/web -n eldercare-prod
   kubectl rollout restart deployment/worker -n eldercare-prod
   ```

4. **Verify recovery**
   ```bash
   for i in {1..30}; do
     curl -f https://api.eldr.care/api/v1/health && \
     echo "✓ API is healthy" && break
     echo "Waiting... [$i/30]"; sleep 5
   done
   ```

---

## On-Call Handoff Checklist

At end of shift, confirm:
- [ ] No active alerts or incidents
- [ ] All services at healthy status
- [ ] Error rate normal
- [ ] Database replication is in sync
- [ ] Backups completed successfully
- [ ] No pending security issues
- [ ] Document any emerging issues for next on-call

---

**Last Updated**: 2024-01-10
**Maintained By**: DevOps & Platform Team
**Review Cycle**: Quarterly or after each major incident
