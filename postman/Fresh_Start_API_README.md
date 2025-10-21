# Fresh Start API - Postman Collection

## 📋 **Collection Overview**

**Collection Name:** `Fresh Start API`  
**Collection ID:** `fresh-start-api-2024`  
**Total Requests:** 7 requests across 6 sections

A clean, comprehensive Postman collection for testing the Fresh Start document processing Azure Functions app.

---

## 🎯 **What's Included**

### 📂 **Sections & Endpoints**

1. **Health & Status** (1 request)
   - `GET /api/health` - System health check

2. **File Management** (1 request)
   - `POST /api/upload` - Upload files for processing

3. **Document Processing** (1 request)
   - `POST /api/process_document` - Process documents with intelligent chunking

4. **Policy Processing** (1 request)
   - `POST /api/process_policy` - Process policy documents with AI analysis

5. **Azure Search Operations** (1 request)
   - `GET /api/search/documents` - Retrieve documents from Azure Search index

6. **Admin Operations** (2 requests)
   - `POST /api/search/setup` - Setup Azure Search index
   - `POST /api/database/reset` - Reset database

---

## 🔧 **Collection Variables**

| Variable | Description | Usage |
|----------|-------------|-------|
| `base_url` | Base URL for Azure Functions app | Set to `http://localhost:7071` for local dev |
| `function_key` | Azure Functions access key | Required for authenticated endpoints |
| `sample_base64_content` | Base64 encoded sample document | Auto-generated in pre-request scripts |
| `sample_policy_base64_content` | Base64 encoded sample policy | Auto-generated in pre-request scripts |
| `last_file_id` | ID of last uploaded file | Auto-stored from upload responses |
| `last_policy_file_id` | Database file ID of last policy | Auto-stored from policy processing |

---

## 🚀 **Getting Started**

### 1. Import Collection
```bash
# Import into Postman
- Open Postman
- Click Import
- Select Fresh_Start_API.postman_collection.json
- Import Fresh_Start_Local_Development.postman_environment.json
```

### 2. Set Environment Variables
```bash
# Required variables in environment:
base_url = http://localhost:7071
function_key = <your_azure_functions_key>
```

### 3. Start Azure Functions
```bash
# In your project directory:
func start
```

### 4. Run Test Sequence
```bash
1. Health Check          → Verify API status
2. Upload File           → Upload test document  
3. Process Document      → Process with AI
4. Process Policy        → Test policy processing
5. Get Search Documents  → Verify Azure Search integration
```

---

## ✅ **Test Features**

### **Automated Testing**
- ✅ **Status Code Validation** - All requests verify 200 OK responses
- ✅ **Response Structure Checks** - Validates expected JSON structure
- ✅ **Data Persistence Verification** - Tests database and Azure Search persistence
- ✅ **Pipeline Integrity** - Ensures processing counts match across stages
- ✅ **Variable Auto-Storage** - Stores IDs for cross-request testing

### **Pre-Request Scripts**
- ✅ **Sample Content Generation** - Auto-generates test content in Base64
- ✅ **Dynamic Policy Content** - Creates test policies for processing
- ✅ **Variable Management** - Sets up required variables automatically

### **Post-Response Tests**
- ✅ **Success Validation** - Verifies successful processing
- ✅ **Data Structure Checks** - Validates response schemas
- ✅ **Count Verification** - Ensures processing integrity
- ✅ **Error Handling** - Tests for proper error responses

---

## 🎯 **Key Benefits**

### **Clean & Simple**
- Single, focused collection with essential endpoints
- Clear naming and organization
- Comprehensive but not overwhelming

### **Fully Automated**
- Pre-request scripts generate test data
- Post-response tests validate everything
- Variables automatically stored between requests

### **Production Ready**
- Proper error handling and validation
- Environment-based configuration
- Ready for CI/CD integration

### **Developer Friendly**
- Clear documentation and examples
- Intuitive request organization
- Easy to extend and modify

---

## 📊 **Request Details**

### Health Check
```http
GET {{base_url}}/api/health
```
**Tests:** Status code, health status, database/storage checks

### Upload File
```http
POST {{base_url}}/api/upload?code={{function_key}}
Content-Type: application/json

{
  "filename": "sample.txt",
  "content": "{{sample_base64_content}}",
  "content_type": "text/plain"
}
```
**Tests:** Upload success, file metadata, ID storage

### Process Document
```http
POST {{base_url}}/api/process_document?code={{function_key}}
Content-Type: application/json

{
  "file_id": "{{last_file_id}}",
  "content": "{{sample_base64_content}}",
  "filename": "sample.txt",
  "chunking_method": "intelligent"
}
```
**Tests:** Processing success, chunk creation, Azure Search upload

### Process Policy
```http
POST {{base_url}}/api/process_policy?code={{function_key}}
Content-Type: application/json

{
  "policy_id": "sample_policy_{{$timestamp}}",
  "content": "{{sample_policy_base64_content}}",
  "filename": "sample_policy.txt"
}
```
**Tests:** Policy processing, database persistence, pipeline integrity

---

## 🔄 **Workflow Example**

```bash
# Complete test workflow:
1. Health Check                    ✅ API Status
2. Upload File                     ✅ File Management  
3. Process Document               ✅ Document Processing
4. Process Policy                 ✅ Policy Processing
5. Get Search Documents           ✅ Azure Search Verification
6. Setup Azure Search Index      ✅ Admin Setup
7. Reset Database                 ✅ Admin Cleanup
```

---

## 📋 **Files Created**

| File | Purpose |
|------|---------|
| `Fresh_Start_API.postman_collection.json` | Main collection file |
| `Fresh_Start_Local_Development.postman_environment.json` | Local development environment |
| `Fresh_Start_API_README.md` | This documentation |

---

## 🎉 **Ready to Use!**

Your new Postman collection is:
- ✅ **Clean and organized** 
- ✅ **Fully tested and validated**
- ✅ **Production ready**
- ✅ **Easy to use and extend**

Import the collection and environment files into Postman and start testing your Fresh Start API! 🚀