#!/usr/bin/env python3
"""
Azure SQL Database Schema Fix Script

This script drops and recreates the azure_search_chunks table in Azure SQL
with the correct schema that matches the SQLite definition.

The script will:
1. Backup existing data (if any)
2. Drop the table
3. Recreate with correct columns
4. Restore data (if backup exists)

Usage:
    python fix_database_schema.py [--backup-only] [--no-backup]
    
Options:
    --backup-only   Only create backup, don't drop/recreate
    --no-backup     Skip backup step (DANGEROUS - data will be lost)
"""

import asyncio
import argparse
import sys
import os
import logging
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import DatabaseManager
from config.config import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def backup_existing_data(db_mgr):
    """Backup existing data from azure_search_chunks table"""
    logger.info("📦 Creating backup of existing azure_search_chunks data...")
    
    try:
        import pyodbc
        
        def _execute_backup():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'azure_search_chunks'
            """)
            
            if cursor.fetchone()[0] == 0:
                logger.info("✅ Table doesn't exist yet - no backup needed")
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
            logger.info(f"✅ Backed up {len(backup_data)} rows")
            return backup_data
        
        backup_data = await asyncio.to_thread(_execute_backup)
        
        # Save backup to file
        backup_filename = f"azure_search_chunks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(os.path.dirname(__file__), backup_filename)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Backup saved to: {backup_path}")
        return backup_path, backup_data
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        raise

async def drop_table(db_mgr):
    """Drop the existing azure_search_chunks table"""
    logger.info("🗑️  Dropping existing azure_search_chunks table...")
    
    try:
        import pyodbc
        
        def _execute_drop():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
            cursor = conn.cursor()
            
            # Drop foreign key constraints first (if any)
            cursor.execute("""
                IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
                          WHERE CONSTRAINT_TYPE = 'FOREIGN KEY' 
                          AND TABLE_NAME = 'azure_search_chunks')
                BEGIN
                    DECLARE @sql NVARCHAR(MAX) = ''
                    SELECT @sql = @sql + 'ALTER TABLE azure_search_chunks DROP CONSTRAINT ' + CONSTRAINT_NAME + ';'
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE CONSTRAINT_TYPE = 'FOREIGN KEY' AND TABLE_NAME = 'azure_search_chunks'
                    EXEC sp_executesql @sql
                END
            """)
            
            # Drop the table
            cursor.execute("IF OBJECT_ID('azure_search_chunks', 'U') IS NOT NULL DROP TABLE azure_search_chunks")
            
            conn.commit()
            conn.close()
        
        await asyncio.to_thread(_execute_drop)
        logger.info("✅ Table dropped successfully")
        
    except Exception as e:
        logger.error(f"❌ Drop table failed: {e}")
        raise

async def create_table_with_correct_schema(db_mgr):
    """Create azure_search_chunks table with the correct schema"""
    logger.info("🏗️  Creating azure_search_chunks table with correct schema...")
    
    try:
        import pyodbc
        
        def _execute_create():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
            cursor = conn.cursor()
            
            # Create table with complete schema from SQLite definition
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
        
        await asyncio.to_thread(_execute_create)
        logger.info("✅ Table created successfully with correct schema")
        
        # Show the new table structure
        await show_table_structure(db_mgr)
        
    except Exception as e:
        logger.error(f"❌ Create table failed: {e}")
        raise

async def restore_data(db_mgr, backup_data, backup_path):
    """Restore data from backup (if compatible)"""
    if not backup_data:
        logger.info("ℹ️  No backup data to restore")
        return
    
    logger.info(f"🔄 Restoring {len(backup_data)} rows from backup...")
    
    try:
        import pyodbc
        
        def _execute_restore():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
            cursor = conn.cursor()
            
            restored_count = 0
            skipped_count = 0
            
            for row_data in backup_data:
                try:
                    # Map old column names to new ones (basic mapping)
                    insert_data = {
                        'document_chunk_id': row_data.get('document_chunk_id'),
                        'search_document_id': row_data.get('search_document_id'),
                        'index_name': row_data.get('index_name'),
                        'upload_status': row_data.get('upload_status', 'pending'),
                        'upload_timestamp': row_data.get('upload_timestamp'),
                        'upload_response': row_data.get('upload_response'),
                        'embedding_dimensions': row_data.get('embedding_dimensions'),
                        'error_message': row_data.get('error_message'),
                        'retry_count': row_data.get('retry_count', 0)
                    }
                    
                    # Only insert if we have required fields
                    if insert_data['document_chunk_id'] and insert_data['search_document_id']:
                        cursor.execute("""
                            INSERT INTO azure_search_chunks 
                            (document_chunk_id, search_document_id, index_name, upload_status,
                             upload_timestamp, upload_response, embedding_dimensions, error_message, retry_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            insert_data['document_chunk_id'],
                            insert_data['search_document_id'],
                            insert_data['index_name'],
                            insert_data['upload_status'],
                            insert_data['upload_timestamp'],
                            insert_data['upload_response'],
                            insert_data['embedding_dimensions'],
                            insert_data['error_message'],
                            insert_data['retry_count']
                        ))
                        restored_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️  Skipped restoring row: {e}")
                    skipped_count += 1
            
            conn.commit()
            conn.close()
            return restored_count, skipped_count
        
        restored, skipped = await asyncio.to_thread(_execute_restore)
        logger.info(f"✅ Restored {restored} rows, skipped {skipped} rows")
        
        if skipped > 0:
            logger.info(f"💡 Backup file preserved at: {backup_path}")
            
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        logger.info(f"💡 Manual restore may be needed from: {backup_path}")

