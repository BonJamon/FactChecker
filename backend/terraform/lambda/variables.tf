variable "lambda_timout" {
    description = "Lambda function timeout in seconds"
    type= number
    default = 60
}

variable "openai_api_key" {
    type=string
    sensitive = true
}

variable "thenewsapi_api_key" {
    type=string
    sensitive = true
}

variable "langsmith_api_key" {
    type=string
    sensitive = true
}

variable "langsmith_tracing" {
    type=string
    default = "true"
}

variable "langsmith_project" {
    type=string
    default = "default"
}

variable "langsmith_endpoint" {
    type=string
    default = "https://eu.api.smith.langchain.com"
}

