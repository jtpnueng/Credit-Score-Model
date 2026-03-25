# Custom Docker container — no more built-in sklearn image, so no version mismatch.
resource "aws_sagemaker_model" "model" {
  name               = "${var.project_name}-model"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    # The model artifact is baked into the image, so no model_data_url needed.
    image = var.sagemaker_image_uri

    environment = {
      MODEL_PATH = "/opt/ml/model/credit_score_model.pkl"
    }
  }
}

resource "aws_sagemaker_endpoint_configuration" "config" {
  name = "${var.project_name}-endpoint-config"

  production_variants {
    variant_name           = "AllTraffic"
    model_name             = aws_sagemaker_model.model.name
    initial_instance_count = 1
    instance_type          = "ml.t2.medium"
  }
}

resource "aws_sagemaker_endpoint" "endpoint" {
  name                 = "${var.project_name}-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.config.name
}
