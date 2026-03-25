variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix applied to every resource name"
  type        = string
  default     = "credit-score"
}

variable "sagemaker_image_uri" {
  description = "ECR URI for the custom SageMaker inference container (output of build_and_push.sh)"
  type        = string
}

variable "api_image_uri" {
  description = "ECR URI for the FastAPI ECS container (output of build_and_push.sh)"
  type        = string
}
