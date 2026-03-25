# HTTP API (API Gateway v2) — cheaper and lower-latency than REST API (v1).
# Routes all traffic to the ALB, which forwards to ECS Fargate.
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api-gw"
  protocol_type = "HTTP"
  description   = "Credit Score prediction API"

  cors_configuration {
    allow_headers = ["Content-Type", "Authorization"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = ["*"]
  }
}

# HTTP_PROXY integration forwards requests directly to the ALB.
# overwrite:path passes the full incoming path so /predict, /health etc. all work.
resource "aws_apigatewayv2_integration" "alb" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = "http://${aws_lb.main.dns_name}"

  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}

# Catch-all route — forwards every method and path to the ALB
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.alb.id}"
}

# Root route so GET / also works (health check, docs, etc.)
resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.alb.id}"
}

# Auto-deploy stage — changes go live immediately on terraform apply
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}
