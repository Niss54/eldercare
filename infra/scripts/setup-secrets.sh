#!/bin/bash
# Secrets Manager setup script for AWS

set -e

ENVIRONMENT="${1:-production}"
REGION="${2:-us-east-1}"

echo "Setting up AWS Secrets Manager for $ENVIRONMENT environment..."

# Database password
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/db-password" \
  --description "PostgreSQL database password for $ENVIRONMENT" \
  --secret-string "$DB_PASSWORD" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/db-password" \
  --secret-string "$DB_PASSWORD" \
  --region $REGION

# JWT secrets
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/jwt-secret" \
  --description "JWT signing secret for $ENVIRONMENT" \
  --secret-string "$JWT_SECRET_KEY" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/jwt-secret" \
  --secret-string "$JWT_SECRET_KEY" \
  --region $REGION

# Redis password
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/redis-password" \
  --description "Redis password for $ENVIRONMENT" \
  --secret-string "$REDIS_PASSWORD" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/redis-password" \
  --secret-string "$REDIS_PASSWORD" \
  --region $REGION

# S3 access keys
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/s3-credentials" \
  --description "S3 access credentials for $ENVIRONMENT" \
  --secret-string "{\"access_key\":\"$S3_ACCESS_KEY\",\"secret_key\":\"$S3_SECRET_KEY\"}" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/s3-credentials" \
  --secret-string "{\"access_key\":\"$S3_ACCESS_KEY\",\"secret_key\":\"$S3_SECRET_KEY\"}" \
  --region $REGION

# Email service credentials
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/email-credentials" \
  --description "Email service credentials for $ENVIRONMENT" \
  --secret-string "{\"smtp_user\":\"$EMAIL_USER\",\"smtp_password\":\"$EMAIL_PASSWORD\"}" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/email-credentials" \
  --secret-string "{\"smtp_user\":\"$EMAIL_USER\",\"smtp_password\":\"$EMAIL_PASSWORD\"}" \
  --region $REGION

# SMS service credentials
if [ ! -z "$TWILIO_AUTH_TOKEN" ]; then
aws secretsmanager create-secret \
  --name "eldercare/$ENVIRONMENT/twilio-credentials" \
  --description "Twilio credentials for $ENVIRONMENT" \
  --secret-string "{\"account_sid\":\"$TWILIO_ACCOUNT_SID\",\"auth_token\":\"$TWILIO_AUTH_TOKEN\"}" \
  --region $REGION \
  2>/dev/null || aws secretsmanager update-secret \
  --secret-id "eldercare/$ENVIRONMENT/twilio-credentials" \
  --secret-string "{\"account_sid\":\"$TWILIO_ACCOUNT_SID\",\"auth_token\":\"$TWILIO_AUTH_TOKEN\"}" \
  --region $REGION
fi

echo "Secrets created or updated successfully!"

# List all secrets
echo -e "\nCreated secrets:"
aws secretsmanager list-secrets \
  --filters Key=name,Values=eldercare/$ENVIRONMENT \
  --region $REGION \
  --query 'SecretList[*].Name' \
  --output table
