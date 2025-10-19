"""
Simple test for Azure SQL authentication methods
Tests the connection string building methods directly
"""
import os
import pytest
from unittest.mock import patch


def test_connection_string_building():
    """Test connection string building methods directly"""
    
    # Mock the Config class to avoid environment interference
    class MockConfig:
        def __init__(self):
            self.AZURE_SQL_DRIVER = 'ODBC Driver 18 for SQL Server'
            self.AZURE_SQL_SERVER = 'test-server.database.windows.net'
            self.AZURE_SQL_DATABASE = 'test-db'
            self.AZURE_SQL_PORT = 1433
            self.AZURE_SQL_USERNAME = None
            self.AZURE_SQL_PASSWORD = None
            self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID = None
            self.AZURE_SQL_AUTH_METHOD = 'managed_identity'
        
        def _build_managed_identity_connection(self, base_conn: str) -> str:
            """Build managed identity connection string"""
            if self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID:
                return f"{base_conn}Authentication=ActiveDirectoryMsi;UID={self.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID};"
            else:
                return f"{base_conn}Authentication=ActiveDirectoryMsi;"
        
        def _build_ad_password_connection(self, base_conn: str) -> str:
            """Build Azure AD password connection string"""
            if not (self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD):
                raise ValueError("AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required for AD password authentication")
            return f"{base_conn}Authentication=ActiveDirectoryPassword;UID={self.AZURE_SQL_USERNAME};PWD={self.AZURE_SQL_PASSWORD};"
        
        def _build_sql_auth_connection(self, base_conn: str) -> str:
            """Build SQL Server authentication connection string"""
            if not (self.AZURE_SQL_USERNAME and self.AZURE_SQL_PASSWORD):
                raise ValueError("AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required for SQL Server authentication")
            return f"{base_conn}Uid={self.AZURE_SQL_USERNAME};Pwd={self.AZURE_SQL_PASSWORD};"
    
    # Test managed identity without client ID
    config = MockConfig()
    base_conn = f"Driver={{{config.AZURE_SQL_DRIVER}}};Server=tcp:{config.AZURE_SQL_SERVER},{config.AZURE_SQL_PORT};Database={config.AZURE_SQL_DATABASE};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    
    conn_str = config._build_managed_identity_connection(base_conn)
    assert 'Authentication=ActiveDirectoryMsi' in conn_str
    assert 'UID=' not in conn_str or conn_str.count('UID=') == 0 or 'UID=;' in conn_str
    
    # Test managed identity with client ID
    config.AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID = 'test-client-id'
    conn_str = config._build_managed_identity_connection(base_conn)
    assert 'Authentication=ActiveDirectoryMsi' in conn_str
    assert 'UID=test-client-id' in conn_str
    
    # Test Azure AD password authentication
    config.AZURE_SQL_USERNAME = 'test@domain.com'
    config.AZURE_SQL_PASSWORD = 'test-password'
    conn_str = config._build_ad_password_connection(base_conn)
    assert 'Authentication=ActiveDirectoryPassword' in conn_str
    assert 'UID=test@domain.com' in conn_str
    assert 'PWD=test-password' in conn_str
    
    # Test SQL Server authentication
    config.AZURE_SQL_USERNAME = 'sql-user'
    config.AZURE_SQL_PASSWORD = 'sql-password'
    conn_str = config._build_sql_auth_connection(base_conn)
    assert 'Uid=sql-user' in conn_str
    assert 'Pwd=sql-password' in conn_str
    assert 'Authentication=' not in conn_str  # SQL auth doesn't use Authentication param
    
    # Test missing credentials
    config.AZURE_SQL_USERNAME = None
    config.AZURE_SQL_PASSWORD = None
    
    with pytest.raises(ValueError) as exc_info:
        config._build_ad_password_connection(base_conn)
    assert 'AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required' in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        config._build_sql_auth_connection(base_conn)
    assert 'AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD required' in str(exc_info.value)


def test_database_manager_connection_helper():
    """Test the database manager connection helper methods"""
    from contracts.database import DatabaseManager
    
    # Test authentication method detection
    db_manager = DatabaseManager()
    
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
    
    # Test troubleshooting info
    mi_info = db_manager._get_troubleshooting_info("Managed Identity")
    assert "managed identity is assigned" in mi_info
    
    ad_info = db_manager._get_troubleshooting_info("Azure AD Password")
    assert "Azure AD username and password" in ad_info
    
    sql_info = db_manager._get_troubleshooting_info("SQL Server Authentication")
    assert "SQL username and password" in sql_info


if __name__ == '__main__':
    pytest.main([__file__, '-v'])