#!/usr/bin/env python3
"""
Script to set up the .env file with required credentials.

This script creates a .env file in the current directory based on the
env.template file. If the .env file already exists, it checks for missing
variables and adds them without overwriting existing user-configured values.
"""

import os
import secrets
import sys
from pathlib import Path

def setup_env_file():
    """
    Creates or updates the .env file based on env.template.
    """
    try:
        # Get the current directory (where the script is located)
        current_dir = Path(__file__).parent
        env_path = current_dir / '.env'
        template_path = current_dir / 'env.template'
        
        print(f"Checking for .env file at: {env_path}")
        print(f"Using template at: {template_path}")

        # Check if template exists
        if not template_path.exists():
            print(f"❌ Error: env.template not found at {template_path}")
            sys.exit(1)

        # Read the template file
        with open(template_path, 'r') as f:
            template_content = f.read()

        # Define default values for variables that need auto-generation
        default_values = {
            'POSTGRES_PASSWORD': secrets.token_hex(16),
            'LINKEDIN_LI_AT': '"Your_long_cookie_string_goes_here"'
        }

        existing_vars = {}
        if env_path.exists():
            print("Found existing .env file. Checking for missing variables...")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()
        else:
            print(".env file not found. Creating a new one from template.")

        # Process the template content
        processed_content = template_content
        
        # Replace default values in template with generated ones
        for key, default_value in default_values.items():
            # Look for the key in the template and replace its value
            lines = processed_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith(f'{key}='):
                    # If the variable already exists in .env, keep the existing value
                    if key in existing_vars:
                        lines[i] = f'{key}={existing_vars[key]}'
                    else:
                        lines[i] = f'{key}={default_value}'
                    break
            processed_content = '\n'.join(lines)

        # Write the processed content to .env file
        with open(env_path, 'w') as f:
            f.write(processed_content)

        if env_path.exists() and existing_vars:
            print("✅ .env file updated successfully!")
        else:
            print("🎉 Successfully created .env file from template!")

    except Exception as e:
        print(f"❌ Error setting up .env file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_env_file()