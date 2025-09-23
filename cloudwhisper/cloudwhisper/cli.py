#!/usr/bin/env python3

import click
import os
import sys
import yaml
from datetime import datetime, timedelta
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .infrawhisper import TerraformGenerator
from .cloudfuel import CostAnalyzer, CostOptimizer

console = Console()

@click.group()
@click.version_option(version="1.0.0")
@click.option('--profile', envvar='AWS_PROFILE', help='AWS profile to use (from ~/.aws/credentials)')
@click.pass_context
def main(ctx, profile):
    """
    CloudWhisper - AI-powered AWS infrastructure and cost optimization CLI tool

    Generate Terraform code from natural language and optimize your AWS costs.
    """
    # Store profile in context for sub-commands
    ctx.ensure_object(dict)
    ctx.obj['aws_profile'] = profile

@main.command()
@click.argument('description')
@click.option('--output', '-o', help='Output file for generated Terraform code')
@click.option('--provider-version', default='~> 5.0', help='AWS provider version')
@click.option('--provider', type=click.Choice(['openai', 'bedrock']), help='LLM provider to use')
@click.option('--model', help='Specific model to use (OpenAI model name or Bedrock model ID)')
@click.option('--region', help='AWS region for Bedrock (if using Bedrock)')
@click.pass_context
def generate(ctx, description, output, provider_version, provider, model, region):
    """Generate Terraform code from natural language description."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print(f"[bold blue]Generating Terraform code for:[/bold blue] {description}")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        # Initialize generator based on parameters or config
        if provider or model or region:
            # Use CLI parameters
            if provider == 'bedrock':
                generator = TerraformGenerator(
                    provider='bedrock',
                    region=region,
                    model_id=model,
                    aws_profile=aws_profile
                )
            else:
                generator = TerraformGenerator(
                    provider='openai',
                    openai_model=model or 'gpt-3.5-turbo',
                    aws_profile=aws_profile
                )
        else:
            # Use config file
            generator = TerraformGenerator.from_config(aws_profile=aws_profile)

        # Display provider info
        provider_info = generator.get_provider_info()
        console.print(f"[dim]Using {provider_info['provider']} provider[/dim]")

        terraform_code = generator.generate_terraform(description, provider_version)

        if output:
            with open(output, 'w') as f:
                f.write(terraform_code)
            console.print(f"[green]✓[/green] Terraform code saved to {output}")
        else:
            console.print("\n[bold yellow]Generated Terraform Code:[/bold yellow]")
            console.print(Panel(terraform_code, title="Terraform Configuration", border_style="green"))

    except Exception as e:
        console.print(f"[red]Error generating Terraform code:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--region', default='us-east-1', help='AWS region for Bedrock')
@click.pass_context
def list_models(ctx, region):
    """List available Bedrock models for text generation."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print(f"[bold blue]Fetching available Bedrock models in {region}...[/bold blue]")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        generator = TerraformGenerator(provider='bedrock', region=region, aws_profile=aws_profile)
        models = generator.get_available_models()

        if not models:
            console.print("[yellow]No models found or unable to fetch models.[/yellow]")
            console.print("[dim]Make sure you have proper AWS credentials and Bedrock access.[/dim]")
            return

        table = Table(title=f"Available Bedrock Models in {region}")
        table.add_column("Provider", style="cyan")
        table.add_column("Model ID", style="magenta")
        table.add_column("Model Name", style="green")

        for model in models:
            table.add_row(
                model['provider'],
                model['model_id'],
                model['name']
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing models:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.pass_context
def provider_info(ctx):
    """Show current LLM provider configuration and available providers."""
    try:
        aws_profile = ctx.obj.get('aws_profile')
        
        # Show detected providers
        console.print("[bold blue]Available Providers:[/bold blue]")
        
        available_providers = []
        
        # Check OpenAI
        if os.getenv('OPENAI_API_KEY'):
            available_providers.append(("OpenAI", "✓ API key configured"))
        else:
            available_providers.append(("OpenAI", "✗ No API key found"))
        
        # Check Bedrock
        try:
            from .aws_session import AWSSessionManager
            session_manager = AWSSessionManager(profile_name=aws_profile)
            session_manager.get_client('bedrock-runtime')
            available_providers.append(("AWS Bedrock", "✓ AWS credentials available"))
        except Exception:
            available_providers.append(("AWS Bedrock", "✗ No AWS credentials"))
        
        table = Table(title="Provider Availability")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        
        for provider, status in available_providers:
            table.add_row(provider, status)
        
        console.print(table)
        
        # Show current configuration
        try:
            generator = TerraformGenerator.from_config(aws_profile=aws_profile)
            info = generator.get_provider_info()
            
            console.print(f"\n[bold blue]Current Configuration:[/bold blue]")
            config_table = Table(title="Active LLM Provider Configuration")
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="green")
            
            for key, value in info.items():
                config_table.add_row(str(key).replace('_', ' ').title(), str(value))
            
            console.print(config_table)
            
            if info['provider'] == 'bedrock':
                console.print(f"\n[dim]Use 'cloudwhisper list-models --region {info.get('region', 'us-east-1')}' to see available models.[/dim]")
                
        except Exception as e:
            console.print(f"\n[yellow]No valid configuration found: {str(e)}[/yellow]")
            console.print("[dim]CloudWhisper will auto-detect the best available provider when needed.[/dim]")

    except Exception as e:
        console.print(f"[red]Error getting provider info:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--days', '-d', default=30, help='Number of days to analyze (default: 30)')
@click.option('--service', '-s', help='Specific AWS service to analyze')
@click.option('--granularity', default='DAILY', type=click.Choice(['DAILY', 'MONTHLY']),
              help='Cost data granularity')
@click.option('--group-by', multiple=True,
              type=click.Choice(['SERVICE', 'REGION', 'INSTANCE_TYPE', 'USAGE_TYPE']),
              help='Group costs by dimension')
@click.pass_context
def analyze_costs(ctx, days, service, granularity, group_by):
    """Analyze AWS costs and usage data."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print(f"[bold blue]Analyzing AWS costs for the last {days} days...[/bold blue]")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        analyzer = CostAnalyzer(aws_profile=aws_profile)

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Get cost data
        cost_data = analyzer.get_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            service_filter=service,
            group_by=list(group_by) if group_by else None
        )

        # Display results
        analyzer.display_cost_analysis(cost_data, service)

        # Get top services if no specific service requested
        if not service:
            top_services = analyzer.get_top_services(start_date, end_date, limit=10)
            analyzer.display_top_services(top_services)

    except Exception as e:
        console.print(f"[red]Error analyzing costs:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--service', '-s', help='Specific AWS service to optimize')
@click.option('--region', '-r', help='Specific AWS region to analyze')
@click.option('--days', '-d', default=30, help='Days of data to analyze for recommendations')
@click.pass_context
def optimize(ctx, service, region, days):
    """Get cost optimization recommendations."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print("[bold blue]Analyzing your AWS resources for optimization opportunities...[/bold blue]")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        optimizer = CostOptimizer(aws_profile=aws_profile)

        # Get recommendations based on service
        if service == 'ec2' or not service:
            console.print("\n[yellow]Analyzing EC2 instances...[/yellow]")
            ec2_recommendations = optimizer.analyze_ec2_rightsizing(region, days)
            optimizer.display_ec2_recommendations(ec2_recommendations)

        if service == 's3' or not service:
            console.print("\n[yellow]Analyzing S3 storage...[/yellow]")
            s3_recommendations = optimizer.analyze_s3_optimization(region)
            optimizer.display_s3_recommendations(s3_recommendations)

        if service == 'rds' or not service:
            console.print("\n[yellow]Analyzing RDS instances...[/yellow]")
            rds_recommendations = optimizer.analyze_rds_optimization(region)
            optimizer.display_rds_recommendations(rds_recommendations)

        # General recommendations
        console.print("\n[yellow]General optimization recommendations...[/yellow]")
        general_recommendations = optimizer.get_general_recommendations(days)
        optimizer.display_general_recommendations(general_recommendations)

    except Exception as e:
        console.print(f"[red]Error getting optimization recommendations:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--days', '-d', default=7, help='Number of days to look back for idle resources')
@click.option('--region', '-r', help='Specific AWS region to analyze')
@click.pass_context
def find_idle(ctx, days, region):
    """Find idle AWS resources that can be terminated to save costs."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print(f"[bold blue]Searching for idle resources in the last {days} days...[/bold blue]")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        optimizer = CostOptimizer(aws_profile=aws_profile)
        idle_resources = optimizer.find_idle_resources(days, region)
        optimizer.display_idle_resources(idle_resources)

    except Exception as e:
        console.print(f"[red]Error finding idle resources:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.pass_context
def savings_plans(ctx):
    """Get Savings Plans recommendations."""
    aws_profile = ctx.obj.get('aws_profile')

    try:
        console.print("[bold blue]Analyzing Savings Plans opportunities...[/bold blue]")

        # Show profile info if specified
        if aws_profile:
            console.print(f"[dim]Using AWS profile: {aws_profile}[/dim]")

        optimizer = CostOptimizer(aws_profile=aws_profile)
        recommendations = optimizer.get_savings_plans_recommendations()
        optimizer.display_savings_plans_recommendations(recommendations)

    except Exception as e:
        console.print(f"[red]Error getting Savings Plans recommendations:[/red] {str(e)}")
        sys.exit(1)

@main.command()
def list_profiles():
    """List available AWS profiles from ~/.aws/credentials."""
    try:
        from .aws_session import AWSSessionManager

        session_manager = AWSSessionManager()
        profiles = session_manager.list_profiles()

        if not profiles:
            console.print("[yellow]No AWS profiles found.[/yellow]")
            console.print("[dim]Run 'aws configure --profile <profile_name>' to create a profile.[/dim]")
            return

        console.print("[bold blue]Available AWS Profiles:[/bold blue]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Profile Name", style="cyan")
        table.add_column("Status", style="green")

        for profile in profiles:
            status = "✓ Available" if profile != 'default' else "✓ Default"
            table.add_row(profile, status)

        console.print(table)
        console.print(f"\n[dim]Use --profile <name> with any command to specify which profile to use.[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing profiles:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--profile', help='AWS profile to check (defaults to current/default)')
@click.pass_context
def aws_info(ctx, profile):
    """Display AWS account and session information."""
    try:
        from .aws_session import AWSSessionManager

        # Use the profile from the command option or fall back to the global one
        aws_profile = profile or ctx.obj.get('aws_profile')

        session_manager = AWSSessionManager(profile_name=aws_profile)
        info = session_manager.get_session_info()

        console.print("[bold blue]AWS Session Information:[/bold blue]")

        table = Table(show_header=False)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")

        table.add_row("Profile", info.get('profile', 'default'))
        table.add_row("Region", info.get('region', 'Not configured'))
        table.add_row("Account ID", info.get('account_id', 'Unable to determine'))
        table.add_row("User/Role", info.get('user_arn', 'Unable to determine'))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting AWS info:[/red] {str(e)}")
        sys.exit(1)

@main.command()
@click.option('--provider', type=click.Choice(['openai', 'bedrock', 'auto']), 
              default='auto', help='LLM provider to configure')
@click.pass_context
def setup(ctx, provider):
    """Interactive setup for CloudWhisper configuration."""
    aws_profile = ctx.obj.get('aws_profile')
    
    try:
        console.print("[bold blue]CloudWhisper Setup[/bold blue]")
        console.print("Let's configure your LLM provider for Terraform generation.\n")
        
        # Auto-detect available providers
        if provider == 'auto':
            try:
                provider = TerraformGenerator._detect_best_provider(aws_profile)
                console.print(f"[green]✓[/green] Auto-detected provider: {provider}")
            except ValueError as e:
                console.print(f"[yellow]Warning:[/yellow] {str(e)}")
                console.print("Please configure at least one provider manually.")
                return
        
        # Create config directory
        config_dir = os.path.expanduser("~/.cloudwhisper")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "config.yaml")
        
        # Generate configuration
        config = _generate_config(provider, aws_profile)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        console.print(f"[green]✓[/green] Configuration saved to {config_path}")
        console.print("\n[dim]You can now use CloudWhisper commands without additional setup.[/dim]")
        
        # Show the generated config
        console.print(f"\n[bold blue]Generated Configuration:[/bold blue]")
        console.print(Panel(yaml.dump(config, default_flow_style=False), title="config.yaml"))
        
    except Exception as e:
        console.print(f"[red]Error during setup:[/red] {str(e)}")
        sys.exit(1)

def _generate_config(provider: str, aws_profile: Optional[str] = None) -> dict:
    """Generate a configuration dictionary based on provider and profile."""
    config = {
        'llm': {
            'provider': provider
        }
    }
    
    if provider == 'openai':
        config['openai'] = {
            'model': 'gpt-3.5-turbo',
            'max_tokens': 2000,
            'temperature': 0.1
        }
        # Add note about API key
        config['# NOTE'] = 'Set OPENAI_API_KEY environment variable or add api_key field under openai section'
    
    elif provider == 'bedrock':
        config['bedrock'] = {
            'region': os.getenv('AWS_DEFAULT_REGION', 'eu-west-1'),
            'model_id': 'eu.anthropic.claude-3-7-sonnet-20250219-v1:0',
            'max_tokens': 2000,
            'temperature': 0.1
        }
    
    if aws_profile:
        config['aws'] = {
            'profile': aws_profile
        }
    
    return config

if __name__ == '__main__':
    main()
