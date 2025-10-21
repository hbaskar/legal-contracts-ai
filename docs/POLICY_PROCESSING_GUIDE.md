# Policy Document Processing System

## Overview
The Policy Document Processing System provides comprehensive AI-powered analysis and indexing of legal and organizational policy documents. It automatically extracts policy clauses, analyzes them with OpenAI, and indexes them in Azure Search for easy retrieval and compliance management.

## Features

### 🧠 **AI Policy Analysis**
- **Structured Extraction**: Uses OpenAI to extract title, instruction, summary, and tags from each policy clause
- **Severity Classification**: Automatically classifies policies as Critical (1) or Important (2)
- **Intelligent Chunking**: Automatically segments policy documents into individual clauses
- **Legal Tag Generation**: Generates relevant legal and compliance tags for each clause

### 🔍 **Azure Search Integration**
- **Policy Index**: Dedicated Azure Search index (`rag-policy-index-v2`) for policy documents
- **Vector Search**: Full embedding support for semantic search capabilities
- **Advanced Filtering**: Filter by severity, tags, groups, filename, or policy ID
- **Faceted Search**: Structured search with proper field mapping

### 📊 **Document Processing Pipeline**
- **Multi-Format Support**: Processes TXT, DOCX, and PDF policy documents
- **Automatic Upload**: Seamlessly uploads processed policies to Azure Search
- **Metadata Tracking**: Maintains complete audit trail and processing metadata
- **Error Handling**: Robust fallback mechanisms for failed AI operations

## API Endpoints

### 1. **Process Policy Document**
**POST** `/api/process_policy`

Processes a policy document through the complete AI analysis pipeline.

**Request Body:**
```json
{
    "file_content": "base64_encoded_file_content",
    "filename": "company_policies.pdf",
    "policy_id": "optional_custom_id",
    "groups": ["legal-team", "compliance", "management"],
    "upload_to_search": true
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Successfully processed policy document: company_policies.pdf",
    "filename": "company_policies.pdf",
    "policy_id": "company_policies-abc123",
    "total_clauses": 12,
    "clauses_processed": 12,
    "processing_method": "ai_policy_analysis",
    "search_upload": {
        "status": "success",
        "uploaded_count": 12,
        "index_name": "rag-policy-index-v2"
    },
    "timestamp": "2025-10-20T09:30:00Z"
}
```

### 2. **Search Policy Documents**  
**GET** `/api/search/policies`

Search and filter policy documents from the Azure Search index.

**Query Parameters:**
- `q` - Search query (default: `*` for all)
- `limit` - Maximum results (default: 10, max: 50)
- `policy_id` - Filter by specific policy ID
- `filename` - Filter by source filename
- `severity` - Filter by severity level (1=Critical, 2=Important)
- `tags` - Comma-separated tags to filter by
- `groups` - Comma-separated access groups to filter by

**Examples:**
```bash
# Search all policies
GET /api/search/policies?q=*&limit=20

# Search for payment-related policies
GET /api/search/policies?q=payment&limit=10

# Get critical policies only
GET /api/search/policies?severity=1&limit=50

# Filter by tags
GET /api/search/policies?tags=confidentiality,security

# Filter by access groups
GET /api/search/policies?groups=legal-team,compliance
```

**Response:**
```json
{
    "status": "success", 
    "message": "Retrieved 3 policy documents",
    "policies": [
        {
            "id": "unique_clause_id",
            "policy_id": "company_policies-abc123",
            "filename": "company_policies.pdf",
            "title": "Payment Terms Policy",
            "instruction": "All invoices must be paid within 30 days...",
            "summary": "30-day payment requirement",
            "tags": ["payments", "contracts", "deadlines"],
            "groups": ["legal-team", "finance"],
            "severity": 1,
            "language": "English",
            "locked": false,
            "search_score": 0.95
        }
    ],
    "total_policies": 3,
    "search_params": {
        "query": "payment",
        "limit": 10,
        "filters_applied": 0
    },
    "index_name": "rag-policy-index-v2",
    "timestamp": "2025-10-20T09:30:00Z"
}
```

### 3. **Health Check**
**GET** `/api/process_policy`

Check the health and availability of policy processing services.

**Response:**
```json
{
    "status": "healthy",
    "message": "Policy Processing Function is running",
    "version": "1.0.0", 
    "policy_services_available": true,
    "supported_file_types": ["txt", "docx", "pdf"],
    "features": [
        "AI policy clause extraction",
        "Structured policy analysis", 
        "Azure Search policy indexing",
        "Policy severity classification"
    ]
}
```

## Policy Data Model

### **PolicyClause Structure**
```python
{
    "id": "unique_identifier",
    "PolicyId": "document_policy_id", 
    "filename": "source_filename",
    "title": "AI_generated_clause_title",
    "instruction": "complete_policy_text",
    "summary": "6-7_word_essence",
    "embedding": [vector_array_1536_dims],
    "tags": ["relevant", "legal", "categories"],
    "locked": false,
    "groups": ["access_control_groups"],
    "severity": 1, // 1=Critical, 2=Important
    "language": "English",
    "original_text": "raw_extracted_clause"
}
```

