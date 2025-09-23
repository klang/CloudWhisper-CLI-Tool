#!/usr/bin/env python3
"""
Basic tests for CloudWhisper CLI tool
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock

# Import the modules to test
from cloudwhisper.infrawhisper import TerraformGenerator
from cloudwhisper.cloudfuel import CostAnalyzer, CostOptimizer

class TestTerraformGenerator:
    """Test the TerraformGenerator class."""

    def test_init_openai_without_api_key(self):
        """Test OpenAI initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                TerraformGenerator(provider='openai')

    def test_init_openai_with_api_key(self):
        """Test OpenAI initialization with API key."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = TerraformGenerator(provider='openai')
            assert generator.provider == 'openai'
            assert generator.api_key == 'test-key'

    @patch('boto3.client')
    def test_init_bedrock(self, mock_boto_client):
        """Test Bedrock initialization."""
        generator = TerraformGenerator(provider='bedrock', region='us-east-1')
        assert generator.provider == 'bedrock'
        assert generator.bedrock_region == 'us-east-1'
        mock_boto_client.assert_called_with('bedrock-runtime', region_name='us-east-1')

    def test_init_invalid_provider(self):
        """Test initialization with invalid provider raises error."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            TerraformGenerator(provider='invalid')

    @patch('boto3.client')
    def test_bedrock_model_configs(self, mock_boto_client):
        """Test Bedrock model configurations are properly loaded."""
        generator = TerraformGenerator(provider='bedrock')

        # Check that model configurations exist
        assert 'anthropic.claude-3-sonnet-20240229-v1:0' in generator.bedrock_model_configs
        assert 'amazon.titan-text-express-v1' in generator.bedrock_model_configs

        # Check model config structure
        claude_config = generator.bedrock_model_configs['anthropic.claude-3-sonnet-20240229-v1:0']
        assert claude_config['input_format'] == 'anthropic'
        assert claude_config['supports_system_prompt'] is True

    @patch('boto3.client')
    def test_anthropic_model_call(self, mock_boto_client):
        """Test Anthropic model call via Bedrock."""
        # Mock the Bedrock client
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'resource "aws_s3_bucket" "test" { bucket = "test" }'}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )

        result = generator._call_anthropic_model("Create an S3 bucket")

        assert "aws_s3_bucket" in result
        mock_bedrock_client.invoke_model.assert_called_once()

    @patch('boto3.client')
    def test_titan_model_call(self, mock_boto_client):
        """Test Amazon Titan model call via Bedrock."""
        # Mock the Bedrock client
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'results': [{'outputText': 'resource "aws_s3_bucket" "test" { bucket = "test" }'}]
        }).encode()

        mock_bedrock_client = MagicMock()
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock_client

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='amazon.titan-text-express-v1'
        )

        result = generator._call_titan_model("Create an S3 bucket")

        assert "aws_s3_bucket" in result
        mock_bedrock_client.invoke_model.assert_called_once()

    @patch('boto3.client')
    def test_get_available_models(self, mock_boto_client):
        """Test getting available Bedrock models."""
        # Mock the Bedrock control plane client
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
                    'modelId': 'amazon.titan-text-express-v1',
                    'providerName': 'Amazon',
                    'modelName': 'Titan Text Express',
                    'inputModalities': ['TEXT'],
                    'outputModalities': ['TEXT']
                }
            ]
        }

        # Mock both bedrock-runtime and bedrock clients
        def mock_client_side_effect(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return MagicMock()
            elif service_name == 'bedrock':
                return mock_bedrock_control
            return MagicMock()

        mock_boto_client.side_effect = mock_client_side_effect

        generator = TerraformGenerator(provider='bedrock')
        models = generator.get_available_models()

        assert len(models) == 2
        assert models[0]['model_id'] == 'anthropic.claude-3-sonnet-20240229-v1:0'
        assert models[0]['provider'] == 'Anthropic'
        assert models[1]['model_id'] == 'amazon.titan-text-express-v1'

    def test_get_provider_info_openai(self):
        """Test getting provider info for OpenAI."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = TerraformGenerator(provider='openai', openai_model='gpt-4')
            info = generator.get_provider_info()

            assert info['provider'] == 'openai'
            assert info['model'] == 'gpt-4'
            assert info['api_key_configured'] is True

    @patch('boto3.client')
    def test_get_provider_info_bedrock(self, mock_boto_client):
        """Test getting provider info for Bedrock."""
        generator = TerraformGenerator(
            provider='bedrock',
            region='us-west-2',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )
        info = generator.get_provider_info()

        assert info['provider'] == 'bedrock'
        assert info['region'] == 'us-west-2'
        assert info['model_id'] == 'anthropic.claude-3-sonnet-20240229-v1:0'

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists')
    def test_from_config_openai(self, mock_exists, mock_open):
        """Test creating generator from config file with OpenAI."""
        mock_exists.return_value = True
        mock_config = """
llm:
  provider: openai
openai:
  api_key: test-key
  model: gpt-4
  max_tokens: 3000
  temperature: 0.2
"""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_config

        with patch('yaml.safe_load', return_value={
            'llm': {'provider': 'openai'},
            'openai': {
                'api_key': 'test-key',
                'model': 'gpt-4',
                'max_tokens': 3000,
                'temperature': 0.2
            }
        }):
            generator = TerraformGenerator.from_config()
            assert generator.provider == 'openai'
            assert generator.openai_model == 'gpt-4'
            assert generator.max_tokens == 3000
            assert generator.temperature == 0.2

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists')
    @patch('boto3.client')
    def test_from_config_bedrock(self, mock_boto_client, mock_exists, mock_open):
        """Test creating generator from config file with Bedrock."""
        mock_exists.return_value = True

        with patch('yaml.safe_load', return_value={
            'llm': {'provider': 'bedrock'},
            'bedrock': {
                'region': 'us-west-2',
                'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
                'max_tokens': 1500,
                'temperature': 0.3
            }
        }):
            generator = TerraformGenerator.from_config()
            assert generator.provider == 'bedrock'
            assert generator.bedrock_region == 'us-west-2'
            assert generator.bedrock_model_id == 'anthropic.claude-3-haiku-20240307-v1:0'
            assert generator.max_tokens == 1500
            assert generator.temperature == 0.3

    def test_clean_terraform_code(self):
        """Test cleaning of Terraform code."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = TerraformGenerator(provider='openai')

            # Test removing markdown code blocks
            code_with_markdown = '''```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
}
```'''

            cleaned = generator._clean_terraform_code(code_with_markdown)
            assert '```' not in cleaned
            assert 'resource "aws_s3_bucket" "example"' in cleaned

    def test_validate_terraform_syntax(self):
        """Test basic Terraform syntax validation."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = TerraformGenerator(provider='openai')

            # Test valid syntax
            valid_code = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
}
'''
            result = generator.validate_terraform_syntax(valid_code)
            assert result['valid'] is True
            assert len(result['errors']) == 0

            # Test invalid syntax (unbalanced braces)
            invalid_code = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
'''
            result = generator.validate_terraform_syntax(invalid_code)
            assert result['valid'] is False
            assert len(result['errors']) > 0

class TestCostAnalyzer:
    """Test the CostAnalyzer class."""

    @patch('boto3.client')
    def test_init(self, mock_boto_client):
        """Test CostAnalyzer initialization."""
        analyzer = CostAnalyzer()
        assert analyzer.region == 'us-east-1'
        # Verify boto3 clients were created
        assert mock_boto_client.call_count >= 2  # ce and cloudwatch clients

class TestCostOptimizer:
    """Test the CostOptimizer class."""

    @patch('boto3.client')
    def test_init(self, mock_boto_client):
        """Test CostOptimizer initialization."""
        optimizer = CostOptimizer()
        assert optimizer.region == 'us-east-1'
        # Verify boto3 clients were created
        assert mock_boto_client.call_count >= 5  # Multiple AWS service clients

    def test_analyze_instance_utilization(self):
        """Test instance utilization analysis."""
        with patch('boto3.client'):
            optimizer = CostOptimizer()

            # Test very low utilization
            result = optimizer._analyze_instance_utilization('i-123', 't3.micro', 5.0)
            assert result is not None
            assert result['recommendation'] == 'Consider downsizing or terminating'
            assert result['potential_savings'] == 'High'

            # Test low utilization
            result = optimizer._analyze_instance_utilization('i-123', 't3.micro', 20.0)
            assert result is not None
            assert result['recommendation'] == 'Consider downsizing'
            assert result['potential_savings'] == 'Medium'

            # Test high utilization
            result = optimizer._analyze_instance_utilization('i-123', 't3.micro', 85.0)
            assert result is not None
            assert result['recommendation'] == 'Consider upsizing'

            # Test normal utilization
            result = optimizer._analyze_instance_utilization('i-123', 't3.micro', 50.0)
            assert result is None

if __name__ == '__main__':
    pytest.main([__file__])
