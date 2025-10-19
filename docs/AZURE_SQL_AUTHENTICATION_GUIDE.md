# Azure SQL Authentication Guide

This guide explains the multiple authentication methods supported by the Fresh Start Document Processing system for connecting to Azure SQL Database.

## Authentication Methods

### 1. Managed Identity (RECOMMENDED)

Managed Identity is the most secure authentication method for Azure-hosted applications.

#### System-Assigned Managed Identity
```bash
AZURE_SQL_AUTH_METHOD=managed_identity
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
```

#### User-Assigned Managed Identity
```bash
AZURE_SQL_AUTH_METHOD=managed_identity
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID=your_user_assigned_mi_client_id
```

**Benefits:**
- No credentials to manage or rotate
- Automatically managed by Azure
- Most secure for production environments
- Works seamlessly in Azure Functions, App Services, VMs, etc.

**Setup Required:**
1. Enable managed identity on your Azure resource
2. Grant SQL permissions to the managed identity
3. Configure firewall rules

### 2. Azure AD Password Authentication

Use when you need to authenticate with Azure AD credentials.

```bash
AZURE_SQL_AUTH_METHOD=ad_password
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
AZURE_SQL_USERNAME=your_email@domain.com
AZURE_SQL_PASSWORD=your_password
```

**Use Cases:**
- Development environments
- Service accounts with Azure AD credentials
- When managed identity is not available

**Security Considerations:**
- Store credentials securely (Azure Key Vault recommended)
- Implement credential rotation
- Use strong passwords and MFA where possible

### 3. Azure AD Integrated Authentication

Uses the current Windows/Azure AD user context.

```bash
AZURE_SQL_AUTH_METHOD=ad_integrated
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
```

**Use Cases:**
- Local development with domain-joined machines
- Windows-based applications
- Interactive applications

### 4. SQL Server Authentication (NOT RECOMMENDED for production)

Traditional SQL Server username/password authentication.

```bash
AZURE_SQL_AUTH_METHOD=sql_auth
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
AZURE_SQL_USERNAME=sql_username
AZURE_SQL_PASSWORD=sql_password
```

**Use Cases:**
- Legacy applications
- Quick prototyping
- When other methods are not feasible

**Security Considerations:**
- Enable SQL authentication on the server
- Use strong passwords
- Implement credential rotation
- Store credentials securely

### 5. Automatic Authentication (DEFAULT)

The system automatically selects the best authentication method based on environment.

```bash
AZURE_SQL_AUTH_METHOD=auto
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database_name
```

**Selection Priority:**
1. **Managed Identity** - If running in Azure environment
2. **Azure AD Password** - If username/password provided with email format
3. **SQL Server Authentication** - If username/password provided without email format
4. **Azure AD Integrated** - Fallback for Windows environments
5. **Managed Identity** - Final fallback

## Environment Detection

The system detects Azure environments using these indicators:
- `WEBSITE_SITE_NAME` (Azure App Service)
- `AZURE_CLIENT_ID` (Managed Identity)
- `MSI_ENDPOINT` (Managed Service Identity endpoint)
- `AZURE_SQL_MANAGED_IDENTITY_CLIENT_ID` (User-assigned MI configuration)

## Connection String Override

You can override all authentication settings with a direct connection string:

```bash
AZURE_SQL_CONNECTION_STRING=Server=tcp:your_server.database.windows.net,1433;Database=your_db;Authentication=ActiveDirectoryMsi;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

## Error Handling and Retry Logic

The system includes:
- **Exponential backoff retry** (3 attempts by default)
- **Connection validation** with test queries
- **Detailed error logging** with authentication context
- **Troubleshooting guidance** for common issues

## Security Best Practices

### Production Recommendations:
1. **Use Managed Identity** whenever possible
2. **Store secrets in Azure Key Vault**
3. **Enable firewall rules** to restrict access
4. **Use least privilege permissions**
5. **Monitor connection attempts** and failures
6. **Rotate credentials regularly**

### Development Recommendations:
1. Use **SQLite for local development** (`DATABASE_TYPE=sqlite`)
2. Use **Azure AD authentication** for cloud development
3. **Never commit credentials** to source control
4. Use **environment-specific configuration**

## Database Permissions Setup

### For Managed Identity:
```sql
-- Create user for system-assigned managed identity
CREATE USER [your-function-app-name] FROM EXTERNAL PROVIDER;
-- Or for user-assigned managed identity
CREATE USER [your-managed-identity-name] FROM EXTERNAL PROVIDER;

-- Grant permissions
ALTER ROLE db_datareader ADD MEMBER [your-function-app-name];
ALTER ROLE db_datawriter ADD MEMBER [your-function-app-name];
ALTER ROLE db_ddladmin ADD MEMBER [your-function-app-name];  -- If schema changes needed
```

### For Azure AD User:
```sql
CREATE USER [user@domain.com] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [user@domain.com];
ALTER ROLE db_datawriter ADD MEMBER [user@domain.com];
```

## Troubleshooting

### Common Issues:

1. **Authentication Failed**
   - Verify credentials are correct
   - Check user/identity has database permissions
   - Ensure firewall allows connections

2. **Server Not Found**
   - Verify server name is correct
   - Check network connectivity
   - Confirm firewall rules

3. **Managed Identity Issues**
   - Ensure MI is enabled on the resource
   - Verify MI has SQL database permissions
   - Check client ID for user-assigned MI

4. **Connection Timeout**
   - Check network connectivity
   - Verify firewall rules
   - Consider increasing timeout values

### Logging

Enable detailed logging to troubleshoot connection issues:
```bash
LOG_LEVEL=DEBUG
```

The system logs authentication method attempts and provides specific troubleshooting guidance for each method.

## Migration Guide

### From Direct Connection String:
1. Set individual components (server, database, etc.)
2. Choose appropriate authentication method
3. Remove direct connection string
4. Test connectivity

### From SQL Authentication to Managed Identity:
1. Enable managed identity on your Azure resource
2. Create managed identity user in database
3. Grant appropriate permissions
4. Update authentication method
5. Remove username/password
6. Test and validate

This multi-authentication approach provides flexibility while maintaining security best practices for different deployment scenarios.