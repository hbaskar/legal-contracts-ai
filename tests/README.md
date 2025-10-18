# Tests Directory

This directory contains all test scripts for the Azure Functions File Upload Service.

## Test Categories

### 🧪 **Unit Tests**
- `test_config.py` - Configuration module tests
- `test_models.py` - Data models and DTOs tests
- `test_function_app_v2.py` - Azure Functions v2 programming model tests

### 🚀 **Integration Tests**
- `test_database.py` - Database operations and connectivity tests
- `test_function.py` - Azure Function endpoint tests
- `test_upload.py` - File upload functionality tests

### 🤖 **AI Processing Tests**
- `test_ai_processing.py` - Direct AI document processing tests
- `test_blob_trigger.py` - Blob trigger automatic processing tests
- `test_complete_workflow.py` - End-to-end workflow tests

### ⚡ **Quick Tests**
- `quick_test.py` - Rapid validation and smoke tests

### 🎯 **Comprehensive Tests**
- `test_whole.py` - Complete system test runner with health checks, document processing, and blob trigger validation

### 📊 **Chunk Analysis Tests**
- `test_chunk_comparison.py` - Database functions for capturing and comparing document chunks
- `test_chunk_comparison_integration.py` - Integrated chunk comparison with multiple chunking methods

## Running Tests

### From Tests Directory
```bash
cd tests
python test_blob_trigger.py      # Test blob trigger functionality
python test_ai_processing.py     # Test AI processing directly
python test_complete_workflow.py # Test complete workflow
python quick_test.py             # Quick validation
python test_whole.py --verbose    # Comprehensive system test with detailed output
python test_whole.py --quick      # Comprehensive test (skip blob trigger)
```

### From Root Directory
```bash
python tests/test_blob_trigger.py
python tests/test_ai_processing.py
python tests/test_complete_workflow.py
python tests/quick_test.py
```

## Test Descriptions

### `test_blob_trigger.py`
Tests the automatic document processing blob trigger:
- Uploads test documents to Azure Blob Storage
- Verifies blob trigger fires automatically
- Monitors Azure Functions for processing logs
- Validates end-to-end blob trigger workflow

### `test_ai_processing.py`
Tests AI document processing functionality:
- Creates test documents with various content types
- Tests intelligent chunking capabilities
- Validates OpenAI integration for keyphrase extraction
- Verifies Azure Search indexing

### `test_complete_workflow.py`
Tests the complete document processing pipeline:
- Full workflow from upload to search indexing
- System status validation
- Comprehensive processing verification
- End-to-end monitoring instructions

### `quick_test.py`
Rapid validation tests for development:
- Quick smoke tests
- Basic functionality verification
- Fast feedback during development

### `test_whole.py`
**Comprehensive System Test Runner** - The ultimate validation tool:
- **Health Checks**: Validates all Azure Function endpoints are responsive
- **Document Processing**: Tests AI-powered document chunking and processing
- **Blob Trigger**: Validates automatic processing when files are uploaded to storage
- **Error Handling**: Comprehensive error detection and reporting
- **Detailed Logging**: Verbose output showing system status and performance
- **Quick Mode**: Skip blob trigger tests for faster execution (`--quick`)
- **Configurable**: Custom Azure Functions URL (`--base-url`)

**Usage Examples:**
```bash
python test_whole.py --verbose    # Full test with detailed output
python test_whole.py --quick      # Skip blob trigger tests
python test_whole.py --base-url http://myapp.azurewebsites.net  # Test deployed app
```

**Perfect for:**
- Pre-deployment validation
- System health monitoring
- Debugging complex issues
- Comprehensive CI/CD testing

## Prerequisites

- Azure Functions runtime running locally (`func start`)
- Valid Azure configuration in `.env` file
- Required Python packages installed
- Azure services accessible (Storage, OpenAI, Search)

## Configuration

Tests use configuration from:
- `.env` file in project root
- `contracts/config.py` module
- `local.settings.json` for Azure Functions

## Monitoring Test Results

### Blob Trigger Tests
Monitor Azure Functions console logs for:
- `ProcessUploadedDocument` function execution
- AI processing status messages
- Chunk creation and upload logs
- Error handling and recovery

### AI Processing Tests
Watch for:
- OpenAI API call success/failure
- Document chunking results
- Search index upload status
- Processing time and performance

## Troubleshooting

### Common Issues
1. **Azure Functions not running**: Start with `func start`
2. **Configuration errors**: Check `.env` file and connection strings
3. **Import errors**: Ensure running from correct directory
4. **API errors**: Verify Azure service accessibility and credentials

### Debug Mode
Enable detailed logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

---

*All tests support the refactored modular architecture with automatic blob trigger processing.*