async def show_table_structure(db_mgr):
    """Show the current table structure"""
    logger.info("📊 Current azure_search_chunks table structure:")
    
    try:
        import pyodbc
        
        def _get_columns():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
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
            return columns
        
        columns = await asyncio.to_thread(_get_columns)
        
        print("\nColumns:")
        for i, (name, data_type, length, nullable, default) in enumerate(columns, 1):
            length_str = f"({length})" if length else ""
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f"DEFAULT {default}" if default else ""
            
            marker = "🆕" if name.startswith('paragraph_') or name in ['filename', 'date_uploaded', 'group_tags', 'department', 'language', 'is_compliant', 'content_length'] else "📋"
            print(f"  {i:2d}. {marker} {name} {data_type}{length_str} {nullable_str} {default_str}")
        
        print(f"\nTotal columns: {len(columns)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to show table structure: {e}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Fix Azure SQL azure_search_chunks table schema')
    parser.add_argument('--backup-only', action='store_true', help='Only create backup, do not drop/recreate')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup step (DANGEROUS)')
    args = parser.parse_args()
    
    print("🔧 Azure SQL Schema Fix Tool")
    print("=" * 50)
    
    try:
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        if db_mgr.db_type != 'azuresql':
            logger.error("❌ This script is for Azure SQL databases only")
            return
        
        logger.info(f"📊 Connected to Azure SQL database")
        
        # Step 1: Backup existing data (unless --no-backup)
        backup_path = None
        backup_data = []
        
        if not args.no_backup:
            backup_path, backup_data = await backup_existing_data(db_mgr)
        else:
            logger.warning("⚠️  Skipping backup - data will be LOST!")
        
        if args.backup_only:
            logger.info("✅ Backup completed. Exiting without schema changes.")
            return
        
        # Confirm before proceeding
        if not args.no_backup and backup_data:
            print(f"\n⚠️  WARNING: About to drop and recreate table")
            print(f"   - {len(backup_data)} rows will be backed up")
            print(f"   - Backup saved to: {backup_path}")
        else:
            print(f"\n⚠️  WARNING: About to drop and recreate table WITHOUT backup!")
        
        response = input("\nProceed? (y/N): ").strip().lower()
        if response != 'y':
            logger.info("❌ Operation cancelled by user")
            return
        
        # Step 2: Drop existing table
        await drop_table(db_mgr)
        
        # Step 3: Create table with correct schema
        await create_table_with_correct_schema(db_mgr)
        
        # Step 4: Restore data (if backup exists)
        if backup_data:
            await restore_data(db_mgr, backup_data, backup_path)
        
        logger.info("🎉 Schema fix completed successfully!")
        logger.info("💡 You can now test the persisted chunks endpoint")
        
    except Exception as e:
        logger.error(f"❌ Schema fix failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())