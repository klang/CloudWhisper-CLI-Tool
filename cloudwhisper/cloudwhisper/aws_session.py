#!/usr/bin/env python3
"""
AWS Session Manager for CloudWhisper

Provides centralized AWS session management with profile support,
following the pattern from claude37.ipynb where boto3.Session(profile_name='sandbox') is used.
"""

import boto3
import os
from typing import Optional, Dict, Any, List
from botocore.exceptions import ProfileNotFound, NoCredentialsError, ClientError

class AWSSessionManager:
    """Centralized AWS session management with profile support."""

    def __init__(self, profile_name: Optional[str] = None, region_name: Optional[str] = None):
        """Initialize AWS session manager.

        Args:
            profile_name: AWS profile name (from ~/.aws/credentials)
            region_name: AWS region name
        """
        self.profile_name = profile_name
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self._session = None
        self._clients = {}

    @property
    def session(self) -> boto3.Session:
        """Get or create boto3 session."""
        if self._session is None:
            try:
                if self.profile_name:
                    self._session = boto3.Session(
                        profile_name=self.profile_name,
                        region_name=self.region_name
                    )
                else:
                    self._session = boto3.Session(region_name=self.region_name)
            except ProfileNotFound as e:
                raise ValueError(f"AWS profile '{self.profile_name}' not found. Check ~/.aws/credentials") from e
            except NoCredentialsError as e:
                raise ValueError("AWS credentials not found. Configure credentials or specify a profile.") from e

        return self._session

    def get_client(self, service_name: str, region_name: Optional[str] = None) -> boto3.client:
        """Get AWS service client with session.

        Args:
            service_name: AWS service name (e.g., 'bedrock-runtime', 'ec2')
            region_name: Override region for this client

        Returns:
            Configured boto3 client
        """
        # Use provided region or fall back to session region
        client_region = region_name or self.region_name

        # Create cache key
        cache_key = f"{service_name}:{client_region}"

        if cache_key not in self._clients:
            self._clients[cache_key] = self.session.client(
                service_name,
                region_name=client_region
            )

        return self._clients[cache_key]

    def get_available_profiles(self) -> List[str]:
        """Get list of available AWS profiles."""
        try:
            return boto3.Session().available_profiles
        except Exception:
            return []

    def validate_profile(self, profile_name: str) -> bool:
        """Validate if a profile exists and has valid credentials."""
        try:
            test_session = boto3.Session(profile_name=profile_name)
            # Try to get caller identity to validate credentials
            sts_client = test_session.client('sts')
            sts_client.get_caller_identity()
            return True
        except Exception:
            return False

    def get_session_info(self):
        """Get information about the current AWS session."""
        try:
            # Get identity information
            sts_client = self.get_client('sts')
            identity = sts_client.get_caller_identity()

            return {
                'profile': self.profile_name or 'default',
                'region': self.session.region_name,
                'account_id': identity.get('Account'),
                'user_arn': identity.get('Arn'),
                'user_id': identity.get('UserId')
            }
        except Exception as e:
            return {
                'profile': self.profile_name or 'default',
                'region': self.session.region_name,
                'error': str(e)
            }

    def list_profiles(self):
        """List all available AWS profiles from ~/.aws/credentials."""
        try:
            import configparser
            import os

            credentials_path = os.path.expanduser('~/.aws/credentials')
            if not os.path.exists(credentials_path):
                return []

            config = configparser.ConfigParser()
            config.read(credentials_path)

            # Return all sections (profiles)
            return config.sections()
        except Exception:
            return []

    def get_credentials(self) -> Dict[str, Any]:
        """Get current credentials information."""
        try:
            credentials = self.session.get_credentials()
            if credentials:
                return {
                    'access_key': credentials.access_key[:8] + '...' if credentials.access_key else None,
                    'secret_key': '***' if credentials.secret_key else None,
                    'session_token': bool(credentials.token),
                    'method': credentials.method if hasattr(credentials, 'method') else 'unknown'
                }
            else:
                return {'error': 'No credentials found'}
        except Exception as e:
            return {'error': str(e)}

    def list_regions(self, service_name: str = 'ec2') -> List[str]:
        """Get list of available regions for a service."""
        try:
            client = self.get_client(service_name)
            regions = client.describe_regions()
            return [region['RegionName'] for region in regions['Regions']]
        except Exception:
            # Fallback to common regions if describe_regions fails
            return [
                'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
                'eu-west-1', 'eu-west-2', 'eu-central-1',
                'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
            ]

    def switch_region(self, new_region: str):
        """Switch to a different region (clears client cache)."""
        self.region_name = new_region
        self._clients.clear()  # Clear cached clients to use new region

    def clone_for_region(self, region_name: str) -> 'AWSSessionManager':
        """Create a new session manager for a different region."""
        return AWSSessionManager(
            profile_name=self.profile_name,
            region_name=region_name
        )
