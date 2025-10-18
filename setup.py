#!/usr/bin/env python3
"""
Setup script for Azure Function File Upload Service
This script installs dependencies and sets up the development environment
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3 or version.minor < 8:
        print("❌ Python 3.8 or higher is required for Azure Functions")
        return False
    
    print("✅ Python version is compatible")
    return True


def install_dependencies():
    """Install Python dependencies"""
    if not run_command("pip install --upgrade pip", "Upgrading pip"):
        return False
    
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Install additional development dependencies
    dev_deps = [
        "requests",  # For testing script
        "pytest",   # For unit testing
        "pytest-asyncio",  # For async test support
    ]
    
    for dep in dev_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep}"):
            print(f"⚠️  Failed to install {dep}, continuing...")
    
    return True


def check_azure_functions_tools():
    """Check if Azure Functions Core Tools is installed"""
    try:
        result = subprocess.run("func --version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Azure Functions Core Tools version: {version}")
            
            # Check if it's version 4.x
            if version.startswith("4."):
                return True
            else:
                print("⚠️  Azure Functions Core Tools v4 is recommended")
                return True
        else:
            raise subprocess.CalledProcessError(result.returncode, "func --version")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Azure Functions Core Tools not found")
        print("\nTo install Azure Functions Core Tools:")
        print("1. Install Node.js from https://nodejs.org/")
        print("2. Run: npm install -g azure-functions-core-tools@4 --unsafe-perm true")
        return False


def setup_local_environment():
    """Set up local development environment"""
    print("\n=== Setting up local environment ===")
    
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print("✅ Data directory created")
    
    # Check if local.settings.json needs updating
    local_settings = Path("local.settings.json")
    if local_settings.exists():
        print("✅ local.settings.json exists")
        print("⚠️  Please review and update the connection strings in local.settings.json")
        print("   - AZURE_STORAGE_CONNECTION_STRING")
        print("   - AZURE_SQL_CONNECTION_STRING (if using Azure SQL)")
    else:
        print("❌ local.settings.json not found")
        return False
    
    return True


def main():
    """Main setup function"""
    print("Azure Function File Upload Service - Setup Script")
    print("=" * 55)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Check Azure Functions Core Tools
    func_tools_ok = check_azure_functions_tools()
    
    # Setup local environment
    if not setup_local_environment():
        print("❌ Failed to setup local environment")
        sys.exit(1)
    
    print("\n" + "=" * 55)
    print("🎉 Setup completed!")
    
    if func_tools_ok:
        print("\n📋 Next steps:")
        print("1. Review and update local.settings.json with your Azure credentials")
        print("2. Start the function: func start")
        print("3. Test the function: python test_function.py")
    else:
        print("\n📋 Next steps:")
        print("1. Install Azure Functions Core Tools (see instructions above)")
        print("2. Review and update local.settings.json with your Azure credentials")
        print("3. Start the function: func start")
        print("4. Test the function: python test_function.py")
    
    print("\n📖 For more information, see README.md")


if __name__ == "__main__":
    main()