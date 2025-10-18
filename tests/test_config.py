"""
Test file for configuration system
"""
import unittest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigurationSystem(unittest.TestCase):
    """Test cases for the configuration management system"""
    
    def test_config_import(self):
        """Test that configuration can be imported"""
        from contracts.config import config, Config
        
        self.assertIsInstance(config, Config)
        
    def test_default_values(self):
        """Test that default configuration values are available"""
        from contracts.config import Config
        
        # Test that values are of correct types (values might come from .env file)
        self.assertIsInstance(Config.FUNCTIONS_WORKER_RUNTIME, str)
        self.assertIsInstance(Config.DATABASE_TYPE, str) 
        self.assertIsInstance(Config.AZURE_STORAGE_CONTAINER_NAME, str)
        self.assertIsInstance(Config.MAX_FILE_SIZE_MB, int)
        self.assertIsInstance(Config.DEFAULT_SAS_EXPIRY_HOURS, int)
        
        # Test reasonable defaults
        self.assertGreater(Config.MAX_FILE_SIZE_MB, 0)
        self.assertGreater(Config.DEFAULT_SAS_EXPIRY_HOURS, 0)
        
    def test_environment_info(self):
        """Test environment info method"""
        from contracts.config import config
        
        env_info = config.get_environment_info()
        
        # Check that all expected keys are present
        expected_keys = [
            'database_type', 'storage_container', 'max_file_size_mb',
            'default_sas_expiry_hours', 'log_level', 'python_isolation', 'sqlite_path'
        ]
        
        for key in expected_keys:
            self.assertIn(key, env_info, f"Missing key: {key}")
            
    def test_config_validation_method_exists(self):
        """Test configuration validation method exists and works"""
        from contracts.config import Config
        
        # Test that validation method exists and returns a boolean
        result = Config.validate_config()
        self.assertIsInstance(result, bool)
        
    @patch.dict(os.environ, {
        'DATABASE_TYPE': 'azuresql',
        'AZURE_SQL_CONNECTION_STRING': '',
        'AZURE_SQL_SERVER': '',
        'AZURE_SQL_USERNAME': '',
        'AZURE_SQL_PASSWORD': '',
        'AZURE_SQL_DATABASE': '',
        'AZURE_STORAGE_CONNECTION_STRING': 'valid_connection_string'
    })
    def test_config_validation_missing_sql(self):
        """Test validation fails when SQL connection string is missing for azuresql"""
        # Need to reload config to pick up environment changes
        from importlib import reload
        from contracts import config as config_module
        reload(config_module)
        
        self.assertFalse(config_module.Config.validate_config())
        
    @patch.dict(os.environ, {
        'DATABASE_TYPE': 'sqlite',
        'AZURE_STORAGE_CONNECTION_STRING': 'DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=testkey;EndpointSuffix=core.windows.net',
        'AZURE_STORAGE_CONTAINER_NAME': 'test-uploads'
    })
    def test_config_validation_valid_sqlite(self):
        """Test validation passes with valid SQLite configuration"""
        # Need to reload config to pick up environment changes
        from importlib import reload
        from contracts import config as config_module
        reload(config_module)
        
        self.assertTrue(config_module.Config.validate_config())
        
    def test_config_type_conversions(self):
        """Test that string environment variables are properly converted"""
        from contracts.config import Config
        
        # Test integer conversions
        self.assertIsInstance(Config.MAX_FILE_SIZE_MB, int)
        self.assertIsInstance(Config.DEFAULT_SAS_EXPIRY_HOURS, int)
        
        # Test string values
        self.assertIsInstance(Config.DATABASE_TYPE, str)
        self.assertIsInstance(Config.LOG_LEVEL, str)
        
    def test_database_managers_use_config(self):
        """Test that database and storage managers use the config"""
        from contracts.database import DatabaseManager
        from contracts.storage import BlobStorageManager
        from contracts.config import config
        
        # Test database manager
        db_mgr = DatabaseManager()
        self.assertEqual(db_mgr.db_type, config.DATABASE_TYPE)
        self.assertEqual(db_mgr.sqlite_path, config.SQLITE_DATABASE_PATH)
        
        # Test storage manager
        storage_mgr = BlobStorageManager()
        self.assertEqual(storage_mgr.container_name, config.AZURE_STORAGE_CONTAINER_NAME)


if __name__ == '__main__':
    unittest.main()