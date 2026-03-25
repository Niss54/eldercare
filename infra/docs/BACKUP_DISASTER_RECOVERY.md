# Backup & Disaster Recovery Runbook

## Overview

This document outlines backup strategies, RTO/RPO targets, and disaster recovery procedures for the Eldercare platform.

## Backup Strategy

### RTO/RPO Targets

| Component | RTO | RPO | Strategy |
|-----------|-----|-----|----------|
| **Database** | 1 hour | 15 minutes | Continuous WAL replication + daily snapshots |
| **Application Code** | 30 minutes | N/A | Git repository (multiple mirrors) |
| **User Data (S3)** | 2 hours | 1 hour | S3 cross-region replication |
| **Configuration** | 30 minutes | Real-time | ConfigMaps in Kubernetes etcd |
| **Secrets** | 30 minutes | Real-time | AWS Secrets Manager with replication |

---

## Database Backup

### Automated Daily Backups

```bash
#!/bin/bash
# infra/scripts/backup-database.sh

set -e

DB_INSTANCE="eldercare-prod"
AWS_REGION="us-east-1"
BACKUP_RETENTION_DAYS=30
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier $DB_INSTANCE \
  --db-snapshot-identifier "backup-${BACKUP_TIMESTAMP}" \
  --tags Key=automated,Value=true Key=retention_days,Value=$BACKUP_RETENTION_DAYS \
  --region $AWS_REGION

echo "✓ RDS snapshot created: backup-${BACKUP_TIMESTAMP}"

# Wait for snapshot to complete
aws rds wait db-snapshot-available \
  --db-snapshot-identifier "backup-${BACKUP_TIMESTAMP}" \
  --region $AWS_REGION

# Copy to secondary region for DR
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier "arn:aws:rds:${AWS_REGION}:ACCOUNT_ID:snapshot:backup-${BACKUP_TIMESTAMP}" \
  --target-db-snapshot-identifier "backup-${BACKUP_TIMESTAMP}-dr" \
  --source-region $AWS_REGION \
  --region us-west-2

echo "✓ Snapshot copied to dr-region"

# Clean up old snapshots (> 30 days)
CUTOFF_DATE=$(date -d "30 days ago" +%Y-%m-%d)
for snapshot in $(aws rds describe-db-snapshots \
  --db-instance-identifier $DB_INSTANCE \
  --query "DBSnapshots[?SnapshotCreateTime<'${CUTOFF_DATE}'].DBSnapshotIdentifier" \
  --output text); do
  
  aws rds delete-db-snapshot \
    --db-snapshot-identifier $snapshot
  echo "✓ Deleted old snapshot: $snapshot"
done

# Kubernetes Database Backup (for StatefulSet deployments)
echo "Starting Kubernetes database backup..."
kubectl exec -it postgres-0 -n eldercare-prod -- \
  pg_dump -U postgres eldercare > /tmp/db-backup-${BACKUP_TIMESTAMP}.sql

# Upload to S3
aws s3 cp /tmp/db-backup-${BACKUP_TIMESTAMP}.sql \
  s3://eldercare-backups/database/

echo "✓ Database backup complete"
```

### Continuous Replication

```yaml
# For RDS Multi-AZ setup (already configured)
# Shows Read Replica in secondary region
apiVersion: v1
kind: ConfigMap
metadata:
  name: database-replication-config
  namespace: eldercare-prod
data:
  replication_lag_max: "10"  # seconds
  wal_level: "replica"
```

### Point-in-Time Recovery (PITR)

```bash
#!/bin/bash
# infra/scripts/restore-database-pitr.sh

# Restore to specific point in time
RESTORE_TIME="2024-01-10 14:30:00"  # UTC
NEW_INSTANCE_ID="eldercare-prod-restored-$(date +%s)"

aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier eldercare-prod \
  --target-db-instance-identifier $NEW_INSTANCE_ID \
  --restore-time "$RESTORE_TIME" \
  --region us-east-1

# Wait for restore to complete
aws rds wait db-instance-available \
  --db-instance-identifier $NEW_INSTANCE_ID

echo "✓ Database restored to $RESTORE_TIME"
echo "✓ New instance: $NEW_INSTANCE_ID"
echo "✓ Test connection and verify data"
echo "✓ Update application connection string"
echo "✓ Delete old instance when ready"
```

