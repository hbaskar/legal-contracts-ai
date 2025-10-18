# Reset Operations Guide

## Overview
The Fresh Start Document Processing system now provides **separate reset functions** for database and Azure Search index management. This allows granular control over data cleanup and system maintenance.

## Reset Functions

### 🗄️ Database Reset
**Endpoint:** `POST/DELETE /api/database/reset`

**Purpose:** Resets all local database tables while preserving Azure Search index

**What it resets:**
- `file_metadata` - File upload records
- `document_chunks` - Processed document chunks  
- `azure_search_chunks` - Azure Search upload tracking
- `chunk_comparisons` - Chunking method comparison results

**What it preserves:**
- ✅ Azure Search index documents
- ✅ Azure Blob Storage files
- ✅ System configuration

### ☁️ Azure Search Index Reset
**Endpoint:** `POST/DELETE /api/search/reset`

**Purpose:** Clears Azure Search index while preserving local database

**What it resets:**
- All documents in the Azure Search index
- Vector embeddings
- Search index contents

**What it preserves:**
- ✅ Local database records
- ✅ File metadata
- ✅ Chunk processing history
- ✅ Azure Blob Storage files

## Usage Examples

### 1. Database Reset Only
```bash
# Reset local database tables only
curl -X POST http://localhost:7071/api/database/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "yes"}'
```

**Use Case:** Clean up local tracking data while keeping search functionality

### 2. Azure Search Reset Only
```bash
# Clear Azure Search index only
curl -X POST http://localhost:7071/api/search/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "yes"}'
```

**Use Case:** Rebuild search index while preserving processing history

### 3. Complete System Reset (Both)
```bash
# Reset database first
curl -X POST http://localhost:7071/api/database/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "yes"}'

# Then reset search index
curl -X POST http://localhost:7071/api/search/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "yes"}'
```

**Use Case:** Complete system cleanup for fresh start

## Safety Features

### Confirmation Required
Both endpoints require explicit confirmation:

```json
{
  "confirm": "yes"
}
```

Or force flag to bypass confirmation:

```json
{
  "force": true
}
```

### Production Protection
- Extra confirmation required in production environments
- Force flag required for production operations
- Environment detection based on database type

### Query Parameters
Alternative confirmation via URL parameters:

```bash
# Confirmation via query parameter
POST /api/database/reset?confirm=yes

# Force via query parameter  
DELETE /api/search/reset?force=true
```

## Response Format

### Successful Reset Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "timestamp": "2024-10-17T12:00:00Z",
  "operation": "database_reset",
  
  // Database reset specific
  "total_records_deleted": 26,
  "summary": {
    "tables_processed": 4,
    "tables_with_errors": 0
  },
  
  // Search reset specific  
  "deleted_documents": 292,
  "failed_deletions": 0,
  "total_found": 292
}
```

### Error Response
```json
{
  "status": "error", 
  "message": "Operation failed",
  "error_details": "Detailed error message",
  "timestamp": "2024-10-17T12:00:00Z"
}
```

## Postman Collection

The updated Postman collection includes:

### Admin Functions Folder
- **Database Reset** - Standard confirmation reset
- **Azure Search Index Reset** - Standard confirmation reset  
- **Database Reset (Force)** - Force flag bypass
- **Azure Search Index Reset (Force)** - Force flag bypass

### Test Scripts
Each request includes validation tests:
- Status code verification (200/207)
- Response structure validation
- Success status confirmation
- Operation-specific metrics

## Use Cases

### 1. Development Workflow
```bash
# Clean slate for testing
POST /api/database/reset + /api/search/reset
# Upload test documents
# Process and verify results
```

### 2. Index Rebuilding
```bash
# Keep processing history, rebuild search
POST /api/search/reset
# Reprocess existing documents
# Verify search functionality
```

### 3. Data Analysis Reset
```bash
# Keep search index, reset tracking
POST /api/database/reset  
# Reprocess with different chunking methods
# Compare new results
```

### 4. Production Maintenance
```bash
# Careful production reset with force flag
DELETE /api/search/reset?force=true
# Verify system state
# Reindex critical documents
```

## Monitoring

### Verification Commands
```bash
# Check database state
python check_database.py

# Verify search index
GET /api/health

# Test functionality
python test_reset_endpoints.py
```

### Logs
Operations are logged with:
- 🗑️ Reset operation indicators
- 📊 Statistics and counts
- ⚠️ Warnings and errors
- ✅ Success confirmations

## Best Practices

### 1. **Separate Operations**
- Use database reset for local cleanup
- Use search reset for index rebuilding
- Combine only when necessary

### 2. **Backup Before Reset**
- Export important data before major resets
- Verify backup integrity
- Test restore procedures

### 3. **Staged Resets**
- Test in development first
- Use confirmation flags appropriately
- Monitor system state after resets

### 4. **Production Safety**
- Always use force flag in production
- Coordinate with team members
- Schedule during maintenance windows

## Testing

### Automated Tests
```bash
# Test both reset functions
python test_reset_endpoints.py

# Verify database state  
python check_database.py

# Full system validation
python tests/test_complete_workflow.py
```

### Manual Validation
1. Run health check
2. Execute reset operation
3. Verify response format
4. Check database/search state
5. Test core functionality

---

## Summary

The separate reset functions provide:
- ✅ **Granular Control** - Reset only what you need
- ✅ **Safety Features** - Confirmation and production protection
- ✅ **Comprehensive Logging** - Full operation tracking
- ✅ **Flexible Usage** - Multiple confirmation methods
- ✅ **Complete Testing** - Automated validation suite

This enables precise system maintenance while minimizing disruption to ongoing operations.