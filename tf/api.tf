
# Create HTTP API
resource "aws_apigatewayv2_api" "http_api" {
  name          = "rmind-hello-api"
  protocol_type = "HTTP"
}

# Integration between API Gateway and Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# Route for POST /parse_transcript
resource "aws_apigatewayv2_route" "parse_transcript" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /parse_transcript"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Default stage (auto-deploys new changes)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

# Permission for API Gateway to invoke the Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Output the public endpoint
output "api_endpoint" {
  value = "${aws_apigatewayv2_stage.default.invoke_url}/parse_transcript"
}