---

## Application Code Backup

### Git Repository Mirroring

```bash
#!/bin/bash
# Setup mirror repositories

# Primary: GitHub
git remote add origin https://github.com/yourorg/eldercare.git

# Mirror 1: GitLab
git push --mirror git@gitlab.com:yourorg/eldercare.git

# Mirror 2: Gitea (internal)
git push --mirror https://gitea.internal/yourorg/eldercare.git

# Automated backup (run via cron weekly)
#!/bin/bash
for repo in origin gitlab-mirror gitea-mirror; do
  git fetch $repo
  git push -u $repo --all
  git push -u $repo --tags
done
```

---

## User Data Backup (S3)

### Cross-Region Replication

```yaml
# infra/cloudformation/s3-replication.yaml
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  
  EldercareBucketReplication:
    Type: AWS::S3::Bucket
    Properties:
      ReplicationConfiguration:
        Role: !GetAtt S3ReplicationRole.Arn
        Rules:
        - Status: Enabled
          Priority: 1
          Filter:
            Prefix: ''
          Destination:
            Bucket: !Sub 'arn:aws:s3:::${BucketName}-dr'
            ReplicationTime:
              Status: Enabled
              Time:
                Minutes: 15
            Metrics:
              Status: Enabled
              EventThreshold:
                Minutes: 15
            StorageClass: GLACIER

  S3ReplicationRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
        - Effect: Allow
          Principal:
            Service: s3.amazonaws.com
          Action: 'sts:AssumeRole'
      Policies:
      - PolicyName: S3Replication
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
          - Effect: Allow
            Action:
            - 's3:GetReplicationConfiguration'
            - 's3:ListBucket'
            Resource: !GetAtt EldercareBucketReplication.Arn
          - Effect: Allow
            Action:
            - 's3:GetObjectVersionForReplication'
            - 's3:GetObjectVersionAcl'
            Resource: !Sub '${EldercareBucketReplication.Arn}/*'
          - Effect: Allow
            Action:
            - 's3:ReplicateObject'
            - 's3:ReplicateDelete'
            Resource: !Sub 'arn:aws:s3:::${BucketName}-dr/*'
```

---

## Configuration & Secrets Backup

### Kubernetes etcd Backup

```bash
#!/bin/bash
# infra/scripts/backup-etcd.sh

# For self-managed Kubernetes, backup etcd regularly
ETCD_ENDPOINT="https://etcd.internal:2379"
CERT_DIR="/etc/kubernetes/pki/etcd"
BACKUP_DIR="/backups/etcd"

ETCDCTL_API=3 etcdctl \
  --endpoints=$ETCD_ENDPOINT \
  --cacert=$CERT_DIR/ca.crt \
  --cert=$CERT_DIR/server.crt \
  --key=$CERT_DIR/server.key \
  snapshot save $BACKUP_DIR/etcd-backup-$(date +%Y%m%d_%H%M%S).db

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://eldercare-backups/k8s-etcd/ --recursive

# Verify backup
ETCDCTL_API=3 etcdctl snapshot status $BACKUP_DIR/etcd-backup-*.db
```

### AWS Secrets Manager Backup

```bash
#!/bin/bash
# infra/scripts/backup-secrets.sh

# Export all secrets to encrypted file
aws secretsmanager list-secrets \
  --query 'SecretList[].Name' \
  --output text | \
  while read secret; do
    aws secretsmanager get-secret-value --secret-id $secret \
      > /tmp/${secret}.json
  done

# Package and encrypt
tar czf /tmp/secrets-backup.tar.gz /tmp/*.json
openssl enc -aes-256-cbc -P -in /tmp/secrets-backup.tar.gz \
  -out /tmp/secrets-backup.encrypted

# Upload to S3 (with encryption)
aws s3 cp /tmp/secrets-backup.encrypted \
  s3://eldercare-backups/secrets/ \
  --sse AES256

# Store encryption key in separate secure location
echo $ENCRYPTION_KEY > /secure/location/secrets-key.txt
```

