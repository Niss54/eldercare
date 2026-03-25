# Deployment Guide - Eldercare Platform

This guide covers deploying the Eldercare platform across development, staging, and production environments.

## Quick Start - Local Development

### Prerequisites
- Docker and Docker Compose (v1.29+)
- Python 3.13
- Node.js 20+

### Setup

1. **Clone the repository and enter the directory:**
```bash
cd eldercare
```

2. **Create environment file:**
```bash
cp .env.example .env
# Edit .env with your local configuration
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Initialize database:**
```bash
docker-compose exec api alembic upgrade head
```

5. **Access the application:**
- API: http://localhost:8000
- Web: http://localhost:3000
- MinIO Console: http://localhost:9001
- Health Check: http://localhost/health

### Verify Services

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest
```

## Staging Deployment

### Setup

1. **Build images:**
```bash
docker-compose -f docker-compose.staging.yml build
```

2. **Create staging environment:**
```bash
cp .env.example .env.staging
# Edit .env.staging with staging configuration
```

3. **Deploy:**
```bash
docker-compose -f docker-compose.staging.yml up -d
```

4. **Run migrations:**
```bash
docker-compose -f docker-compose.staging.yml exec api alembic upgrade head
```

### Monitoring Staging

```bash
# Logs
docker-compose -f docker-compose.staging.yml logs -f api

# Database backup
docker-compose -f docker-compose.staging.yml exec postgres pg_dump -U postgres eldercare > backup.sql

# Health checks
curl https://api.staging.eldr.care/api/v1/health
curl https://staging.eldr.care
```

## Production Deployment

### Prerequisites
- Kubernetes cluster (EKS, AKS, or self-managed)
- Helm 3+
- kubectl configured
- AWS or respective cloud CLI configured
- Images pushed to container registry

### Option 1: Docker Compose (Single Host)

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Verify health
curl http://localhost/api/v1/health
```

### Option 2: Kubernetes with Helm

1. **Install prerequisites:**
```bash
# Install nginx-ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx

# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager --set installCRDs=true
```

2. **Deploy using Helm:**
```bash
# Create secret for credentials
kubectl create secret generic eldercare-secrets \
  --from-literal=DATABASE_URL=$DATABASE_URL \
  --from-literal=JWT_SECRET_KEY=$JWT_SECRET_KEY \
  -n eldercare-prod

# Install Helm chart
helm install eldercare ./infra/helm/eldercare \
  -n eldercare-prod \
  -f ./infra/helm/eldercare/values-prod.yaml
```

3. **Verify deployment:**
```bash
# Check pods
kubectl get pods -n eldercare-prod

# Check services
kubectl get services -n eldercare-prod

# Check ingress
kubectl get ingress -n eldercare-prod

# Watch deployment progress
kubectl rollout status deployment/api -n eldercare-prod
```

### Option 3: Manual Kubernetes Manifests

```bash
# Create namespace
kubectl create namespace eldercare-prod

# Apply manifests
kubectl apply -f infra/kubernetes/00-namespaces.yaml
kubectl apply -f infra/kubernetes/01-configmaps.yaml
kubectl apply -f infra/kubernetes/02-api-deployment.yaml
kubectl apply -f infra/kubernetes/03-web-deployment.yaml
kubectl apply -f infra/kubernetes/04-postgres-statefulset.yaml
kubectl apply -f infra/kubernetes/05-worker-scheduler.yaml
kubectl apply -f infra/kubernetes/06-rbac.yaml
kubectl apply -f infra/kubernetes/07-ingress.yaml

# Verify
kubectl get all -n eldercare-prod
```

## Database Migrations

### Development
```bash
# Create migration
docker-compose exec api alembic revision --autogenerate -m "Add new table"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback
docker-compose exec api alembic downgrade -1
```

### Production
```bash
# Backup database
kubectl exec -it postgres-0 -n eldercare-prod -- \
  pg_dump -U postgres eldercare > backup.sql

# Apply migrations
kubectl exec -it api-0 -n eldercare-prod -- \
  alembic upgrade head

# Verify health
kubectl exec -it api-0 -n eldercare-prod -- curl localhost:8000/api/v1/health
```

## Backup and Recovery

### Backup Database
```bash
# Docker Compose
docker-compose exec postgres pg_dump -U postgres eldercare > backup.sql

# Kubernetes
kubectl exec -it postgres-0 -n eldercare-prod -- \
  pg_dump -U postgres eldercare > backup.sql
