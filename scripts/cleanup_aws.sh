#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# cleanup_aws.sh
#
# Deletes all credit-score AWS resources so Terraform can start clean.
# Run this ONCE from your local machine (needs AWS CLI + credentials):
#
#   AWS_REGION=us-east-1 bash scripts/cleanup_aws.sh
#
# Safe to re-run — every delete is wrapped in || true.
# ---------------------------------------------------------------------------
set -uo pipefail

PROJECT="${PROJECT_NAME:-credit-score}"
REGION="${AWS_REGION:-us-east-1}"

echo "==> Cleaning up project='$PROJECT' in region='$REGION'"
echo "    (errors are expected if a resource doesn't exist)"
echo ""

# ── SageMaker (slowest to delete — do first) ---------------------------------
echo "[1/9] SageMaker endpoint..."
aws sagemaker delete-endpoint \
  --endpoint-name "${PROJECT}-endpoint" \
  --region "$REGION" 2>/dev/null && echo "    endpoint deletion initiated (async)" || echo "    not found"

# Wait for endpoint to finish deleting before removing config/model
echo "    waiting for endpoint to delete (up to 10 min)..."
aws sagemaker wait endpoint-deleted \
  --endpoint-name "${PROJECT}-endpoint" \
  --region "$REGION" 2>/dev/null || echo "    (already gone or timed out)"

echo "    endpoint config..."
aws sagemaker delete-endpoint-config \
  --endpoint-config-name "${PROJECT}-endpoint-config" \
  --region "$REGION" 2>/dev/null || echo "    not found"

echo "    model..."
aws sagemaker delete-model \
  --model-name "${PROJECT}-model" \
  --region "$REGION" 2>/dev/null || echo "    not found"

# ── ECS Service (must be stopped before cluster can be deleted) ---------------
echo "[2/9] ECS service..."
aws ecs update-service \
  --cluster "${PROJECT}-cluster" \
  --service "${PROJECT}-api-service" \
  --desired-count 0 \
  --region "$REGION" 2>/dev/null || echo "    not found"

aws ecs delete-service \
  --cluster "${PROJECT}-cluster" \
  --service "${PROJECT}-api-service" \
  --force \
  --region "$REGION" 2>/dev/null || echo "    not found"

echo "[3/9] ECS cluster..."
aws ecs delete-cluster \
  --cluster "${PROJECT}-cluster" \
  --region "$REGION" 2>/dev/null || echo "    not found"

# ── ALB + Listener + Target Group ---------------------------------------------
echo "[4/9] ALB listener, load balancer, target group..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names "${PROJECT}-alb" \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text --region "$REGION" 2>/dev/null || echo "")

if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
  # Delete listeners first
  LISTENER_ARNS=$(aws elbv2 describe-listeners \
    --load-balancer-arn "$ALB_ARN" \
    --query "Listeners[].ListenerArn" \
    --output text --region "$REGION" 2>/dev/null || echo "")
  for L in $LISTENER_ARNS; do
    aws elbv2 delete-listener --listener-arn "$L" --region "$REGION" 2>/dev/null || true
  done
  aws elbv2 delete-load-balancer --load-balancer-arn "$ALB_ARN" --region "$REGION" 2>/dev/null || true
  echo "    waiting for ALB to delete..."
  aws elbv2 wait load-balancers-deleted --load-balancer-arns "$ALB_ARN" --region "$REGION" 2>/dev/null || true
else
  echo "    ALB not found"
fi

TG_ARN=$(aws elbv2 describe-target-groups \
  --names "${PROJECT}-tg" \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ] && \
  aws elbv2 delete-target-group --target-group-arn "$TG_ARN" --region "$REGION" 2>/dev/null || true

# ── API Gateway ---------------------------------------------------------------
echo "[5/9] API Gateway..."
API_ID=$(aws apigatewayv2 get-apis \
  --query "Items[?Name=='${PROJECT}-api-gw'].ApiId | [0]" \
  --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$API_ID" ] && [ "$API_ID" != "None" ] && \
  aws apigatewayv2 delete-api --api-id "$API_ID" --region "$REGION" 2>/dev/null || echo "    not found"

# ── Security Groups (must delete after ALB/ECS) -------------------------------
echo "[6/9] Security groups..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" --output text --region "$REGION" 2>/dev/null)

for SG_NAME in "${PROJECT}-ecs-sg" "${PROJECT}-alb-sg"; do
  SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" \
    --output text --region "$REGION" 2>/dev/null || echo "")
  if [ -n "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
    aws ec2 delete-security-group --group-id "$SG_ID" --region "$REGION" 2>/dev/null \
      && echo "    deleted $SG_NAME" || echo "    could not delete $SG_NAME (may still have dependencies)"
  else
    echo "    $SG_NAME not found"
  fi
done

# ── CloudWatch Log Group ------------------------------------------------------
echo "[7/9] CloudWatch log group..."
aws logs delete-log-group \
  --log-group-name "/ecs/${PROJECT}-api" \
  --region "$REGION" 2>/dev/null || echo "    not found"

# ── IAM ----------------------------------------------------------------------
echo "[8/9] IAM roles and policies..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

detach_and_delete_role() {
  local ROLE="$1"
  # Detach all managed policies
  POLICIES=$(aws iam list-attached-role-policies --role-name "$ROLE" \
    --query "AttachedPolicies[].PolicyArn" --output text 2>/dev/null || echo "")
  for P in $POLICIES; do
    aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$P" 2>/dev/null || true
  done
  aws iam delete-role --role-name "$ROLE" 2>/dev/null \
    && echo "    deleted $ROLE" || echo "    $ROLE not found"
}

detach_and_delete_role "${PROJECT}-sagemaker-role"
detach_and_delete_role "${PROJECT}-ecs-execution-role"
detach_and_delete_role "${PROJECT}-ecs-task-role"

POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${PROJECT}-sagemaker-invoke"
aws iam delete-policy --policy-arn "$POLICY_ARN" 2>/dev/null || echo "    policy not found"

# ── Terraform state (clear so next run starts fresh) -------------------------
echo "[9/9] Clearing Terraform state file in S3..."
BUCKET="credit-score-tf-state-${ACCOUNT_ID}"
aws s3 rm "s3://${BUCKET}/terraform.tfstate" --region "$REGION" 2>/dev/null || echo "    state file not found"
aws s3 rm "s3://${BUCKET}/terraform.tfstate.backup" --region "$REGION" 2>/dev/null || true

echo ""
echo "==> Cleanup complete."
echo "    All credit-score resources have been removed."
echo "    Push a commit to main to trigger a fresh Terraform deploy."
