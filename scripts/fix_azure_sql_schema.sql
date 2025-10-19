-- Drop and recreate azure_search_chunks table with correct schema
-- This SQL script will be executed via Azure CLI

-- First, check if table exists and show current structure
IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'azure_search_chunks')
BEGIN
    PRINT 'Table azure_search_chunks exists - showing current structure...'
    
    SELECT 
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE,
        COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'azure_search_chunks'
    ORDER BY ORDINAL_POSITION;
    
    -- Show row count
    SELECT COUNT(*) as current_row_count FROM azure_search_chunks;
    
    PRINT 'Dropping existing table...'
    DROP TABLE azure_search_chunks;
    PRINT 'Table dropped successfully.'
END
ELSE
BEGIN
    PRINT 'Table azure_search_chunks does not exist yet.'
END;

-- Create table with complete schema that matches SQLite definition
PRINT 'Creating azure_search_chunks table with correct schema...'

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
);

PRINT 'Table created successfully!'

-- Show new table structure
PRINT 'New table structure:'
SELECT 
    ORDINAL_POSITION as Position,
    COLUMN_NAME as ColumnName,
    DATA_TYPE as DataType,
    CHARACTER_MAXIMUM_LENGTH as MaxLength,
    IS_NULLABLE as Nullable,
    COLUMN_DEFAULT as DefaultValue
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'azure_search_chunks'
ORDER BY ORDINAL_POSITION;

PRINT 'Schema fix completed successfully!'