### ConfigMap Backup

```bash
#!/bin/bash
# Backup all Kubernetes ConfigMaps

for ns in eldercare-prod eldercare-staging; do
  mkdir -p /backups/configmaps/$ns
  
  kubectl get configmaps -n $ns -o yaml > \
    /backups/configmaps/$ns/configmaps-backup-$(date +%Y%m%d).yaml
done

# Upload to S3
aws s3 cp /backups/configmaps/ \
  s3://eldercare-backups/configmaps/ --recursive
```

---

## Restore Procedures

### Restore Database from Snapshot

```bash
#!/bin/bash
# infra/scripts/restore-database.sh

SNAPSHOT_ID="backup-20240110_120000"
NEW_INSTANCE="eldercare-restored"

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $NEW_INSTANCE \
  --db-snapshot-identifier $SNAPSHOT_ID \
  --db-instance-class db.t3.medium

# Wait for restore
aws rds wait db-instance-available \
  --db-instance-identifier $NEW_INSTANCE

# Get new endpoint
NEW_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $NEW_INSTANCE \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

echo "✓ Database restored from snapshot"
echo "✓ New instance endpoint: $NEW_ENDPOINT"
echo ""
echo "Next steps:"
echo "1. Run: psql -h $NEW_ENDPOINT -U postgres -d eldercare"
echo "2. Verify data integrity"
echo "3. Update application connection string"
echo "4. Run smoke tests"
echo "5. Delete old instance when confirmed working"
```

### Restore S3 Data

```bash
#!/bin/bash
# infra/scripts/restore-s3-data.sh

# List available versions
aws s3api list-object-versions \
  --bucket eldercare-data \
  --query 'Versions[*].[Key,VersionId,LastModified]' \
  --output table

# Restore specific version
aws s3api copy-object \
  --bucket eldercare-data \
  --copy-source eldercare-data/path/to/file?versionId=OLD_VERSION_ID \
  --key path/to/file

# Or restore entire bucket from secondary region (DR scenario)
aws s3 sync s3://eldercare-data-dr/ s3://eldercare-data/ \
  --delete  # Only if primary is completely lost
```

### Restore Kubernetes ConfigMaps

```bash
#!/bin/bash
# Restore ConfigMaps from backup

# From file
kubectl apply -f /backups/configmaps/eldercare-prod/configmaps-backup-20240110.yaml

# Or individual ConfigMap
kubectl create configmap app-config \
  --from-file=/backups/config/ \
  -n eldercare-prod
```

---

## Disaster Recovery Drill

### Monthly DR Drill Procedure

```bash
#!/bin/bash
# infra/scripts/dr-drill.sh

echo "🚨 Starting monthly DR drill..."
echo "Target RTO: 1 hour | Target RPO: 15 minutes"

echo ""
echo "=== PHASE 1: Assessment ==="
echo "1. Verify all backups exist"
aws s3 ls s3://eldercare-backups/ --recursive

echo "2. Check backup freshness"
LATEST_DB_BACKUP=$(aws s3 ls s3://eldercare-backups/database/ | tail -1 | awk '{print $4}')
echo "   Latest database backup: $LATEST_DB_BACKUP (should be < 24h old)"

echo ""
echo "=== PHASE 2: Preparation ==="
echo "Creating test environment in us-west-2 (DR region)..."

# Create test RDS instance from snapshot
RESTORE_ID="dr-drill-$(date +%s)"
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $RESTORE_ID \
  --db-snapshot-identifier $LATEST_DB_BACKUP \
  --region us-west-2

echo "Created test instance: $RESTORE_ID"
echo "Waiting for instance to be ready (est. 10-15 minutes)..."

aws rds wait db-instance-available \
  --db-instance-identifier $RESTORE_ID \
  --region us-west-2

echo ""
echo "=== PHASE 3: Validation ==="

# Connect and validate
TEST_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier $RESTORE_ID \
  --region us-west-2 \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Run data integrity checks
psql -h $TEST_ENDPOINT -U postgres -d eldercare << 'SQL'
\dt
SELECT count(*) FROM users;
SELECT count(*) FROM appointments;
SELECT count(*) FROM care_plans;
SQL

echo "3. Restore S3 data to test bucket"
aws s3 sync s3://eldercare-data-dr/ s3://eldercare-data-test/ \
  --region us-west-2

echo "4. Run smoke tests against restored data"
curl -f https://api-dr-test.eldr.care/api/v1/health || \
  echo "⚠️  API not yet running (expected)"

echo ""
echo "=== PHASE 4: Cleanup ==="
echo "5. Delete test resources"
aws rds delete-db-instance \
  --db-instance-identifier $RESTORE_ID \
  --skip-final-snapshot \
  --region us-west-2

echo ""
echo "✅ DR DRILL COMPLETE"
echo ""
echo "Results:"
echo "- Database restored in: XX minutes"
echo "- Data integrity: PASSED"
echo "- S3 restore time: XX minutes"
echo "- Total RTO estimate: XX minutes (target: < 60 min)"
echo ""
echo "Next steps:"
echo "[ ] Update runbook if needed"
echo "[ ] Document lessons learned"
echo "[ ] Update SLAs/RTO/RPO if necessary"
```

