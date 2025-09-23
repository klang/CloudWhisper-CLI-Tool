#!/usr/bin/env python3
"""
Comprehensive tests for AWS Bedrock integration in CloudWhisper CLI tool
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError

from cloudwhisper.infrawhisper import TerraformGenerator


class TestBedrockIntegration:
    """Test AWS Bedrock integration functionality."""

    @patch('boto3.client')
    def test_bedrock_client_initialization(self, mock_boto_client):
        """Test proper initialization of Bedrock client."""
        generator = TerraformGenerator(
            provider='bedrock',
            region='us-west-2',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )

        # Verify client was created with correct parameters
        mock_boto_client.assert_called_with(
            'bedrock-runtime',
            region_name='us-west-2'
        )

        assert generator.bedrock_region == 'us-west-2'
        assert generator.bedrock_model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'

    @patch('boto3.client')
    def test_bedrock_client_initialization_failure(self, mock_boto_client):
        """Test handling of Bedrock client initialization failure."""
        mock_boto_client.side_effect = Exception("AWS credentials not found")

        with pytest.raises(ValueError, match="Failed to initialize Bedrock client"):
            TerraformGenerator(provider='bedrock')

    @patch('boto3.client')
    def test_generate_terraform_with_anthropic_model(self, mock_boto_client):
        """Test Terraform generation using Anthropic Claude model."""
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        terraform_code = '''
resource "aws_s3_bucket" "example" {
  bucket        = "my-terraform-bucket"
  force_destroy = false

  tags = {
    Environment = "dev"
    Project     = "infrastructure"
    ManagedBy   = "CloudWhisper"
  }
}

resource "aws_s3_bucket_versioning" "example" {
  bucket = aws_s3_bucket.example.id
  versioning_configuration {
    status = "Enabled"
  }
}

output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.example.id
}
'''
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': terraform_code}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )

        result = generator.generate_terraform("Create an S3 bucket with versioning enabled")

        # Verify the request was made correctly
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args

        assert call_args[1]['modelId'] == 'anthropic.claude-3-sonnet-20240229-v1:0'
        assert call_args[1]['contentType'] == 'application/json'

        # Parse the request body
        request_body = json.loads(call_args[1]['body'])
        assert request_body['anthropic_version'] == 'bedrock-2023-05-31'
        assert 'system' in request_body
        assert len(request_body['messages']) == 1
        assert request_body['messages'][0]['role'] == 'user'

        # Verify the result contains expected elements
        assert 'terraform {' in result
        assert 'provider "aws"' in result
        assert 'aws_s3_bucket' in result
        assert 'versioning' in result

    @patch('boto3.client')
    def test_generate_terraform_with_titan_model(self, mock_boto_client):
        """Test Terraform generation using Amazon Titan model."""
        # Mock Bedrock response for Titan
        mock_response = {
            'body': MagicMock()
        }
        terraform_code = '''
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "main-vpc"
    Environment = "dev"
    Project     = "infrastructure"
    ManagedBy   = "CloudWhisper"
  }
}
'''
        mock_response['body'].read.return_value = json.dumps({
            'results': [{'outputText': terraform_code}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='amazon.titan-text-express-v1'
        )

        result = generator.generate_terraform("Create a VPC with DNS support")

        # Verify Titan-specific request format
        call_args = mock_bedrock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])

        assert 'inputText' in request_body
        assert 'textGenerationConfig' in request_body
        assert request_body['textGenerationConfig']['maxTokenCount'] == 2000

        # Verify result
        assert 'aws_vpc' in result
        assert 'cidr_block' in result

    @patch('boto3.client')
    def test_model_error_handling(self, mock_boto_client):
        """Test handling of model invocation errors."""
        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'Model not found'
                }
            },
            operation_name='InvokeModel'
        )
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(provider='bedrock')

        with pytest.raises(Exception, match="Failed to generate Terraform code"):
            generator.generate_terraform("Create an S3 bucket")

    @patch('boto3.client')
    def test_get_available_models_success(self, mock_boto_client):
        """Test successful retrieval of available models."""
        # Mock the bedrock control plane client
        mock_bedrock_control = MagicMock()
        mock_bedrock_control.list_foundation_models.return_value = {
            'modelSummaries': [
                {
                    'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
                    'providerName': 'Anthropic',
                    'modelName': 'Claude 3 Sonnet',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                },
                {
                    'modelId': 'anthropic.claude-3-haiku-20240307-v1:0',
                    'providerName': 'Anthropic',
                    'modelName': 'Claude 3 Haiku',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                },
                {
                    'modelId': 'amazon.titan-text-express-v1',
                    'providerName': 'Amazon',
                    'modelName': 'Titan Text Express',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                },
                {
                    'modelId': 'ai21.j2-ultra-v1',
                    'providerName': 'AI21 Labs',
                    'modelName': 'Jurassic-2 Ultra',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                }
            ]
        }

        def mock_client_factory(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return MagicMock()
            elif service_name == 'bedrock':
                return mock_bedrock_control
            return MagicMock()

        mock_boto_client.side_effect = mock_client_factory

        generator = TerraformGenerator(provider='bedrock')
        models = generator.get_available_models()

        assert len(models) == 4

        # Check specific models
        claude_sonnet = next(m for m in models if 'sonnet' in m['model_id'])
        assert claude_sonnet['provider'] == 'Anthropic'
        assert claude_sonnet['name'] == 'Claude 3 Sonnet'

        titan = next(m for m in models if 'titan' in m['model_id'])
        assert titan['provider'] == 'Amazon'

        ai21 = next(m for m in models if 'ai21' in m['model_id'])
        assert ai21['provider'] == 'AI21 Labs'

    @patch('boto3.client')
    def test_get_available_models_with_openai_provider(self, mock_boto_client):
        """Test that get_available_models returns empty list for OpenAI provider."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = TerraformGenerator(provider='openai')
            models = generator.get_available_models()
            assert models == []

    @patch('boto3.client')
    def test_get_available_models_error_handling(self, mock_boto_client):
        """Test error handling when fetching available models fails."""
        mock_bedrock_control = MagicMock()
        mock_bedrock_control.list_foundation_models.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized'
                }
            },
            operation_name='ListFoundationModels'
        )

        def mock_client_factory(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return MagicMock()
            elif service_name == 'bedrock':
                return mock_bedrock_control
            return MagicMock()

        mock_boto_client.side_effect = mock_client_factory

        generator = TerraformGenerator(provider='bedrock')

        # Should return empty list and print warning (captured by mock)
        with patch('builtins.print') as mock_print:
            models = generator.get_available_models()
            assert models == []
            mock_print.assert_called_once()
            assert "Warning: Could not fetch available models" in mock_print.call_args[0][0]

    @patch('boto3.client')
    def test_unsupported_model_format(self, mock_boto_client):
        """Test handling of unsupported model format."""
        generator = TerraformGenerator(provider='bedrock')

        # Manually set an unsupported model ID
        generator.bedrock_model_id = 'unsupported.model-v1'

        with pytest.raises(ValueError, match="Unsupported model format"):
            generator._generate_with_bedrock("test prompt")

    @patch('boto3.client')
    def test_ai21_model_call(self, mock_boto_client):
        """Test AI21 model call formatting."""
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'completions': [{'data': {'text': 'resource "aws_instance" "test" {}'}}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='ai21.j2-ultra-v1'
        )

        result = generator._call_ai21_model("Create an EC2 instance")

        # Verify AI21-specific request format
        call_args = mock_bedrock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])

        assert 'prompt' in request_body
        assert 'maxTokens' in request_body
        assert 'temperature' in request_body
        assert request_body['maxTokens'] == 2000

        assert 'aws_instance' in result

    @patch('boto3.client')
    def test_cohere_model_call(self, mock_boto_client):
        """Test Cohere model call formatting."""
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'generations': [{'text': 'resource "aws_lambda_function" "test" {}'}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='cohere.command-text-v14'
        )

        result = generator._call_cohere_model("Create a Lambda function")

        # Verify Cohere-specific request format
        call_args = mock_bedrock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]['body'])

        assert 'prompt' in request_body
        assert 'max_tokens' in request_body
        assert 'temperature' in request_body
        assert 'p' in request_body  # Cohere uses 'p' instead of 'topP'

        assert 'aws_lambda_function' in result

    @patch('boto3.client')
    def test_configuration_priority(self, mock_boto_client):
        """Test that explicit parameters override environment variables."""
        with patch.dict(os.environ, {
            'AWS_DEFAULT_REGION': 'us-east-1',
            'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1'
        }):
            generator = TerraformGenerator(
                provider='bedrock',
                region='eu-west-1',
                model_id='anthropic.claude-3-sonnet-20240229-v1:0'
            )

            # Explicit parameters should take precedence
            assert generator.bedrock_region == 'eu-west-1'
            assert generator.bedrock_model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'

    @patch('boto3.client')
    def test_environment_variable_fallback(self, mock_boto_client):
        """Test fallback to environment variables when parameters not provided."""
        with patch.dict(os.environ, {
            'AWS_DEFAULT_REGION': 'ap-southeast-1',
            'BEDROCK_MODEL_ID': 'ai21.j2-ultra-v1'
        }):
            generator = TerraformGenerator(provider='bedrock')

            # Should use environment variables
            assert generator.bedrock_region == 'ap-southeast-1'
            assert generator.bedrock_model_id == 'ai21.j2-ultra-v1'

    @patch('boto3.client')
    def test_default_values(self, mock_boto_client):
        """Test default values when no parameters or environment variables provided."""
        with patch.dict(os.environ, {}, clear=True):
            generator = TerraformGenerator(provider='bedrock')

            # Should use defaults
            assert generator.bedrock_region == 'us-east-1'
            assert generator.bedrock_model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'


