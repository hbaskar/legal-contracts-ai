#!/usr/bin/env python3
"""
Test script to create the file_metadata table in Azure SQL Server

This script will:
1. Test the connection to Azure SQL Server
2. Create the file_metadata table if it doesn't exist
3. Verify the table was created
"""

import os
import sys
import pyodbc

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.config import config

def test_sql_connection():
    """Test the SQL Server connection and create table"""
    
    print("🔧 Azure SQL Server Table Creation")
    print("=" * 50)
    
    # Get configuration
    print(f"📋 Configuration:")
    print(f"   Server: {config.AZURE_SQL_SERVER}")
    print(f"   Database: {config.AZURE_SQL_DATABASE}")
    print(f"   Username: {config.AZURE_SQL_USERNAME}")
    print(f"   Database type: {config.DATABASE_TYPE}")
    
    # Get connection string
    conn_str = config.AZURE_SQL_CONNECTION_STRING
    if not conn_str:
        print("❌ Failed to construct connection string")
        return False
    
    print(f"   Connection string: {conn_str[:80]}...")
    
    try:
        print(f"\n🔌 Connecting to Azure SQL Server...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print(f"✅ Successfully connected to Azure SQL Server")
        
        # Check if table exists
        print(f"\n� Checking if file_metadata table exists...")
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'file_metadata'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            print(f"✅ Table 'file_metadata' already exists")
            
            # Show table structure
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'file_metadata' 
                ORDER BY ORDINAL_POSITION
            """)
            columns = cursor.fetchall()
            print(f"\n📋 Table structure:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                max_len = f"({col[3]})" if col[3] else ""
                print(f"   - {col[0]}: {col[1]}{max_len} {nullable}")
        else:
            print(f"📦 Table 'file_metadata' does not exist. Creating...")
            
            # Create the table
            create_table_sql = """
            CREATE TABLE file_metadata (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                filename NVARCHAR(255) NOT NULL,
                original_filename NVARCHAR(255) NOT NULL,
                file_size BIGINT NOT NULL,
                content_type NVARCHAR(255),
                blob_url NVARCHAR(1000) NOT NULL,
                container_name NVARCHAR(255) NOT NULL,
                upload_timestamp DATETIME2 DEFAULT GETUTCDATE(),
                checksum NVARCHAR(64),
                user_id NVARCHAR(255)
            )
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            print(f"✅ Successfully created table 'file_metadata'")
        
        # Test insert and select
        print(f"\n🧪 Testing table operations...")
        
        # Insert test record
        cursor.execute("""
            INSERT INTO file_metadata 
            (filename, original_filename, file_size, content_type, blob_url, container_name, checksum, user_id)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_file.txt',
            'original_test.txt', 
            1024,
            'text/plain',
            'https://example.blob.core.windows.net/uploads/test_file.txt',
            'uploads',
            'abc123',
            'test-user'
        ))
        
        row = cursor.fetchone()
        test_id = row[0] if row else None
        conn.commit()
        print(f"✅ Test insert successful - ID: {test_id}")
        
        # Select test record
        cursor.execute("SELECT * FROM file_metadata WHERE id = ?", (test_id,))
        record = cursor.fetchone()
        
        if record:
            print(f"✅ Test select successful")
            print(f"   ID: {record[0]}")
            print(f"   Filename: {record[1]}")
            print(f"   Original: {record[2]}")
            print(f"   Size: {record[3]} bytes")
            print(f"   Upload time: {record[7]}")
        
        # Clean up test record
        cursor.execute("DELETE FROM file_metadata WHERE id = ?", (test_id,))
        conn.commit()
        print(f"🧹 Cleaned up test record")
        
        conn.close()
        return True
        
    except pyodbc.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_database_manager():
    """Test the database manager initialization"""
    print(f"\n🧪 Testing DatabaseManager initialization...")
    
    try:
        from contracts.database import DatabaseManager
        import asyncio
        
        async def test_manager():
            db_mgr = DatabaseManager()
            await db_mgr.initialize()
            print(f"✅ DatabaseManager initialized successfully")
            return True
        
        return asyncio.run(test_manager())
        
    except Exception as e:
        print(f"❌ DatabaseManager initialization failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Azure SQL Server Database Setup...")
    
    # Test direct connection
    sql_success = test_sql_connection()
    
    # Test database manager
    manager_success = test_database_manager()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Direct SQL Connection: {'✅ Success' if sql_success else '❌ Failed'}")
    print(f"DatabaseManager Init: {'✅ Success' if manager_success else '❌ Failed'}")
    
    if sql_success and manager_success:
        print("\n🎉 Azure SQL Database is ready!")
        print("The file_metadata table has been created and tested.")
        print("You can now run upload tests with Azure SQL:")
        print("   python quick_test.py")
        print("   python test_upload.py --create-files")
    else:
        print("\n⚠️ Some tests failed - check errors above")
        sys.exit(1)