```

### Restore Database
```bash
# Docker Compose
docker-compose exec -T postgres psql -U postgres eldercare < backup.sql

# Kubernetes
kubectl exec -i postgres-0 -n eldercare-prod -- \
  psql -U postgres eldercare < backup.sql
```

### Backup S3 Objects
```bash
# List buckets
aws s3 ls --endpoint-url http://minio:9000

# Sync to AWS
aws s3 sync s3://eldercare . --endpoint-url http://minio:9000
```

## Scaling

### Docker Compose
```bash
# Scale workers
docker-compose up -d --scale worker=5
```

### Kubernetes
```bash
# Manual scaling
kubectl scale deployment/worker --replicas=5 -n eldercare-prod

# HPA will auto-scale based on metrics:
# CPU > 70% → scale up
# Memory > 80% → scale up
kubectl get hpa -n eldercare-prod
```

## Monitoring and Logs

### Docker Compose
```bash
# View logs
docker-compose logs -f api

# Check resource usage
docker stats

# Inspect container
docker exec -it eldercare-api bash
```

### Kubernetes
```bash
# Logs
kubectl logs deployment/api -n eldercare-prod -f

# Resource usage
kubectl top nodes
kubectl top pods -n eldercare-prod

# Describe pod
kubectl describe pod <pod-name> -n eldercare-prod

# Port forward
kubectl port-forward svc/api 8000:8000 -n eldercare-prod
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs <service>

# Check configuration
docker-compose config

# Verify health
curl http://localhost:8000/health
```

### Database connection issues
```bash
# Test database
docker-compose exec api psql $DATABASE_URL -c "SELECT 1"

# Check environment variables
docker-compose exec api env | grep DATABASE
```

### Memory issues
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose
# Edit service resources section

# Kubernetes: check node resources
kubectl describe node <node-name>
```

## Rolling Updates

### Docker Compose
```bash
# Update image and restart
docker-compose up -d --no-deps --build api
```

### Kubernetes
```bash
# Update image
kubectl set image deployment/api api=eldercare-api:v1.1.0 -n eldercare-prod

# Monitor rollout
kubectl rollout status deployment/api -n eldercare-prod

# Rollback if needed
kubectl rollout undo deployment/api -n eldercare-prod
```

## Health Checks

### Endpoint Status
```bash
# API health
curl http://api:8000/api/v1/health

# Web health
curl http://web:3000

# PostgreSQL ready
docker-compose exec postgres pg_isready -U postgres

# Redis ping
docker-compose exec redis redis-cli ping
```

## Security

### Access Control
```bash
# Configure network policies (Kubernetes)
kubectl apply -f infra/kubernetes/network-policies.yaml

# Setup RBAC
kubectl apply -f infra/kubernetes/06-rbac.yaml

# Enable Pod Security Policy
kubectl apply -f infra/kubernetes/pod-security-policy.yaml
```

### Secrets Management
```bash
# Create secrets
kubectl create secret generic eldercare-secrets \
  --from-literal=JWT_SECRET_KEY=$JWT_SECRET_KEY \
  -n eldercare-prod

# Rotate secrets (recreate) 
kubectl delete secret eldercare-secrets -n eldercare-prod
kubectl create secret generic eldercare-secrets \
  --from-literal=JWT_SECRET_KEY=$NEW_KEY \
  -n eldercare-prod

# Restart pods to pick up new secrets
kubectl rollout restart deployment/api -n eldercare-prod
```

## Compliance and Auditing

### Enable audit logging
```bash
# Check API audit logs
kubectl logs deployment/api -n eldercare-prod | grep "audit"

# PostgreSQL query logging
docker-compose exec postgres psql -U postgres -d eldercare -c "SELECT * FROM pg_stat_statements;"
```

### Data retention
```bash
# Clean old audit logs (30 day retention)
docker-compose exec api python -c "from src.modules.audit_logging.retention import cleanup; cleanup.execute_retention(days=30)"
```

## Disaster Recovery

### Point-in-time recovery
```bash
# Enable WAL archiving in PostgreSQL
# Backup WAL files regularly
# Restore to specific point in time

docker-compose exec postgres pg_basebackup -D /backup -Ft
```

### Cross-region replication
```bash
# Setup replication to backup cluster
# Test failover regularly
# Document RTO/RPO targets
```

See other documentation for detailed AWS CloudFormation, Terraform IaC, and GitHub Actions CI/CD setup.
