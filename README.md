# Azure Function File Upload Service

A comprehensive Azure Function service for uploading files to Azure Blob Storage with metadata storage in Azure SQL or SQLite.

## Features

- **Azure Functions v2 Programming Model**: Uses the latest Python v2 programming model with decorators
- **Environment Configuration**: Secure .env-based configuration with validation
- **File Upload**: HTTP endpoint for uploading files to Azure Blob Storage
- **AI Document Processing**: Intelligent document chunking with OpenAI integration and Azure Search
- **Configurable Chunking Methods**: Environment variable control for default chunking strategy
- **Metadata Storage**: Stores file metadata in Azure SQL (production) or SQLite (local development)
- **Security**: Uses managed identity for Azure resource access in production
- **File Integrity**: Calculates MD5 checksums for uploaded files
- **Secure Downloads**: Generates SAS URLs for secure file access
- **Health Monitoring**: Health check endpoint with configuration info
- **Error Handling**: Comprehensive error handling and logging
- **Performance Optimized**: Retry policies and health monitoring configured
- **Multi-Environment Support**: Easy configuration for dev/staging/production environments

## Project Structure

```
fresh_start/
├── host.json              # Function host configuration
├── local.settings.json    # Development settings
├── requirements.txt       # Python dependencies
├── function_app.py        # Main application entry
├── run_tests.py           # Test runner script
├── contracts/             # Core business logic
│   ├── __init__.py        # Module initialization
│   ├── config.py          # Configuration management
│   ├── ai_services.py     # AI processing and OpenAI integration
│   ├── database.py        # Database operations
│   ├── storage.py         # Blob storage operations
│   ├── index_creation.py  # Azure Search index management
│   ├── chunk_comparison.py# Document chunking comparison
│   └── models.py          # Data models
├── blob/                  # Blob processing
│   ├── README.md          # Blob processing documentation
│   └── blob_processor.py  # Blob processing utilities
├── deployment/            # Deployment scripts
│   ├── README.md          # Deployment documentation
│   └── deploy.ps1         # PowerShell deployment script
├── docs/                  # Documentation
│   ├── README.md          # Documentation index
│   └── *.md               # Guides and references
├── postman/              # API testing
│   ├── README.md          # Postman collection documentation
│   ├── *.postman_collection.json
│   └── *.postman_environment.json
├── scripts/              # Utility scripts
│   ├── README.md          # Scripts documentation
│   ├── setup.py           # Project setup
│   ├── check_database.py  # Database validation
│   └── update_postman_*.py # Postman collection updates
├── tests/                # Test suite
│   ├── README.md          # Test documentation
│   ├── __init__.py
│   └── test_*.py          # Unit and integration tests
├── test_files/           # Test data
└── data/                 # Local data storage
```

## API Endpoints

### 1. Upload File
- **POST** `/api/upload`
- **Content-Type**: `multipart/form-data`
- **Parameters**: `file` (required)
- **Response**: JSON with file metadata

### 2. Get File Information
- **GET** `/api/files/{file_id}`
- **Query Parameters**: 
  - `download_url=true` (optional) - Generate secure download URL
  - `expiry_hours=24` (optional) - SAS token expiry time
- **Response**: JSON with file metadata and optional download URL

### 3. Document Processing (AI)
- **POST** `/api/process_document`
- **Content-Type**: `application/json`
- **Parameters**: 
  - `file_content` (base64 encoded file content)
  - `filename` (original filename)
  - `force_reindex` (optional, default: false)
  - `chunking_method` (optional, default: "intelligent")
- **Response**: JSON with AI processing results

### 4. Health Check
- **GET** `/api/health`
- **Response**: JSON with service health status

### 5. Admin Functions

#### Database Reset
- **POST/DELETE** `/api/database/reset`
- **Content-Type**: `application/json`
- **Parameters**: `{"confirm": "yes"}` or `{"force": true}`
- **Response**: JSON with reset results and statistics
- **Note**: Resets all database tables (file_metadata, document_chunks, azure_search_chunks, chunk_comparisons)

#### Azure Search Index Reset
- **POST/DELETE** `/api/search/reset`
- **Content-Type**: `application/json`
- **Parameters**: `{"confirm": "yes"}` or `{"force": true}`
- **Response**: JSON with deletion results
- **Note**: Deletes all documents from Azure Search index only

## Automatic Processing (Blob Trigger)

### Event-Driven Document Processing
The service includes an automatic blob trigger that processes documents when uploaded directly to Azure Blob Storage:

- **Trigger Path**: `uploads/{filename}`
- **Supported Formats**: TXT, DOCX, PDF
- **Processing**: Automatic AI-powered document analysis
- **Features**: 
  - Intelligent document chunking
  - AI keyphrase extraction using OpenAI
  - Automatic indexing to Azure Search
  - Comprehensive error handling and logging

### Usage Methods
1. **HTTP Upload**: Use the `/api/upload` endpoint for traditional uploads with metadata storage
2. **Direct Blob Upload**: Upload files directly to the `uploads` container for automatic AI processing

## Environment Configuration

Configuration is managed through `.env` files using python-dotenv for better security and flexibility.

### Configuration Files

- **`.env.example`** - Template with all available configuration options
- **`.env`** - Main configuration file (create from .env.example)  
- **`.env.local`** - Local overrides (automatically gitignored)

