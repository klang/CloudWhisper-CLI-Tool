#!/usr/bin/env python3
"""
CloudWhisper Usage Examples

This script demonstrates how to use CloudWhisper programmatically.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import cloudwhisper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cloudwhisper.infrawhisper import TerraformGenerator
from cloudwhisper.cloudfuel import CostAnalyzer, CostOptimizer

def example_terraform_generation(aws_profile=None):
    """Example of generating Terraform code."""
    print("=== Terraform Generation Example ===")

    if aws_profile:
        print(f"Using AWS profile: {aws_profile}")

    # Initialize the generator (requires OPENAI_API_KEY environment variable)
    try:
        generator = TerraformGenerator(aws_profile=aws_profile)

        # Generate Terraform code for an S3 bucket
        description = "Create an S3 bucket with versioning enabled and server-side encryption"
        terraform_code = generator.generate_terraform(description)

        print("Generated Terraform code:")
        print(terraform_code)

        # Validate the generated code
        validation = generator.validate_terraform_syntax(terraform_code)
        print(f"\nValidation result: {'Valid' if validation['valid'] else 'Invalid'}")
        if validation['errors']:
            print("Errors:", validation['errors'])
        if validation['warnings']:
            print("Warnings:", validation['warnings'])

    except Exception as e:
        print(f"Error: {e}")

def example_bedrock_generation(aws_profile=None):
    """Example of generating Terraform code using AWS Bedrock."""
    print("\n=== Bedrock Terraform Generation Example ===")

    if aws_profile:
        print(f"Using AWS profile: {aws_profile}")

    try:
        # Initialize generator with Bedrock provider
        generator = TerraformGenerator(
            provider='bedrock',
            model_id='anthropic.claude-3-haiku-20240307-v1:0',
            aws_profile=aws_profile
        )

        # Show provider info
        provider_info = generator.get_provider_info()
        print(f"Using {provider_info['provider']} provider with {provider_info.get('model', 'default')} model")

        # Generate Terraform code for a VPC
        description = "Create a VPC with public and private subnets in two availability zones"
        terraform_code = generator.generate_terraform(description)

        print("Generated Terraform code:")
        print(terraform_code)

        # List available models
        models = generator.get_available_models()
        print(f"\nAvailable models: {len(models)} found")
        for model in models[:3]:  # Show first 3 models
            print(f"  - {model.get('model_id', model.get('modelId', 'Unknown'))}")
        print("  ...")

    except Exception as e:
        print(f"Error: {e}")

def example_cost_analysis(aws_profile=None):
    """Example of analyzing AWS costs."""
    print("\n=== Cost Analysis Example ===")

    if aws_profile:
        print(f"Using AWS profile: {aws_profile}")

    try:
        analyzer = CostAnalyzer(aws_profile=aws_profile)

        # Analyze costs for the last 7 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)

        cost_data = analyzer.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity='DAILY'
        )

        analyzer.display_cost_analysis(cost_data)

        # Get top services
        top_services = analyzer.get_top_services(start_date, end_date, limit=5)
        analyzer.display_top_services(top_services)

    except Exception as e:
        print(f"Error: {e}")

def example_cost_optimization(aws_profile=None):
    """Example of getting cost optimization recommendations."""
    print("\n=== Cost Optimization Example ===")

    if aws_profile:
        print(f"Using AWS profile: {aws_profile}")

    try:
        optimizer = CostOptimizer(aws_profile=aws_profile)

        # Analyze EC2 rightsizing opportunities
        ec2_recommendations = optimizer.analyze_ec2_rightsizing(days=30)
        optimizer.display_ec2_recommendations(ec2_recommendations)

        # Find idle resources
        idle_resources = optimizer.find_idle_resources(days=7)
        optimizer.display_idle_resources(idle_resources)

        # Get general recommendations
        general_recommendations = optimizer.get_general_recommendations(days=30)
        optimizer.display_general_recommendations(general_recommendations)

    except Exception as e:
        print(f"Error: {e}")

def example_s3_optimization(aws_profile=None):
    """Example of S3 optimization analysis."""
    print("\n=== S3 Optimization Example ===")

    if aws_profile:
        print(f"Using AWS profile: {aws_profile}")

    try:
        optimizer = CostOptimizer(aws_profile=aws_profile)

        # Analyze S3 buckets for optimization
        s3_recommendations = optimizer.analyze_s3_optimization()
        optimizer.display_s3_recommendations(s3_recommendations)

    except Exception as e:
        print(f"Error: {e}")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='CloudWhisper Usage Examples',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python usage_examples.py                    # Use default AWS profile
  python usage_examples.py --profile sandbox  # Use 'sandbox' AWS profile
  python usage_examples.py --openai-only      # Only run OpenAI examples
  python usage_examples.py --bedrock-only     # Only run Bedrock examples
  python usage_examples.py --cost-only        # Only run cost analysis examples
        '''
    )

    parser.add_argument(
        '--profile',
        type=str,
        help='AWS profile to use (from ~/.aws/credentials)'
    )

    parser.add_argument(
        '--openai-only',
        action='store_true',
        help='Only run OpenAI Terraform generation examples'
    )

    parser.add_argument(
        '--bedrock-only',
        action='store_true',
        help='Only run Bedrock Terraform generation examples'
    )

    parser.add_argument(
        '--cost-only',
        action='store_true',
        help='Only run cost analysis and optimization examples'
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    print("CloudWhisper Usage Examples")
    print("=" * 50)

    if args.profile:
        print(f"Using AWS profile: {args.profile}")
    else:
        print("Using default AWS profile")

    # Check for required environment variables
    if not args.cost_only and not os.getenv('OPENAI_API_KEY'):
        print("Warning: OPENAI_API_KEY not set. OpenAI-based Terraform generation will fail.")

    if not args.openai_only and not args.bedrock_only and not os.getenv('AWS_ACCESS_KEY_ID') and not args.profile:
        print("Warning: AWS credentials not set and no profile specified. AWS operations will fail.")

    print()

    # Run examples based on arguments
    if args.openai_only:
        example_terraform_generation(args.profile)
    elif args.bedrock_only:
        example_bedrock_generation(args.profile)
    elif args.cost_only:
        example_cost_analysis(args.profile)
        example_cost_optimization(args.profile)
        example_s3_optimization(args.profile)
    else:
        # Run all examples
        example_terraform_generation(args.profile)
        example_bedrock_generation(args.profile)
        example_cost_analysis(args.profile)
        example_cost_optimization(args.profile)
        example_s3_optimization(args.profile)

    print("\n=== Examples Complete ===")
    print("To use CloudWhisper CLI, run: cloudwhisper --help")
    if args.profile:
        print(f"To use CLI with profile, run: cloudwhisper --profile {args.profile} --help")
