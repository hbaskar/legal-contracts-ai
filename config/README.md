# Configuration Guide

This directory contains configuration templates and examples for different deployment environments.

## Configuration Files

### Environment Templates

- **`.env.example`** - General configuration template with all available options
- **`.env.local.example`** - Local development configuration using SQLite and Azurite
- **`.env.staging.example`** - Development/staging environment with cloud resources
- **`.env.production.example`** - Production environment with security best practices

### Core Configuration Files (in root directory)

- **`host.json`** - Azure Functions host configuration (must remain in root)
- **`local.settings.json`** - Azure Functions local development settings (must remain in root)

## Usage Instructions

### 1. Local Development Setup

```bash
# Copy local development template
cp config/.env.local.example .env

# Install and start Azurite (local storage emulator)
npm install -g azurite
azurite --silent --location ./data --debug ./data/debug.log

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Start the function app
func start
```

### 2. Cloud Development/Staging Setup

```bash
# Copy staging template
cp config/.env.staging.example .env

# Customize with your Azure resources:
# - Update storage account details
# - Configure Azure SQL database
# - Set up AI services (OpenAI, Search)
# - Configure authentication
```

### 3. Production Deployment

```bash
# Use production template as reference
cp config/.env.production.example .env.production

# IMPORTANT: 
# - Store sensitive values in Azure Key Vault
# - Use managed identity for authentication
# - Configure proper firewall rules
# - Enable monitoring and logging
```

## Configuration Categories

### Azure Functions Core
- `AzureWebJobsStorage` - Storage account for Azure Functions runtime
- `FUNCTIONS_WORKER_RUNTIME` - Runtime (python)
- `AzureWebJobsFeatureFlags` - Feature flags

### Storage Configuration
- `AZURE_STORAGE_CONNECTION_STRING` - Blob storage connection
- `AZURE_STORAGE_CONTAINER_NAME` - Container for file uploads

### Database Configuration
- `DATABASE_TYPE` - sqlite (local) or azuresql (cloud)
- `SQLITE_DATABASE_PATH` - SQLite database path
- Azure SQL settings (see [Azure SQL Authentication Guide](../docs/AZURE_SQL_AUTHENTICATION_GUIDE.md))

### AI Services
- Azure OpenAI configuration
- Azure Search configuration  
- Document processing settings

### Application Settings
- File size limits
- SAS URL expiry
- Logging levels

## Security Best Practices

### Local Development
✅ Use SQLite and Azurite for offline development  
✅ Keep sensitive values out of version control  
✅ Use `.env.local` for local overrides  

### Staging/Development
✅ Use separate Azure resources for non-production  
✅ Use Azure AD authentication where possible  
✅ Enable detailed logging for troubleshooting  

### Production
✅ Use Azure Key Vault for all secrets  
✅ Enable managed identity authentication  
✅ Configure network security (firewalls, private endpoints)  
✅ Enable monitoring and alerting  
✅ Use least privilege access principles  

## Environment Variable Priority

1. System environment variables
2. `.env` file in root directory
3. `.env.local` file (for local overrides)
4. Default values in code

## Troubleshooting

### Common Issues

1. **Azure Functions not starting**
   - Check `host.json` and `local.settings.json` are in root
   - Verify storage connection string
   - Check Python version compatibility

2. **Database connection failures**
   - Verify authentication method and credentials
   - Check firewall rules
   - See [Azure SQL Authentication Guide](../docs/AZURE_SQL_AUTHENTICATION_GUIDE.md)

3. **AI services not working**
   - Verify OpenAI endpoint and key
   - Check Search service configuration
   - Validate model deployment names

### Getting Help

- Check the main [README.md](../README.md) for setup instructions
- Review specific guides in [docs/](../docs/) directory
- Check test files in [tests/](../tests/) for examples
- Enable DEBUG logging for detailed diagnostics

## Template Customization

When using these templates:

1. **Copy** the appropriate template to `.env` in the root directory
2. **Replace** placeholder values with your actual configuration
3. **Remove** unused configuration sections
4. **Add** any additional settings your deployment requires
5. **Test** the configuration in a safe environment first

Remember to never commit sensitive configuration values to version control!