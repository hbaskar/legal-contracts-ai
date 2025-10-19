# Simple PowerShell script to fix Azure SQL database schema

Write-Host "Azure SQL Schema Fix Tool" -ForegroundColor Yellow
Write-Host ("=" * 50)

# Load System.Data.SqlClient
Add-Type -AssemblyName System.Data

# Connection parameters
$server = "ggndadev-sqlsvr01.database.windows.net"
$database = "CMSDEVDB"

# Build connection string with Azure AD authentication
$connectionString = "Server=tcp:$server,1433;Initial Catalog=$database;Integrated Security=True;Encrypt=True;TrustServerCertificate=False;"

Write-Host "Connecting to Azure SQL..." -ForegroundColor Cyan

try {
    $connection = New-Object System.Data.SqlClient.SqlConnection
    $connection.ConnectionString = $connectionString
    $connection.Open()
    
    Write-Host "Connection successful" -ForegroundColor Green
    
    # Check if paragraph_content column exists
    $checkColumnCmd = $connection.CreateCommand()
    $checkColumnCmd.CommandText = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'azure_search_chunks' AND COLUMN_NAME = 'paragraph_content'"
    $columnExists = $checkColumnCmd.ExecuteScalar()
    
    if ($columnExists -gt 0) {
        Write-Host "paragraph_content column already exists!" -ForegroundColor Green
        Write-Host "The schema appears to be correct." -ForegroundColor Blue
        return
    }
    
    # Confirm before proceeding
    Write-Host ""
    Write-Host "WARNING: About to drop and recreate azure_search_chunks table" -ForegroundColor Red
    Write-Host "This will remove all existing data!" -ForegroundColor Red
    
    $response = Read-Host "Proceed? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Operation cancelled" -ForegroundColor Red
        return
    }
    
    # Drop existing table
    Write-Host "Dropping existing table..." -ForegroundColor Yellow
    $dropCmd = $connection.CreateCommand()
    $dropCmd.CommandText = "IF OBJECT_ID('azure_search_chunks', 'U') IS NOT NULL DROP TABLE azure_search_chunks"
    $dropCmd.ExecuteNonQuery()
    Write-Host "Table dropped" -ForegroundColor Green
    
    # Create new table with correct schema
    Write-Host "Creating table with correct schema..." -ForegroundColor Cyan
    
    $createSql = @"
CREATE TABLE azure_search_chunks (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    document_chunk_id BIGINT NOT NULL,
    search_document_id NVARCHAR(255) NOT NULL,
    index_name NVARCHAR(100) NOT NULL,
    paragraph_content NTEXT,
    paragraph_title NVARCHAR(500),
    paragraph_summary NTEXT,
    paragraph_keyphrases NTEXT,
    filename NVARCHAR(255),
    paragraph_id NVARCHAR(50),
    date_uploaded DATETIME2,
    group_tags NTEXT,
    department NVARCHAR(100),
    language NVARCHAR(10),
    is_compliant BIT,
    content_length INTEGER,
    upload_status NVARCHAR(20) DEFAULT 'pending',
    upload_timestamp DATETIME2,
    upload_response NTEXT,
    embedding_dimensions INTEGER,
    search_score REAL,
    retry_count INTEGER DEFAULT 0,
    error_message NTEXT,
    CONSTRAINT UQ_azure_search_chunks UNIQUE(document_chunk_id, index_name)
)
"@
    
    $createCmd = $connection.CreateCommand()
    $createCmd.CommandText = $createSql
    $createCmd.ExecuteNonQuery()
    
    Write-Host "Table created successfully!" -ForegroundColor Green
    
    # Verify the schema
    $verifyCmd = $connection.CreateCommand()
    $verifyCmd.CommandText = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'azure_search_chunks'"
    $columnCount = $verifyCmd.ExecuteScalar()
    
    Write-Host "New table has $columnCount columns" -ForegroundColor Cyan
    Write-Host "Schema fix completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "Database connection closed" -ForegroundColor Blue
    }
}