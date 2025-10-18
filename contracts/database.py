"""
Database operations for file metadata storage
Supports both SQLite (local development) and Azure SQL (production)
"""
import os
import logging
from datetime import datetime, UTC
from typing import Optional, List
import asyncio
from contracts.models import FileMetadata

# Database imports
import aiosqlite
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


class DatabaseManager:
    """Manages database operations for file metadata"""
    
    def __init__(self):
        from contracts.config import config
        self.config = config
        self.db_type = config.DATABASE_TYPE
        self.sqlite_path = config.SQLITE_DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        
    @property
    def azure_sql_conn_str(self):
        """Get Azure SQL connection string from config"""
        return self.config.AZURE_SQL_CONNECTION_STRING
        
    async def initialize(self):
        """Initialize database and create tables if they don't exist"""
        try:
            if self.db_type == 'sqlite':
                await self._initialize_sqlite()
            elif self.db_type == 'azuresql':
                self._initialize_azure_sql()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
            self.logger.info(f"Database initialized successfully with {self.db_type}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def _initialize_sqlite(self):
        """Initialize SQLite database"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    content_type TEXT,
                    blob_url TEXT NOT NULL,
                    container_name TEXT NOT NULL,
                    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT,
                    user_id TEXT
                )
            """)
            
            # Create document chunks table for comparison purposes
            await db.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_method TEXT NOT NULL,  -- 'original', 'intelligent', 'fixed_size', etc.
                    chunk_size INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_hash TEXT,  -- For deduplication
                    start_position INTEGER,  -- Character position in original document
                    end_position INTEGER,
                    keyphrases TEXT,  -- JSON array of extracted keyphrases
                    ai_summary TEXT,  -- AI-generated summary
                    ai_title TEXT,   -- AI-generated title
                    created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,  -- Time taken to process this chunk
                    FOREIGN KEY (file_id) REFERENCES file_metadata (id),
                    UNIQUE(file_id, chunk_method, chunk_index)
                )
            """)
            
            # Create Azure Search chunks table for tracking what was indexed
            await db.execute("""
                CREATE TABLE IF NOT EXISTS azure_search_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_chunk_id INTEGER NOT NULL,
                    search_document_id TEXT NOT NULL,  -- Azure Search document ID
                    index_name TEXT NOT NULL,
                    
                    -- Persisted paragraph data from Azure Search
                    paragraph_content TEXT,  -- Full content of the paragraph
                    paragraph_title TEXT,   -- AI-generated title
                    paragraph_summary TEXT, -- AI-generated summary
                    paragraph_keyphrases TEXT, -- JSON array of keyphrases
                    filename TEXT,           -- Original filename
                    paragraph_id TEXT,       -- Paragraph/chunk sequence ID
                    date_uploaded DATETIME,  -- When uploaded to Azure Search
                    group_tags TEXT,         -- JSON array of group tags
                    department TEXT,         -- Department classification
                    language TEXT,           -- Document language
                    is_compliant BOOLEAN,    -- Compliance status
                    content_length INTEGER,  -- Length of paragraph content
                    
                    -- Upload tracking metadata
                    upload_status TEXT DEFAULT 'pending',  -- 'pending', 'success', 'failed'
                    upload_timestamp DATETIME,
                    upload_response TEXT,  -- JSON response from Azure Search
                    embedding_dimensions INTEGER,
                    search_score REAL,  -- Relevance score if retrieved
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (document_chunk_id) REFERENCES document_chunks (id),
                    UNIQUE(document_chunk_id, index_name)
                )
            """)
            
            # Create chunk comparison analysis table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chunk_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    comparison_name TEXT NOT NULL,
                    method_a TEXT NOT NULL,  -- First chunking method
                    method_b TEXT NOT NULL,  -- Second chunking method
                    total_chunks_a INTEGER,
                    total_chunks_b INTEGER,
                    similarity_score REAL,  -- Overall similarity between methods
                    content_overlap_pct REAL,  -- Percentage of content overlap
                    avg_chunk_size_a REAL,
                    avg_chunk_size_b REAL,
                    processing_time_a_ms INTEGER,
                    processing_time_b_ms INTEGER,
                    analysis_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    detailed_analysis TEXT,  -- JSON with detailed comparison results
                    FOREIGN KEY (file_id) REFERENCES file_metadata (id),
                    UNIQUE(file_id, method_a, method_b)
                )
            """)
            
            await db.commit()
    
    def _initialize_azure_sql(self):
        """Initialize Azure SQL database"""
        if not PYODBC_AVAILABLE:
            raise ImportError("pyodbc is required for Azure SQL connections")
            
        if not self.azure_sql_conn_str:
            raise ValueError("AZURE_SQL_CONNECTION_STRING environment variable is required")
        
        # Note: For production, this should be handled by database migration scripts
        # This is a simplified version for demonstration
        conn = pyodbc.connect(self.azure_sql_conn_str)
        cursor = conn.cursor()
        
        # Create file_metadata table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='file_metadata' AND xtype='U')
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
        """)
        
        # Create document_chunks table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='document_chunks' AND xtype='U')
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
            )
        """)
        
        # Create azure_search_chunks table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='azure_search_chunks' AND xtype='U')
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
                FOREIGN KEY (document_chunk_id) REFERENCES document_chunks (id),
                CONSTRAINT UQ_azure_search_chunks UNIQUE(document_chunk_id, index_name)
            )
        """)
        
        # Create chunk_comparisons table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chunk_comparisons' AND xtype='U')
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
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def save_file_metadata(self, metadata: FileMetadata) -> int:
        """
        Save file metadata to database
        Returns the ID of the inserted record
        """
        try:
            if self.db_type == 'sqlite':
                return await self._save_to_sqlite(metadata)
            elif self.db_type == 'azuresql':
                return await self._save_to_azure_sql(metadata)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
        except Exception as e:
            self.logger.error(f"Failed to save file metadata: {str(e)}")
            raise
    
    async def _save_to_sqlite(self, metadata: FileMetadata) -> int:
        """Save metadata to SQLite database"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute("""
                INSERT INTO file_metadata 
                (filename, original_filename, file_size, content_type, blob_url, 
                 container_name, upload_timestamp, checksum, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.filename,
                metadata.original_filename,
                metadata.file_size,
                metadata.content_type,
                metadata.blob_url,
                metadata.container_name,
                metadata.upload_timestamp or datetime.now(UTC),
                metadata.checksum,
                metadata.user_id
            ))
            
            await db.commit()
            return cursor.lastrowid
    
    async def _save_to_azure_sql(self, metadata: FileMetadata) -> int:
        """Save metadata to Azure SQL database"""
        # For async operations with pyodbc, we'll use asyncio.to_thread
        def _execute_insert():
            conn = pyodbc.connect(self.azure_sql_conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO file_metadata 
                (filename, original_filename, file_size, content_type, blob_url,
                 container_name, upload_timestamp, checksum, user_id)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.filename,
                metadata.original_filename,
                metadata.file_size,
                metadata.content_type,
                metadata.blob_url,
                metadata.container_name,
                metadata.upload_timestamp or datetime.now(UTC),
                metadata.checksum,
                metadata.user_id
            ))
            
            row = cursor.fetchone()
            record_id = row[0] if row else None
            conn.commit()
            conn.close()
            
            return record_id
        
        return await asyncio.to_thread(_execute_insert)
    
    async def get_file_metadata(self, file_id: int) -> Optional[FileMetadata]:
        """Retrieve file metadata by ID"""
        try:
            if self.db_type == 'sqlite':
                return await self._get_from_sqlite(file_id)
            elif self.db_type == 'azuresql':
                return await self._get_from_azure_sql(file_id)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
        except Exception as e:
            self.logger.error(f"Failed to retrieve file metadata: {str(e)}")
            raise
    
    async def _get_from_sqlite(self, file_id: int) -> Optional[FileMetadata]:
        """Get metadata from SQLite database"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute("""
                SELECT id, filename, original_filename, file_size, content_type, 
                       blob_url, container_name, upload_timestamp, checksum, user_id
                FROM file_metadata WHERE id = ?
            """, (file_id,))
            
            row = await cursor.fetchone()
            if row:
                return FileMetadata(
                    id=row[0],
                    filename=row[1],
                    original_filename=row[2],
                    file_size=row[3],
                    content_type=row[4],
                    blob_url=row[5],
                    container_name=row[6],
                    upload_timestamp=datetime.fromisoformat(row[7]) if row[7] else None,
                    checksum=row[8],
                    user_id=row[9]
                )
            return None
    
    async def _get_from_azure_sql(self, file_id: int) -> Optional[FileMetadata]:
        """Get metadata from Azure SQL database"""
        def _execute_select():
            conn = pyodbc.connect(self.azure_sql_conn_str)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, filename, original_filename, file_size, content_type,
                       blob_url, container_name, upload_timestamp, checksum, user_id
                FROM file_metadata WHERE id = ?
            """, (file_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return FileMetadata(
                    id=row[0],
                    filename=row[1],
                    original_filename=row[2],
                    file_size=row[3],
                    content_type=row[4],
                    blob_url=row[5],
                    container_name=row[6],
                    upload_timestamp=row[7],
                    checksum=row[8],
                    user_id=row[9]
                )
            return None
        
        return await asyncio.to_thread(_execute_select)
    
    # ===== CHUNK MANAGEMENT FUNCTIONS =====
    
    async def save_document_chunk(self, file_id: int, chunk_index: int, chunk_method: str, 
                                chunk_text: str, start_pos: int = None, end_pos: int = None,
                                keyphrases: List[str] = None, ai_summary: str = None, 
                                ai_title: str = None, processing_time_ms: int = None) -> int:
        """
        Save a document chunk to the database for comparison purposes
        Returns the chunk ID
        """
        import hashlib
        import json
        
        # Generate hash for deduplication
        chunk_hash = hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
        keyphrases_json = json.dumps(keyphrases) if keyphrases else None
        
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("""
                        INSERT OR REPLACE INTO document_chunks 
                        (file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                         start_position, end_position, keyphrases, ai_summary, ai_title, processing_time_ms)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id, chunk_index, chunk_method, len(chunk_text), chunk_text, chunk_hash,
                        start_pos, end_pos, keyphrases_json, ai_summary, ai_title, processing_time_ms
                    ))
                    chunk_id = cursor.lastrowid
                    await db.commit()
                    return chunk_id
                    
            elif self.db_type == 'azuresql':
                def _execute_insert():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    # Use simpler UPSERT approach for Azure SQL
                    cursor.execute("""
                        IF EXISTS (SELECT 1 FROM document_chunks WHERE file_id = ? AND chunk_method = ? AND chunk_index = ?)
                        BEGIN
                            UPDATE document_chunks 
                            SET chunk_size = ?, chunk_text = ?, chunk_hash = ?,
                                start_position = ?, end_position = ?, keyphrases = ?,
                                ai_summary = ?, ai_title = ?, processing_time_ms = ?,
                                created_timestamp = GETUTCDATE()
                            WHERE file_id = ? AND chunk_method = ? AND chunk_index = ?
                        END
                        ELSE
                        BEGIN
                            INSERT INTO document_chunks 
                            (file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                             start_position, end_position, keyphrases, ai_summary, ai_title, processing_time_ms)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        END
                    """, (
                        file_id, chunk_method, chunk_index,  # EXISTS check
                        len(chunk_text), chunk_text, chunk_hash, start_pos, end_pos,  # UPDATE values
                        keyphrases_json, ai_summary, ai_title, processing_time_ms,
                        file_id, chunk_method, chunk_index,  # UPDATE WHERE
                        file_id, chunk_index, chunk_method, len(chunk_text), chunk_text, chunk_hash,  # INSERT values
                        start_pos, end_pos, keyphrases_json, ai_summary, ai_title, processing_time_ms
                    ))
                    
                    # Get the chunk ID
                    cursor.execute("""
                        SELECT id FROM document_chunks 
                        WHERE file_id = ? AND chunk_method = ? AND chunk_index = ?
                    """, (file_id, chunk_method, chunk_index))
                    
                    row = cursor.fetchone()
                    chunk_id = row[0] if row else None
                    conn.commit()
                    conn.close()
                    return chunk_id
                
                return await asyncio.to_thread(_execute_insert)
                
        except Exception as e:
            self.logger.error(f"Failed to save document chunk: {str(e)}")
            raise
    
    async def save_azure_search_chunk(self, document_chunk_id: int, search_document_id: str,
                                    index_name: str, upload_status: str = 'pending',
                                    upload_response: str = None, embedding_dimensions: int = None,
                                    error_message: str = None,
                                    # New paragraph data fields
                                    paragraph_content: str = None, paragraph_title: str = None,
                                    paragraph_summary: str = None, paragraph_keyphrases: str = None,
                                    filename: str = None, paragraph_id: str = None,
                                    date_uploaded: datetime = None, group_tags: str = None,
                                    department: str = None, language: str = None,
                                    is_compliant: bool = None, content_length: int = None) -> int:
        """
        Save Azure Search chunk information for tracking what was indexed,
        including the actual paragraph data for persistence
        """
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("""
                        INSERT OR REPLACE INTO azure_search_chunks 
                        (document_chunk_id, search_document_id, index_name, upload_status,
                         upload_timestamp, upload_response, embedding_dimensions, error_message,
                         paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                         filename, paragraph_id, date_uploaded, group_tags, department, language,
                         is_compliant, content_length)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document_chunk_id, search_document_id, index_name, upload_status,
                        datetime.now(UTC), upload_response, embedding_dimensions, error_message,
                        paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                        filename, paragraph_id, date_uploaded, group_tags, department, language,
                        is_compliant, content_length
                    ))
                    search_chunk_id = cursor.lastrowid
                    await db.commit()
                    return search_chunk_id
                    
            elif self.db_type == 'azuresql':
                def _execute_insert():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    # Use simpler UPSERT approach for Azure SQL
                    cursor.execute("""
                        IF EXISTS (SELECT 1 FROM azure_search_chunks WHERE document_chunk_id = ? AND index_name = ?)
                        BEGIN
                            UPDATE azure_search_chunks 
                            SET search_document_id = ?, upload_status = ?,
                                upload_timestamp = GETUTCDATE(), upload_response = ?,
                                embedding_dimensions = ?, error_message = ?, retry_count = retry_count + 1,
                                paragraph_content = ?, paragraph_title = ?, paragraph_summary = ?,
                                paragraph_keyphrases = ?, filename = ?, paragraph_id = ?,
                                date_uploaded = ?, group_tags = ?, department = ?, language = ?,
                                is_compliant = ?, content_length = ?
                            WHERE document_chunk_id = ? AND index_name = ?
                        END
                        ELSE
                        BEGIN
                            INSERT INTO azure_search_chunks 
                            (document_chunk_id, search_document_id, index_name, upload_status,
                             upload_timestamp, upload_response, embedding_dimensions, error_message,
                             paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                             filename, paragraph_id, date_uploaded, group_tags, department, language,
                             is_compliant, content_length)
                            VALUES (?, ?, ?, ?, GETUTCDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        END
                    """, (
                        document_chunk_id, index_name,  # EXISTS check
                        search_document_id, upload_status, upload_response, embedding_dimensions, error_message,  # UPDATE values
                        paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                        filename, paragraph_id, date_uploaded, group_tags, department, language,
                        is_compliant, content_length,
                        document_chunk_id, index_name,  # UPDATE WHERE
                        document_chunk_id, search_document_id, index_name, upload_status,  # INSERT values
                        upload_response, embedding_dimensions, error_message,
                        paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                        filename, paragraph_id, date_uploaded, group_tags, department, language,
                        is_compliant, content_length
                    ))
                    
                    # Get the search chunk ID
                    cursor.execute("""
                        SELECT id FROM azure_search_chunks 
                        WHERE document_chunk_id = ? AND index_name = ?
                    """, (document_chunk_id, index_name))
                    
                    row = cursor.fetchone()
                    search_chunk_id = row[0] if row else None
                    conn.commit()
                    conn.close()
                    return search_chunk_id
                
                return await asyncio.to_thread(_execute_insert)
                
        except Exception as e:
            self.logger.error(f"Failed to save Azure Search chunk: {str(e)}")
            raise
    
    async def get_document_chunks(self, file_id: int, chunk_method: str = None) -> List[dict]:
        """
        Retrieve document chunks for a file, optionally filtered by chunk method
        """
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    if chunk_method:
                        query = """
                            SELECT id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks WHERE file_id = ? AND chunk_method = ?
                            ORDER BY chunk_index
                        """
                        cursor = await db.execute(query, (file_id, chunk_method))
                    else:
                        query = """
                            SELECT id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks WHERE file_id = ?
                            ORDER BY chunk_method, chunk_index
                        """
                        cursor = await db.execute(query, (file_id,))
                    
                    rows = await cursor.fetchall()
                    
                    chunks = []
                    for row in rows:
                        import json
                        keyphrases = json.loads(row[9]) if row[9] else []
                        chunks.append({
                            'id': row[0],
                            'file_id': row[1],
                            'chunk_index': row[2],
                            'chunk_method': row[3],
                            'chunk_size': row[4],
                            'chunk_text': row[5],
                            'chunk_hash': row[6],
                            'start_position': row[7],
                            'end_position': row[8],
                            'keyphrases': keyphrases,
                            'ai_summary': row[10],
                            'ai_title': row[11],
                            'created_timestamp': row[12],
                            'processing_time_ms': row[13]
                        })
                    return chunks
                    
            elif self.db_type == 'azuresql':
                def _execute_select():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    if chunk_method:
                        cursor.execute("""
                            SELECT id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks WHERE file_id = ? AND chunk_method = ?
                            ORDER BY chunk_index
                        """, (file_id, chunk_method))
                    else:
                        cursor.execute("""
                            SELECT id, file_id, chunk_index, chunk_method, chunk_size, chunk_text, chunk_hash,
                                   start_position, end_position, keyphrases, ai_summary, ai_title, 
                                   created_timestamp, processing_time_ms
                            FROM document_chunks WHERE file_id = ?
                            ORDER BY chunk_method, chunk_index
                        """, (file_id,))
                    
                    rows = cursor.fetchall()
                    conn.close()
                    
                    chunks = []
                    for row in rows:
                        import json
                        keyphrases = json.loads(row[9]) if row[9] else []
                        chunks.append({
                            'id': row[0],
                            'file_id': row[1],
                            'chunk_index': row[2],
                            'chunk_method': row[3],
                            'chunk_size': row[4],
                            'chunk_text': row[5],
                            'chunk_hash': row[6],
                            'start_position': row[7],
                            'end_position': row[8],
                            'keyphrases': keyphrases,
                            'ai_summary': row[10],
                            'ai_title': row[11],
                            'created_timestamp': row[12],
                            'processing_time_ms': row[13]
                        })
                    return chunks
                
                return await asyncio.to_thread(_execute_select)
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve document chunks: {str(e)}")
            raise

    async def get_azure_search_chunks_with_content(self, file_id: int = None, search_document_id: str = None) -> List[dict]:
        """
        Retrieve Azure Search chunks with their full content by joining with document_chunks table
        
        Args:
            file_id: Optional file ID to filter by
            search_document_id: Optional search document ID to filter by specific chunk
            
        Returns:
            List of dictionaries containing both Azure Search tracking info and chunk content
        """
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    # Build dynamic query based on filters
                    base_query = """
                        SELECT 
                            asc.id as search_chunk_id,
                            asc.search_document_id,
                            asc.index_name,
                            asc.upload_status,
                            asc.upload_timestamp,
                            asc.embedding_dimensions,
                            asc.error_message,
                            dc.id as document_chunk_id,
                            dc.file_id,
                            dc.chunk_index,
                            dc.chunk_method,
                            dc.chunk_size,
                            dc.chunk_text,
                            dc.keyphrases,
                            dc.ai_summary,
                            dc.ai_title,
                            dc.created_timestamp
                        FROM azure_search_chunks asc
                        JOIN document_chunks dc ON asc.document_chunk_id = dc.id
                    """
                    
                    params = []
                    conditions = []
                    
                    if file_id:
                        conditions.append("dc.file_id = ?")
                        params.append(file_id)
                        
                    if search_document_id:
                        conditions.append("asc.search_document_id = ?")
                        params.append(search_document_id)
                    
                    if conditions:
                        base_query += " WHERE " + " AND ".join(conditions)
                    
                    base_query += " ORDER BY dc.chunk_index"
                    
                    cursor = await db.execute(base_query, params)
                    rows = await cursor.fetchall()
                    
                    chunks = []
                    for row in rows:
                        import json
                        keyphrases = json.loads(row[13]) if row[13] else []
                        chunks.append({
                            'search_chunk_id': row[0],
                            'search_document_id': row[1],
                            'index_name': row[2],
                            'upload_status': row[3],
                            'upload_timestamp': row[4],
                            'embedding_dimensions': row[5],
                            'error_message': row[6],
                            'document_chunk_id': row[7],
                            'file_id': row[8],
                            'chunk_index': row[9],
                            'chunk_method': row[10],
                            'chunk_size': row[11],
                            'chunk_text': row[12],  # This is the actual content!
                            'keyphrases': keyphrases,
                            'ai_summary': row[14],
                            'ai_title': row[15],
                            'created_timestamp': row[16]
                        })
                    return chunks
                    
            elif self.db_type == 'azuresql':
                def _execute_select():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    base_query = """
                        SELECT 
                            asc.id as search_chunk_id,
                            asc.search_document_id,
                            asc.index_name,
                            asc.upload_status,
                            asc.upload_timestamp,
                            asc.embedding_dimensions,
                            asc.error_message,
                            dc.id as document_chunk_id,
                            dc.file_id,
                            dc.chunk_index,
                            dc.chunk_method,
                            dc.chunk_size,
                            dc.chunk_text,
                            dc.keyphrases,
                            dc.ai_summary,
                            dc.ai_title,
                            dc.created_timestamp
                        FROM azure_search_chunks asc
                        JOIN document_chunks dc ON asc.document_chunk_id = dc.id
                    """
                    
                    params = []
                    conditions = []
                    
                    if file_id:
                        conditions.append("dc.file_id = ?")
                        params.append(file_id)
                        
                    if search_document_id:
                        conditions.append("asc.search_document_id = ?")
                        params.append(search_document_id)
                    
                    if conditions:
                        base_query += " WHERE " + " AND ".join(conditions)
                    
                    base_query += " ORDER BY dc.chunk_index"
                    
                    cursor.execute(base_query, params)
                    rows = cursor.fetchall()
                    conn.close()
                    
                    chunks = []
                    for row in rows:
                        import json
                        keyphrases = json.loads(row[13]) if row[13] else []
                        chunks.append({
                            'search_chunk_id': row[0],
                            'search_document_id': row[1],
                            'index_name': row[2],
                            'upload_status': row[3],
                            'upload_timestamp': row[4],
                            'embedding_dimensions': row[5],
                            'error_message': row[6],
                            'document_chunk_id': row[7],
                            'file_id': row[8],
                            'chunk_index': row[9],
                            'chunk_method': row[10],
                            'chunk_size': row[11],
                            'chunk_text': row[12],  # This is the actual content!
                            'keyphrases': keyphrases,
                            'ai_summary': row[14],
                            'ai_title': row[15],
                            'created_timestamp': row[16]
                        })
                    return chunks
                
                return await asyncio.to_thread(_execute_select)
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve Azure Search chunks with content: {str(e)}")
            raise
    
    async def get_azure_search_chunks_persisted(self, filename: str = None, search_document_id: str = None, limit: int = None) -> List[dict]:
        """
        Retrieve Azure Search chunks with persisted paragraph data directly from azure_search_chunks table
        
        Args:
            filename: Optional filename to filter by
            search_document_id: Optional search document ID to filter by specific chunk
            limit: Optional limit on number of results
            
        Returns:
            List of dictionaries containing persisted paragraph data
        """
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    # Build dynamic query for persisted paragraph data
                    base_query = """
                        SELECT 
                            id, search_document_id, index_name, upload_status, upload_timestamp,
                            paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                            filename, paragraph_id, date_uploaded, group_tags, department, language,
                            is_compliant, content_length, embedding_dimensions, error_message
                        FROM azure_search_chunks
                        WHERE upload_status = 'success' AND paragraph_content IS NOT NULL
                    """
                    
                    params = []
                    
                    if filename:
                        base_query += " AND filename = ?"
                        params.append(filename)
                        
                    if search_document_id:
                        base_query += " AND search_document_id = ?"
                        params.append(search_document_id)
                    
                    base_query += " ORDER BY paragraph_id"
                    
                    if limit:
                        base_query += " LIMIT ?"
                        params.append(limit)
                    
                    cursor = await db.execute(base_query, params)
                    rows = await cursor.fetchall()
                    
                    chunks = []
                    for row in rows:
                        import json
                        
                        # Parse JSON fields safely
                        keyphrases = json.loads(row[8]) if row[8] else []
                        group_tags = json.loads(row[12]) if row[12] else []
                        
                        chunks.append({
                            'id': row[1],  # search_document_id as primary ID
                            'title': row[6],  # paragraph_title
                            'content': row[5],  # paragraph_content
                            'content_length': row[16],  # content_length
                            'summary': row[7],  # paragraph_summary
                            'keyphrases': keyphrases,
                            'filename': row[9],  # filename
                            'paragraph_id': row[10],  # paragraph_id
                            'date': row[11].isoformat() if row[11] and hasattr(row[11], 'isoformat') else str(row[11]) if row[11] else None,  # date_uploaded
                            'group': group_tags,
                            'department': row[13],  # department
                            'language': row[14],  # language
                            'is_compliant': bool(row[15]) if row[15] is not None else None,  # is_compliant
                            'search_score': None,  # Not available in stored data
                            'upload_status': row[3],  # upload_status
                            'upload_timestamp': row[4],  # upload_timestamp
                            'index_name': row[2],  # index_name
                            'embedding_dimensions': row[17],  # embedding_dimensions
                            'error_message': row[18]  # error_message
                        })
                    return chunks
                    
            elif self.db_type == 'azuresql':
                def _execute_select():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    base_query = """
                        SELECT 
                            id, search_document_id, index_name, upload_status, upload_timestamp,
                            paragraph_content, paragraph_title, paragraph_summary, paragraph_keyphrases,
                            filename, paragraph_id, date_uploaded, group_tags, department, language,
                            is_compliant, content_length, embedding_dimensions, error_message
                        FROM azure_search_chunks
                        WHERE upload_status = 'success' AND paragraph_content IS NOT NULL
                    """
                    
                    params = []
                    
                    if filename:
                        base_query += " AND filename = ?"
                        params.append(filename)
                        
                    if search_document_id:
                        base_query += " AND search_document_id = ?"
                        params.append(search_document_id)
                    
                    base_query += " ORDER BY paragraph_id"
                    
                    if limit:
                        base_query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
                    
                    cursor.execute(base_query, params)
                    rows = cursor.fetchall()
                    conn.close()
                    
                    chunks = []
                    for row in rows:
                        import json
                        
                        # Parse JSON fields safely
                        keyphrases = json.loads(row[8]) if row[8] else []
                        group_tags = json.loads(row[12]) if row[12] else []
                        
                        chunks.append({
                            'id': row[1],  # search_document_id as primary ID
                            'title': row[6],  # paragraph_title
                            'content': row[5],  # paragraph_content
                            'content_length': row[16],  # content_length
                            'summary': row[7],  # paragraph_summary
                            'keyphrases': keyphrases,
                            'filename': row[9],  # filename
                            'paragraph_id': row[10],  # paragraph_id
                            'date': row[11].isoformat() if row[11] and hasattr(row[11], 'isoformat') else str(row[11]) if row[11] else None,  # date_uploaded
                            'group': group_tags,
                            'department': row[13],  # department
                            'language': row[14],  # language
                            'is_compliant': bool(row[15]) if row[15] is not None else None,  # is_compliant
                            'search_score': None,  # Not available in stored data
                            'upload_status': row[3],  # upload_status
                            'upload_timestamp': row[4],  # upload_timestamp
                            'index_name': row[2],  # index_name
                            'embedding_dimensions': row[17],  # embedding_dimensions
                            'error_message': row[18]  # error_message
                        })
                    return chunks
                
                return await asyncio.to_thread(_execute_select)
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve persisted Azure Search chunks: {str(e)}")
            raise
    
    async def compare_chunking_methods(self, file_id: int, method_a: str, method_b: str) -> dict:
        """
        Compare two chunking methods for the same document and return analysis
        """
        import json
        from collections import defaultdict
        
        try:
            # Get chunks for both methods
            chunks_a = await self.get_document_chunks(file_id, method_a)
            chunks_b = await self.get_document_chunks(file_id, method_b)
            
            if not chunks_a or not chunks_b:
                raise ValueError(f"No chunks found for comparison. Method A: {len(chunks_a)}, Method B: {len(chunks_b)}")
            
            # Calculate basic statistics
            total_chars_a = sum(chunk['chunk_size'] for chunk in chunks_a)
            total_chars_b = sum(chunk['chunk_size'] for chunk in chunks_b)
            avg_chunk_size_a = total_chars_a / len(chunks_a)
            avg_chunk_size_b = total_chars_b / len(chunks_b)
            
            # Calculate processing times
            total_time_a = sum(chunk['processing_time_ms'] or 0 for chunk in chunks_a)
            total_time_b = sum(chunk['processing_time_ms'] or 0 for chunk in chunks_b)
            
            # Calculate content overlap using chunk hashes
            hashes_a = set(chunk['chunk_hash'] for chunk in chunks_a if chunk['chunk_hash'])
            hashes_b = set(chunk['chunk_hash'] for chunk in chunks_b if chunk['chunk_hash'])
            
            if hashes_a and hashes_b:
                overlap_hashes = hashes_a.intersection(hashes_b)
                content_overlap_pct = len(overlap_hashes) / max(len(hashes_a), len(hashes_b)) * 100
            else:
                # Fallback: calculate text similarity
                content_overlap_pct = self._calculate_text_similarity(chunks_a, chunks_b)
            
            # Calculate similarity score (0-1)
            size_similarity = 1 - abs(avg_chunk_size_a - avg_chunk_size_b) / max(avg_chunk_size_a, avg_chunk_size_b)
            count_similarity = 1 - abs(len(chunks_a) - len(chunks_b)) / max(len(chunks_a), len(chunks_b))
            similarity_score = (size_similarity + count_similarity + content_overlap_pct/100) / 3
            
            # Detailed analysis
            detailed_analysis = {
                'method_a_stats': {
                    'total_chunks': len(chunks_a),
                    'avg_size': avg_chunk_size_a,
                    'min_size': min(chunk['chunk_size'] for chunk in chunks_a),
                    'max_size': max(chunk['chunk_size'] for chunk in chunks_a),
                    'total_processing_time_ms': total_time_a
                },
                'method_b_stats': {
                    'total_chunks': len(chunks_b),
                    'avg_size': avg_chunk_size_b,
                    'min_size': min(chunk['chunk_size'] for chunk in chunks_b),
                    'max_size': max(chunk['chunk_size'] for chunk in chunks_b),
                    'total_processing_time_ms': total_time_b
                },
                'overlap_analysis': {
                    'duplicate_hashes': len(overlap_hashes) if hashes_a and hashes_b else 0,
                    'unique_to_a': len(hashes_a - hashes_b) if hashes_a and hashes_b else len(chunks_a),
                    'unique_to_b': len(hashes_b - hashes_a) if hashes_a and hashes_b else len(chunks_b)
                }
            }
            
            comparison_result = {
                'file_id': file_id,
                'method_a': method_a,
                'method_b': method_b,
                'total_chunks_a': len(chunks_a),
                'total_chunks_b': len(chunks_b),
                'similarity_score': similarity_score,
                'content_overlap_pct': content_overlap_pct,
                'avg_chunk_size_a': avg_chunk_size_a,
                'avg_chunk_size_b': avg_chunk_size_b,
                'processing_time_a_ms': total_time_a,
                'processing_time_b_ms': total_time_b,
                'detailed_analysis': detailed_analysis
            }
            
            # Save comparison to database
            await self._save_chunk_comparison(comparison_result)
            
            return comparison_result
            
        except Exception as e:
            self.logger.error(f"Failed to compare chunking methods: {str(e)}")
            raise
    
    def _calculate_text_similarity(self, chunks_a: List[dict], chunks_b: List[dict]) -> float:
        """
        Calculate text similarity between two sets of chunks using basic string comparison
        """
        try:
            text_a = ' '.join(chunk['chunk_text'] for chunk in chunks_a)
            text_b = ' '.join(chunk['chunk_text'] for chunk in chunks_b)
            
            # Simple similarity based on common words
            words_a = set(text_a.lower().split())
            words_b = set(text_b.lower().split())
            
            if not words_a or not words_b:
                return 0.0
            
            intersection = words_a.intersection(words_b)
            union = words_a.union(words_b)
            
            return len(intersection) / len(union) * 100 if union else 0.0
            
        except Exception:
            return 0.0
    
    async def _save_chunk_comparison(self, comparison_result: dict):
        """
        Save chunk comparison analysis to database
        """
        import json
        
        try:
            detailed_json = json.dumps(comparison_result['detailed_analysis'])
            comparison_name = f"{comparison_result['method_a']}_vs_{comparison_result['method_b']}"
            
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    await db.execute("""
                        INSERT OR REPLACE INTO chunk_comparisons 
                        (file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                         similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                         processing_time_a_ms, processing_time_b_ms, detailed_analysis)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comparison_result['file_id'], comparison_name, comparison_result['method_a'], comparison_result['method_b'],
                        comparison_result['total_chunks_a'], comparison_result['total_chunks_b'],
                        comparison_result['similarity_score'], comparison_result['content_overlap_pct'],
                        comparison_result['avg_chunk_size_a'], comparison_result['avg_chunk_size_b'],
                        comparison_result['processing_time_a_ms'], comparison_result['processing_time_b_ms'],
                        detailed_json
                    ))
                    await db.commit()
                    
            elif self.db_type == 'azuresql':
                def _execute_insert():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    # Use simpler UPSERT approach for Azure SQL
                    cursor.execute("""
                        IF EXISTS (SELECT 1 FROM chunk_comparisons WHERE file_id = ? AND method_a = ? AND method_b = ?)
                        BEGIN
                            UPDATE chunk_comparisons 
                            SET comparison_name = ?, total_chunks_a = ?, total_chunks_b = ?,
                                similarity_score = ?, content_overlap_pct = ?, avg_chunk_size_a = ?,
                                avg_chunk_size_b = ?, processing_time_a_ms = ?, processing_time_b_ms = ?,
                                analysis_timestamp = GETUTCDATE(), detailed_analysis = ?
                            WHERE file_id = ? AND method_a = ? AND method_b = ?
                        END
                        ELSE
                        BEGIN
                            INSERT INTO chunk_comparisons 
                            (file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                             similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                             processing_time_a_ms, processing_time_b_ms, detailed_analysis)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        END
                    """, (
                        comparison_result['file_id'], comparison_result['method_a'], comparison_result['method_b'],  # EXISTS check
                        comparison_name, comparison_result['total_chunks_a'], comparison_result['total_chunks_b'],  # UPDATE values
                        comparison_result['similarity_score'], comparison_result['content_overlap_pct'], 
                        comparison_result['avg_chunk_size_a'], comparison_result['avg_chunk_size_b'],
                        comparison_result['processing_time_a_ms'], comparison_result['processing_time_b_ms'], detailed_json,
                        comparison_result['file_id'], comparison_result['method_a'], comparison_result['method_b'],  # UPDATE WHERE
                        comparison_result['file_id'], comparison_name, comparison_result['method_a'], comparison_result['method_b'],  # INSERT values
                        comparison_result['total_chunks_a'], comparison_result['total_chunks_b'],
                        comparison_result['similarity_score'], comparison_result['content_overlap_pct'], 
                        comparison_result['avg_chunk_size_a'], comparison_result['avg_chunk_size_b'],
                        comparison_result['processing_time_a_ms'], comparison_result['processing_time_b_ms'], detailed_json
                    ))
                    
                    conn.commit()
                    conn.close()
                
                await asyncio.to_thread(_execute_insert)
                
        except Exception as e:
            self.logger.error(f"Failed to save chunk comparison: {str(e)}")
            # Don't raise - this is just for tracking
    
    async def get_chunk_comparisons(self, file_id: int = None) -> List[dict]:
        """
        Get chunk comparison results, optionally filtered by file_id
        """
        try:
            if self.db_type == 'sqlite':
                async with aiosqlite.connect(self.sqlite_path) as db:
                    if file_id:
                        query = """
                            SELECT id, file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                                   similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                                   processing_time_a_ms, processing_time_b_ms, analysis_timestamp, detailed_analysis
                            FROM chunk_comparisons WHERE file_id = ?
                            ORDER BY analysis_timestamp DESC
                        """
                        cursor = await db.execute(query, (file_id,))
                    else:
                        query = """
                            SELECT id, file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                                   similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                                   processing_time_a_ms, processing_time_b_ms, analysis_timestamp, detailed_analysis
                            FROM chunk_comparisons
                            ORDER BY analysis_timestamp DESC
                        """
                        cursor = await db.execute(query)
                    
                    rows = await cursor.fetchall()
                    
                    comparisons = []
                    for row in rows:
                        import json
                        detailed_analysis = json.loads(row[14]) if row[14] else {}
                        comparisons.append({
                            'id': row[0],
                            'file_id': row[1],
                            'comparison_name': row[2],
                            'method_a': row[3],
                            'method_b': row[4],
                            'total_chunks_a': row[5],
                            'total_chunks_b': row[6],
                            'similarity_score': row[7],
                            'content_overlap_pct': row[8],
                            'avg_chunk_size_a': row[9],
                            'avg_chunk_size_b': row[10],
                            'processing_time_a_ms': row[11],
                            'processing_time_b_ms': row[12],
                            'analysis_timestamp': row[13],
                            'detailed_analysis': detailed_analysis
                        })
                    return comparisons
                    
            elif self.db_type == 'azuresql':
                def _execute_select():
                    conn = pyodbc.connect(self.azure_sql_conn_str)
                    cursor = conn.cursor()
                    
                    if file_id:
                        cursor.execute("""
                            SELECT id, file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                                   similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                                   processing_time_a_ms, processing_time_b_ms, analysis_timestamp, detailed_analysis
                            FROM chunk_comparisons WHERE file_id = ?
                            ORDER BY analysis_timestamp DESC
                        """, (file_id,))
                    else:
                        cursor.execute("""
                            SELECT id, file_id, comparison_name, method_a, method_b, total_chunks_a, total_chunks_b,
                                   similarity_score, content_overlap_pct, avg_chunk_size_a, avg_chunk_size_b,
                                   processing_time_a_ms, processing_time_b_ms, analysis_timestamp, detailed_analysis
                            FROM chunk_comparisons
                            ORDER BY analysis_timestamp DESC
                        """)
                    
                    rows = cursor.fetchall()
                    conn.close()
                    
                    comparisons = []
                    for row in rows:
                        import json
                        detailed_analysis = json.loads(row[14]) if row[14] else {}
                        comparisons.append({
                            'id': row[0],
                            'file_id': row[1],
                            'comparison_name': row[2],
                            'method_a': row[3],
                            'method_b': row[4],
                            'total_chunks_a': row[5],
                            'total_chunks_b': row[6],
                            'similarity_score': row[7],
                            'content_overlap_pct': row[8],
                            'avg_chunk_size_a': row[9],
                            'avg_chunk_size_b': row[10],
                            'processing_time_a_ms': row[11],
                            'processing_time_b_ms': row[12],
                            'analysis_timestamp': row[13],
                            'detailed_analysis': detailed_analysis
                        })
                    return comparisons
                
                return await asyncio.to_thread(_execute_select)
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve chunk comparisons: {str(e)}")
            raise

    async def reset_table(self, table_name: str) -> dict:
        """
        Reset a specific table by deleting all records
        Returns count of deleted records and any errors
        """
        try:
            result = {
                "table": table_name,
                "records_deleted": 0,
                "success": False,
                "error": None
            }
            
            if self.db_type == "sqlite":
                async with aiosqlite.connect(self.sqlite_path) as db:
                    # Count records before deletion
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await cursor.fetchone()
                    record_count = count_result[0] if count_result else 0
                    
                    # Delete all records
                    await db.execute(f"DELETE FROM {table_name}")
                    
                    # Reset auto-increment sequence
                    await db.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                    
                    await db.commit()
                    
                    result["records_deleted"] = record_count
                    result["success"] = True
                    self.logger.info(f"✅ Reset table {table_name}: {record_count} records deleted")
                    
            elif self.db_type == "azuresql":
                def _execute_reset():
                    import pyodbc
                    with pyodbc.connect(self.azure_sql_conn_str) as conn:
                        cursor = conn.cursor()
                        
                        # Count records before deletion
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        record_count = cursor.fetchone()[0]
                        
                        # Delete all records
                        cursor.execute(f"DELETE FROM {table_name}")
                        
                        # Reset identity column if it exists
                        try:
                            cursor.execute(f"DBCC CHECKIDENT ('{table_name}', RESEED, 0)")
                        except:
                            # Not all tables have identity columns
                            pass
                            
                        conn.commit()
                        return record_count
                
                record_count = await asyncio.to_thread(_execute_reset)
                result["records_deleted"] = record_count
                result["success"] = True
                self.logger.info(f"✅ Reset table {table_name}: {record_count} records deleted")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to reset {table_name}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "table": table_name,
                "records_deleted": 0,
                "success": False,
                "error": error_msg
            }

    async def reset_all_tables(self) -> dict:
        """
        Reset all tables in dependency order
        Returns comprehensive reset results
        """
        try:
            # Define tables in dependency order (child tables first)
            tables_to_reset = [
                "chunk_comparisons",
                "azure_search_chunks", 
                "document_chunks",
                "file_metadata"
            ]
            
            reset_results = {
                "tables_reset": [],
                "tables_with_errors": [],
                "total_records_deleted": 0,
                "summary": {
                    "tables_processed": 0,
                    "tables_reset_successfully": 0,
                    "tables_with_errors": 0,
                    "total_records_deleted": 0
                }
            }
            
            for table_name in tables_to_reset:
                self.logger.info(f"🗑️ Resetting table: {table_name}")
                result = await self.reset_table(table_name)
                
                reset_results["summary"]["tables_processed"] += 1
                
                if result["success"]:
                    reset_results["tables_reset"].append(table_name)
                    reset_results["total_records_deleted"] += result["records_deleted"]
                    reset_results["summary"]["tables_reset_successfully"] += 1
                    reset_results["summary"]["total_records_deleted"] += result["records_deleted"]
                else:
                    reset_results["tables_with_errors"].append({
                        "table": table_name,
                        "error": result["error"]
                    })
                    reset_results["summary"]["tables_with_errors"] += 1
            
            return reset_results
            
        except Exception as e:
            self.logger.error(f"Failed to reset all tables: {str(e)}")
            raise