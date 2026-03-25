output "ecr_sagemaker_repo_url" {
  description = "ECR repository URL for the SageMaker inference image"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}-sagemaker-model"
}

output "ecr_api_repo_url" {
  description = "ECR repository URL for the FastAPI image"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}-api"
}

output "sagemaker_endpoint_name" {
  description = "Name of the live SageMaker endpoint"
  value       = aws_sagemaker_endpoint.endpoint.name
}

output "alb_dns_name" {
  description = "ALB DNS — direct access to ECS (bypasses API Gateway)"
  value       = aws_lb.main.dns_name
}

output "api_gateway_url" {
  description = "Public API Gateway URL — use this to call /predict and /health"
  value       = aws_apigatewayv2_api.main.api_endpoint
}
