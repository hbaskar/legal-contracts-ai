-- Alternative approach: ADD missing columns to existing table
-- Use this if you want to preserve any existing data in azure_search_chunks

-- Add the missing paragraph data columns
ALTER TABLE azure_search_chunks ADD paragraph_content NTEXT;
ALTER TABLE azure_search_chunks ADD paragraph_title NVARCHAR(500);
ALTER TABLE azure_search_chunks ADD paragraph_summary NTEXT;
ALTER TABLE azure_search_chunks ADD paragraph_keyphrases NTEXT;
ALTER TABLE azure_search_chunks ADD filename NVARCHAR(255);
ALTER TABLE azure_search_chunks ADD paragraph_id NVARCHAR(50);
ALTER TABLE azure_search_chunks ADD date_uploaded DATETIME2;
ALTER TABLE azure_search_chunks ADD group_tags NTEXT;
ALTER TABLE azure_search_chunks ADD department NVARCHAR(100);
ALTER TABLE azure_search_chunks ADD language NVARCHAR(10);
ALTER TABLE azure_search_chunks ADD is_compliant BIT;
ALTER TABLE azure_search_chunks ADD content_length INTEGER;

-- Verify the columns were added
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'azure_search_chunks'
ORDER BY ORDINAL_POSITION;