# EventGrid Setup Guide for Blob Deletion Handling

This guide explains how to configure Azure EventGrid to automatically trigger the `HandleBlobDeletion` function when files are deleted from blob storage containers.

## Prerequisites

- Azure Storage Account: `ggcorestorageacc`
- Azure Functions App deployed to Azure (not just local)
- Admin access to Azure portal

## Step 1: Deploy Functions to Azure

Before configuring EventGrid, ensure your functions are deployed to Azure:

```powershell
# Deploy to Azure (from project root)
func azure functionapp publish <your-function-app-name>
```

## Step 2: Configure EventGrid Subscription via Azure Portal

### 2.1 Navigate to Storage Account
1. Open [Azure Portal](https://portal.azure.com)
2. Navigate to your storage account: `ggcorestorageacc`
3. In the left menu, click **Events**

### 2.2 Create Event Subscription
1. Click **+ Event Subscription**
2. Fill in the following details:

**Basic Settings:**
- **Name**: `blob-deletion-handler`
- **Event Schema**: `Event Grid Schema`

**Topic Details:**
- **Topic Type**: `Storage Accounts`
- **Source Resource**: Should auto-populate with your storage account

**Event Types:**
- **Filter to Event Types**: Uncheck "Subscribe to all event types"
- **Check only**: `Blob Deleted`

**Endpoint Details:**
- **Endpoint Type**: `Azure Function`
- **Endpoint**: Click "Select an endpoint"
  - **Subscription**: Your Azure subscription
  - **Resource Group**: Your function app's resource group
  - **Function App**: Your deployed function app name
  - **Function**: `HandleBlobDeletion`

### 2.3 Advanced Filters (Optional but Recommended)
Click **Filters** tab to add subject filters:

**Subject Filters:**
- **Subject Begins With**: `/blobServices/default/containers/contract-policies/`
- **Subject Begins With**: `/blobServices/default/containers/uploads/`

This ensures only deletions from our monitored containers trigger the function.

### 2.4 Complete Setup
1. Click **Create**
2. Wait for deployment to complete (usually takes 1-2 minutes)

## Step 3: Alternative - Azure CLI Configuration

If you prefer command line, use this Azure CLI command:

```bash
# Set variables
SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="your-resource-group"
STORAGE_ACCOUNT="ggcorestorageacc"
FUNCTION_APP="your-function-app-name"
FUNCTION_NAME="HandleBlobDeletion"

# Create EventGrid subscription
az eventgrid event-subscription create \
  --name blob-deletion-handler \
  --source-resource-id "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT" \
  --endpoint-type azurefunction \
  --endpoint "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP/functions/$FUNCTION_NAME" \
  --included-event-types Microsoft.Storage.BlobDeleted \
  --subject-begins-with "/blobServices/default/containers/contract-policies/" \
  --subject-begins-with "/blobServices/default/containers/uploads/"
```

## Step 4: Alternative - PowerShell Configuration

```powershell
# Set variables
$subscriptionId = "your-subscription-id"
$resourceGroup = "your-resource-group"
$storageAccount = "ggcorestorageacc"
$functionApp = "your-function-app-name"
$functionName = "HandleBlobDeletion"

# Create EventGrid subscription
New-AzEventGridSubscription `
  -EventSubscriptionName "blob-deletion-handler" `
  -ResourceId "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Storage/storageAccounts/$storageAccount" `
  -EndpointType "AzureFunction" `
  -Endpoint "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Web/sites/$functionApp/functions/$functionName" `
  -IncludedEventType "Microsoft.Storage.BlobDeleted" `
  -SubjectBeginsWith "/blobServices/default/containers/contract-policies/","/blobServices/default/containers/uploads/"
```

## Step 5: Test the Configuration

### 5.1 Upload a Test File
```bash
az storage blob upload \
  --file "test_policy_document.txt" \
  --container-name "contract-policies" \
  --name "test-deletion.txt" \
  --connection-string "your-connection-string"
```

### 5.2 Verify Processing
```bash
curl "https://your-function-app.azurewebsites.net/api/search/policies?search_text=test"
```

### 5.3 Delete and Verify Cleanup
```bash
# Delete the blob
az storage blob delete \
  --container-name "contract-policies" \
  --name "test-deletion.txt" \
  --connection-string "your-connection-string"

# Wait 10-30 seconds then check if policy was removed
curl "https://your-function-app.azurewebsites.net/api/search/policies?search_text=test"
```

## Step 6: Monitor EventGrid Events

### 6.1 View Event Delivery in Portal
1. Go to Storage Account → Events → Event Subscriptions
2. Click on `blob-deletion-handler`
3. Click **Metrics** to see delivery success/failure rates

### 6.2 View Function Logs
1. Go to Function App → Functions → HandleBlobDeletion
2. Click **Monitor** to see execution logs
3. Look for logs starting with "🗑️ EventGrid blob event"

## Troubleshooting

### Common Issues:

1. **Events not triggering:**
   - Verify function is deployed to Azure (not just local)
   - Check EventGrid subscription status in portal
   - Ensure storage account and function app are in same region

2. **Function errors:**
   - Check Application Insights logs in function app
   - Verify function has proper permissions to access search index
   - Ensure environment variables are configured in function app settings

3. **Permissions issues:**
   - Function app needs `Storage Blob Data Reader` role on storage account
   - Function app needs access to Azure Search service

### Required Environment Variables in Function App:
```
AZURE_SEARCH_ENDPOINT=your-search-endpoint
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_POLICY_INDEX=rag-policy-index-v2
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
```

## Security Considerations

1. **Principle of Least Privilege**: Function only has access to required resources
2. **Network Security**: Consider using private endpoints for production
3. **Key Management**: Use Azure Key Vault for sensitive configuration
4. **Monitoring**: Enable Application Insights for comprehensive logging

## Cost Considerations

- EventGrid: ~$0.60 per million operations
- Function executions: Consumption plan charges per execution
- Storage operations: Standard blob storage rates apply

Expected monthly cost for typical usage: < $5.00

## Next Steps

After successful configuration:
1. Test with various file types and containers
2. Monitor deletion events and cleanup success rates
3. Consider adding alerts for failed EventGrid deliveries
4. Document the complete workflow for your team

---

**Note**: This configuration requires your Azure Functions to be deployed to Azure. Local development functions cannot receive EventGrid events directly. For local testing, use the HTTP endpoints to manually trigger policy processing and deletion.