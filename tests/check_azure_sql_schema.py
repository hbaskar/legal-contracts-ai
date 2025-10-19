#!/usr/bin/env python3
"""
Check Azure SQL Database Schema
Verifies what tables and columns are actually available in the Azure SQL database
"""

import sys
import os
import asyncio
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from config.database import DatabaseManager
    from config.config import config
    import pyodbc
    
    async def check_azure_sql_schema():
        """Check what tables and columns exist in Azure SQL"""
        
        print("🔍 Checking Azure SQL Database Schema...")
        
        if config.DATABASE_TYPE != 'azuresql':
            print(f"❌ Current database type: {config.DATABASE_TYPE}")
            print("Switch to Azure SQL to check schema")
            return
        
        if not config.AZURE_SQL_CONNECTION_STRING:
            print("❌ Azure SQL connection string not configured")
            return
        
        try:
            # Connect to Azure SQL
            conn = pyodbc.connect(config.AZURE_SQL_CONNECTION_STRING)
            cursor = conn.cursor()
            
            print(f"✅ Connected to Azure SQL database")
            print(f"Server: {config.AZURE_SQL_SERVER}")
            print(f"Database: {config.AZURE_SQL_DATABASE}")
            
            # Get all user tables
            print(f"\n📋 Checking existing tables...")
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_TYPE 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            
            tables = cursor.fetchall()
            
            if not tables:
                print("❌ No user tables found in database")
                return
            
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   • {table[0]}")
            
            # Check each table we expect
            expected_tables = ['file_metadata', 'document_chunks', 'azure_search_chunks', 'chunk_comparisons']
            
            for table_name in expected_tables:
                print(f"\n🔍 Checking table: {table_name}")
                
                # Check if table exists
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = ?
                """, (table_name,))
                
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    print(f"   ✅ Table '{table_name}' exists")
                    
                    # Get column information
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = ?
                        ORDER BY ORDINAL_POSITION
                    """, (table_name,))
                    
                    columns = cursor.fetchall()
                    print(f"   📊 Columns ({len(columns)}):")
                    for col in columns:
                        nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                        default = f" DEFAULT {col[3]}" if col[3] else ""
                        print(f"      • {col[0]} ({col[1]}) {nullable}{default}")
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    print(f"   📈 Row count: {row_count}")
                    
                else:
                    print(f"   ❌ Table '{table_name}' NOT found")
                    
                    # Show create statement that should be run
                    print(f"   💡 To create this table, run:")
                    if table_name == 'document_chunks':
                        print(f"""
                        CREATE TABLE document_chunks (
                            id BIGINT IDENTITY(1,1) PRIMARY KEY,
                            file_id BIGINT NOT NULL,
                            chunk_index INTEGER NOT NULL,
                            chunk_method NVARCHAR(50) NOT NULL,
                            chunk_size INTEGER NOT NULL,
                            chunk_text NTEXT NOT NULL,
                            chunk_hash NVARCHAR(64),
                            start_position INTEGER,
                            end_position INTEGER,
                            keyphrases NTEXT,
                            ai_summary NTEXT,
                            ai_title NVARCHAR(255),
                            created_timestamp DATETIME2 DEFAULT GETUTCDATE(),
                            processing_time_ms INTEGER,
                            FOREIGN KEY (file_id) REFERENCES file_metadata (id),
                            CONSTRAINT UQ_document_chunks UNIQUE(file_id, chunk_method, chunk_index)
                        );
                        """)
                    elif table_name == 'azure_search_chunks':
                        print(f"""
                        CREATE TABLE azure_search_chunks (
                            id BIGINT IDENTITY(1,1) PRIMARY KEY,
                            document_chunk_id BIGINT NOT NULL,
                            search_document_id NVARCHAR(255) NOT NULL,
                            index_name NVARCHAR(100) NOT NULL,
                            upload_status NVARCHAR(20) DEFAULT 'pending',
                            upload_timestamp DATETIME2,
                            upload_response NTEXT,
                            embedding_dimensions INTEGER,
                            search_score REAL,
                            retry_count INTEGER DEFAULT 0,
                            error_message NTEXT,
                            FOREIGN KEY (document_chunk_id) REFERENCES document_chunks (id),
                            CONSTRAINT UQ_azure_search_chunks UNIQUE(document_chunk_id, index_name)
                        );
                        """)
                    elif table_name == 'chunk_comparisons':
                        print(f"""
                        CREATE TABLE chunk_comparisons (
                            id BIGINT IDENTITY(1,1) PRIMARY KEY,
                            file_id BIGINT NOT NULL,
                            comparison_name NVARCHAR(255) NOT NULL,
                            method_a NVARCHAR(50) NOT NULL,
                            method_b NVARCHAR(50) NOT NULL,
                            total_chunks_a INTEGER,
                            total_chunks_b INTEGER,
                            similarity_score REAL,
                            content_overlap_pct REAL,
                            avg_chunk_size_a REAL,
                            avg_chunk_size_b REAL,
                            processing_time_a_ms INTEGER,
                            processing_time_b_ms INTEGER,
                            analysis_timestamp DATETIME2 DEFAULT GETUTCDATE(),
                            detailed_analysis NTEXT,
                            FOREIGN KEY (file_id) REFERENCES file_metadata (id),
                            CONSTRAINT UQ_chunk_comparisons UNIQUE(file_id, method_a, method_b)
                        );
                        """)
            
            # Check if database initialization was run
            print(f"\n🔧 Database Initialization Status:")
            try:
                db = DatabaseManager()
                await db.initialize()
                print(f"   ✅ Database initialization completed successfully")
            except Exception as e:
                print(f"   ❌ Database initialization failed: {e}")
                print(f"   💡 Try running: await DatabaseManager().initialize()")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Failed to check Azure SQL schema: {e}")
            import traceback
            traceback.print_exc()

    async def main():
        """Main function"""
        try:
            print("🚀 Azure SQL Database Schema Check")
            print("=" * 50)
            
            await check_azure_sql_schema()
            
            print(f"\n✅ Schema check completed!")
            
        except Exception as e:
            print(f"\n❌ Schema check failed: {e}")
            import traceback
            traceback.print_exc()

    if __name__ == "__main__":
        asyncio.run(main())
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the tests directory and all packages are installed")
    sys.exit(1)
