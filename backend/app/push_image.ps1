$ErrorActionPreference = "Stop"

$Region = "eu-central-1"
$RepoName = "my-lambda"
$ImageTag = "latest"

# Get AWS account ID
$AccountId = aws sts get-caller-identity --query Account --output text

$EcrUri = "${AccountId}.dkr.ecr.${Region}.amazonaws.com/${RepoName}"

Write-Host "Logging in to ECR..."
aws ecr get-login-password --region ${Region} `
  | docker login --username AWS --password-stdin ${EcrUri}

Write-Host "Building Docker image..."
docker build -t "${RepoName}:${ImageTag}" .

Write-Host "Tagging image..."
docker tag "${RepoName}:${ImageTag}" "${EcrUri}:${ImageTag}"

Write-Host "Pushing image to ECR..."
docker push "${EcrUri}:${ImageTag}"

Write-Host "Done!"