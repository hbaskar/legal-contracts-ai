#!/usr/bin/env python3
"""
Simple Azure SQL Table Drop and Recreate Script

This script directly connects to Azure SQL and recreates the azure_search_chunks table
with the correct schema that includes all the paragraph_* columns.
"""

import pyodbc
import os
import json
from datetime import datetime

def get_azure_sql_connection():
    """Get Azure SQL connection string"""
    
    # Use the production server details from deployment settings
    server = 'ggndadev-sqlsvr01.database.windows.net'
    database = 'CMSDEVDB'
    
    # Try Azure AD authentication first
    conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    
    return conn_str

def backup_existing_data(conn_str):
    """Backup existing data from azure_search_chunks table"""
    print("📦 Creating backup of existing azure_search_chunks data...")
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'azure_search_chunks'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("✅ Table doesn't exist yet - no backup needed")
            conn.close()
            return []
        
        # Get all existing data
        cursor.execute("SELECT * FROM azure_search_chunks")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        backup_data = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Handle datetime serialization
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row_dict[col] = value
            backup_data.append(row_dict)
        
        conn.close()
        print(f"✅ Backed up {len(backup_data)} rows")
        return backup_data
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        raise

def drop_and_recreate_table(conn_str):
    """Drop and recreate the azure_search_chunks table with correct schema"""
    print("🏗️  Dropping and recreating azure_search_chunks table...")
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Drop the table if it exists
        cursor.execute("IF OBJECT_ID('azure_search_chunks', 'U') IS NOT NULL DROP TABLE azure_search_chunks")
        
        # Create table with complete schema
        cursor.execute("""
            CREATE TABLE azure_search_chunks (
                id BIGINT IDENTITY(1,1) PRIMARY KEY,
                document_chunk_id BIGINT NOT NULL,
                search_document_id NVARCHAR(255) NOT NULL,
                index_name NVARCHAR(100) NOT NULL,
                
                -- Persisted paragraph data from Azure Search
                paragraph_content NTEXT,      -- Full content of the paragraph
                paragraph_title NVARCHAR(500), -- AI-generated title
                paragraph_summary NTEXT,      -- AI-generated summary
                paragraph_keyphrases NTEXT,   -- JSON array of keyphrases
                filename NVARCHAR(255),       -- Original filename
                paragraph_id NVARCHAR(50),    -- Paragraph/chunk sequence ID
                date_uploaded DATETIME2,      -- When uploaded to Azure Search
                group_tags NTEXT,            -- JSON array of group tags
                department NVARCHAR(100),     -- Department classification
                language NVARCHAR(10),        -- Document language
                is_compliant BIT,             -- Compliance status
                content_length INTEGER,       -- Length of paragraph content
                
                -- Upload tracking metadata
                upload_status NVARCHAR(20) DEFAULT 'pending',
                upload_timestamp DATETIME2,
                upload_response NTEXT,
                embedding_dimensions INTEGER,
                search_score REAL,
                retry_count INTEGER DEFAULT 0,
                error_message NTEXT,
                
                -- Constraints
                CONSTRAINT UQ_azure_search_chunks UNIQUE(document_chunk_id, index_name)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Table recreated successfully")
        
    except Exception as e:
        print(f"❌ Failed to recreate table: {e}")
        raise

def show_table_structure(conn_str):
    """Show the current table structure"""
    print("📊 Current azure_search_chunks table structure:")
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'azure_search_chunks'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        conn.close()
        
        print("\nColumns:")
        for i, (name, data_type, length, nullable, default) in enumerate(columns, 1):
            length_str = f"({length})" if length else ""
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f"DEFAULT {default}" if default else ""
            
            marker = "🆕" if name.startswith('paragraph_') or name in ['filename', 'date_uploaded', 'group_tags', 'department', 'language', 'is_compliant', 'content_length'] else "📋"
            print(f"  {i:2d}. {marker} {name} {data_type}{length_str} {nullable_str} {default_str}")
        
        print(f"\nTotal columns: {len(columns)}")
        
    except Exception as e:
        print(f"❌ Failed to show table structure: {e}")

def main():
    """Main function"""
    print("🔧 Azure SQL Schema Fix Tool")
    print("=" * 50)
    
    try:
        # Get connection string
        conn_str = get_azure_sql_connection()
        
        print("📊 Connecting to Azure SQL...")
        
        # Test connection
        test_conn = pyodbc.connect(conn_str)
        test_conn.close()
        print("✅ Connection successful")
        
        # Show current structure (if table exists)
        try:
            show_table_structure(conn_str)
        except:
            print("ℹ️  Table doesn't exist yet")
        
        # Confirm before proceeding
        print(f"\n⚠️  WARNING: About to drop and recreate azure_search_chunks table")
        print(f"   - This will remove all existing data!")
        print(f"   - New table will have the correct schema with paragraph_content column")
        
        response = input("\nProceed? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled by user")
            return
        
        # Step 1: Backup existing data
        backup_data = backup_existing_data(conn_str)
        
        # Save backup to file if there's data
        if backup_data:
            backup_filename = f"azure_search_chunks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Backup saved to: {backup_filename}")
        
        # Step 2: Drop and recreate table
        drop_and_recreate_table(conn_str)
        
        # Step 3: Show new structure
        show_table_structure(conn_str)
        
        print("\n🎉 Schema fix completed successfully!")
        print("💡 You can now test the persisted chunks endpoint")
        
        if backup_data:
            print(f"💾 Original data backed up to: {backup_filename}")
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()