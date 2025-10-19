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


def log_environment_variables():
    """Log all environment variables for debugging purposes"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("ENVIRONMENT VARIABLES LOADED")
    logger.info("=" * 60)
    
    # Get all environment variables and sort them
    env_vars = dict(os.environ)
    
    # Categorize environment variables
    azure_vars = {k: v for k, v in env_vars.items() if k.upper().startswith(('AZURE', 'FUNCTIONS'))}
    database_vars = {k: v for k, v in env_vars.items() if 'DATABASE' in k.upper() or 'SQL' in k.upper()}
    openai_vars = {k: v for k, v in env_vars.items() if 'OPENAI' in k.upper()}
    search_vars = {k: v for k, v in env_vars.items() if 'SEARCH' in k.upper()}
    storage_vars = {k: v for k, v in env_vars.items() if 'STORAGE' in k.upper() and not k.upper().startswith('AZURE')}
    
    def log_vars_safely(category, vars_dict):
        """Log variables safely, masking sensitive values"""
        if not vars_dict:
            logger.info(f"{category}: No variables found")
            return
            
        logger.info(f"{category}:")
        for key, value in sorted(vars_dict.items()):
            # Mask sensitive values
            if any(sensitive in key.upper() for sensitive in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'CONNECTION']):
                masked_value = value[:8] + "***" if len(value) > 8 else "***"
                logger.info(f"  {key} = {masked_value}")
            else:
                logger.info(f"  {key} = {value}")
        logger.info("")
    
    log_vars_safely("Azure & Functions", azure_vars)
    log_vars_safely("Database", database_vars)
    log_vars_safely("OpenAI", openai_vars)
    log_vars_safely("Search", search_vars)
    log_vars_safely("Storage", storage_vars)
    
    # Log other important variables
    other_vars = {k: v for k, v in env_vars.items() 
                  if not any(category in k.upper() for category in ['AZURE', 'FUNCTIONS', 'DATABASE', 'SQL', 'OPENAI', 'SEARCH', 'STORAGE'])
                  and k.upper() in ['PYTHON_ISOLATE_WORKER_DEPENDENCIES', 'MAX_FILE_SIZE_MB', 'SAS_EXPIRY_HOURS', 'LOG_LEVEL']}
    
    log_vars_safely("Application", other_vars)
    
    logger.info(f"Total environment variables: {len(env_vars)}")
    logger.info("=" * 60)


def log_config_summary():
    """Log a summary of the current configuration"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("CONFIGURATION SUMMARY")
    logger.info("=" * 60)
    
    config_obj = Config()
    
    logger.info(f"Database Type: {config_obj.DATABASE_TYPE}")
    logger.info(f"Storage Container: {config_obj.AZURE_STORAGE_CONTAINER_NAME}")
    logger.info(f"OpenAI Endpoint: {config_obj.AZURE_OPENAI_ENDPOINT}")
    logger.info(f"Search Endpoint: {config_obj.AZURE_SEARCH_ENDPOINT}")
    logger.info(f"Functions Runtime: {config_obj.FUNCTIONS_WORKER_RUNTIME}")
    logger.info(f"Max File Size: {config_obj.MAX_FILE_SIZE_MB}MB")
    logger.info(f"Log Level: {config_obj.LOG_LEVEL}")
    
    logger.info("=" * 60)


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
    
    # Azure SQL Authentication Method - priority order configuration
    AZURE_SQL_AUTH_METHOD: str = os.getenv('AZURE_SQL_AUTH_METHOD', 'auto').lower()
    # Options: 'managed_identity', 'ad_password', 'ad_integrated', 'sql_auth', 'auto'
    
    # Managed Identity Configuration
    AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID: Optional[str] = os.getenv('AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID')
    
    # Construct connection string with enhanced authentication support
    @property
    def AZURE_SQL_CONNECTION_STRING(self) -> Optional[str]:
        """
        Generate Azure SQL connection string with multiple authentication methods.
        
        Authentication priority when AUTH_METHOD='auto':
        1. Managed Identity (if running in Azure)
        2. Azure AD Password (if username/password provided)
        3. SQL Server Authentication (fallback)
        
        Returns connection string or None if configuration is incomplete.
        """
        # Return direct connection string if provided
        direct_conn_str = os.getenv('AZURE_SQL_CONNECTION_STRING')
        if direct_conn_str:
            return direct_conn_str
            
        # Validate required components
        if not (self.AZURE_SQL_SERVER and self.AZURE_SQL_DATABASE):
            return None
            
        base_conn = f"Driver={{{self.AZURE_SQL_DRIVER}}};Server=tcp:{self.AZURE_SQL_SERVER},{self.AZURE_SQL_PORT};Database={self.AZURE_SQL_DATABASE};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        
        auth_method = self.AZURE_SQL_AUTH_METHOD
        
        if auth_method == 'managed_identity':
            return self._build_managed_identity_connection(base_conn)
        elif auth_method == 'ad_password':
            return self._build_ad_password_connection(base_conn)
        elif auth_method == 'ad_integrated':
            return self._build_ad_integrated_connection(base_conn)
        elif auth_method == 'sql_auth':
            return self._build_sql_auth_connection(base_conn)
        elif auth_method == 'auto':
            return self._build_auto_connection(base_conn)
        else:
            raise ValueError(f"Invalid AZURE_SQL_AUTH_METHOD: {auth_method}. Valid options: managed_identity, ad_password, ad_integrated, sql_auth, auto")
    
    def _build_managed_identity_connection(self, base_conn: str) -> str:
        """Build managed identity connection string"""
        if self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID:
            # User-assigned managed identity
            return f"{base_conn}Authentication=ActiveDirectoryMsi;UID={self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID};"
        else:
            # System-assigned managed identity
            return f"{base_conn}Authentication=ActiveDirectoryMsi;"
    
    def _build_ad_password_connection(self, base_conn: str) -> str:
        """Build Azure AD password connection string"""
        if not (self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD):
            raise ValueError("AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required for AD password authentication")
        return f"{base_conn}Authentication=ActiveDirectoryPassword;UID={self.AZURE_SQL_USERNAME};PWD={self.AZURE_SQL_PASSWORD};"
    
    def _build_ad_integrated_connection(self, base_conn: str) -> str:
        """Build Azure AD integrated connection string"""
        return f"{base_conn}Authentication=ActiveDirectoryIntegrated;"
    
    def _build_sql_auth_connection(self, base_conn: str) -> str:
        """Build SQL Server authentication connection string"""
        if not (self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD):
            raise ValueError("AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required for SQL Server authentication")
        return f"{base_conn}Uid={self.AZURE_SQL_USERNAME};Pwd={self.AZURE_SQL_PASSWORD};"
    
    def _build_auto_connection(self, base_conn: str) -> str:
        """Build connection string using automatic authentication method selection"""
        # Priority 1: Try managed identity (best for Azure-hosted apps)
        try:
            # Check if we're running in Azure environment
            if (os.getenv('WEBSITE_SITE_NAME') or 
                os.getenv('AZURE_CLIENT_ID') or 
                os.getenv('MSI_ENDPOINT') or
                self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID):
                return self._build_managed_identity_connection(base_conn)
        except:
            pass
        
        # Priority 2: Try Azure AD password authentication
        if self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD:
            if '@' in self.AZURE_SQL_USERNAME:
                return self._build_ad_password_connection(base_conn)
            else:
                # SQL Server authentication
                return self._build_sql_auth_connection(base_conn)
        
        # Priority 3: Try Azure AD integrated authentication
        try:
            return self._build_ad_integrated_connection(base_conn)
        except:
            pass
        
        # Fallback: Use managed identity without client ID
        return f"{base_conn}Authentication=ActiveDirectoryMsi;"
    
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
    AZURE_SEARCH_DOC_INDEX: str = os.getenv('AZURE_SEARCH_DOC_INDEX', 'rag_doc-index')
    AZURE_SEARCH_POLICY_INDEX: str = os.getenv('AZURE_SEARCH_POLICY_INDEX', 'rag_policy-index')
    AZURE_SEARCH_DATASOURCE: Optional[str] = os.getenv('AZURE_SEARCH_DATASOURCE')
    
    # Backward compatibility property - use DOC_INDEX as the primary index
    @property
    def AZURE_SEARCH_INDEX(self) -> str:
        """Backward compatibility: returns AZURE_SEARCH_DOC_INDEX"""
        return self.AZURE_SEARCH_DOC_INDEX
    
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
    
    # Log environment variables for debugging
    log_environment_variables()
    
    if config.DATABASE_TYPE == 'sqlite':
        logging.info(f"Using SQLite database: {config.SQLITE_DATABASE_PATH}")
    elif config.DATABASE_TYPE == 'azuresql':
        logging.info(f"Using Azure SQL database: {config.AZURE_SQL_SERVER}/{config.AZURE_SQL_DATABASE}")
    
    logging.info(f"Storage container: {config.AZURE_STORAGE_CONTAINER_NAME}")
    config._logged = True