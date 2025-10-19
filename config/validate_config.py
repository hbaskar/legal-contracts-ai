#!/usr/bin/env python3
"""
Configuration Validation Script

This script validates the current environment configuration and provides
helpful feedback about missing or incorrect settings.

Usage:
    python config/validate_config.py
    python config/validate_config.py --env local
    python config/validate_config.py --env staging
    python config/validate_config.py --env production
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    # Import from the config directory (this file's directory)
    import importlib.util
    config_dir = Path(__file__).parent
    
    # Import config.py directly
    config_spec = importlib.util.spec_from_file_location("config_module", config_dir / "config.py")
    config_module = importlib.util.module_from_spec(config_spec)
    config_spec.loader.exec_module(config_module)
    Config = config_module.Config
    
except ImportError as e:
    print(f"Error importing config module: {e}")
    print("Make sure you're running this script from the project root or install dependencies")
    sys.exit(1)


class ConfigValidator:
    """Validates configuration for different environments"""
    
    def __init__(self, environment: str = "local"):
        self.environment = environment
        self.config = Config()
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.info: List[str] = []
    
    def validate(self) -> bool:
        """Run all validation checks"""
        print(f"🔍 Validating configuration for {self.environment} environment...")
        print()
        
        # Core validations
        self._validate_azure_functions_core()
        self._validate_storage_configuration()
        self._validate_database_configuration()
        self._validate_ai_services()
        self._validate_application_settings()
        
        # Environment-specific validations
        if self.environment == "local":
            self._validate_local_environment()
        elif self.environment in ["staging", "development"]:
            self._validate_staging_environment()
        elif self.environment == "production":
            self._validate_production_environment()
        
        # Print results
        self._print_results()
        
        return len(self.errors) == 0
    
    def _validate_azure_functions_core(self):
        """Validate Azure Functions core settings"""
        self.info.append("📦 Azure Functions Core Settings")
        
        if not self.config.AZURE_WEB_JOBS_STORAGE:
            self.errors.append("AzureWebJobsStorage is required")
        elif self.config.AZURE_WEB_JOBS_STORAGE == "UseDevelopmentStorage=true":
            if self.environment == "production":
                self.errors.append("Production should not use development storage")
            else:
                self.info.append("✓ Using Azurite development storage")
        else:
            self.info.append("✓ Using Azure Storage for Functions runtime")
        
        if self.config.FUNCTIONS_WORKER_RUNTIME != "python":
            self.warnings.append("FUNCTIONS_WORKER_RUNTIME should be 'python'")
    
    def _validate_storage_configuration(self):
        """Validate Azure Storage configuration"""
        self.info.append("\n💾 Storage Configuration")
        
        if not self.config.AZURE_STORAGE_CONNECTION_STRING:
            self.errors.append("AZURE_STORAGE_CONNECTION_STRING is required")
        elif "UseDevelopmentStorage=true" in self.config.AZURE_STORAGE_CONNECTION_STRING:
            if self.environment == "production":
                self.errors.append("Production should not use development storage")
            else:
                self.info.append("✓ Using Azurite for blob storage")
        else:
            self.info.append("✓ Using Azure Blob Storage")
        
        if not self.config.AZURE_STORAGE_CONTAINER_NAME:
            self.warnings.append("AZURE_STORAGE_CONTAINER_NAME not set, using default 'uploads'")
        else:
            self.info.append(f"✓ Container name: {self.config.AZURE_STORAGE_CONTAINER_NAME}")
    
    def _validate_database_configuration(self):
        """Validate database configuration"""
        self.info.append("\n🗄️ Database Configuration")
        
        if self.config.DATABASE_TYPE == "sqlite":
            if self.environment == "production":
                self.warnings.append("SQLite not recommended for production")
            else:
                self.info.append("✓ Using SQLite for local development")
                
            if not os.path.exists(os.path.dirname(self.config.SQLITE_DATABASE_PATH)):
                self.warnings.append(f"SQLite directory does not exist: {os.path.dirname(self.config.SQLITE_DATABASE_PATH)}")
        
        elif self.config.DATABASE_TYPE == "azuresql":
            self.info.append("✓ Using Azure SQL Database")
            
            if not self.config.AZURE_SQL_SERVER:
                self.errors.append("AZURE_SQL_SERVER is required for Azure SQL")
            
            if not self.config.AZURE_SQL_DATABASE:
                self.errors.append("AZURE_SQL_DATABASE is required for Azure SQL")
            
            # Validate authentication method
            auth_method = getattr(self.config, 'AZURE_SQL_AUTH_METHOD', 'auto')
            self.info.append(f"✓ Authentication method: {auth_method}")
            
            if auth_method == "managed_identity":
                if self.environment == "local":
                    self.warnings.append("Managed identity may not work in local environment")
                else:
                    self.info.append("✓ Using managed identity (recommended for production)")
            
            elif auth_method in ["ad_password", "sql_auth"]:
                if not (self.config.AZURE_SQL_USERNAME and self.config.AZURE_SQL_PASSWORD):
                    self.errors.append(f"Username and password required for {auth_method}")
                
                if auth_method == "sql_auth" and self.environment == "production":
                    self.warnings.append("SQL authentication not recommended for production")
        
        else:
            self.errors.append(f"Invalid DATABASE_TYPE: {self.config.DATABASE_TYPE}")
    
    def _validate_ai_services(self):
        """Validate AI services configuration"""
        self.info.append("\n🤖 AI Services Configuration")
        
        # Azure OpenAI
        if self.config.AZURE_OPENAI_ENDPOINT:
            self.info.append("✓ Azure OpenAI endpoint configured")
            
            if not self.config.AZURE_OPENAI_KEY:
                self.warnings.append("AZURE_OPENAI_KEY not set - AI features may not work")
            
            if not self.config.AZURE_OPENAI_MODEL_DEPLOYMENT:
                self.warnings.append("AZURE_OPENAI_MODEL_DEPLOYMENT not set")
        else:
            self.warnings.append("Azure OpenAI not configured - AI features will be disabled")
        
        # Azure Search
        if self.config.AZURE_SEARCH_ENDPOINT:
            self.info.append("✓ Azure Search endpoint configured")
            
            if not self.config.AZURE_SEARCH_KEY:
                self.warnings.append("AZURE_SEARCH_KEY not set - search features may not work")
        else:
            self.warnings.append("Azure Search not configured - search features will be disabled")
    
    def _validate_application_settings(self):
        """Validate application settings"""
        self.info.append("\n⚙️ Application Settings")
        
        if self.config.MAX_FILE_SIZE_MB > 1000:
            self.warnings.append(f"Large max file size: {self.config.MAX_FILE_SIZE_MB}MB")
        
        if self.config.DEFAULT_SAS_EXPIRY_HOURS > 168:  # 1 week
            self.warnings.append(f"Long SAS expiry: {self.config.DEFAULT_SAS_EXPIRY_HOURS} hours")
        
        if self.config.LOG_LEVEL == "DEBUG" and self.environment == "production":
            self.warnings.append("DEBUG logging not recommended for production")
        
        self.info.append(f"✓ Max file size: {self.config.MAX_FILE_SIZE_MB}MB")
        self.info.append(f"✓ SAS expiry: {self.config.DEFAULT_SAS_EXPIRY_HOURS} hours")
        self.info.append(f"✓ Log level: {self.config.LOG_LEVEL}")
    
    def _validate_local_environment(self):
        """Validate local development environment"""
        self.info.append("\n🏠 Local Development Environment")
        
        # Check for Azurite
        if "UseDevelopmentStorage=true" in self.config.AZURE_STORAGE_CONNECTION_STRING:
            self.info.append("💡 Make sure Azurite is running: azurite --silent --location ./data")
        
        # Check for SQLite directory
        if self.config.DATABASE_TYPE == "sqlite":
            db_dir = os.path.dirname(self.config.SQLITE_DATABASE_PATH)
            if not os.path.exists(db_dir):
                self.info.append(f"💡 SQLite directory will be created: {db_dir}")
    
    def _validate_staging_environment(self):
        """Validate staging/development environment"""
        self.info.append("\n🧪 Staging/Development Environment")
        
        if self.config.DATABASE_TYPE != "azuresql":
            self.warnings.append("Staging should typically use Azure SQL to match production")
        
        if self.config.LOG_LEVEL != "DEBUG":
            self.info.append("💡 Consider using DEBUG log level for staging")
    
    def _validate_production_environment(self):
        """Validate production environment"""
        self.info.append("\n🚀 Production Environment")
        
        # Security checks
        if self.config.DATABASE_TYPE != "azuresql":
            self.errors.append("Production must use Azure SQL Database")
        
        auth_method = getattr(self.config, 'AZURE_SQL_AUTH_METHOD', 'auto')
        if auth_method == "sql_auth":
            self.warnings.append("Consider using managed identity instead of SQL authentication")
        
        if self.config.LOG_LEVEL == "DEBUG":
            self.warnings.append("DEBUG logging not recommended for production")
        
        if "UseDevelopmentStorage=true" in (self.config.AZURE_STORAGE_CONNECTION_STRING or ""):
            self.errors.append("Production cannot use development storage")
        
        # Key Vault recommendations
        if self.config.AZURE_OPENAI_KEY and not self.config.AZURE_OPENAI_KEY.startswith("@Microsoft.KeyVault"):
            self.warnings.append("Consider storing OpenAI key in Azure Key Vault")
        
        if self.config.AZURE_SEARCH_KEY and not self.config.AZURE_SEARCH_KEY.startswith("@Microsoft.KeyVault"):
            self.warnings.append("Consider storing Search key in Azure Key Vault")
    
    def _print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("📋 VALIDATION RESULTS")
        print("="*60)
        
        if self.info:
            for info in self.info:
                print(info)
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        print("\n" + "="*60)
        if self.errors:
            print("❌ Configuration validation FAILED")
            print("Please fix the errors above before proceeding.")
        elif self.warnings:
            print("⚠️  Configuration validation PASSED with warnings")
            print("Consider addressing the warnings above.")
        else:
            print("✅ Configuration validation PASSED")
            print("Your configuration looks good!")
        print("="*60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate Fresh Start configuration")
    parser.add_argument(
        "--env", 
        choices=["local", "staging", "development", "production"], 
        default="local",
        help="Target environment (default: local)"
    )
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.env)
    success = validator.validate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()