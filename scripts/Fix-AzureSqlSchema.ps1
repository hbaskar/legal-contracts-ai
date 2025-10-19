# PowerShell script to fix Azure SQL database schema
# This script uses .NET SQL Client to connect and execute the SQL

Write-Host "Azure SQL Schema Fix Tool (PowerShell)" -ForegroundColor Yellow
Write-Host ("=" * 50)

# Load System.Data.SqlClient
Add-Type -AssemblyName System.Data

# Connection parameters
$server = "ggndadev-sqlsvr01.database.windows.net"
$database = "CMSDEVDB"

# Build connection string with Azure AD authentication
$connectionString = "Server=tcp:$server,1433;Initial Catalog=$database;Persist Security Info=False;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Authentication=Active Directory Interactive;"

Write-Host "Connecting to Azure SQL..." -ForegroundColor Cyan

try {
    $connection = New-Object System.Data.SqlClient.SqlConnection
    $connection.ConnectionString = $connectionString
    $connection.Open()
    
    Write-Host "Connection successful" -ForegroundColor Green
    
    # Check if table exists and show current structure
    Write-Host "📋 Checking current table structure..." -ForegroundColor Cyan
    
    $checkTableCmd = $connection.CreateCommand()
    $checkTableCmd.CommandText = @"
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'azure_search_chunks'
"@
    $tableExists = $checkTableCmd.ExecuteScalar()
    
    if ($tableExists -gt 0) {
        Write-Host "📊 Current table structure:" -ForegroundColor Yellow
        
        $showStructureCmd = $connection.CreateCommand()
        $showStructureCmd.CommandText = @"
            SELECT 
                ORDINAL_POSITION as Position,
                COLUMN_NAME as ColumnName,
                DATA_TYPE as DataType,
                CHARACTER_MAXIMUM_LENGTH as MaxLength,
                IS_NULLABLE as Nullable
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'azure_search_chunks'
            ORDER BY ORDINAL_POSITION
"@
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($showStructureCmd)
        $dataSet = New-Object System.Data.DataSet
        $adapter.Fill($dataSet)
        
        $dataSet.Tables[0] | Format-Table -AutoSize
        
        # Show row count
        $countCmd = $connection.CreateCommand()
        $countCmd.CommandText = "SELECT COUNT(*) FROM azure_search_chunks"
        $rowCount = $countCmd.ExecuteScalar()
        Write-Host "📊 Current row count: $rowCount" -ForegroundColor Yellow
        
        # Check if paragraph_content column exists
        $checkColumnCmd = $connection.CreateCommand()
        $checkColumnCmd.CommandText = @"
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'azure_search_chunks' AND COLUMN_NAME = 'paragraph_content'
"@
        $columnExists = $checkColumnCmd.ExecuteScalar()
        
        if ($columnExists -gt 0) {
            Write-Host "✅ paragraph_content column already exists!" -ForegroundColor Green
            Write-Host "ℹ️  The schema appears to be correct. The issue might be elsewhere." -ForegroundColor Blue
            return
        } else {
            Write-Host "❌ paragraph_content column is missing" -ForegroundColor Red
        }
        
    } else {
        Write-Host "ℹ️  Table doesn't exist yet" -ForegroundColor Blue
    }
    
    # Confirm before proceeding
    Write-Host ""
    Write-Host "⚠️  WARNING: About to drop and recreate azure_search_chunks table" -ForegroundColor Red
    Write-Host "   - This will remove all existing data!" -ForegroundColor Red
    Write-Host "   - New table will have the correct schema with paragraph_content column" -ForegroundColor Yellow
    
    $response = Read-Host "`nProceed? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "❌ Operation cancelled by user" -ForegroundColor Red
        return
    }
    
    # Drop existing table
    if ($tableExists -gt 0) {
        Write-Host "🗑️  Dropping existing table..." -ForegroundColor Yellow
        
        $dropCmd = $connection.CreateCommand()
        $dropCmd.CommandText = "DROP TABLE azure_search_chunks"
        $dropCmd.ExecuteNonQuery()
        
        Write-Host "✅ Table dropped successfully" -ForegroundColor Green
    }
    
    # Create new table with correct schema
    Write-Host "🏗️  Creating table with correct schema..." -ForegroundColor Cyan
    
    $createCmd = $connection.CreateCommand()
    $createCmd.CommandText = @"
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
"@
    
    $createCmd.ExecuteNonQuery()
    Write-Host "✅ Table created successfully!" -ForegroundColor Green
    
    # Show new table structure
    Write-Host "📊 New table structure:" -ForegroundColor Cyan
    
    $showNewStructureCmd = $connection.CreateCommand()
    $showNewStructureCmd.CommandText = @"
        SELECT 
            ORDINAL_POSITION as Position,
            COLUMN_NAME as ColumnName,
            DATA_TYPE as DataType,
            CHARACTER_MAXIMUM_LENGTH as MaxLength,
            IS_NULLABLE as Nullable
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'azure_search_chunks'
        ORDER BY ORDINAL_POSITION
"@
    $newAdapter = New-Object System.Data.SqlClient.SqlDataAdapter($showNewStructureCmd)
    $newDataSet = New-Object System.Data.DataSet
    $newAdapter.Fill($newDataSet)
    
    $newDataSet.Tables[0] | Format-Table -AutoSize
    
    Write-Host ""
    Write-Host "🎉 Schema fix completed successfully!" -ForegroundColor Green
    Write-Host "💡 You can now test the persisted chunks endpoint" -ForegroundColor Blue
    
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.Exception.StackTrace -ForegroundColor Red
} finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
        Write-Host "📋 Database connection closed" -ForegroundColor Blue
    }
}