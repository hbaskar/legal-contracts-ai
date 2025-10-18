"""
Configuration management for Azure Function File Upload Service
Loads environment variables from .env files and system environment
"""

import os
from pathlib import Path
from typing import Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    
    # Load .env file if it exists
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logging.info(f"Loaded environment variables from {env_path}")
    else:
        # Try .env.local as fallback
        env_local_path = Path(__file__).parent.parent / '.env.local'
        if env_local_path.exists():
            load_dotenv(env_local_path)
            logging.info(f"Loaded environment variables from {env_local_path}")
        else:
            logging.info("No .env file found, using system environment variables")
            
except ImportError:
    logging.warning("python-dotenv not available, using system environment variables only")


class Config:
    """Configuration class for accessing environment variables"""
    
    # Azure Functions Core Settings
    AZURE_WEB_JOBS_STORAGE: str = os.getenv('AzureWebJobsStorage', 'UseDevelopmentStorage=true')
    FUNCTIONS_WORKER_RUNTIME: str = os.getenv('FUNCTIONS_WORKER_RUNTIME', 'python')
    AZURE_WEB_JOBS_FEATURE_FLAGS: str = os.getenv('AzureWebJobsFeatureFlags', 'EnableWorkerIndexing')
    PYTHON_ISOLATE_WORKER_DEPENDENCIES: str = os.getenv('PYTHON_ISOLATE_WORKER_DEPENDENCIES', '1')
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
    AZURE_STORAGE_CONTAINER_NAME: str = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'uploads')
    AZURE_STORAGE_ACCOUNT_URL: Optional[str] = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
    
    # Database Configuration - using your actual env variable names
    DATABASE_TYPE: str = os.getenv('DATABASE_TYPE', 'sqlite').lower()
    SQLITE_DATABASE_PATH: str = os.getenv('SQLITE_DATABASE_PATH', './data/metadata.db')
    
    # Azure SQL Configuration - using your actual variables
    AZURE_SQL_SERVER: Optional[str] = os.getenv('AZURE_SQL_SERVER')
    AZURE_SQL_DATABASE: Optional[str] = os.getenv('AZURE_SQL_DATABASE')
    AZURE_SQL_USERNAME: Optional[str] = os.getenv('AZURE_SQL_USERNAME')
    AZURE_SQL_PASSWORD: Optional[str] = os.getenv('AZURE_SQL_PASSWORD')
    AZURE_SQL_DRIVER: str = os.getenv('AZURE_SQL_DRIVER', 'ODBC Driver 18 for SQL Server')
    AZURE_SQL_PORT: int = int(os.getenv('AZURE_SQL_PORT', '1433'))
    
    # Construct connection string from individual components
    @property
    def AZURE_SQL_CONNECTION_STRING(self) -> Optional[str]:
        if self.AZURE_SQL_SERVER and self.AZURE_SQL_DATABASE:
            if self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD:
                # Check if username looks like an email (Azure AD)
                if '@' in self.AZURE_SQL_USERNAME:
                    # Use Azure AD authentication with username/password
                    return f"Driver={{{self.AZURE_SQL_DRIVER}}};Server=tcp:{self.AZURE_SQL_SERVER},{self.AZURE_SQL_PORT};Database={self.AZURE_SQL_DATABASE};Authentication=ActiveDirectoryPassword;UID={self.AZURE_SQL_USERNAME};PWD={self.AZURE_SQL_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
                else:
                    # Use SQL Server authentication
                    return f"Driver={{{self.AZURE_SQL_DRIVER}}};Server=tcp:{self.AZURE_SQL_SERVER},{self.AZURE_SQL_PORT};Database={self.AZURE_SQL_DATABASE};Uid={self.AZURE_SQL_USERNAME};Pwd={self.AZURE_SQL_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            else:
                # Use managed identity
                return f"Driver={{{self.AZURE_SQL_DRIVER}}};Server=tcp:{self.AZURE_SQL_SERVER},{self.AZURE_SQL_PORT};Database={self.AZURE_SQL_DATABASE};Authentication=ActiveDirectoryMsi;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        return os.getenv('AZURE_SQL_CONNECTION_STRING')
    
    # Application Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
    DEFAULT_SAS_EXPIRY_HOURS: int = int(os.getenv('DEFAULT_SAS_EXPIRY_HOURS', '24'))
    
    # Document Processing Configuration
    DEFAULT_CHUNKING_METHOD: str = os.getenv('DEFAULT_CHUNKING_METHOD', 'intelligent')
    
    # Logging and Monitoring
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # AI and Search Configuration
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_KEY: Optional[str] = os.getenv('AZURE_OPENAI_KEY')
    AZURE_OPENAI_API_VERSION: str = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
    AZURE_OPENAI_MODEL_DEPLOYMENT: str = os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt-4o-cms')
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002')
    AZURE_SEARCH_ENDPOINT: Optional[str] = os.getenv('AZURE_SEARCH_ENDPOINT')
    AZURE_SEARCH_KEY: Optional[str] = os.getenv('AZURE_SEARCH_KEY')
    AZURE_SEARCH_INDEX: str = os.getenv('AZURE_SEARCH_INDEX', 'legal-documents-gc')
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that required configuration values are present
        Returns True if configuration is valid, False otherwise
        """
        errors = []
        
        # Check database configuration
        if cls().DATABASE_TYPE == 'azuresql':
            sql_conn = cls().AZURE_SQL_CONNECTION_STRING
            if not sql_conn:
                # Check if we have individual ODBC components
                if not (cls.AZURE_SQL_SERVER and cls.AZURE_SQL_USERNAME and 
                       cls.AZURE_SQL_PASSWORD and cls.AZURE_SQL_DATABASE):
                    errors.append("Azure SQL connection information is required when DATABASE_TYPE is 'azuresql'. " +
                                "Either provide AZURE_SQL_CONNECTION_STRING or individual ODBC components " +
                                "(AZURE_SQL_SERVER, AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD, AZURE_SQL_DATABASE)")
        
        
        # Check storage configuration
        if not cls.AZURE_STORAGE_CONNECTION_STRING:
            errors.append("AZURE_STORAGE_CONNECTION_STRING must be configured")
        
        # Check container name
        if not cls.AZURE_STORAGE_CONTAINER_NAME:
            errors.append("AZURE_STORAGE_CONTAINER cannot be empty")
        
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
        
        return True
    
    @classmethod
    def get_environment_info(cls) -> dict:
        """Get current environment configuration info"""
        return {
            "database_type": cls().DATABASE_TYPE,
            "storage_container": cls.AZURE_STORAGE_CONTAINER_NAME,
            "max_file_size_mb": cls.MAX_FILE_SIZE_MB,
            "default_sas_expiry_hours": cls.DEFAULT_SAS_EXPIRY_HOURS,
            "default_chunking_method": cls().DEFAULT_CHUNKING_METHOD,
            "log_level": cls.LOG_LEVEL,
            "python_isolation": cls.PYTHON_ISOLATE_WORKER_DEPENDENCIES == '1',
            "sqlite_path": cls.SQLITE_DATABASE_PATH if cls().DATABASE_TYPE == 'sqlite' else None,
            "azure_sql_server": cls().AZURE_SQL_SERVER if cls().DATABASE_TYPE == 'azuresql' else None,
            "azure_sql_database": cls().AZURE_SQL_DATABASE if cls().DATABASE_TYPE == 'azuresql' else None,
            "openai_configured": bool(cls.AZURE_OPENAI_ENDPOINT and cls.AZURE_OPENAI_KEY),
            "search_configured": bool(cls.AZURE_SEARCH_ENDPOINT and cls.AZURE_SEARCH_KEY)
        }


# Create a global config instance
config = Config()

# Log configuration on import (but only once)
if not hasattr(config, '_logged'):
    logging.info("Configuration loaded successfully")
    if config.DATABASE_TYPE == 'sqlite':
        logging.info(f"Using SQLite database: {config.SQLITE_DATABASE_PATH}")
    elif config.DATABASE_TYPE == 'azuresql':
        logging.info(f"Using Azure SQL database: {config.AZURE_SQL_SERVER}/{config.AZURE_SQL_DATABASE}")
    
    logging.info(f"Storage container: {config.AZURE_STORAGE_CONTAINER_NAME}")
    config._logged = True