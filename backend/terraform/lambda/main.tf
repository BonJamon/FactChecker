provider "aws" {
  region  = "eu-central-1"
}

data "terraform_remote_state" "ecr" {
  backend = "local" # or s3 in real setups
  config = {
    path = "../ecr/terraform.tfstate"
  }
}


resource "aws_iam_role" "lambda_role" {
  name = "factchecker-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_logs" {
  role      = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_lambda_function" "factchecker" {
  function_name = "factchecker-api"
  role          = aws_iam_role.lambda_role.arn
  timeout       = var.lambda_timout
  memory_size   = 512
  package_type  = "Image"
  image_uri     = "${data.terraform_remote_state.ecr.outputs.repository_url}:latest"

  environment {
    variables = {
        OPENAI_API_KEY = var.openai_api_key
        THENEWSAPI_API_KEY=var.thenewsapi_api_key
        LANGSMITH_API_KEY=var.langsmith_api_key
        LANGSMITH_TRACING=var.langsmith_tracing
        LANGSMITH_PROJECT=var.langsmith_project
        LANGSMITH_ENDPOINT=var.langsmith_endpoint
    }
  }
}


resource "aws_apigatewayv2_api" "my_api" {
  name          = "my-fastapi-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.my_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.factchecker.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.my_api.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.my_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "verify" {
  api_id    = aws_apigatewayv2_api.my_api.id
  route_key = "GET /verify"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.my_api.id
  name        = "$default"
  auto_deploy = true
}


resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.factchecker.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.my_api.execution_arn}/*/*"
}