# Deployment Strategies - Blue/Green & Canary

## Overview

This guide documents production deployment strategies for the Eldercare platform, covering blue/green deployments and canary releases across Docker Compose, Kubernetes, and AWS ECS environments.

## Table of Contents

1. [Blue/Green Deployment Strategy](#bluegreen-deployment-strategy)
2. [Canary Deployment Strategy](#canary-deployment-strategy)
3. [Docker Compose Blue/Green](#docker-compose-bluegreen)
4. [Kubernetes Blue/Green](#kubernetes-bluegreen)
5. [AWS ECS Blue/Green](#aws-ecs-bluegreen)
6. [Rollback Procedures](#rollback-procedures)
7. [Traffic Shifting](#traffic-shifting)

---

## Blue/Green Deployment Strategy

### Concept

Blue/green deployments maintain two identical production environments:
- **Blue**: Current production version (serving traffic)
- **Green**: New version (staged and validated)

Traffic switches entirely from blue to green after health verification. If issues occur, traffic instantly reverts to blue.

### Prerequisites

- Two separate application stacks identically configured
- Load balancer capable of instant traffic rerouting
- Database with read-write replicas or transaction logs for rollback
- Automated health checks on both stacks

### Advantages

✅ True zero-downtime deployments
✅ Instant rollback capability
✅ Full version testing before traffic shift
✅ Simple to understand and operate

### Disadvantages

❌ Double infrastructure cost
❌ Database migration coordination required
❌ State synchronization between stacks

---

## Canary Deployment Strategy

### Concept

Canary deployments gradually shift traffic to new versions:

1. Route small percentage (5-10%) traffic to new version (canary)
2. Monitor error rates, latency, resource usage
3. If metrics healthy, increment traffic (25% → 50% → 100%)
4. If metrics exceed threshold, halt and rollback

### Prerequisites

- Load balancer with weighted traffic routing
- Real-time metrics collection and alerting
- Ability to reach new version endpoints during canary period
- Automated rollback triggers

### Advantages

✅ Gradual risk reduction
✅ Early issue detection with minimal impact
✅ Single infrastructure footprint
✅ Natural A/B testing opportunity

### Disadvantages

❌ Longer deployment duration (20-30 minutes)
❌ Complex traffic routing configuration
❌ Requires sophisticated monitoring

---

## Docker Compose Blue/Green

### Setup

```bash
# Blue environment
docker-compose -f docker-compose.prod.yml \
  -p eldercare-blue up -d

# Green environment (separate network)
docker-compose -f docker-compose.prod.yml \
  -p eldercare-green up -d
```

### Deployment Procedure

```bash
#!/bin/bash
set -e

ENV_NAME="eldercare-green"
PREVIOUS_ENV="eldercare-blue"

# 1. Stop old monitoring
docker-compose -p $PREVIOUS_ENV exec nginx \
  curl -X POST http://localhost:8081/metrics/stop || true

# 2. Build and start green services
echo "Building green environment..."
docker-compose -f docker-compose.prod.yml \
  -p $ENV_NAME build --no-cache

echo "Starting green environment..."
docker-compose -f docker-compose.prod.yml \
  -p $ENV_NAME up -d

# 3. Wait for services to be ready
sleep 30

# 4. Health checks on green
echo "Verifying green environment health..."
for i in {1..10}; do
  if docker-compose -p $ENV_NAME exec -T api \
    curl -f http://localhost:8000/api/v1/health; then
    echo "API is healthy"
    break
  fi
  sleep 5
done

# 5. Run smoke tests
echo "Running smoke tests..."
docker-compose -p $ENV_NAME exec -T api \
  python -m pytest tests/smoke/ -v

# 6. Update Nginx to route to green
docker-compose -p $ENV_NAME exec -T nginx \
  curl -X POST http://localhost:8081/traffic/switch?target=green

# 7. Monitor green (5 minutes)
echo "Monitoring green environment for 5 minutes..."
for i in {1..60}; do
  ERROR_RATE=$(docker-compose -p $ENV_NAME exec -T api \
    curl -s http://localhost:8000/metrics | grep http_errors_total | tail -1)
  echo "[$i/60] Error rate: $ERROR_RATE"
  sleep 5
done

# 8. If all good, clean up blue
echo "Promotion to green complete. Keeping blue as rollback..."
docker-compose -p $PREVIOUS_ENV stop

# Alternative: revert traffic
# docker-compose -p $ENV_NAME exec -T nginx \
#   curl -X POST http://localhost:8081/traffic/switch?target=blue
```

### Nginx Traffic Switching Configuration

```nginx
# apps/nginx/conf.d/traffic.conf

# Blue backend
upstream blue_backend {
    server api-blue:8000;
}

# Green backend
upstream green_backend {
    server api-green:8000;
}

# Current active upstream
set $active_backend "blue_backend";

server {
    listen 8081;
    
    # Endpoint to switch traffic
    location /traffic/switch {
        default_type application/json;
        
        if ($arg_target = "blue") {
            set $active_backend "blue_backend";
            return 200 '{"status":"switched to blue"}';
        }
        
        if ($arg_target = "green") {
            set $active_backend "green_backend";
            return 200 '{"status":"switched to green"}';
        }
        
        return 400 '{"error":"invalid target"}';
    }
}
```

---

## Kubernetes Blue/Green

### Setup with Helm

```bash
# Deploy blue version
helm install eldercare-blue ./infra/helm/eldercare \
  --namespace eldercare-prod \
  --values infra/helm/values-blue.yaml \
  --set appVersion=$(git rev-parse --short HEAD)

# Deploy green version (high replicas for canary)
helm install eldercare-green ./infra/helm/eldercare \
  --namespace eldercare-prod \
  --values infra/helm/values-green.yaml \
  --set appVersion=$(git describe --tags || git rev-parse --short HEAD)
```

### Create Separate Deployments

```yaml
# infra/kubernetes/blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-blue
  namespace: eldercare-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
      version: blue
  template:
    metadata:
      labels:
        app: api
        version: blue
    spec:
      containers:
      - name: api
        image: ghcr.io/eldercare/api:stable
        # ... rest of spec
---
# infra/kubernetes/green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-green
  namespace: eldercare-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
      version: green
  template:
    metadata:
      labels:
        app: api
        version: green
    spec:
      containers:
      - name: api
        image: ghcr.io/eldercare/api:latest
        # ... rest of spec
```

### Switch Traffic via Ingress

```yaml
# infra/kubernetes/ingress-blue-green.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: eldercare-prod
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/canary: "false"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.eldr.care
    secretName: api-tls
  rules:
  - host: api.eldr.care
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-blue  # Switch to api-green for promotion
            port:
              number: 8000
```

### Script for Blue/Green Switch

```bash
#!/bin/bash
set -e

NAMESPACE="eldercare-prod"
NEW_VERSION="api-green"
OLD_VERSION="api-blue"

# 1. Health check green
echo "Health checking $NEW_VERSION..."
kubectl wait --for=condition=ready pod \
  -l app=api,version=green \
  -n $NAMESPACE \
  --timeout=5m

# 2. Run integration tests against green service
kubectl run test-pod --rm -it \
  --image=python:3.13-alpine \
  --restart=Never \
  --env="TEST_URL=http://api-green:8000" \
  -n $NAMESPACE \
  -- pytest /tests/integration -v

# 3. Get current traffic
CURRENT=$(kubectl get ingress api-ingress -n $NAMESPACE \
  -o jsonpath='{.spec.rules[0].http.paths[0].backend.service.name}')
echo "Current traffic: $CURRENT"

# 4. Patch ingress to switch traffic
kubectl patch ingress api-ingress -n $NAMESPACE \
  -p "{\"spec\":{\"rules\":[{\"host\":\"api.eldr.care\",\"http\":{\"paths\":[{\"path\":\"/\",\"pathType\":\"Prefix\",\"backend\":{\"service\":{\"name\":\"$NEW_VERSION\",\"port\":{\"number\":8000}}}}]}}]}}"

echo "Traffic switched to $NEW_VERSION"

# 5. Monitor for 5 minutes
echo "Monitoring new version..."
for i in {1..30}; do
  ERRORS=$(kubectl logs -l app=api,version=green -n $NAMESPACE \
    --since=1m 2>/dev/null | grep ERROR | wc -l || true)
  echo "[$i/30] Errors in last 1m: $ERRORS"
  sleep 10
done

# 6. Rollback if needed
if [ $ERRORS -gt 5 ]; then
  echo "ERROR THRESHOLD EXCEEDED - Rolling back"
  kubectl patch ingress api-ingress -n $NAMESPACE \
    -p "{\"spec\":{\"rules\":[{\"host\":\"api.eldr.care\",\"http\":{\"paths\":[{\"path\":\"/\",\"pathType\":\"Prefix\",\"backend\":{\"service\":{\"name\":\"$OLD_VERSION\",\"port\":{\"number\":8000}}}}]}}]}}"
  exit 1
fi

echo "✓ Deployment successful"
```

---

## AWS ECS Blue/Green

### Setup with CloudFormation

ECS natively supports blue/green deployments through CodeDeploy integration.

```yaml
# Enable in service definition
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  APIService:
    Type: AWS::ECS::Service
    Properties:
      DeploymentController:
        Type: BLUE_GREEN
      DeploymentConfiguration:
        MaximumPercent: 200
        MinimumHealthyPercent: 100
        DeploymentCircuitBreaker:
          Enable: true
          Rollback: true
      LoadBalancers:
      - ContainerName: api
        ContainerPort: 8000
        TargetGroupArn: !Ref APITargetGroup
      NetworkConfiguration:
        AwsvpcConfiguration:
          AssignPublicIp: DISABLED
          Subnets:
          - !Ref PrivateSubnet1
          - !Ref PrivateSubnet2
          SecurityGroups:
          - !Ref SecurityGroup
```

### Deployment Script

```bash
#!/bin/bash
set -e

CLUSTER="prod-cluster"
SERVICE="prod-api-service"
REGION="us-east-1"

# 1. Get current task definition ARN
CURRENT_TASK=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region $REGION \
  --query 'services[0].taskDefinition' \
  --output text)

# 2. Register new task definition
NEW_TASK=$(aws ecs register-task-definition \
  --family prod-api-task \
  --container-definitions file://task-def.json \
  --region $REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "New task definition: $NEW_TASK"

# 3. Update service (triggers blue/green)
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --task-definition $NEW_TASK \
  --region $REGION

# 4. Wait for deployment
echo "Waiting for deployment..."
aws ecs wait services-stable \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region $REGION

# 5. Verify target health
ALB_ARN=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --region $REGION \
  --query 'services[0].loadBalancers[0].targetGroupArn' \
  --output text)

echo "Checking target health..."
HEALTHY=$(aws elbv2 describe-target-health \
  --target-group-arn $ALB_ARN \
  --region $REGION \
  --query 'length(TargetHealthDescriptions[?TargetHealth.State==`healthy`])' \
  --output text)

TOTAL=$(aws elbv2 describe-target-health \
  --target-group-arn $ALB_ARN \
  --region $REGION \
  --query 'length(TargetHealthDescriptions)' \
  --output text)

echo "Healthy targets: $HEALTHY/$TOTAL"

if [ "$HEALTHY" -lt 3 ]; then
  echo "ERROR: Not enough healthy targets, rolling back..."
  exit 1
fi

echo "✓ Deployment successful"
```

---

## AWS ECS Canary Deployment

### Step Function for Canary Orchestration

```json
{
  "Comment": "Canary deployment with gradual traffic shift",
  "StartAt": "StartCanary",
  "States": {
    "StartCanary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:start-canary",
      "Parameters": {
        "service": "prod-api-service",
        "traffic_percent": 10
      },
      "Next": "WaitCanary10"
    },
    "WaitCanary10": {
      "Type": "Wait",
      "Seconds": 300,
      "Next": "CheckCanary10"
    },
    "CheckCanary10": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:check-metrics",
      "Parameters": {
        "service": "prod-api-service",
        "threshold": 2
      },
      "Next": "CanaryHealthy10?",
      "Catch": [{
        "ErrorEquals": ["MetricsThresholdExceeded"],
        "Next": "RollbackCanary"
      }]
    },
    "CanaryHealthy10?": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.healthy",
        "BooleanEquals": true,
        "Next": "IncrementCanary50"
      }],
      "Default": "RollbackCanary"
    },
    "IncrementCanary50": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:update-traffic",
      "Parameters": {
        "service": "prod-api-service",
        "traffic_percent": 50
      },
      "Next": "WaitCanary50"
    },
    "WaitCanary50": {
      "Type": "Wait",
      "Seconds": 300,
      "Next": "CheckCanary50"
    },
    "CheckCanary50": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:check-metrics",
      "Next": "CanaryHealthy50?"
    },
    "CanaryHealthy50?": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.healthy",
        "BooleanEquals": true,
        "Next": "PromoteCanary"
      }],
      "Default": "RollbackCanary"
    },
    "PromoteCanary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:promote-canary",
      "Parameters": {
        "service": "prod-api-service",
        "traffic_percent": 100
      },
      "Next": "Success"
    },
    "RollbackCanary": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789:function:rollback",
      "Parameters": {
        "service": "prod-api-service"
      },
      "Next": "Failed"
    },
    "Success": {
      "Type": "Succeed"
    },
    "Failed": {
      "Type": "Fail",
      "Error": "CanaryDeploymentFailed",
      "Cause": "Metrics exceeded thresholds"
    }
  }
}
```

---

## Rollback Procedures

### Docker Compose Rollback

```bash
#!/bin/bash
# Immediate reversal to previous environment

docker-compose -p eldercare-blue start
docker-compose -p eldercare-green stop

# Or with version tags
docker-compose -p eldercare \
  -f docker-compose.prod.yml \
  up -d --no-build
```

### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/api -n eldercare-prod

# Rollback to previous revision
kubectl rollout undo deployment/api -n eldercare-prod

# Rollback to specific revision
kubectl rollout undo deployment/api -n eldercare-prod --to-revision=2

# Monitor rollback
kubectl rollout status deployment/api -n eldercare-prod -w
```

### ECS Rollback

```bash
# Automatic rollback (circuit breaker)
# Already enabled in task definition via deploymentCircuitBreaker

# Manual rollback
aws ecs update-service \
  --cluster prod-cluster \
  --service prod-api-service \
  --force-new-deployment \
  --task-definition prod-api-task:PREVIOUS_REVISION
```

---

## Traffic Shifting Patterns

### Linear (10% every 5 minutes)

```
Timeline: 0m   5m   10m  15m  20m  25m
Traffic:  10% → 20% → 30% → 40% → 50% → 100%
```

Best for: Low-risk changes with proven CI/CD

### Canary (5% for extended period)

```
Timeline: 0m   30m  60m  90m
Traffic:  5% → 10% → 50% → 100%
```

Best for: High-risk changes, new features

### Blue/Green (Instant)

```
Timeline: 0m → SWITCH → ∞
Traffic:  Blue (100%) → Green (100%)
```

Best for: Critical hotfixes, known issue resolutions

---

## Monitoring During Deployment

### Key Metrics to Watch

- **Error Rate**: Should remain < 1% during deployment
- **P99 Latency**: Should not increase > 20%
- **CPU Utilization**: Should stay < 80%
- **Memory Usage**: Should stay < 85%
- **Active Connections**: Track for unusual patterns
- **Database Connections**: Monitor pool utilization

### Example Metrics Query (CloudWatch)

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=TargetGroup,Value=prod-api-tg \
  --start-time $(date -d '5 minutes ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Maximum
```

### SLO Targets During Deployment

| Metric | Standard | During Deployment |
|--------|----------|-------------------|
| Error Rate | < 0.1% | < 1% |
| P99 Latency | < 500ms | < 600ms |
| Availability | 99.95% | 99.9% |
| CPU | < 70% | < 80% |
| Memory | < 75% | < 85% |

---

## Best Practices

✅ **Always test deployments in staging first**
✅ **Have a rollback plan before deploying**
✅ **Monitor for 5-10 minutes after promotion**
✅ **Use blue/green for critical services**
✅ **Use canary for experimental features**
✅ **Automate traffic shifting where possible**
✅ **Document all manual intervention steps**
✅ **Maintain database schema compatibility**
✅ **Coordinate with on-call team before deployment**
✅ **Post-deployment: Archive logs and metrics**

---

## Troubleshooting

### Deployment Hangs on Healthy Check

```bash
# Check service events
kubectl describe svc api -n eldercare-prod

# View pod logs
kubectl logs -l app=api,version=green -n eldercare-prod --tail=50

# Check resource availability
kubectl top nodes
kubectl top pod -n eldercare-prod
```

### Traffic Still Going to Old Version

```bash
# Verify ingress/service configuration
kubectl get ingress -n eldercare-prod -o yaml

# Check load balancer target groups
aws elbv2 describe-target-health \
  --target-group-arn <tg-arn>

# Check route53 DNS
nslookup api.eldr.care
```

### Database Migrations Failed

See MIGRATION_RUNBOOK.md for detailed procedures.

---

**Last Updated**: 2024-01-10
**Maintained By**: DevOps Team
**Review Cycle**: Quarterly
