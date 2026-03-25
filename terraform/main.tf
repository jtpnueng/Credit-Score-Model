# Backend configured dynamically via -backend-config flags in CI (see ci-cd.yml)
# This keeps bucket name flexible (includes AWS account ID for global uniqueness).
terraform {
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

# Default VPC and subnets — used by ALB and ECS
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_caller_identity" "current" {}