### Setup Configuration

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   # Azure Storage (required)
   AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net
   AZURE_STORAGE_CONTAINER_NAME=uploads
   
   # Database Configuration (choose one)
   DATABASE_TYPE=sqlite                    # For local development
   # DATABASE_TYPE=azuresql               # For production
   SQLITE_DATABASE_PATH=./data/metadata.db
   
   # Azure SQL Authentication (when using azuresql)
   AZURE_SQL_AUTH_METHOD=auto             # auto, managed_identity, ad_password, sql_auth
   AZURE_SQL_SERVER=yourserver.database.windows.net
   AZURE_SQL_DATABASE=yourdatabase
   
   # Optional: For managed identity authentication (RECOMMENDED)
   # AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID=your-client-id  # For user-assigned MI
   
   # Optional: For username/password authentication (NOT RECOMMENDED for production)
   # AZURE_SQL_USERNAME=your-username
   # AZURE_SQL_PASSWORD=your-password
   
   # Document Processing Configuration
   DEFAULT_CHUNKING_METHOD=intelligent     # Options: intelligent, heading, sentence, basic, paragraph
   
   # Optional settings
   MAX_FILE_SIZE_MB=100
   DEFAULT_SAS_EXPIRY_HOURS=24
   LOG_LEVEL=INFO
   ```

### Azure SQL Authentication Methods

The application supports multiple Azure SQL authentication methods for different deployment scenarios:

#### 1. **Managed Identity (RECOMMENDED for Production)**
```bash
AZURE_SQL_AUTH_METHOD=managed_identity
# System-assigned: No additional configuration needed
# User-assigned: Set AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID
```

#### 2. **Azure AD Password Authentication**
```bash
AZURE_SQL_AUTH_METHOD=ad_password
AZURE_SQL_USERNAME=user@domain.com
AZURE_SQL_PASSWORD=your-password
```

#### 3. **SQL Server Authentication (NOT RECOMMENDED for production)**
```bash
AZURE_SQL_AUTH_METHOD=sql_auth
AZURE_SQL_USERNAME=sql-username
AZURE_SQL_PASSWORD=sql-password
```

#### 4. **Automatic Selection (DEFAULT)**
```bash
AZURE_SQL_AUTH_METHOD=auto  # Automatically selects best method based on environment
```

For detailed authentication setup, see [Azure SQL Authentication Guide](docs/AZURE_SQL_AUTHENTICATION_GUIDE.md).

### Environment-Specific Configuration

**Local Development:**
- Use `DATABASE_TYPE=sqlite` for local SQLite database
- Use Azurite for local storage emulation or real Azure Storage
- Configure logging level for development needs

**Production:**
- Use `DATABASE_TYPE=azuresql` for Azure SQL Database
- Configure managed identity for secure Azure resource access
- Set appropriate log levels for production monitoring
- Use Azure Key Vault for sensitive connection strings (recommended)

### Configuration Validation

The application includes built-in configuration validation:
- Validates required settings on startup
- Provides clear error messages for missing or invalid configuration
- Supports different configurations for different environments

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Azure Functions Core Tools

```bash
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 3. Configure Local Settings

Update `local.settings.json` with your Azure Storage and database configuration.

### 4. Run Locally

```bash
func start
```

### 5. Test the Function

```bash
# Upload a file
curl -X POST http://localhost:7071/api/upload \
  -F "file=@path/to/your/file.txt"

# Get file information
curl http://localhost:7071/api/files/1?download_url=true

# Health check
curl http://localhost:7071/api/health
```

## Deployment to Azure

### 1. Create Azure Resources

```bash
# Resource group
az group create --name myResourceGroup --location eastus

# Storage account
az storage account create --name mystorageaccount --resource-group myResourceGroup --location eastus --sku Standard_LRS

# Function App
az functionapp create --resource-group myResourceGroup --consumption-plan-location eastus \
  --runtime python --runtime-version 3.11 --functions-version 4 \
  --name myFunctionApp --storage-account mystorageaccount
```

### 2. Configure Application Settings

```bash
# Set storage connection string
az functionapp config appsettings set --name myFunctionApp --resource-group myResourceGroup \
  --settings AZURE_STORAGE_CONNECTION_STRING="your_connection_string"

# Set database type
az functionapp config appsettings set --name myFunctionApp --resource-group myResourceGroup \
  --settings DATABASE_TYPE="azuresql"

# Set SQL connection string (with managed identity)
az functionapp config appsettings set --name myFunctionApp --resource-group myResourceGroup \
  --settings AZURE_SQL_CONNECTION_STRING="Server=tcp:yourserver.database.windows.net,1433;Initial Catalog=yourdatabase;Authentication=Active Directory Default;"
```

### 3. Deploy Function

```bash
func azure functionapp publish myFunctionApp
```

## Security Considerations

- Uses managed identity for Azure resource access in production
- Implements file size limits (100MB default)
- Generates time-limited SAS URLs for secure downloads
- Validates file uploads and prevents empty files
- Stores file checksums for integrity verification
- Uses parameterized queries to prevent SQL injection

## Monitoring and Logging

- Comprehensive logging throughout the application
- Health check endpoint for monitoring service status
- Integration with Azure Application Insights
- Error tracking and performance monitoring

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

## Troubleshooting

### Common Issues

1. **Import errors during development**: The Azure Functions runtime and dependencies are not available in the local development environment. This is normal and the function will work correctly when deployed or run with the Azure Functions runtime.

2. **Database connection issues**: Ensure your connection strings are properly configured and the database is accessible.

3. **Storage access errors**: Verify your storage account configuration and permissions.

4. **File upload failures**: Check file size limits and ensure the storage container exists.

## License

This project is licensed under the MIT License.