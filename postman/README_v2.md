# Fresh Start Document Processing API - Postman Collection v2

## 🚀 Quick Start Guide

### 📦 Files to Import
1. **Collection**: `Fresh_Start_Document_Processing_v2.postman_collection.json`
2. **Azure Environment**: `Azure_Production_v2.postman_environment.json`
3. **Local Environment**: `Local_Development_v2.postman_environment.json`

### 🔧 Import Instructions

1. **Open Postman**
2. **Import Collection**:
   - Click **Import** button
   - Select `Fresh_Start_Document_Processing_v2.postman_collection.json`
   - Click **Import**

3. **Import Environments**:
   - Click **Import** button
   - Select both environment files
   - Click **Import**

4. **Select Environment**:
   - Click the environment dropdown (top right)
   - Select **"Azure Production v2"** for testing your deployed functions

### ✅ Pre-configured Settings

#### Azure Production Environment:
- ✅ **base_url**: `https://aifnc.azurewebsites.net`
- ✅ **function_key**: `YOUR_FUNCTION_KEY_HERE`
- ✅ **user_id**: `prod-user`

#### Local Development Environment:
- ✅ **base_url**: `http://localhost:7071`
- ✅ **function_key**: (empty - not needed for local dev)
- ✅ **user_id**: `local-dev-user`

## 🧪 Collection Features

### 📋 **Endpoint Categories**:

1. **Health & Status** (2 requests)
   - ✅ Health Check (no auth required)
   - ✅ Document Processing Health (with auth)

2. **File Management** (2 requests)
   - ✅ Upload File
   - ✅ Get File Info

3. **Document Processing** (3 requests)
   - ✅ Process with Intelligent Chunking
   - ✅ Process with Heading-Based Chunking
   - ✅ Process with Fixed-Size Chunking

4. **Azure Search Operations** (2 requests)
   - ✅ Get Azure Search Documents
   - ✅ Get Persisted Chunks

5. **Admin Operations** (3 requests)
   - ✅ Setup Azure Search Index
   - ✅ Reset Azure Search Index
   - ✅ Reset Database

### 🔐 **Authentication**
- **Method**: Query parameter `?code={{function_key}}`
- **Health endpoint**: No authentication needed
- **All other endpoints**: Require function key
- **Auto-configured**: All URLs include proper authentication

### 🎯 **Testing Workflow**

1. **Start with Health Check**:
   ```
   GET {{base_url}}/api/health
   ```

2. **Test Document Processing Health**:
   ```
   GET {{base_url}}/api/process_document?code={{function_key}}
   ```

3. **Upload a file** (optional):
   ```
   POST {{base_url}}/api/upload?code={{function_key}}
   ```

4. **Process documents** with different chunking methods:
   - Intelligent chunking (AI-powered)
   - Heading-based chunking (structural)
   - Fixed-size chunking (baseline)

5. **Retrieve results**:
   ```
   GET {{base_url}}/api/search/documents?code={{function_key}}
   ```

### 📊 **Built-in Tests**

Each request includes automatic tests that verify:
- ✅ Correct HTTP status codes
- ✅ Required response fields
- ✅ Data structure validation
- ✅ Processing success indicators
- ✅ Authentication handling

### 🐛 **Troubleshooting**

#### Common Issues:

1. **401 Unauthorized**:
   - ✅ **Solution**: Function key is already configured in environment

2. **404 Not Found**:
   - Check if the function app is running
   - Verify the endpoint URL is correct

3. **503 Service Unavailable**:
   - Function host may be starting up (wait 30-60 seconds)
   - Check Azure Function App status in portal

#### Debug Information:
- Response times are logged automatically
- Authentication errors are flagged
- Request URLs are logged in console

### 🔄 **Environment Switching**

**For Azure Production Testing**:
- Select **"Azure Production v2"** environment
- All requests automatically use `https://aifnc.azurewebsites.net`
- Authentication included automatically

**For Local Development**:
- Select **"Local Development v2"** environment  
- All requests use `http://localhost:7071`
- No authentication needed (if running locally with ANONYMOUS auth)

## 🎉 Ready to Use!

Your new Postman collection is:
- ✅ **Clean and organized**
- ✅ **Properly authenticated**
- ✅ **Pre-configured for your Azure deployment**
- ✅ **Includes comprehensive tests**
- ✅ **Has built-in debugging**

**Start testing with the Health Check request and work your way through the collection!** 🚀