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
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file
pytest cloudwhisper/tests/test_basic.py

# Run a specific test class or function
pytest cloudwhisper/tests/test_basic.py::TestTerraformGenerator
pytest cloudwhisper/tests/test_basic.py::TestTerraformGenerator::test_clean_terraform_code
```

### Running the CLI
```bash
# View all available commands
cloudwhisper --help

# Generate Terraform code
cloudwhisper generate "Create an S3 bucket with versioning enabled"
cloudwhisper generate "Set up a VPC with public and private subnets" --output vpc.tf

# Analyze AWS costs
cloudwhisper analyze-costs --days 30
cloudwhisper analyze-costs --service ec2 --days 7 --granularity DAILY

# Get optimization recommendations
cloudwhisper optimize
cloudwhisper optimize --service ec2
cloudwhisper optimize --service s3

# Find idle resources
cloudwhisper find-idle --days 7

# Get Savings Plans recommendations
cloudwhisper savings-plans
```

### Demo Script
```bash
# Run the demo script to see example commands
python cloudwhisper/demo.py
```

## Architecture Overview

### Project Structure
- `cloudwhisper/`: Main package directory
  - `cloudwhisper/`: Core code files
    - `__init__.py`: Package initialization
    - `cli.py`: CLI command definitions using Click
    - `infrawhisper.py`: Terraform generation functionality
    - `cloudfuel.py`: AWS cost analysis and optimization
  - `tests/`: Unit tests
  - `examples/`: Usage examples
  - `setup.py`: Package installation script

### Key Components

1. **CLI Module** (`cli.py`):
   - Defines all command-line commands using the Click framework
   - Entry point for the application
   - Routes commands to appropriate functionality

2. **InfraWhisper** (`infrawhisper.py`):
   - `TerraformGenerator` class uses OpenAI to convert natural language to Terraform
   - Includes template rendering with Jinja2
   - Provides validation and cleaning of generated code

3. **CloudFuel** (`cloudfuel.py`):
   - `CostAnalyzer` class fetches and analyzes AWS cost data
   - `CostOptimizer` class identifies cost-saving opportunities
   - Uses AWS Cost Explorer, EC2, S3, RDS, and other AWS APIs
   - Displays recommendations using rich tables and panels

### Data Flow
1. **Terraform Generation Flow**:
   - User provides natural language description
   - OpenAI API generates Terraform code
   - Code is processed, cleaned, and validated
   - Output is displayed or saved to file

2. **Cost Analysis Flow**:
   - AWS Cost Explorer API fetches cost data
   - Data is processed and analyzed
   - Results displayed in formatted tables

3. **Optimization Flow**:
   - AWS resource utilization data is collected
   - Analysis identifies optimization opportunities
   - Recommendations are presented to the user

### Dependencies
- `boto3`: AWS SDK for Python
- `openai`: OpenAI API client
- `click`: Command-line interface creation
- `rich`: Terminal formatting and display
- `jinja2`: Template rendering
- `tabulate`: Table formatting
- `pytest`: Testing framework