# Horizontal Autoscaling Rules

This document defines production autoscaling guardrails for API, workers, Redis, and database read traffic.

## 1. API Autoscaling (Kubernetes + ECS)

Kubernetes (`infra/kubernetes/02-api-deployment.yaml`):
- Min replicas: 3
- Max replicas: 10
- Scale-out policy: up to 100% per 60s, 60s stabilization
- Scale-in policy: 25% per 60s, 300s stabilization
- Targets:
  - CPU average utilization: 70%
  - Memory average utilization: 80%

ECS (`infra/cloudformation/ecs-cluster.yaml`):
- Min tasks: 3
- Max tasks: 10
- Target tracking policy:
  - ECSServiceAverageCPUUtilization target: 70
  - Scale-out cooldown: 60s
  - Scale-in cooldown: 300s

## 2. Worker Autoscaling (Kubernetes + ECS)

Kubernetes (`infra/kubernetes/05-worker-scheduler.yaml`):
- Min replicas: 3
- Max replicas: 15
- Scale-out policy: up to 100% per 60s, 60s stabilization
- Scale-in policy: 20% per 60s, 300s stabilization
- Targets:
  - CPU average utilization: 70%
  - Memory average utilization: 80%

ECS (`infra/cloudformation/ecs-cluster.yaml`):
- Min tasks: 3
- Max tasks: 15
- Target tracking policy:
  - ECSServiceAverageCPUUtilization target: 70
  - Scale-out cooldown: 60s
  - Scale-in cooldown: 300s

## 3. Redis Horizontal Strategy

CloudFormation (`infra/cloudformation/network-rds-redis.yaml`):
- Parameterized replica count through `RedisReplicaCount`.
- Allowed range: 2 to 6 cache nodes.
- Uses ElastiCache replication group with Multi-AZ and automatic failover.

Operational rule:
- Start at 2 nodes in staging.
- Increase to 3-4 nodes if p95 Redis latency or command timeout alerts sustain for 15 minutes.
- Increase to 5-6 nodes for prolonged write bursts or queue congestion events.

## 4. DB Read Strategy

CloudFormation (`infra/cloudformation/network-rds-redis.yaml`):
- Optional read replica via `EnableDBReadReplica` (default: true).
- Exposes `DBReadEndpoint` output; falls back to primary when disabled.

Runtime wiring:
- `.env.example` defines `DATABASE_READ_URL`.
- API settings include `database_read_url`.
- ECS API and worker tasks inject `DATABASE_READ_URL` from `DBReadEndpoint`.

Operational rule:
- Route heavy list/search/reporting queries to `DATABASE_READ_URL`.
- Keep writes, transactional checks, and strongly consistent reads on `DATABASE_URL`.

## 5. Rollout Verification Commands

Kubernetes:
- `kubectl get hpa -n eldercare-prod`
- `kubectl describe hpa api-hpa -n eldercare-prod`
- `kubectl describe hpa worker-hpa -n eldercare-prod`

AWS:
- `aws application-autoscaling describe-scalable-targets --service-namespace ecs`
- `aws application-autoscaling describe-scaling-policies --service-namespace ecs`
- `aws rds describe-db-instances --db-instance-identifier production-postgres-read-1`
- `aws elasticache describe-replication-groups --replication-group-id production-redis`
