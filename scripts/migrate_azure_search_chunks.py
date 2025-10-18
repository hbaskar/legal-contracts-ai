#!/usr/bin/env python3
"""
Database Migration Script for Azure Search Chunks Paragraph Data Persistence

This script migrates existing azure_search_chunks tables to include
the new paragraph data fields. It handles both SQLite and Azure SQL databases.

The migration adds the following columns:
- paragraph_content TEXT - Full content of the paragraph
- paragraph_title TEXT - AI-generated title
- paragraph_summary TEXT - AI-generated summary
- paragraph_keyphrases TEXT - JSON array of keyphrases
- filename TEXT - Original filename
- paragraph_id TEXT - Paragraph/chunk sequence ID
- date_uploaded DATETIME - When uploaded to Azure Search
- group_tags TEXT - JSON array of group tags
- department TEXT - Department classification
- language TEXT - Document language
- is_compliant BOOLEAN - Compliance status
- content_length INTEGER - Length of paragraph content

Usage:
    python migrate_azure_search_chunks.py [--force]
    
Options:
    --force    Force migration even if columns already exist
"""

import asyncio
import argparse
import sys
import os
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contracts.database import DatabaseManager
from contracts.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_existing_columns(db_mgr):
    """Check which new columns already exist in the database"""
    try:
        if db_mgr.db_type == 'sqlite':
            import aiosqlite
            async with aiosqlite.connect(db_mgr.sqlite_path) as db:
                cursor = await db.execute("PRAGMA table_info(azure_search_chunks)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                return column_names
                
        elif db_mgr.db_type == 'azuresql':
            import pyodbc
            
            def _get_columns():
                conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'azure_search_chunks'
                    ORDER BY ORDINAL_POSITION
                """)
                
                columns = [row[0] for row in cursor.fetchall()]
                conn.close()
                return columns
            
            return await asyncio.to_thread(_get_columns)
            
    except Exception as e:
        logger.error(f"Failed to check existing columns: {e}")
        return []

async def migrate_sqlite(db_mgr, force=False):
    """Migrate SQLite database to add new paragraph data columns"""
    logger.info("🔄 Migrating SQLite database...")
    
    try:
        import aiosqlite
        
        # Check existing columns
        existing_columns = await check_existing_columns(db_mgr)
        new_columns = [
            'paragraph_content', 'paragraph_title', 'paragraph_summary',
            'paragraph_keyphrases', 'filename', 'paragraph_id',
            'date_uploaded', 'group_tags', 'department', 'language',
            'is_compliant', 'content_length'
        ]
        
        missing_columns = [col for col in new_columns if col not in existing_columns]
        
        if not missing_columns and not force:
            logger.info("✅ All columns already exist in SQLite database")
            return True
        
        if force:
            logger.info("🔄 Force migration requested - recreating table...")
            missing_columns = new_columns
        
        async with aiosqlite.connect(db_mgr.sqlite_path) as db:
            # Add missing columns one by one
            for column in missing_columns:
                try:
                    if column == 'paragraph_content':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN paragraph_content TEXT")
                    elif column == 'paragraph_title':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN paragraph_title TEXT")
                    elif column == 'paragraph_summary':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN paragraph_summary TEXT")
                    elif column == 'paragraph_keyphrases':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN paragraph_keyphrases TEXT")
                    elif column == 'filename':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN filename TEXT")
                    elif column == 'paragraph_id':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN paragraph_id TEXT")
                    elif column == 'date_uploaded':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN date_uploaded DATETIME")
                    elif column == 'group_tags':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN group_tags TEXT")
                    elif column == 'department':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN department TEXT")
                    elif column == 'language':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN language TEXT")
                    elif column == 'is_compliant':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN is_compliant BOOLEAN")
                    elif column == 'content_length':
                        await db.execute("ALTER TABLE azure_search_chunks ADD COLUMN content_length INTEGER")
                    
                    logger.info(f"✅ Added column: {column}")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Failed to add column {column}: {e}")
            
            await db.commit()
            logger.info("✅ SQLite migration completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ SQLite migration failed: {e}")
        return False

async def migrate_azure_sql(db_mgr, force=False):
    """Migrate Azure SQL database to add new paragraph data columns"""
    logger.info("🔄 Migrating Azure SQL database...")
    
    try:
        import pyodbc
        
        # Check existing columns
        existing_columns = await check_existing_columns(db_mgr)
        new_columns = [
            'paragraph_content', 'paragraph_title', 'paragraph_summary',
            'paragraph_keyphrases', 'filename', 'paragraph_id',
            'date_uploaded', 'group_tags', 'department', 'language',
            'is_compliant', 'content_length'
        ]
        
        missing_columns = [col for col in new_columns if col not in existing_columns]
        
        if not missing_columns and not force:
            logger.info("✅ All columns already exist in Azure SQL database")
            return True
        
        if force:
            logger.info("🔄 Force migration requested - adding all columns...")
            missing_columns = new_columns
        
        def _execute_migration():
            conn = pyodbc.connect(db_mgr.azure_sql_conn_str)
            cursor = conn.cursor()
            
            # Add missing columns one by one
            for column in missing_columns:
                try:
                    if column == 'paragraph_content':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD paragraph_content NTEXT")
                    elif column == 'paragraph_title':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD paragraph_title NVARCHAR(500)")
                    elif column == 'paragraph_summary':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD paragraph_summary NTEXT")
                    elif column == 'paragraph_keyphrases':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD paragraph_keyphrases NTEXT")
                    elif column == 'filename':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD filename NVARCHAR(255)")
                    elif column == 'paragraph_id':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD paragraph_id NVARCHAR(50)")
                    elif column == 'date_uploaded':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD date_uploaded DATETIME2")
                    elif column == 'group_tags':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD group_tags NTEXT")
                    elif column == 'department':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD department NVARCHAR(100)")
                    elif column == 'language':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD language NVARCHAR(10)")
                    elif column == 'is_compliant':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD is_compliant BIT")
                    elif column == 'content_length':
                        cursor.execute("ALTER TABLE azure_search_chunks ADD content_length INTEGER")
                    
                    logger.info(f"✅ Added column: {column}")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Failed to add column {column}: {e}")
            
            conn.commit()
            conn.close()
        
        await asyncio.to_thread(_execute_migration)
        logger.info("✅ Azure SQL migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Azure SQL migration failed: {e}")
        return False

async def verify_migration(db_mgr):
    """Verify that the migration was successful"""
    logger.info("🔍 Verifying migration...")
    
    try:
        existing_columns = await check_existing_columns(db_mgr)
        required_columns = [
            'paragraph_content', 'paragraph_title', 'paragraph_summary',
            'paragraph_keyphrases', 'filename', 'paragraph_id',
            'date_uploaded', 'group_tags', 'department', 'language',
            'is_compliant', 'content_length'
        ]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.error(f"❌ Migration verification failed. Missing columns: {missing_columns}")
            return False
        else:
            logger.info("✅ Migration verification successful. All required columns present.")
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration verification error: {e}")
        return False

async def show_table_info(db_mgr):
    """Show current table structure"""
    logger.info("📊 Current azure_search_chunks table structure:")
    
    try:
        existing_columns = await check_existing_columns(db_mgr)
        
        print("\nColumns:")
        for i, column in enumerate(existing_columns, 1):
            marker = "🆕" if column.startswith('paragraph_') or column in ['filename', 'date_uploaded', 'group_tags', 'department', 'language', 'is_compliant', 'content_length'] else "📋"
            print(f"  {i:2d}. {marker} {column}")
        
        print(f"\nTotal columns: {len(existing_columns)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to show table info: {e}")
        return False

async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate azure_search_chunks table for paragraph data persistence')
    parser.add_argument('--force', action='store_true', help='Force migration even if columns exist')
    parser.add_argument('--info-only', action='store_true', help='Only show table information, do not migrate')
    args = parser.parse_args()
    
    print("🚀 Azure Search Chunks Migration Tool")
    print("=" * 50)
    
    try:
        # Initialize database manager
        db_mgr = DatabaseManager()
        await db_mgr.initialize()
        
        logger.info(f"📊 Using database type: {db_mgr.db_type}")
        
        # Show current table info
        await show_table_info(db_mgr)
        
        if args.info_only:
            logger.info("ℹ️  Info-only mode. Exiting without migration.")
            return
        
        # Perform migration based on database type
        if db_mgr.db_type == 'sqlite':
            success = await migrate_sqlite(db_mgr, force=args.force)
        elif db_mgr.db_type == 'azuresql':
            success = await migrate_azure_sql(db_mgr, force=args.force)
        else:
            logger.error(f"❌ Unsupported database type: {db_mgr.db_type}")
            return
        
        if success:
            # Verify migration
            verification_success = await verify_migration(db_mgr)
            
            if verification_success:
                print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
                print("\n📝 Next Steps:")
                print("1. Test document processing to ensure paragraph data is persisted")
                print("2. Use the new /api/search/chunks/persisted endpoint")
                print("3. Verify data integrity with test_paragraph_persistence.py")
                print("4. Update any existing applications to use the new fields")
            else:
                print("\n⚠️  Migration completed but verification failed")
                print("Please check the logs and verify manually")
        else:
            print("\n❌ Migration failed. Please check the logs for details.")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())