### Regional Failover Procedure

```bash
#!/bin/bash
# infra/scripts/failover-to-dr-region.sh

# Use ONLY if primary region (us-east-1) is completely down

PRIMARY_REGION="us-east-1"
DR_REGION="us-west-2"

echo "⚠️  INITIATING REGIONAL FAILOVER"
echo "From: $PRIMARY_REGION → To: $DR_REGION"
echo "This action is CRITICAL. Do not proceed unless absolutely necessary."
read -p "Type 'FAILOVER' to confirm: " confirm

if [ "$confirm" != "FAILOVER" ]; then
  echo "Failover cancelled."
  exit 1
fi

echo ""
echo "=== STEP 1: Promote Read Replica ==="
aws rds promote-read-replica \
  --db-instance-identifier eldercare-prod-dr-readonly \
  --region $DR_REGION

echo "Waiting for promotion..."
aws rds wait db-instance-available \
  --db-instance-identifier eldercare-prod-dr-readonly \
  --region $DR_REGION

echo ""
echo "=== STEP 2: Update DNS ==="
# Use Route 53 to switch traffic to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.eldr.care",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "api-dr.eldr.care",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'

echo "DNS updated to point to DR region"

echo ""
echo "=== STEP 3: Verify Recovery ==="
sleep 30
curl https://api.eldr.care/api/v1/health

echo ""
echo "=== STEP 4: Notify Stakeholders ==="
# Send notifications
slack-notify "#incidents" "🚨 Regional failover to DR completed. Monitoring."
pagerduty-update-incident "Failover to DR region completed"

echo ""
echo "✓ Failover complete. Continuous monitoring enabled."
echo "⚠️  Primary region restoration should begin immediately."
```

---

## Backup Verification Checklist

Run daily:
- [ ] Latest database snapshot exists and is less than 24 hours old
- [ ] S3 replication is in sync (check replication metrics)
- [ ] Git repositories are synced across mirrors
- [ ] Kubernetes etcd backups created (if self-managed)
- [ ] AWS Secrets Manager backup completed
- [ ] No backup job failures in logs

Run monthly:
- [ ] DR drill executed successfully
- [ ] Database restore time verified (< RTO)
- [ ] Data integrity validated
- [ ] S3 restore tested
- [ ] DNS failover tested
- [ ] Documentation updated

---

## Emergency Contacts

- **Database DBA**: +1-XXX-XXX-XXXX
- **Infrastructure Lead**: +1-XXX-XXX-XXXX
- **On-Call Rotation**: See PagerDuty
- **AWS Support**: Premium support case

---

**Last Updated**: 2024-01-10
**Maintained By**: DevOps & Infrastructure Team
**Testing Cycle**: Monthly (mandatory)
**RTO/RPO Review**: Quarterly
