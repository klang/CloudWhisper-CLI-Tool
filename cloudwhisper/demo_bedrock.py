#!/usr/bin/env python3
"""
Demo script showing the new Bedrock integration in CloudWhisper
"""

import os
import yaml
import tempfile
from unittest.mock import patch, MagicMock
from cloudwhisper.infrawhisper import TerraformGenerator

def demo_bedrock_integration():
    """Demonstrate the new Bedrock integration capabilities."""

    print("🚀 CloudWhisper Bedrock Integration Demo")
    print("=" * 50)

    # 1. Show direct initialization
    print("\n1. Direct Bedrock Initialization:")
    print("-" * 35)

    with patch('boto3.client') as mock_boto:
        mock_boto.return_value = MagicMock()

        generator = TerraformGenerator(
            provider='bedrock',
            region='us-east-1',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0',
            max_tokens=2000,
            temperature=0.1
        )

        print(f"✅ Provider: {generator.provider}")
        print(f"✅ Region: {generator.bedrock_region}")
        print(f"✅ Model: {generator.bedrock_model_id}")
        print(f"✅ Max Tokens: {generator.max_tokens}")
        print(f"✅ Temperature: {generator.temperature}")

    # 2. Show configuration file loading
    print("\n2. Configuration File Loading:")
    print("-" * 35)

    config = {
        'llm': {'provider': 'bedrock'},
        'bedrock': {
            'region': 'us-west-2',
            'model_id': 'anthropic.claude-3-haiku-20240307-v1:0',
            'max_tokens': 1500,
            'temperature': 0.2
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name

    try:
        with patch('boto3.client'):
            generator = TerraformGenerator.from_config(config_path)
            print(f"✅ Loaded from config: {generator.provider}")
            print(f"✅ Region: {generator.bedrock_region}")
            print(f"✅ Model: {generator.bedrock_model_id}")
    finally:
        os.unlink(config_path)

    # 3. Show provider info
    print("\n3. Provider Information:")
    print("-" * 25)

    with patch('boto3.client'):
        generator = TerraformGenerator(provider='bedrock')
        info = generator.get_provider_info()

        for key, value in info.items():
            print(f"✅ {key.replace('_', ' ').title()}: {value}")

    # 4. Show available models (mocked)
    print("\n4. Available Models (Demo):")
    print("-" * 30)

    mock_models = [
        {'provider': 'Anthropic', 'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0', 'name': 'Claude 3 Sonnet'},
        {'provider': 'Anthropic', 'model_id': 'anthropic.claude-3-haiku-20240307-v1:0', 'name': 'Claude 3 Haiku'},
        {'provider': 'Anthropic', 'model_id': 'anthropic.claude-3-opus-20240229-v1:0', 'name': 'Claude 3 Opus'},
        {'provider': 'Amazon', 'model_id': 'amazon.titan-text-express-v1', 'name': 'Titan Text Express'},
        {'provider': 'AI21 Labs', 'model_id': 'ai21.j2-ultra-v1', 'name': 'Jurassic-2 Ultra'},
        {'provider': 'Cohere', 'model_id': 'cohere.command-text-v14', 'name': 'Command'}
    ]

    for model in mock_models:
        print(f"✅ {model['provider']}: {model['name']} ({model['model_id']})")

    # 5. Show model-specific configurations
    print("\n5. Model-Specific Configurations:")
    print("-" * 35)

    with patch('boto3.client'):
        generator = TerraformGenerator(provider='bedrock')

        print("✅ Supported model formats:")
        for model_id, config in generator.bedrock_model_configs.items():
            print(f"   • {model_id}: {config['input_format']} format")

    # 6. Demo different model calls (mocked)
    print("\n6. Model Call Demonstrations:")
    print("-" * 32)

    with patch('boto3.client') as mock_boto:
        mock_bedrock_client = MagicMock()
        mock_boto.return_value = mock_bedrock_client

        # Mock Anthropic response
        mock_response = {'body': MagicMock()}
        mock_response['body'].read.return_value = b'{"content": [{"text": "terraform code here"}]}'
        mock_bedrock_client.invoke_model.return_value = mock_response

        generator = TerraformGenerator(
            provider='bedrock',
            model_id='anthropic.claude-3-sonnet-20240229-v1:0'
        )

        result = generator._call_anthropic_model("Create an S3 bucket")
        print(f"✅ Anthropic call successful: {result}")

        # Mock Titan response
        mock_response['body'].read.return_value = b'{"results": [{"outputText": "terraform code here"}]}'

        generator.bedrock_model_id = 'amazon.titan-text-express-v1'
        result = generator._call_titan_model("Create a VPC")
        print(f"✅ Titan call successful: {result}")

    print("\n🎉 Demo completed successfully!")
    print("\nKey features implemented:")
    print("• ✅ Multiple LLM provider support (OpenAI + Bedrock)")
    print("• ✅ Configuration file support")
    print("• ✅ Multiple Bedrock models (Claude, Titan, AI21, Cohere)")
    print("• ✅ CLI commands (list-models, provider-info)")
    print("• ✅ Comprehensive error handling")
    print("• ✅ Backward compatibility with OpenAI")
    print("• ✅ Extensive test coverage")

if __name__ == '__main__':
    demo_bedrock_integration()
