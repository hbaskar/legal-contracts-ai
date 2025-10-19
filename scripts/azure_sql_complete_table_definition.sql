-- Complete Azure SQL table definition for azure_search_chunks
-- This includes all the paragraph_* columns that are missing

-- First, drop the existing table (CAUTION: This will delete all data)
IF OBJECT_ID('azure_search_chunks', 'U') IS NOT NULL
    DROP TABLE azure_search_chunks;

-- Create the complete table with all required columns
CREATE TABLE azure_search_chunks (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    document_chunk_id BIGINT NOT NULL,
    search_document_id NVARCHAR(255) NOT NULL,
    index_name NVARCHAR(100) NOT NULL,
    
    -- Persisted paragraph data from Azure Search (THESE ARE THE MISSING COLUMNS)
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
    
    -- Upload tracking metadata (EXISTING COLUMNS)
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

-- Verify the table was created with all columns
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