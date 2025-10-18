# Fresh Start Document Processing API - Postman Collection

This directory contains comprehensive Postman collections and environments for testing the Fresh Start Document Processing Azure Functions API.

## 📁 Files Included

### Collections
- **`Fresh_Start_Document_Processing.postman_collection.json`** - Main API collection with all endpoints

### Environments  
- **`Local_Development.postman_environment.json`** - Local development server (http://localhost:7071)
- **`Azure_Production.postman_environment.json`** - Azure production environment template

## 🚀 Quick Start

### 1. Import into Postman
1. Open Postman
2. Click **Import** in the top left
3. Drag and drop the collection file or browse to select it
4. Import the environment files the same way

### 2. Set Up Environment
1. Select the appropriate environment (Local Development or Azure Production)
2. Update the `base_url` variable if needed
3. For production, add your Function App URL and access keys

### 3. Start Testing
1. Make sure your Azure Functions app is running (`func start` for local)
2. Run the **Health Check** request first to verify connectivity
3. Use **Upload File** to test file upload functionality
4. Test document processing with different chunking methods

## 📊 Collection Structure

### 🏥 Health & Status
- **Health Check** - Verify API availability
- **Document Processing Health** - Check AI services status

### 📁 File Management  
- **Upload File** - Upload documents (PDF, DOCX, TXT)
- **Get File Info** - Retrieve file metadata and download URLs

### 🧠 Document Processing
- **Process Document with Base64** - Process with intelligent chunking
- **Process with Fixed-Size Chunking** - Test fixed-size method
- **Process with Heading-Based Chunking** - Test structural chunking

### 📊 Chunk Comparison Tests
- **Compare All Chunking Methods** - Comprehensive analysis test

### � Azure Search Content Access
**NEW!** Direct access to content stored in Azure Search index without database joins:
- **Get All Documents from Search Index** - Retrieve all documents with full content
- **Get Documents with Limit** - Paginated results (default: 5 documents)  
- **Get Documents by Filename** - Filter documents by original filename
- **Get Specific Document by ID** - Retrieve individual document by unique ID
- **Get Documents with Pagination** - Advanced pagination with optional filtering

**Key Features**:
- ✅ **Direct from Azure Search** - No database joins required
- ✅ **Full content access** - Complete document text from `paragraph` field
- ✅ **Rich metadata** - Titles, summaries, keyphrases, and more
- ✅ **Flexible filtering** - By filename, document ID, or limit results
- ✅ **Performance optimized** - Fast search index retrieval

**Endpoint**: `GET /api/search/documents[?filename=X&document_id=Y&limit=N]`

###  Admin & Utilities
- **Reset Database (CAUTION)** - Reset all database tables (requires confirmation)
- **Reset Database with URL Parameters** - Alternative reset method using URL params
- **Reset Database (Safety Check)** - Test safety mechanisms without actual reset
- **Azure Search Index Reset** - Reset only the Azure Search index (separate from database)
- **Database Reset (Force)** - Force database reset without confirmation prompts
- **Azure Search Index Reset (Force)** - Force search index reset without confirmation

⚠️ **IMPORTANT**: 
- **Database reset** affects local SQL tables only (`POST/DELETE /api/database/reset`)
- **Search index reset** affects Azure Search index only (`POST/DELETE /api/search/reset`)
- **Separate operations** allow granular control over data management
- Use with extreme caution as these operations delete ALL data!

**Database Endpoint**: `POST/DELETE /api/database/reset`
**Search Index Endpoint**: `POST/DELETE /api/search/reset`

### ❌ Error Handling Tests
- **Upload without File** - Test error handling
- **Process without File Content** - Test validation  
- **Get Non-existent File** - Test 404 responses

## 🔧 Variables

### Collection Variables
- `base_url` - API base URL
- `user_id` - User identifier for requests  
- `last_file_id` - Automatically set from upload responses
- `sample_base64_content` - Auto-generated test content
- `comprehensive_doc_base64` - Complex document for testing

### Environment Variables  
- **Local Development**: `http://localhost:7071`
- **Azure Production**: Update with your Function App URL

## 🧪 Testing Features

### Automated Tests
Each request includes automated tests that verify:
- ✅ Correct HTTP status codes
- ✅ Response structure validation
- ✅ Business logic verification  
- ✅ Error handling validation

### Pre-request Scripts
- Auto-generate base64 test content
- Set up variables for dependent requests
- Logging for debugging

### Global Tests
- Response time validation (< 30 seconds)
- Response logging for debugging
- Variable management

## 📈 Chunking Methods Tested

The collection tests all 4 chunking methods:

1. **🧠 Intelligent (AI-powered)**
   - Uses OpenAI for semantic chunking
   - Generates keyphrases and summaries
   - Slowest but most accurate

2. **📋 Heading-based (Structural)**  
   - Splits on document headings/sections
   - Fast and logical organization
   - Great for structured documents

3. **📏 Fixed-size (Baseline)**
   - Simple character-based splitting
   - Fastest processing
   - Consistent chunk sizes

4. **📝 Paragraph-based (Simple)**
   - Splits on paragraph boundaries  
   - Basic document structure
   - Good baseline comparison

## 🔍 Sample Request Flow

1. **Health Check** → Verify service is running
2. **Upload File** → Upload your document  
3. **Process Document** → Choose chunking method
4. **Compare Methods** → Analyze different approaches
5. **Get File Info** → Retrieve processed results

## 🛠️ Customization

### Adding New Endpoints
1. Right-click collection → Add Request
2. Configure method, URL, headers
3. Add tests in the **Tests** tab
4. Use variables for dynamic values

### Environment Setup
```json
{
  "base_url": "https://your-app.azurewebsites.net",
  "user_id": "your-user-id",
  "function_key": "your-function-key"
}
```

### Custom Test Content
Modify the pre-request scripts to use your own test documents:

```javascript
const customDoc = "Your document content here...";
const base64Content = btoa(customDoc);
pm.collectionVariables.set('custom_content', base64Content);
```

## � Azure Search Content Access Guide

### Overview
The new **Azure Search Content Access** endpoints provide direct access to document content stored in the Azure Search index without requiring complex database joins. This approach offers:

- **✅ Performance**: Direct index queries are faster than database joins
- **✅ Accuracy**: Content comes directly from the searchable index  
- **✅ Simplicity**: No complex relationship management required
- **✅ Completeness**: Full document text with all metadata preserved

### Available Endpoints

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /api/search/documents` | Get all documents | Get everything in index |
| `GET /api/search/documents?limit=10` | Paginated results | Limit response size |
| `GET /api/search/documents?filename=doc.pdf` | Filter by file | All chunks from specific file |
| `GET /api/search/documents?document_id=xyz` | Get specific document | Single document by ID |

### Response Format
```json
{
  "status": "success",
  "message": "Retrieved X documents from Azure Search index",
  "documents": [
    {
      "id": "document_id_here",
      "title": "AI-generated title",
      "content": "Full document text content...",
      "content_length": 150,
      "summary": "AI-generated summary",
      "keyphrases": ["key", "phrases"],
      "filename": "original_file.pdf",
      "paragraph_id": "1",
      "date": "2025-01-01T00:00:00Z"
    }
  ],
  "total_documents": 5,
  "source": "azure_search_index"
}
```

### Testing Workflow
1. **Upload and process** a document using existing endpoints
2. **Verify content** using `GET /api/search/documents?limit=1`
3. **Filter by filename** to find your specific document chunks
4. **Access individual chunks** using document IDs
5. **Compare with database** approach (optional)

### Key Differences: Database vs Azure Search

| Aspect | Database Approach | Azure Search Approach |
|--------|-------------------|----------------------|
| **Data Source** | `document_chunks` table | Azure Search index |
| **Content Field** | `chunk_text` | `paragraph` |
| **Access Method** | SQL joins | Direct search queries |
| **Performance** | Slower (joins) | Faster (index) |
| **Use Case** | Relational analysis | Content retrieval |

## �🚨 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Verify Azure Functions is running (`func start`)
   - Check the `base_url` variable
   - Ensure port 7071 is accessible

2. **File Upload Fails**  
   - Check file size limits
   - Verify supported file types (PDF, DOCX, TXT)
   - Ensure proper Content-Type headers

3. **Processing Errors**
   - Verify OpenAI configuration
   - Check Azure Search service availability
   - Review function logs for details

4. **Base64 Content Issues**
   - Use small files for testing
   - Check pre-request script execution
   - Verify content encoding

### Debug Tips
- Enable Postman Console (View → Show Postman Console)
- Check request/response logs
- Verify environment variable values
- Test endpoints individually

```

## ⚠️ Database Reset Functionality

The collection includes administrative reset functions for development and testing:

### Reset Methods Available

1. **Reset Database (CAUTION)** - Full POST request with JSON body
   - Requires `confirm: "yes"` in request body
   - Uses collection variable `reset_confirmation`
   - Includes comprehensive safety checks

2. **Reset Database with URL Parameters** - DELETE request
   - Uses URL parameter `?confirm=yes`
   - Alternative method for reset operations
   - Same safety protections apply

3. **Reset Database (Safety Check)** - Test safety mechanisms
   - Sends `confirm: "no"` to verify protection
   - Should return error without performing reset
   - Validates security measures work correctly

### Safety Features

- ✅ **Confirmation Required**: Must explicitly confirm with "yes"
- ✅ **Production Protection**: Blocks resets in production environment
- ✅ **Dependency Order**: Resets tables in correct order to avoid conflicts
- ✅ **Comprehensive Logging**: Detailed operation logging for audit trail
- ✅ **Error Recovery**: Graceful handling of partial failures

### Usage Guidelines

⚠️ **CRITICAL WARNING**: Reset operations delete ALL data from database tables

**Development Use Only**:
- Use for testing new features
- Clean slate for integration tests  
- Reset between test runs

**Never Use In Production**:
- Production environment automatically blocked
- Data loss is permanent and irreversible
- Always backup before any reset operations

### Reset Response Format
```json
{
  "status": "success",
  "message": "Database reset completed",
  "environment": "development", 
  "tables_reset": ["table1", "table2", ...],
  "total_records_deleted": 150,
  "summary": {
    "tables_processed": 5,
    "tables_succeeded": 5, 
    "tables_failed": 0
  }
}
```

## 📝 Notes

- The collection uses automatic variable management
- File IDs are captured from upload responses
- Base64 content is auto-generated for testing
- Tests provide detailed feedback on API behavior
- Environments allow easy switching between local/production

## 🔄 Workflow Examples

### Quick API Test
```
Health Check → Upload File → Process Document
```

### Comprehensive Testing  
```
Health Check → Upload → Process (all methods) → Compare Results → Error Tests
```

### Production Validation
```  
Switch to Azure Production environment → Health Check → Upload → Verify Processing
```

This Postman collection provides complete coverage of your Document Processing API, with automated testing, error handling validation, and support for all chunking methods including the new heading-based approach!