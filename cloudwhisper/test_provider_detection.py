#!/usr/bin/env python3
"""Test script to verify provider detection functionality."""

import os
import sys
sys.path.insert(0, '/Users/klang/projects/CloudWhisper-CLI-Tool/cloudwhisper')

from cloudwhisper.infrawhisper import TerraformGenerator

def test_provider_detection():
    """Test the provider detection logic."""
    
    print("Testing provider detection...")
    
    # Test 1: Check what providers are available
    try:
        # Check with no AWS profile
        print("\n1. Testing detection with no AWS profile:")
        provider = TerraformGenerator._detect_best_provider(None)
        print(f"   Detected provider: {provider}")
    except ValueError as e:
        print(f"   Error: {e}")
    
    # Test 2: Check with AWS profile
    try:
        print("\n2. Testing detection with AWS profile 'default':")
        provider = TerraformGenerator._detect_best_provider('default')
        print(f"   Detected provider: {provider}")
    except ValueError as e:
        print(f"   Error: {e}")
    
    # Test 3: Test from_config with auto-detection
    try:
        print("\n3. Testing from_config with auto-detection:")
        generator = TerraformGenerator.from_config()
        info = generator.get_provider_info()
        print(f"   Using provider: {info['provider']}")
        print(f"   Configuration: {info}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Show environment status
    print("\n4. Environment status:")
    print(f"   OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print(f"   AWS_PROFILE: {os.getenv('AWS_PROFILE', 'Not set')}")
    print(f"   AWS_DEFAULT_REGION: {os.getenv('AWS_DEFAULT_REGION', 'Not set')}")

if __name__ == "__main__":
    test_provider_detection()