# AWS Bedrock Integration for CloudWhisper

This document describes the AWS Bedrock integration implemented in CloudWhisper, providing an alternative to OpenAI for generating Terraform code.

## Overview

CloudWhisper now supports AWS Bedrock as an LLM provider, offering access to multiple foundation models including:

- **Anthropic Claude 3** (Sonnet, Haiku, Opus)
- **Amazon Titan Text Express**
- **AI21 Labs Jurassic-2**
- **Cohere Command**

## Configuration

### Provider Selection

You can specify the LLM provider in your configuration file:

```yaml
# ~/.cloudwhisper/config.yaml
llm:
  provider: bedrock  # or 'openai'

# Bedrock configuration
bedrock:
  region: us-east-1
  model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
  max_tokens: 2000
  temperature: 0.1

# OpenAI configuration (still supported)
openai:
  api_key: your_openai_api_key_here
  model: gpt-4
  temperature: 0.1
  max_tokens: 2000
```

### Environment Variables

```bash
# AWS credentials (required for Bedrock)
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Optional: Default Bedrock model
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

## Available Models

### Anthropic Claude 3 Models

- `anthropic.claude-3-sonnet-20240229-v1:0` - Balanced performance and speed
- `anthropic.claude-3-haiku-20240307-v1:0` - Fastest, most cost-effective
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable, highest quality

### Amazon Titan Models

- `amazon.titan-text-express-v1` - Amazon's foundation model

### Other Models

- `ai21.j2-ultra-v1` - AI21 Labs Jurassic-2 Ultra
- `cohere.command-text-v14` - Cohere Command model

## CLI Commands

### List Available Models

```bash
# List all available Bedrock models
cloudwhisper list-models

# List models in a specific region
cloudwhisper list-models --region us-west-2
```

### Check Provider Configuration

```bash
# Show current LLM provider configuration
cloudwhisper provider-info
```

### Generate Terraform Code

```bash
# Use configured provider (from config file)
cloudwhisper generate "Create an S3 bucket with versioning"

# Explicitly use Bedrock with specific model
cloudwhisper generate "Create a VPC with public subnets" \
  --provider bedrock \
  --model anthropic.claude-3-sonnet-20240229-v1:0 \
  --region us-east-1

# Use OpenAI explicitly
cloudwhisper generate "Create an EC2 instance" \
  --provider openai \
  --model gpt-4

# Save output to file
cloudwhisper generate "Create an RDS database" \
  --output main.tf \
  --provider bedrock
```

## IAM Permissions

To use Bedrock, your AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        }
    ]
}
```

## Model-Specific Features

### Anthropic Claude 3

- **System Prompts**: Supports dedicated system prompts for better instruction following
- **Advanced Reasoning**: Excellent for complex infrastructure requirements
- **Code Quality**: Generates high-quality, well-structured Terraform code

### Amazon Titan

- **AWS Integration**: Native AWS model with deep AWS service knowledge
- **Cost-Effective**: Competitive pricing for AWS customers
- **Consistent Output**: Reliable and consistent code generation

### AI21 & Cohere

- **Alternative Options**: Provides diversity in model capabilities
- **Specialized Use Cases**: Different models may excel at different types of infrastructure

## Programmatic Usage

```python
from cloudwhisper.infrawhisper import TerraformGenerator

# Initialize with Bedrock
generator = TerraformGenerator(
    provider='bedrock',
    region='us-east-1',
    model_id='anthropic.claude-3-sonnet-20240229-v1:0'
)

# Generate Terraform code
terraform_code = generator.generate_terraform(
    "Create a highly available web application infrastructure"
)

# Get available models
models = generator.get_available_models()
for model in models:
    print(f"{model['provider']}: {model['name']} ({model['model_id']})")

# Get provider information
info = generator.get_provider_info()
print(f"Using {info['provider']} with model {info.get('model_id', info.get('model'))}")
```

## Error Handling

The integration includes comprehensive error handling for common scenarios:

### Access Denied
```
Error: User is not authorized to perform: bedrock:InvokeModel
```
**Solution**: Ensure your AWS credentials have the required IAM permissions.

### Model Not Found
```
Error: The provided model identifier is invalid
```
**Solution**: Use `cloudwhisper list-models` to see available models in your region.

### Throttling
```
Error: Too many requests
```
**Solution**: Implement exponential backoff or reduce request frequency.

### Region Availability
```
Error: Bedrock is not available in this region
```
**Solution**: Use a supported region like `us-east-1` or `us-west-2`.

## Performance Comparison

| Model | Speed | Cost | Quality | Use Case |
|-------|-------|------|---------|----------|
| Claude 3 Haiku | Fast | Low | Good | Quick prototypes |
| Claude 3 Sonnet | Medium | Medium | Excellent | Production code |
| Claude 3 Opus | Slow | High | Best | Complex architectures |
| Titan Express | Fast | Low | Good | AWS-native solutions |

## Migration from OpenAI

1. **Backup Configuration**: Save your current `config.yaml`
2. **Update Provider**: Change `llm.provider` to `bedrock`
3. **Add Bedrock Config**: Add the `bedrock` section to your config
4. **Test**: Run `cloudwhisper provider-info` to verify configuration
5. **Generate**: Test with a simple infrastructure description

## Best Practices

1. **Model Selection**: Start with Claude 3 Sonnet for balanced performance
2. **Region Choice**: Use regions with lowest latency to your location
3. **Error Handling**: Implement retry logic for production applications
4. **Cost Optimization**: Use Haiku for development, Sonnet for production
5. **Monitoring**: Track your Bedrock usage and costs in AWS console

## Troubleshooting

### Common Issues

1. **No models returned**: Check AWS credentials and region availability
2. **Authentication errors**: Verify IAM permissions and credential configuration
3. **Model access denied**: Some models require explicit access requests in AWS console
4. **Quota exceeded**: Monitor your Bedrock quotas and request increases if needed

### Debug Commands

```bash
# Check AWS credentials
aws sts get-caller-identity

# List Bedrock models directly
aws bedrock list-foundation-models --region us-east-1

# Test Bedrock access
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-haiku-20240307-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --cli-binary-format raw-in-base64-out \
  response.json
```

## Support

For issues specific to Bedrock integration:

1. Check AWS Bedrock service health
2. Verify model availability in your region
3. Review CloudTrail logs for API call details
4. Monitor CloudWatch metrics for Bedrock usage

For general CloudWhisper issues, refer to the main documentation.