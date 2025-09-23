#!/usr/bin/env python3

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from openai import OpenAI
import boto3
from jinja2 import Template
from botocore.exceptions import ClientError
from .aws_session import AWSSessionManager

class TerraformGenerator:
    """Generate Terraform code from natural language descriptions using LLM."""

    def __init__(self,
                 provider: str = "openai",
                 api_key: Optional[str] = None,
                 region: Optional[str] = None,
                 model_id: Optional[str] = None,
                 openai_model: str = "gpt-3.5-turbo",
                 max_tokens: int = 2000,
                 temperature: float = 0.1,
                 aws_profile: Optional[str] = None):
        """Initialize the Terraform generator with specified LLM provider."""

        self.provider = provider.lower()
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.aws_profile = aws_profile

        # Initialize based on provider
        if self.provider == "openai":
            self._init_openai(api_key, openai_model)
        elif self.provider == "bedrock":
            self._init_bedrock(region, model_id, aws_profile)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'bedrock'")

        # Terraform templates for common AWS resources
        self.templates = {
            'provider': '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ provider_version }}"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
''',
            'variables': '''
variable "{{ name }}" {
  description = "{{ description }}"
  type        = {{ type }}
  {% if default %}default     = {{ default }}{% endif %}
}
''',
            'outputs': '''
output "{{ name }}" {
  description = "{{ description }}"
  value       = {{ value }}
}
'''
        }

        # Model-specific configurations for Bedrock
        self.bedrock_model_configs = {
            'anthropic.claude-3-sonnet-20240229-v1:0': {
                'input_format': 'anthropic',
                'supports_system_prompt': True
            },
            'anthropic.claude-3-haiku-20240307-v1:0': {
                'input_format': 'anthropic',
                'supports_system_prompt': True
            },
            'anthropic.claude-3-opus-20240229-v1:0': {
                'input_format': 'anthropic',
                'supports_system_prompt': True
            },
            'amazon.titan-text-express-v1': {
                'input_format': 'titan',
                'supports_system_prompt': False
            },
            'ai21.j2-ultra-v1': {
                'input_format': 'ai21',
                'supports_system_prompt': False
            },
            'cohere.command-text-v14': {
                'input_format': 'cohere',
                'supports_system_prompt': False
            }
        }

    def _init_openai(self, api_key: Optional[str], model: str):
        """Initialize OpenAI client."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self.openai_client = OpenAI(api_key=self.api_key)
        self.openai_model = model

    def _init_bedrock(self, region: Optional[str], model_id: Optional[str], aws_profile: Optional[str]):
        """Initialize AWS Bedrock client with profile support."""
        self.bedrock_region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.bedrock_model_id = model_id or os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

        try:
            # Use session manager for profile support
            self.aws_session_manager = AWSSessionManager(
                profile_name=aws_profile,
                region_name=self.bedrock_region
            )
            self.bedrock_client = self.aws_session_manager.get_client('bedrock-runtime')
        except Exception as e:
            raise ValueError(f"Failed to initialize Bedrock client: {str(e)}")

    @classmethod
    def from_config(cls, config_path: Optional[str] = None, aws_profile: Optional[str] = None, auto_detect_provider: bool = True):
        """Create TerraformGenerator from configuration file with smart provider detection."""
        if config_path is None:
            # Try common config locations
            config_locations = [
                os.path.expanduser("~/.cloudwhisper/config.yaml"),
                os.path.join(os.getcwd(), "config.yaml"),
                os.path.join(os.getcwd(), "config.example.yaml")
            ]

            for location in config_locations:
                if os.path.exists(location):
                    config_path = location
                    break

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Extract AWS profile from config or parameter
            aws_config = config.get('aws', {})
            profile = aws_profile or aws_config.get('profile')

            # Extract configuration
            llm_config = config.get('llm', {})
            provider = llm_config.get('provider', 'openai')

            if provider == 'openai':
                openai_config = config.get('openai', {})
                return cls(
                    provider='openai',
                    api_key=openai_config.get('api_key'),
                    openai_model=openai_config.get('model', 'gpt-3.5-turbo'),
                    max_tokens=openai_config.get('max_tokens', 2000),
                    temperature=openai_config.get('temperature', 0.1),
                    aws_profile=profile
                )
            elif provider == 'bedrock':
                bedrock_config = config.get('bedrock', {})
                return cls(
                    provider='bedrock',
                    region=bedrock_config.get('region'),
                    model_id=bedrock_config.get('model_id'),
                    max_tokens=bedrock_config.get('max_tokens', 2000),
                    temperature=bedrock_config.get('temperature', 0.1),
                    aws_profile=profile
                )

        # No config file found - use smart detection if enabled
        if auto_detect_provider:
            provider = cls._detect_best_provider(aws_profile)
            
            if provider == 'bedrock':
                return cls(
                    provider='bedrock',
                    aws_profile=aws_profile,
                    region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                )
            elif provider == 'openai':
                return cls(provider='openai', aws_profile=aws_profile)

        # Fallback to original behavior with better error handling
        return cls._create_with_fallback(aws_profile)

    @classmethod
    def _detect_best_provider(cls, aws_profile: Optional[str] = None) -> str:
        """Detect the best available provider based on available credentials."""
        
        # Check OpenAI availability
        openai_available = bool(os.getenv('OPENAI_API_KEY'))
        
        # Check AWS/Bedrock availability
        bedrock_available = False
        try:
            session_manager = AWSSessionManager(profile_name=aws_profile)
            # Try to create a bedrock client to test access
            bedrock_client = session_manager.get_client('bedrock-runtime')
            bedrock_available = True
        except Exception:
            bedrock_available = False
        
        # Priority logic:
        # 1. If AWS profile is specified and Bedrock is available, prefer Bedrock
        # 2. If OpenAI is available and no AWS profile specified, use OpenAI
        # 3. If both available, prefer the one that doesn't require API keys (Bedrock with AWS profile)
        # 4. If neither available, provide helpful error
        
        if aws_profile and bedrock_available:
            return 'bedrock'
        elif openai_available and not aws_profile:
            return 'openai'
        elif bedrock_available:
            return 'bedrock'
        elif openai_available:
            return 'openai'
        else:
            raise ValueError(
                "No LLM provider available. Please either:\n"
                "1. Set OPENAI_API_KEY environment variable for OpenAI, or\n"
                "2. Configure AWS credentials/profile for Bedrock access, or\n"
                "3. Create a config file with provider settings"
            )

    @classmethod
    def _create_with_fallback(cls, aws_profile: Optional[str] = None):
        """Create TerraformGenerator with fallback logic when no config is found."""
        try:
            # Try to detect the best provider
            provider = cls._detect_best_provider(aws_profile)
            
            if provider == 'bedrock':
                return cls(
                    provider='bedrock',
                    aws_profile=aws_profile,
                    region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
                )
            else:  # OpenAI
                return cls(provider='openai', aws_profile=aws_profile)
                
        except ValueError as e:
            # If detection fails, provide helpful error message
            raise ValueError(f"Cannot initialize TerraformGenerator: {str(e)}")

    def generate_terraform(self, description: str, provider_version: str = "~> 5.0") -> str:
        """Generate Terraform code from natural language description."""

        # Create a comprehensive prompt for the LLM
        prompt = self._create_terraform_prompt(description)

        try:
            if self.provider == "openai":
                terraform_code = self._generate_with_openai(prompt)
            elif self.provider == "bedrock":
                terraform_code = self._generate_with_bedrock(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Add provider configuration
            provider_template = Template(self.templates['provider'])
            provider_config = provider_template.render(provider_version=provider_version)

            # Combine provider config with generated code
            full_terraform_code = f"{provider_config}\n{terraform_code}"

            return self._clean_terraform_code(full_terraform_code)

        except Exception as e:
            raise Exception(f"Failed to generate Terraform code: {str(e)}")

    def _generate_with_openai(self, prompt: str) -> str:
        """Generate Terraform code using OpenAI."""
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Terraform developer specializing in AWS infrastructure. Generate clean, production-ready Terraform code with proper resource naming, tags, and best practices."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content.strip()

    def _generate_with_bedrock(self, prompt: str) -> str:
        """Generate Terraform code using AWS Bedrock."""
        model_config = self.bedrock_model_configs.get(
            self.bedrock_model_id,
            {'input_format': 'anthropic', 'supports_system_prompt': True}
        )

        if model_config['input_format'] == 'anthropic':
            return self._call_anthropic_model(prompt)
        elif model_config['input_format'] == 'titan':
            return self._call_titan_model(prompt)
        elif model_config['input_format'] == 'ai21':
            return self._call_ai21_model(prompt)
        elif model_config['input_format'] == 'cohere':
            return self._call_cohere_model(prompt)
        else:
            raise ValueError(f"Unsupported model format: {model_config['input_format']}")

    def _call_anthropic_model(self, prompt: str) -> str:
        """Call Anthropic Claude models via Bedrock."""
        system_prompt = "You are an expert Terraform developer specializing in AWS infrastructure. Generate clean, production-ready Terraform code with proper resource naming, tags, and best practices."

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(body),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

    def _call_titan_model(self, prompt: str) -> str:
        """Call Amazon Titan models via Bedrock."""
        system_prompt = "You are an expert Terraform developer specializing in AWS infrastructure. Generate clean, production-ready Terraform code with proper resource naming, tags, and best practices."
        full_prompt = f"{system_prompt}\n\n{prompt}"

        body = {
            "inputText": full_prompt,
            "textGenerationConfig": {
                "maxTokenCount": self.max_tokens,
                "temperature": self.temperature,
                "topP": 0.9
            }
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(body),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        return response_body['results'][0]['outputText']

    def _call_ai21_model(self, prompt: str) -> str:
        """Call AI21 models via Bedrock."""
        system_prompt = "You are an expert Terraform developer specializing in AWS infrastructure. Generate clean, production-ready Terraform code with proper resource naming, tags, and best practices."
        full_prompt = f"{system_prompt}\n\n{prompt}"

        body = {
            "prompt": full_prompt,
            "maxTokens": self.max_tokens,
            "temperature": self.temperature,
            "topP": 0.9
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(body),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        return response_body['completions'][0]['data']['text']

    def _call_cohere_model(self, prompt: str) -> str:
        """Call Cohere models via Bedrock."""
        system_prompt = "You are an expert Terraform developer specializing in AWS infrastructure. Generate clean, production-ready Terraform code with proper resource naming, tags, and best practices."
        full_prompt = f"{system_prompt}\n\n{prompt}"

        body = {
            "prompt": full_prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "p": 0.9
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(body),
            contentType='application/json'
        )

        response_body = json.loads(response['body'].read())
        return response_body['generations'][0]['text']

    def get_available_models(self) -> List[Dict[str, str]]:
        """Get list of available Bedrock models for text generation."""
        if self.provider != "bedrock":
            return []

        try:
            bedrock_client = self.aws_session_manager.get_client('bedrock')
            response = bedrock_client.list_foundation_models(
                byOutputModality='TEXT'
            )

            models = []
            for model in response['modelSummaries']:
                if 'TEXT' in model.get('inputModalities', []):
                    models.append({
                        'model_id': model['modelId'],
                        'provider': model['providerName'],
                        'name': model['modelName']
                    })

            return models

        except Exception as e:
            print(f"Warning: Could not fetch available models: {str(e)}")
            return []

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider configuration."""
        info = {
            'provider': self.provider,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
        }

        if self.provider == 'openai':
            info.update({
                'model': self.openai_model,
                'api_key_configured': bool(self.api_key),
                'aws_profile': self.aws_profile
            })
        elif self.provider == 'bedrock':
            info.update({
                'region': self.bedrock_region,
                'model_id': self.bedrock_model_id,
                'available_models': len(self.get_available_models()),
                'aws_profile': self.aws_profile
            })

            # Add session info if we have a session manager
            if hasattr(self, 'aws_session_manager'):
                session_info = self.aws_session_manager.get_session_info()
                info.update({
                    'account_id': session_info.get('account_id'),
                    'user_arn': session_info.get('user_arn')
                })

        return info

    def _create_terraform_prompt(self, description: str) -> str:
        """Create a detailed prompt for Terraform code generation."""

        prompt = f"""
Generate Terraform code for the following AWS infrastructure requirement:

"{description}"

Requirements:
1. Use AWS provider version ~> 5.0
2. Include appropriate resource tags (Environment, Project, ManagedBy)
3. Use descriptive resource names with consistent naming convention
4. Include necessary variables for customization
5. Add outputs for important resource attributes
6. Follow Terraform best practices and AWS security guidelines
7. Include comments explaining complex configurations
8. Use data sources where appropriate
9. Ensure resources are properly configured for production use

Please provide only the Terraform resource definitions, variables, and outputs (no provider block as it will be added separately).

Focus on:
- Security best practices
- Cost optimization
- Scalability
- Maintainability

Return only valid Terraform HCL code without any markdown formatting or explanations.
"""
        return prompt

    def _clean_terraform_code(self, code: str) -> str:
        """Clean and format the generated Terraform code."""

        # Remove markdown code blocks if present
        if "```" in code:
            lines = code.split('\n')
            cleaned_lines = []
            in_code_block = False

            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block or line.strip() == '':
                    continue
                cleaned_lines.append(line)

            code = '\n'.join(cleaned_lines)

        # Remove extra whitespace and ensure proper formatting
        lines = [line.rstrip() for line in code.split('\n')]

        # Remove empty lines at the beginning and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        return '\n'.join(lines)

    def validate_terraform_syntax(self, terraform_code: str) -> Dict[str, Any]:
        """Basic validation of Terraform syntax (simplified)."""

        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Basic checks
        required_blocks = ['resource', 'variable', 'output']
        found_blocks = []

        lines = terraform_code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('resource '):
                found_blocks.append('resource')
            elif line.startswith('variable '):
                found_blocks.append('variable')
            elif line.startswith('output '):
                found_blocks.append('output')

        # Check for balanced braces
        open_braces = terraform_code.count('{')
        close_braces = terraform_code.count('}')

        if open_braces != close_braces:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Unbalanced braces: {open_braces} opening, {close_braces} closing")

        # Check for at least one resource
        if 'resource' not in found_blocks:
            validation_result['warnings'].append("No resources found in generated code")

        return validation_result

    def generate_terraform_plan_command(self, terraform_dir: str = ".") -> str:
        """Generate the terraform plan command for the generated code."""

        commands = [
            f"cd {terraform_dir}",
            "terraform init",
            "terraform validate",
            "terraform plan",
            "# To apply: terraform apply"
        ]

        return '\n'.join(commands)

    def get_resource_examples(self) -> Dict[str, str]:
        """Get examples of common AWS resources that can be generated."""

        examples = {
            "S3 Bucket": "Create an S3 bucket with versioning and encryption enabled",
            "VPC": "Create a VPC with public and private subnets across 2 availability zones",
            "EC2 Instance": "Launch a t3.micro EC2 instance with security group allowing SSH",
            "RDS Database": "Create a MySQL RDS instance with backup retention",
            "Lambda Function": "Create a Python Lambda function with IAM role",
            "API Gateway": "Set up REST API Gateway with Lambda integration",
            "CloudFront": "Create CloudFront distribution for S3 static website",
            "ECS Cluster": "Set up ECS cluster with Fargate service",
            "Load Balancer": "Create Application Load Balancer with target groups",
            "Auto Scaling": "Set up Auto Scaling Group with launch template"
        }

        return examples
