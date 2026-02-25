#!/bin/bash
# MandiMitra — AWS Infrastructure Setup Script
# Run this ONCE to create all required AWS resources.
#
# Prerequisites:
#   1. AWS CLI installed and configured (aws configure)
#   2. Sufficient IAM permissions (admin or specific permissions below)
#   3. Bedrock model access enabled for Claude in us-east-1
#
# Usage: bash infra/setup_aws.sh

set -e

REGION="us-east-1"
TABLE_NAME="MandiMitraPrices"
S3_BUCKET="mandimitra-data-$(aws sts get-caller-identity --query Account --output text)"
STACK_PREFIX="mandimitra"

echo "=================================="
echo "MandiMitra AWS Infrastructure Setup"
echo "=================================="
echo "Region: $REGION"
echo "DynamoDB Table: $TABLE_NAME"
echo "S3 Bucket: $S3_BUCKET"
echo ""

# ─── 1. DynamoDB Table ───────────────────────────────────────────────
echo "[1/5] Creating DynamoDB table..."

aws dynamodb create-table \
  --region $REGION \
  --table-name $TABLE_NAME \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=mandi_name,AttributeType=S \
    AttributeName=date_commodity,AttributeType=S \
    AttributeName=arrival_date,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "MANDI-INDEX",
        "KeySchema": [
          {"AttributeName": "mandi_name", "KeyType": "HASH"},
          {"AttributeName": "date_commodity", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "DATE-INDEX",
        "KeySchema": [
          {"AttributeName": "arrival_date", "KeyType": "HASH"},
          {"AttributeName": "PK", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST \
  --tags Key=Project,Value=MandiMitra Key=Environment,Value=hackathon \
  2>/dev/null && echo "  ✓ Table created" || echo "  ℹ Table already exists"

# ─── 2. S3 Bucket ───────────────────────────────────────────────────
echo "[2/5] Creating S3 bucket..."

aws s3 mb "s3://$S3_BUCKET" --region $REGION 2>/dev/null \
  && echo "  ✓ Bucket created" || echo "  ℹ Bucket already exists"

# Block public access
aws s3api put-public-access-block \
  --region $REGION \
  --bucket $S3_BUCKET \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
  2>/dev/null

# ─── 3. IAM Role for Lambda ────────────────────────────────────────
echo "[3/5] Creating IAM role for Lambda..."

TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}'

ROLE_NAME="${STACK_PREFIX}-lambda-role"

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document "$TRUST_POLICY" \
  --tags Key=Project,Value=MandiMitra \
  2>/dev/null && echo "  ✓ Role created" || echo "  ℹ Role already exists"

# Attach policies
aws iam attach-role-policy --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null

# Custom inline policy for DynamoDB + S3 + Bedrock
LAMBDA_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/'$TABLE_NAME'*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::'$S3_BUCKET'",
        "arn:aws:s3:::'$S3_BUCKET'/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeAgent"
      ],
      "Resource": "*"
    }
  ]
}'

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name "${STACK_PREFIX}-lambda-policy" \
  --policy-document "$LAMBDA_POLICY" 2>/dev/null
echo "  ✓ Policies attached"

# ─── 4. Get Role ARN ────────────────────────────────────────────────
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "  Role ARN: $ROLE_ARN"

# ─── 5. Create .env template ────────────────────────────────────────
echo "[4/5] Creating .env template..."

cat > ../.env.example << EOF
# MandiMitra Environment Variables
# Copy this to .env and fill in the values

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# DynamoDB
PRICE_TABLE=$TABLE_NAME

# S3
S3_BUCKET=$S3_BUCKET

# data.gov.in API (register at https://data.gov.in)
DATA_GOV_API_KEY=your_api_key_here

# Bedrock Agent (fill after creating agents in AWS Console)
BEDROCK_AGENT_ID=
BEDROCK_AGENT_ALIAS_ID=

# LangFuse (register at https://langfuse.com)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com

# Frontend
NEXT_PUBLIC_API_URL=https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod
EOF

echo "  ✓ .env.example created"

# ─── Summary ────────────────────────────────────────────────────────
echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Resources created:"
echo "  • DynamoDB Table: $TABLE_NAME"
echo "  • S3 Bucket: $S3_BUCKET"
echo "  • IAM Role: $ROLE_NAME ($ROLE_ARN)"
echo ""
echo "Next steps:"
echo "  1. Register at https://data.gov.in and get API key"
echo "  2. Enable Bedrock model access (Claude) in AWS Console"
echo "  3. Create Bedrock Agents using configs in backend/agent_configs/"
echo "  4. Copy .env.example to .env and fill in values"
echo "  5. Deploy Lambda functions"
echo "  6. Set up API Gateway"
echo ""
