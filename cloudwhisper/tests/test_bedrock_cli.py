#!/usr/bin/env python3
"""
Tests for CLI commands related to Bedrock integration
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cloudwhisper.cli import main, list_models, provider_info, generate


class TestBedrockCLICommands:
    """Test CLI commands for Bedrock integration."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_list_models_command(self, mock_generator_class):
        """Test the list-models CLI command."""
        # Mock the generator and its methods
        mock_generator = MagicMock()
        mock_generator.get_available_models.return_value = [
            {
                'provider': 'Anthropic',
                'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'name': 'Claude 3 Sonnet'
            },
            {
                'provider': 'Amazon',
                'model_id': 'amazon.titan-text-express-v1',
                'name': 'Titan Text Express'
            }
        ]
        mock_generator_class.return_value = mock_generator

        # Run the command
        result = self.runner.invoke(list_models, ['--region', 'us-west-2'])

        # Verify the command executed successfully
        assert result.exit_code == 0
        assert 'Anthropic' in result.output
        assert 'Claude 3 Sonnet' in result.output
        assert 'Amazon' in result.output
        assert 'Titan Text Express' in result.output

        # Verify the generator was created with correct parameters
        mock_generator_class.assert_called_once_with(provider='bedrock', region='us-west-2')
        mock_generator.get_available_models.assert_called_once()

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_list_models_command_no_models(self, mock_generator_class):
        """Test list-models command when no models are available."""
        mock_generator = MagicMock()
        mock_generator.get_available_models.return_value = []
        mock_generator_class.return_value = mock_generator

        result = self.runner.invoke(list_models)

        assert result.exit_code == 0
        assert 'No models found' in result.output
        assert 'AWS credentials' in result.output

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_list_models_command_error(self, mock_generator_class):
        """Test list-models command error handling."""
        mock_generator_class.side_effect = Exception("AWS connection failed")

        result = self.runner.invoke(list_models)

        assert result.exit_code == 1
        assert 'Error listing models' in result.output
        assert 'AWS connection failed' in result.output

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_provider_info_command_openai(self, mock_generator_class):
        """Test provider-info command with OpenAI configuration."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key_configured': True,
            'max_tokens': 2000,
            'temperature': 0.1
        }
        mock_generator_class.from_config.return_value = mock_generator

        result = self.runner.invoke(provider_info)

        assert result.exit_code == 0
        assert 'openai' in result.output
        assert 'gpt-4' in result.output
        assert 'True' in result.output  # api_key_configured

        mock_generator_class.from_config.assert_called_once()
        mock_generator.get_provider_info.assert_called_once()

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_provider_info_command_bedrock(self, mock_generator_class):
        """Test provider-info command with Bedrock configuration."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {
            'provider': 'bedrock',
            'region': 'us-east-1',
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'available_models': 5,
            'max_tokens': 2000,
            'temperature': 0.1
        }
        mock_generator_class.from_config.return_value = mock_generator

        result = self.runner.invoke(provider_info)

        assert result.exit_code == 0
        assert 'bedrock' in result.output
        assert 'us-east-1' in result.output
        assert 'anthropic.claude-3-sonnet' in result.output
        assert 'list-models' in result.output  # Should show hint about list-models command

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_provider_info_command_error(self, mock_generator_class):
        """Test provider-info command error handling."""
        mock_generator_class.from_config.side_effect = Exception("Configuration error")

        result = self.runner.invoke(provider_info)

        assert result.exit_code == 1
        assert 'Error getting provider info' in result.output
        assert 'Configuration error' in result.output

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_generate_command_with_bedrock_provider(self, mock_generator_class):
        """Test generate command with explicit Bedrock provider."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {'provider': 'bedrock'}
        mock_generator.generate_terraform.return_value = '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_s3_bucket" "example" {
  bucket = "my-test-bucket"
}
'''
        mock_generator_class.return_value = mock_generator

        result = self.runner.invoke(generate, [
            'Create an S3 bucket',
            '--provider', 'bedrock',
            '--model', 'anthropic.claude-3-sonnet-20240229-v1:0',
            '--region', 'us-west-2'
        ])

        assert result.exit_code == 0
        assert 'Using bedrock provider' in result.output
        assert 'aws_s3_bucket' in result.output

        # Verify generator was created with correct parameters
        mock_generator_class.assert_called_once_with(
            provider='bedrock',
            region='us-west-2',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )
        mock_generator.generate_terraform.assert_called_once_with(
            'Create an S3 bucket', '~> 5.0'
        )

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_generate_command_with_openai_provider(self, mock_generator_class):
        """Test generate command with explicit OpenAI provider."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {'provider': 'openai'}
        mock_generator.generate_terraform.return_value = 'terraform code here'
        mock_generator_class.return_value = mock_generator

        result = self.runner.invoke(generate, [
            'Create a VPC',
            '--provider', 'openai',
            '--model', 'gpt-4'
        ])

        assert result.exit_code == 0
        assert 'Using openai provider' in result.output

        # Verify generator was created with OpenAI parameters
        mock_generator_class.assert_called_once_with(
            provider='openai',
            openai_model='gpt-4'
        )

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_generate_command_with_config_file(self, mock_generator_class):
        """Test generate command using configuration file."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {'provider': 'bedrock'}
        mock_generator.generate_terraform.return_value = 'terraform code'
        mock_generator_class.from_config.return_value = mock_generator

        result = self.runner.invoke(generate, ['Create an EC2 instance'])

        assert result.exit_code == 0
        assert 'Using bedrock provider' in result.output

        # Should use from_config when no explicit provider specified
        mock_generator_class.from_config.assert_called_once()

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_generate_command_with_output_file(self, mock_generator_class):
        """Test generate command with output file."""
        mock_generator = MagicMock()
        mock_generator.get_provider_info.return_value = {'provider': 'bedrock'}
        mock_generator.generate_terraform.return_value = '''
resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t3.micro"
}
'''
        mock_generator_class.from_config.return_value = mock_generator

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(generate, [
                'Create an EC2 instance',
                '--output', 'main.tf'
            ])

            assert result.exit_code == 0
            assert 'saved to main.tf' in result.output

            # Verify file was created
            with open('main.tf', 'r') as f:
                content = f.read()
                assert 'aws_instance' in content

    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_generate_command_error_handling(self, mock_generator_class):
        """Test generate command error handling."""
        mock_generator_class.from_config.side_effect = Exception("Model not available")

        result = self.runner.invoke(generate, ['Create an S3 bucket'])

        assert result.exit_code == 1
        assert 'Error generating Terraform code' in result.output
        assert 'Model not available' in result.output


class TestBedrockCLIIntegration:
    """Integration tests for Bedrock CLI commands."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('boto3.client')
    @patch('cloudwhisper.cli.TerraformGenerator')
    def test_end_to_end_bedrock_workflow(self, mock_generator_class, mock_boto_client):
        """Test end-to-end workflow using Bedrock."""
        # Mock Bedrock responses
        mock_generator = MagicMock()
        mock_generator.get_available_models.return_value = [
            {
                'provider': 'Anthropic',
                'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'name': 'Claude 3 Sonnet'
            }
        ]
        mock_generator.get_provider_info.return_value = {
            'provider': 'bedrock',
            'region': 'us-east-1',
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0'
        }
        mock_generator.generate_terraform.return_value = '''
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_s3_bucket" "example" {
  bucket = "my-terraform-bucket"

  tags = {
    Environment = "dev"
    Project     = "infrastructure"
    ManagedBy   = "CloudWhisper"
  }
}
'''
        mock_generator_class.return_value = mock_generator
        mock_generator_class.from_config.return_value = mock_generator

        # Test the workflow

        # 1. List available models
        result = self.runner.invoke(list_models)
        assert result.exit_code == 0
        assert 'Claude 3 Sonnet' in result.output

        # 2. Check provider info
        result = self.runner.invoke(provider_info)
        assert result.exit_code == 0
        assert 'bedrock' in result.output

        # 3. Generate Terraform code
        result = self.runner.invoke(generate, [
            'Create an S3 bucket with proper tags',
            '--provider', 'bedrock'
        ])
        assert result.exit_code == 0
        assert 'aws_s3_bucket' in result.output
        assert 'CloudWhisper' in result.output  # Check for tags


if __name__ == '__main__':
    pytest.main([__file__])