### **Severity Levels**
- **1 (Critical/Mandatory)**: Must-follow policies, compliance requirements, legal obligations
- **2 (Important/Recommended)**: Best practices, guidelines, recommended procedures

## Processing Workflow

### **Document Analysis Pipeline**
```
1. File Upload (TXT/DOCX/PDF)
    ↓
2. Content Extraction 
    ↓
3. Policy Chunking (clause segmentation)
    ↓
4. AI Analysis per Clause
   - Title generation
   - Summary creation (6-7 words)
   - Tag extraction
   - Severity classification
    ↓
5. Embedding Generation
    ↓
6. Azure Search Upload
    ↓
7. Metadata Storage & Response
```

### **AI Processing Features**
- **Intelligent Clause Detection**: Recognizes policy boundaries using patterns like numbered items, headings, and definitions
- **Semantic Analysis**: Understands policy intent and context for accurate categorization
- **Fallback Mechanisms**: Multiple recovery strategies when AI analysis fails
- **Content Preservation**: Maintains original policy text alongside extracted structure

## Usage Examples

### **Basic Policy Processing**
```bash
# Process a company handbook
curl -X POST "http://localhost:7071/api/process_policy" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "employee_handbook.pdf",
    "file_content": "base64_encoded_content",
    "groups": ["hr", "management"]
  }'
```

### **Advanced Policy Search**
```bash
# Find all critical security policies
curl "http://localhost:7071/api/search/policies?q=security&severity=1&limit=20"

# Search policies by specific tags
curl "http://localhost:7071/api/search/policies?tags=confidentiality,data-protection"
```

## Integration with Existing System

### **Shared Infrastructure**
- **OpenAI Integration**: Uses same Azure OpenAI client and configuration as document processing
- **Azure Search**: Separate policy index alongside document index
- **Authentication**: Same Azure Function key authentication system
- **Error Handling**: Consistent error patterns and logging framework

### **Postman Collection Support**
The policy processing endpoints are included in the main Postman collection:
- Pre-configured test requests
- Sample policy content generators
- Automated response validation
- Environment variable management

## Configuration

### **Required Environment Variables**
```env
# Azure OpenAI (shared with document processing)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your_openai_key
AZURE_OPENAI_MODEL_DEPLOYMENT=gpt-4o

# Azure Search (shared infrastructure)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net  
AZURE_SEARCH_KEY=your_search_key
AZURE_SEARCH_POLICY_INDEX=rag-policy-index-v2
```

### **Index Configuration**
The policy index includes:
- **Text Fields**: id, PolicyId, filename, title, instruction, summary, language, original_text
- **Vector Field**: embedding (1536 dimensions for OpenAI embeddings)
- **Collection Fields**: tags, groups (for filtering and access control)
- **Metadata Fields**: locked, severity (for classification)

## Best Practices

### **Policy Document Structure**
For optimal processing results:
1. **Clear Headings**: Use numbered sections and clear policy titles
2. **Consistent Format**: Maintain uniform structure across policy documents  
3. **Logical Separation**: Separate distinct policies into individual clauses
4. **Complete Context**: Include sufficient context for each policy statement

### **Search Optimization**
- **Use Specific Terms**: Search for specific policy concepts rather than generic terms
- **Combine Filters**: Use severity and tag filters to narrow results effectively
- **Group-Based Access**: Leverage groups for role-based policy access control

### **Performance Considerations**
- **Batch Processing**: Process multiple policies in separate requests for better error isolation
- **Error Monitoring**: Monitor failed clause processing and embedding generation
- **Index Management**: Regular index maintenance for optimal search performance

## Error Handling

### **Common Error Scenarios**
1. **AI Analysis Failures**: Automatic fallback to rule-based extraction
2. **Embedding Generation Issues**: Documents uploaded without embeddings (still searchable)
3. **Index Upload Problems**: Detailed error reporting with specific failure reasons
4. **File Format Issues**: Clear error messages for unsupported formats or corrupted files

### **Troubleshooting**
- Check Azure Function logs for detailed processing information
- Verify OpenAI service availability and quota limits
- Confirm Azure Search index health and schema compatibility
- Validate file encoding and format specifications

## Future Enhancements

### **Planned Features**
- **Database Integration**: Store policy metadata in SQL database for enhanced querying
- **Version Control**: Track policy changes and maintain historical versions
- **Compliance Mapping**: Link policies to specific regulatory requirements
- **Approval Workflows**: Integrate with approval systems for policy management

This policy processing system provides a comprehensive solution for AI-powered policy document management, seamlessly integrated with the existing document processing infrastructure while offering specialized capabilities for legal and organizational policy handling.