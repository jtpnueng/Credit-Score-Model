#!/bin/bash
# Build Docker images and push them to ECR.
# Run this from the project root BEFORE running terraform apply.
#
# Usage:
#   chmod +x scripts/build_and_push.sh
#   ./scripts/build_and_push.sh
set -e

AWS_REGION=${AWS_REGION:-"us-east-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

SAGEMAKER_REPO="credit-score-sagemaker-model"
API_REPO="credit-score-api"
TAG="latest"

echo "==> Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_BASE"

# --- SageMaker inference container ---
echo "==> Creating ECR repo: $SAGEMAKER_REPO (if not exists)..."
aws ecr describe-repositories --repository-names "$SAGEMAKER_REPO" \
  --region "$AWS_REGION" 2>/dev/null \
  || aws ecr create-repository --repository-name "$SAGEMAKER_REPO" \
     --region "$AWS_REGION"

echo "==> Building SageMaker image..."
docker build -f docker/Dockerfile.sagemaker -t "$SAGEMAKER_REPO:$TAG" .

echo "==> Pushing SageMaker image..."
docker tag "$SAGEMAKER_REPO:$TAG" "$ECR_BASE/$SAGEMAKER_REPO:$TAG"
docker push "$ECR_BASE/$SAGEMAKER_REPO:$TAG"

# --- FastAPI container ---
echo "==> Creating ECR repo: $API_REPO (if not exists)..."
aws ecr describe-repositories --repository-names "$API_REPO" \
  --region "$AWS_REGION" 2>/dev/null \
  || aws ecr create-repository --repository-name "$API_REPO" \
     --region "$AWS_REGION"

echo "==> Building API image..."
docker build -f docker/Dockerfile.api -t "$API_REPO:$TAG" .

echo "==> Pushing API image..."
docker tag "$API_REPO:$TAG" "$ECR_BASE/$API_REPO:$TAG"
docker push "$ECR_BASE/$API_REPO:$TAG"

echo ""
echo "=== Build complete ==="
echo "SageMaker image : $ECR_BASE/$SAGEMAKER_REPO:$TAG"
echo "API image       : $ECR_BASE/$API_REPO:$TAG"
echo ""
echo "Next step — deploy infrastructure:"
echo "  cd terraform"
echo "  terraform init"
echo "  terraform apply \\"
echo "    -var=\"sagemaker_image_uri=$ECR_BASE/$SAGEMAKER_REPO:$TAG\" \\"
echo "    -var=\"api_image_uri=$ECR_BASE/$API_REPO:$TAG\""
