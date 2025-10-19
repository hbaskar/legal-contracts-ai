"""
Test Azure SQL authentication methods
Tests the multiple authentication options for Azure SQL Database
"""
import os
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from contracts.database import DatabaseManager
from contracts.config import Config

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestAzureSQLAuthentication:
    """Test Azure SQL authentication methods"""

    def setup_method(self):
        """Setup test environment"""
        self.original_env = os.environ.copy()
        # Clear any existing Azure SQL environment variables
        for key in list(os.environ.keys()):
            if key.startswith('AZURE_SQL') or key.startswith('DATABASE'):
                del os.environ[key]
        
        # Also clear any direct connection string that might interfere
        if 'AZURE_SQL_CONNECTION_STRING' in os.environ:
            del os.environ['AZURE_SQL_CONNECTION_STRING']

    def teardown_method(self):
        """Restore original environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_managed_identity_system_assigned(self):
        """Test system-assigned managed identity authentication"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        
        # Create fresh config instance to avoid cached values
        config = Config()
        # Force re-instantiation by reloading the module
        import importlib
        import contracts.config
        importlib.reload(contracts.config)
        config = contracts.config.Config()
        
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Authentication=ActiveDirectoryMsi' in conn_str
        assert 'UID=' not in conn_str  # No client ID for system-assigned
        assert 'test-server.database.windows.net' in conn_str
        assert 'test-db' in conn_str

    def test_managed_identity_user_assigned(self):
        """Test user-assigned managed identity authentication"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID'] = 'test-client-id'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Authentication=ActiveDirectoryMsi' in conn_str
        assert 'UID=test-client-id' in conn_str
        assert 'test-server.database.windows.net' in conn_str
        assert 'test-db' in conn_str

    def test_azure_ad_password_authentication(self):
        """Test Azure AD password authentication"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'ad_password'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_USERNAME'] = 'test@domain.com'
        os.environ['AZURE_SQL_PASSWORD'] = 'test-password'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Authentication=ActiveDirectoryPassword' in conn_str
        assert 'UID=test@domain.com' in conn_str
        assert 'PWD=test-password' in conn_str
        assert 'test-server.database.windows.net' in conn_str

    def test_azure_ad_integrated_authentication(self):
        """Test Azure AD integrated authentication"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'ad_integrated'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Authentication=ActiveDirectoryIntegrated' in conn_str
        assert 'test-server.database.windows.net' in conn_str
        assert 'test-db' in conn_str

    def test_sql_server_authentication(self):
        """Test SQL Server authentication"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'sql_auth'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_USERNAME'] = 'sql-user'
        os.environ['AZURE_SQL_PASSWORD'] = 'sql-password'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Uid=sql-user' in conn_str
        assert 'Pwd=sql-password' in conn_str
        assert 'Authentication=' not in conn_str  # SQL auth doesn't use Authentication param
        assert 'test-server.database.windows.net' in conn_str

    def test_auto_authentication_azure_environment(self):
        """Test automatic authentication in Azure environment"""
        # Simulate Azure environment
        os.environ['WEBSITE_SITE_NAME'] = 'test-function-app'
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'auto'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        # Should use managed identity in Azure environment
        assert 'Authentication=ActiveDirectoryMsi' in conn_str

    def test_auto_authentication_with_ad_credentials(self):
        """Test automatic authentication with Azure AD credentials"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'auto'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_USERNAME'] = 'test@domain.com'
        os.environ['AZURE_SQL_PASSWORD'] = 'test-password'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        # Should use AD password because username contains @
        assert 'Authentication=ActiveDirectoryPassword' in conn_str
        assert 'UID=test@domain.com' in conn_str

    def test_auto_authentication_with_sql_credentials(self):
        """Test automatic authentication with SQL credentials"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'auto'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_USERNAME'] = 'sql-user'
        os.environ['AZURE_SQL_PASSWORD'] = 'sql-password'
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        # Should use SQL authentication because username doesn't contain @
        assert 'Uid=sql-user' in conn_str
        assert 'Pwd=sql-password' in conn_str

    def test_direct_connection_string_override(self):
        """Test direct connection string override"""
        # Set direct connection string
        direct_conn_str = "Server=tcp:direct.database.windows.net,1433;Database=direct-db;Authentication=ActiveDirectoryMsi;Encrypt=yes;"
        os.environ['AZURE_SQL_CONNECTION_STRING'] = direct_conn_str
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'  # Should be ignored
        os.environ['AZURE_SQL_SERVER'] = 'ignored-server'  # Should be ignored
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        # Should return direct connection string
        assert conn_str == direct_conn_str

    def test_invalid_auth_method(self):
        """Test invalid authentication method raises error"""
        # Set environment variables
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'invalid_method'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        
        config = Config()
        
        with pytest.raises(ValueError) as exc_info:
            _ = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'Invalid AZURE_SQL_AUTH_METHOD' in str(exc_info.value)

    def test_missing_credentials_for_auth_method(self):
        """Test missing credentials for authentication method"""
        # Set environment variables without required credentials
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'ad_password'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        # Missing username and password
        
        config = Config()
        
        with pytest.raises(ValueError) as exc_info:
            _ = config.AZURE_SQL_CONNECTION_STRING
        
        assert 'AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required' in str(exc_info.value)

    def test_missing_server_or_database(self):
        """Test missing server or database returns None"""
        # Missing server
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        # Missing AZURE_SQL_SERVER
        
        config = Config()
        conn_str = config.AZURE_SQL_CONNECTION_STRING
        
        assert conn_str is None

    @patch('contracts.database.pyodbc')
    def test_database_manager_connection_retry(self, mock_pyodbc):
        """Test database manager connection retry logic"""
        # Setup mock to fail twice then succeed
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # First two calls fail, third succeeds
        mock_pyodbc.connect.side_effect = [
            Exception("Connection failed"),
            Exception("Still failing"), 
            mock_conn
        ]
        mock_pyodbc.Error = Exception  # Mock pyodbc.Error
        
        # Set environment for test
        os.environ['DATABASE_TYPE'] = 'azuresql'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'
        
        db_manager = DatabaseManager()
        
        # Should succeed on third attempt
        conn = db_manager.get_azure_sql_connection()
        assert conn == mock_conn
        assert mock_pyodbc.connect.call_count == 3

    @patch('contracts.database.pyodbc')
    def test_database_manager_connection_failure(self, mock_pyodbc):
        """Test database manager connection failure after all retries"""
        # Setup mock to always fail
        mock_pyodbc.connect.side_effect = Exception("Connection always fails")
        mock_pyodbc.Error = Exception  # Mock pyodbc.Error
        
        # Set environment for test
        os.environ['DATABASE_TYPE'] = 'azuresql'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        os.environ['AZURE_SQL_AUTH_METHOD'] = 'managed_identity'
        
        db_manager = DatabaseManager()
        
        # Should fail after 3 attempts
        with pytest.raises(ConnectionError) as exc_info:
            db_manager.get_azure_sql_connection()
        
        assert 'Failed to connect to Azure SQL after 3 attempts' in str(exc_info.value)
        assert mock_pyodbc.connect.call_count == 3

    def test_auth_method_detection_from_connection_string(self):
        """Test authentication method detection from connection string"""
        os.environ['DATABASE_TYPE'] = 'azuresql'
        os.environ['AZURE_SQL_SERVER'] = 'test-server.database.windows.net'
        os.environ['AZURE_SQL_DATABASE'] = 'test-db'
        
        db_manager = DatabaseManager()
        
        # Test different connection string patterns
        test_cases = [
            ("Server=test;Authentication=ActiveDirectoryMsi;", "Managed Identity"),
            ("Server=test;Authentication=ActiveDirectoryPassword;", "Azure AD Password"),
            ("Server=test;Authentication=ActiveDirectoryIntegrated;", "Azure AD Integrated"),
            ("Server=test;Uid=user;Pwd=pass;", "SQL Server Authentication"),
            ("Server=test;", "Unknown")
        ]
        
        for conn_str, expected_method in test_cases:
            method = db_manager._get_auth_method_from_conn_str(conn_str)
            assert method == expected_method

    def test_troubleshooting_info_generation(self):
        """Test troubleshooting information generation"""
        os.environ['DATABASE_TYPE'] = 'azuresql'
        db_manager = DatabaseManager()
        
        # Test troubleshooting for different auth methods
        mi_info = db_manager._get_troubleshooting_info("Managed Identity")
        assert "managed identity is assigned" in mi_info
        assert "client ID is correct" in mi_info
        
        ad_info = db_manager._get_troubleshooting_info("Azure AD Password")
        assert "Azure AD username and password" in ad_info
        assert "account is not locked" in ad_info
        
        sql_info = db_manager._get_troubleshooting_info("SQL Server Authentication")
        assert "SQL username and password" in sql_info
        assert "SQL authentication is enabled" in sql_info


if __name__ == '__main__':
    pytest.main([__file__, '-v'])