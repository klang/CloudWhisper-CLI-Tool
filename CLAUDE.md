# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install the package in development mode
pip install -e .

# Set required environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
export OPENAI_API_KEY=your_openai_key

# Or alternatively setup the config
cloudwhisper setup
```

### Running Tests
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_basic.py

# Run a specific test class or function
pytest tests/test_basic.py::TestTerraformGenerator
pytest tests/test_basic.py::TestTerraformGenerator::test_clean_terraform_code

# Run tests with coverage
pytest --cov=cloudwhisper tests/
```

### CLI Commands Reference

#### Terraform Generation
```bash
# Generate Terraform code from natural language
cloudwhisper generate "Create an S3 bucket with versioning enabled"
cloudwhisper generate "Set up a VPC with public and private subnets" --output vpc.tf

# Specify provider and model
cloudwhisper generate "Create an EC2 instance" --provider openai --model gpt-4
cloudwhisper generate "Create an RDS instance" --provider bedrock --model anthropic.claude-3-sonnet-20240229-v1:0 --region us-east-1
cloudwhisper generate "Create a Lambda function" --provider lmstudio --base-url http://127.0.0.1:1234
cloudwhisper generate "Create a CloudFront distribution" --provider ollama --model llama3.2
```

#### LLM Provider Management
```bash
# Configure LLM provider
cloudwhisper setup --provider [openai|bedrock|lmstudio|ollama|auto]

# List available models
cloudwhisper list-models
cloudwhisper list-models --provider bedrock --region us-east-1

# Show provider information
cloudwhisper provider-info

# Test connections to local LLMs
cloudwhisper test-connection
```

#### AWS Cost Analysis
```bash
# Analyze costs
cloudwhisper analyze-costs --days 30
cloudwhisper analyze-costs --service ec2 --days 7 --granularity DAILY
cloudwhisper analyze-costs --group-by SERVICE --group-by REGION

# Get optimization recommendations
cloudwhisper optimize
cloudwhisper optimize --service ec2
cloudwhisper optimize --service s3

# Find idle resources
cloudwhisper find-idle --days 7

# Get Savings Plans recommendations
cloudwhisper savings-plans
```

#### AWS Profile Management
```bash
# List available AWS profiles
cloudwhisper list-profiles

# Show AWS account information
cloudwhisper aws-info --profile [profile-name]

# Use specific profile with any command
cloudwhisper [command] --profile [profile-name]
```

## Project Architecture

### Core Components

1. **CLI Module** (`cli.py`):
   - Built with Click framework
   - Defines command groups, options, and parameters
   - Handles command routing and output formatting using Rich
   - Central entry point via `main()` function

2. **InfraWhisper** (`infrawhisper.py`):
   - `TerraformGenerator` class converts natural language to Terraform
   - Multi-provider LLM support (OpenAI, AWS Bedrock, LM Studio, Ollama)
   - Smart provider detection based on available credentials
   - Template rendering for common Terraform patterns
   - Code validation and cleaning

3. **CloudFuel** (`cloudfuel.py`):
   - `CostAnalyzer` for AWS cost data analysis
   - `CostOptimizer` for resource optimization recommendations
   - Rich console output formatting with tables and panels

4. **AWS Session Manager** (`aws_session.py`):
   - Centralized AWS client creation with profile support
   - Client caching and region management
   - Credentials validation and session information retrieval

### Provider Architecture

The tool supports four LLM providers:

1. **OpenAI**: Cloud-based models requiring API key
   - Models: GPT-3.5 Turbo, GPT-4, etc.
   - Authentication via `OPENAI_API_KEY` environment variable

2. **AWS Bedrock**: AWS-managed foundation models
   - Models: Claude (Anthropic), Titan (Amazon), etc.
   - Authentication via AWS credentials or profile
   - Supports multiple model-specific input formats

3. **LM Studio**: Local LLM server with OpenAI-compatible API
   - Default URL: http://127.0.0.1:1234
   - No API key required for local usage

4. **Ollama**: Local LLM server for running models locally
   - Default URL: http://localhost:11434
   - Models: Llama, Mistral, etc.

### Testing Approach

The codebase uses pytest for testing with:
- Unit tests for individual components
- Mock objects for AWS services using `unittest.mock`
- Test fixtures for common testing scenarios
- Parameterized tests for comprehensive coverage

Key test files:
- `test_basic.py`: Core functionality tests
- `test_bedrock_cli.py`: AWS Bedrock CLI command tests
- `test_bedrock_integration.py`: AWS Bedrock integration tests

### Configuration Management

The tool uses a layered configuration approach:
1. Command-line arguments (highest priority)
2. Configuration file (~/.cloudwhisper/config.yaml)
3. Environment variables
4. Auto-detection of available providers (lowest priority)

Configuration file example:
```yaml
llm:
  provider: bedrock
bedrock:
  region: us-east-1
  model_id: anthropic.claude-3-sonnet-20240229-v1:0
  max_tokens: 2000
  temperature: 0.1
aws:
  profile: default
```

## Development Notes

- Python 3.8+ required
- Key dependencies: boto3, openai, click, rich, jinja2, pyyaml
- Local model support requires LM Studio or Ollama running locally
- AWS credentials with appropriate permissions needed for cost analysis