class TestBedrockErrorScenarios:
    """Test error scenarios specific to Bedrock integration."""

    @patch('boto3.client')
    def test_invalid_model_id_error(self, mock_boto_client):
        """Test handling of invalid model ID."""
        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': 'The provided model identifier is invalid'
                }
            },
            operation_name='InvokeModel'
        )
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='invalid.model.id'
        )

        with pytest.raises(Exception, match="Failed to generate Terraform code"):
            generator.generate_terraform("Create an S3 bucket")

    @patch('boto3.client')
    def test_access_denied_error(self, mock_boto_client):
        """Test handling of access denied errors."""
        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'User is not authorized to perform: bedrock:InvokeModel'
                }
            },
            operation_name='InvokeModel'
        )
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(provider='bedrock')

        with pytest.raises(Exception, match="Failed to generate Terraform code"):
            generator.generate_terraform("Create an S3 bucket")

    @patch('boto3.client')
    def test_throttling_error(self, mock_boto_client):
        """Test handling of throttling errors."""
        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ThrottlingException',
                    'Message': 'Too many requests'
                }
            },
            operation_name='InvokeModel'
        )
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(provider='bedrock')

        with pytest.raises(Exception, match="Failed to generate Terraform code"):
            generator.generate_terraform("Create an S3 bucket")


if __name__ == '__main__':
    pytest.main([__file__])
