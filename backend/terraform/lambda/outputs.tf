output "lambda_function_name" {
    description= "Name of the lambda function"
    value = aws_lambda_function.factchecker.function_name
}