# Azure Environment Setup Guide for Postman

This guide explains how to configure and use the Azure Production environment for testing your deployed Azure Functions.

## Files Created

- `Fresh_Start_Azure_Production.postman_environment.json` - Azure environment configuration
- This guide for setup instructions

## Setup Instructions

### Step 1: Import the Azure Environment

1. Open Postman
2. Click the **Environments** tab (left sidebar)
3. Click **Import** 
4. Select `Fresh_Start_Azure_Production.postman_environment.json`
5. Click **Import**

### Step 2: Configure Environment Variables

After importing, you need to fill in the following variables:

#### Required Variables (Must be configured):

1. **base_url**
   - Replace `YOUR_FUNCTION_APP_NAME` with your actual Azure Function App name
   - Example: `https://my-legal-contracts-app.azurewebsites.net`

2. **function_key**
   - Get from Azure Portal: Function App → App keys → Host keys
   - Copy the `default` host key or create a new one
   - This is required for authentication to Azure Functions

3. **azure_search_endpoint**
   - Replace `YOUR_SEARCH_SERVICE` with your Azure Cognitive Search service name
   - Example: `https://my-search-service.search.windows.net`

4. **azure_search_key**
   - Get from Azure Portal: Search Service → Keys → Primary admin key

#### Optional Variables (for advanced features):

5. **azure_subscription_id**
   - Your Azure subscription ID (found in Azure Portal → Subscriptions)

6. **azure_resource_group**
   - Resource group containing your Function App

7. **azure_tenant_id**
   - Azure AD tenant ID (if using Azure AD authentication)

### Step 3: How to Find Azure Configuration Values

#### Function App URL and Keys:
```bash
# Get Function App URL
az functionapp show --name YOUR_FUNCTION_APP_NAME --resource-group YOUR_RESOURCE_GROUP --query "defaultHostName" --output tsv

# Get Function App Host Key
az functionapp keys list --name YOUR_FUNCTION_APP_NAME --resource-group YOUR_RESOURCE_GROUP --query "functionKeys.default" --output tsv
```

#### Azure Search Configuration:
```bash
# Get Search Service endpoint
az search service show --name YOUR_SEARCH_SERVICE --resource-group YOUR_RESOURCE_GROUP --query "searchServiceEndpoint" --output tsv

# Get Search Service admin key
az search admin-key show --service-name YOUR_SEARCH_SERVICE --resource-group YOUR_RESOURCE_GROUP --query "primaryKey" --output tsv
```

#### Storage Account Configuration:
```bash
# List storage account details
az storage account show --name ggcorestorageacc --resource-group YOUR_RESOURCE_GROUP
```

### Step 4: Test the Configuration

#### 4.1 Test Basic Health Check
```
GET {{base_url}}/api/health
Headers:
- x-functions-key: {{function_key}}
```

#### 4.2 Test Policy Processing Health Check
```
GET {{base_url}}/api/process_policy
Headers:
- x-functions-key: {{function_key}}
```

#### 4.3 Test Policy Search
```
GET {{base_url}}/api/search/policies?search_text=*
Headers:
- x-functions-key: {{function_key}}
```

### Step 5: Environment-Specific Postman Collection Updates

Some requests may need different configurations for Azure vs Local. Here are common patterns:

#### Authentication Headers
Local: Usually no authentication required
Azure: Requires function key in header

```javascript
// Pre-request Script for Azure environment
if (pm.environment.get("environment") === "azure") {
    pm.request.headers.add({
        key: "x-functions-key",
        value: pm.environment.get("function_key")
    });
}
```

#### Request URLs
Local: `http://localhost:7071/api/endpoint`
Azure: `https://your-app.azurewebsites.net/api/endpoint`

The environment variable `{{base_url}}` handles this automatically.

### Step 6: Advanced Configuration

#### CORS Configuration
If testing from browser-based tools, ensure CORS is configured:

```bash
az functionapp cors add --name YOUR_FUNCTION_APP_NAME --resource-group YOUR_RESOURCE_GROUP --allowed-origins "*"
```

#### Application Settings
Ensure your Function App has all required environment variables:

```bash
az functionapp config appsettings set --name YOUR_FUNCTION_APP_NAME --resource-group YOUR_RESOURCE_GROUP --settings \
  "AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net" \
  "AZURE_SEARCH_KEY=your-search-key" \
  "AZURE_SEARCH_POLICY_INDEX=rag-policy-index-v2" \
  "AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string"
```

## Common Issues and Solutions

### Issue 1: 401 Unauthorized
**Cause**: Missing or incorrect function key
**Solution**: 
1. Verify function key in Azure Portal
2. Ensure `x-functions-key` header is included in requests
3. Check if function requires authentication

### Issue 2: 404 Not Found
**Cause**: Incorrect base URL or function not deployed
**Solution**:
1. Verify function app name in base_url
2. Ensure functions are deployed: `func azure functionapp publish YOUR_APP_NAME`
3. Check function app is running in Azure Portal

### Issue 3: 500 Internal Server Error
**Cause**: Configuration issues in Azure Function App
**Solution**:
1. Check Application Insights logs in Azure Portal
2. Verify all environment variables are set
3. Check function app logs for detailed error messages

### Issue 4: CORS Errors
**Cause**: Cross-origin requests blocked
**Solution**:
1. Configure CORS in Function App settings
2. Add allowed origins: `*` for testing, specific domains for production

## Environment Switching

To switch between local and Azure environments in Postman:

1. Click the environment dropdown (top right)
2. Select "Fresh Start Azure Production" for Azure testing
3. Select "Fresh Start Local Development" for local testing

## Security Best Practices

1. **Never commit function keys to source control**
2. **Use environment variables for sensitive data**
3. **Rotate function keys regularly**
4. **Limit CORS origins in production**
5. **Monitor function app logs for security events**

## Testing Workflow

1. **Deploy Functions**: `func azure functionapp publish YOUR_APP_NAME`
2. **Configure Environment**: Fill in all required variables
3. **Test Health Endpoints**: Verify connectivity
4. **Test Policy Workflow**: Upload → Process → Search → Delete
5. **Monitor Logs**: Check Application Insights for issues

---

**Next Steps:**
1. Deploy your functions to Azure
2. Configure the environment variables above
3. Import and test with your Postman collection
4. Set up EventGrid for blob deletion handling (see EVENTGRID_SETUP_GUIDE.md)