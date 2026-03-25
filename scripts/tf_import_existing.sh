#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# tf_import_existing.sh
#
# Imports AWS resources that already exist into the Terraform state.
# Safe to run on every deploy — each import is skipped if the resource is
# already tracked in state, and skipped if the resource doesn't exist yet.
#
# Run from the repo root after `terraform init`.
# ---------------------------------------------------------------------------
set -euo pipefail

PROJECT="${PROJECT_NAME:-credit-score}"
REGION="${AWS_REGION:-us-east-1}"

cd terraform

echo "==> Detecting default VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" --output text --region "$REGION")
echo "    VPC: $VPC_ID"

# Helper — import only if not already in state
tf_import() {
  local resource="$1"
  local id="$2"
  if terraform state show "$resource" &>/dev/null; then
    echo "  [skip] $resource already in state"
  else
    echo "  [import] $resource  <--  $id"
    terraform import "$resource" "$id" || echo "    (resource not found in AWS — will be created)"
  fi
}

# ── CloudWatch Log Group ─────────────────────────────────────────────────────
tf_import "aws_cloudwatch_log_group.api" "/ecs/${PROJECT}-api"

# ── IAM Roles ────────────────────────────────────────────────────────────────
tf_import "aws_iam_role.sagemaker_role"     "${PROJECT}-sagemaker-role"
tf_import "aws_iam_role.ecs_execution_role" "${PROJECT}-ecs-execution-role"
tf_import "aws_iam_role.ecs_task_role"      "${PROJECT}-ecs-task-role"

# ── IAM Policy ───────────────────────────────────────────────────────────────
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${PROJECT}-sagemaker-invoke"
POLICY_EXISTS=$(aws iam get-policy --policy-arn "$POLICY_ARN" \
  --query "Policy.Arn" --output text 2>/dev/null || echo "")
if [ -n "$POLICY_EXISTS" ]; then
  tf_import "aws_iam_policy.sagemaker_invoke" "$POLICY_ARN"
fi

# ── Security Groups ──────────────────────────────────────────────────────────
lookup_sg() {
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$1" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text --region "$REGION" 2>/dev/null || echo ""
}

ALB_SG=$(lookup_sg "${PROJECT}-alb-sg")
[ -n "$ALB_SG" ] && [ "$ALB_SG" != "None" ] && tf_import "aws_security_group.alb" "$ALB_SG"

ECS_SG=$(lookup_sg "${PROJECT}-ecs-sg")
[ -n "$ECS_SG" ] && [ "$ECS_SG" != "None" ] && tf_import "aws_security_group.ecs" "$ECS_SG"

# ── ALB ──────────────────────────────────────────────────────────────────────
ALB_ARN=$(aws elbv2 describe-load-balancers --names "${PROJECT}-alb" \
  --query "LoadBalancers[0].LoadBalancerArn" --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ] && tf_import "aws_lb.main" "$ALB_ARN"

# ── Target Group ─────────────────────────────────────────────────────────────
TG_ARN=$(aws elbv2 describe-target-groups --names "${PROJECT}-tg" \
  --query "TargetGroups[0].TargetGroupArn" --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ] && tf_import "aws_lb_target_group.api" "$TG_ARN"

# ── ALB Listener ─────────────────────────────────────────────────────────────
if [ -n "$ALB_ARN" ] && [ "$ALB_ARN" != "None" ]; then
  LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" \
    --query "Listeners[?Port==\`80\`].ListenerArn | [0]" --output text --region "$REGION" 2>/dev/null || echo "")
  [ -n "$LISTENER_ARN" ] && [ "$LISTENER_ARN" != "None" ] && \
    tf_import "aws_lb_listener.http" "$LISTENER_ARN"
fi

# ── ECS Cluster ──────────────────────────────────────────────────────────────
CLUSTER_ARN=$(aws ecs describe-clusters --clusters "${PROJECT}-cluster" \
  --query "clusters[?status=='ACTIVE'].clusterArn | [0]" --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$CLUSTER_ARN" ] && [ "$CLUSTER_ARN" != "None" ] && tf_import "aws_ecs_cluster.main" "$CLUSTER_ARN"

# ── ECR Repositories ─────────────────────────────────────────────────────────
ECR_SM=$(aws ecr describe-repositories --repository-names "${PROJECT}-sagemaker-model" \
  --query "repositories[0].repositoryArn" --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$ECR_SM" ] && [ "$ECR_SM" != "None" ] && \
  tf_import "aws_ecr_repository.sagemaker_model" "${PROJECT}-sagemaker-model"

ECR_API=$(aws ecr describe-repositories --repository-names "${PROJECT}-api" \
  --query "repositories[0].repositoryArn" --output text --region "$REGION" 2>/dev/null || echo "")
[ -n "$ECR_API" ] && [ "$ECR_API" != "None" ] && \
  tf_import "aws_ecr_repository.api" "${PROJECT}-api"

echo ""
echo "==> Import complete. Ready for terraform apply."
