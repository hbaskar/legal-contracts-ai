#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy the Azure Function File Upload Service to Azure

.DESCRIPTION
    This script creates the necessary Azure resources and deploys the function app
    
.PARAMETER ResourceGroupName
    Name of the Azure resource group
    
.PARAMETER StorageAccountName
    Name of the Azure storage account
    
.PARAMETER FunctionAppName
    Name of the Azure function app
    
.PARAMETER SqlServerName
    Name of the Azure SQL server (optional)
    
.PARAMETER SqlDatabaseName
    Name of the Azure SQL database (optional)
    
.PARAMETER Location
    Azure region for deployment (default: eastus)
    
.PARAMETER UseSqlite
    Use SQLite instead of Azure SQL (for development deployments)

.EXAMPLE
    ./deploy.ps1 -ResourceGroupName "rg-fileupload" -StorageAccountName "stfileupload123" -FunctionAppName "func-fileupload-123"
    
.EXAMPLE
    ./deploy.ps1 -ResourceGroupName "rg-fileupload" -StorageAccountName "stfileupload123" -FunctionAppName "func-fileupload-123" -SqlServerName "sql-fileupload" -SqlDatabaseName "FileUploadDB"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$SqlServerName,
    
    [Parameter(Mandatory=$false)]
    [string]$SqlDatabaseName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseSqlite
)

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check if Azure CLI is installed
function Test-AzureCli {
    try {
        $version = az --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Azure CLI is installed" "Green"
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ Azure CLI is not installed or not in PATH" "Red"
        Write-ColorOutput "Please install Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli" "Yellow"
        return $false
    }
}

# Function to check if logged in to Azure
function Test-AzureLogin {
    try {
        $account = az account show 2>$null | ConvertFrom-Json
        if ($account) {
            Write-ColorOutput "✅ Logged in to Azure as: $($account.user.name)" "Green"
            Write-ColorOutput "   Subscription: $($account.name) ($($account.id))" "Gray"
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ Not logged in to Azure" "Red"
        Write-ColorOutput "Please run: az login" "Yellow"
        return $false
    }
}

# Function to create resource group
function New-ResourceGroup {
    param([string]$Name, [string]$Location)
    
    Write-ColorOutput "`n🔨 Creating resource group: $Name" "Cyan"
    
    $rg = az group create --name $Name --location $Location 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Resource group created successfully" "Green"
        return $true
    } else {
        Write-ColorOutput "❌ Failed to create resource group" "Red"
        return $false
    }
}

# Function to create storage account
function New-StorageAccount {
    param([string]$Name, [string]$ResourceGroup, [string]$Location)
    
    Write-ColorOutput "`n🔨 Creating storage account: $Name" "Cyan"
    
    $storage = az storage account create --name $Name --resource-group $ResourceGroup --location $Location --sku Standard_LRS --kind StorageV2 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Storage account created successfully" "Green"
        
        # Create the uploads container
        Write-ColorOutput "   Creating uploads container..." "Gray"
        az storage container create --name uploads --account-name $Name --auth-mode login 2>$null
        
        return $true
    } else {
        Write-ColorOutput "❌ Failed to create storage account" "Red"
        return $false
    }
}

# Function to create SQL server and database
function New-SqlResources {
    param([string]$ServerName, [string]$DatabaseName, [string]$ResourceGroup, [string]$Location)
    
    Write-ColorOutput "`n🔨 Creating SQL Server: $ServerName" "Cyan"
    
    # Generate a random password
    $password = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | % {[char]$_})
    $adminUser = "sqladmin"
    
    # Create SQL Server
    $server = az sql server create --name $ServerName --resource-group $ResourceGroup --location $Location --admin-user $adminUser --admin-password $password 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "❌ Failed to create SQL server" "Red"
        return $false
    }
    
    Write-ColorOutput "✅ SQL Server created successfully" "Green"
    Write-ColorOutput "   Admin User: $adminUser" "Gray"
    Write-ColorOutput "   Password: $password (save this securely!)" "Yellow"
    
    # Configure firewall to allow Azure services
    Write-ColorOutput "   Configuring firewall rules..." "Gray"
    az sql server firewall-rule create --resource-group $ResourceGroup --server $ServerName --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 2>$null
    
    # Create database
    Write-ColorOutput "   Creating database: $DatabaseName" "Gray"
    $database = az sql db create --resource-group $ResourceGroup --server $ServerName --name $DatabaseName --service-objective Basic 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ SQL Database created successfully" "Green"
        return $true
    } else {
        Write-ColorOutput "❌ Failed to create SQL database" "Red"
        return $false
    }
}

# Function to create function app
function New-FunctionApp {
    param([string]$Name, [string]$ResourceGroup, [string]$StorageAccount, [string]$Location)
    
    Write-ColorOutput "`n🔨 Creating Function App: $Name" "Cyan"
    
    $functionApp = az functionapp create --resource-group $ResourceGroup --consumption-plan-location $Location --runtime python --runtime-version 3.11 --functions-version 4 --name $Name --storage-account $StorageAccount --os-type Linux 2>$null | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Function App created successfully" "Green"
        Write-ColorOutput "   URL: https://$Name.azurewebsites.net" "Gray"
        return $true
    } else {
        Write-ColorOutput "❌ Failed to create Function App" "Red"
        return $false
    }
}

# Function to configure app settings
function Set-AppSettings {
    param([string]$FunctionAppName, [string]$ResourceGroup, [string]$StorageAccount, [string]$SqlServer, [string]$SqlDatabase, [bool]$UsesSqlite)
    
    Write-ColorOutput "`n⚙️ Configuring application settings..." "Cyan"
    
    # Get storage connection string
    $storageConnString = az storage account show-connection-string --name $StorageAccount --resource-group $ResourceGroup --output tsv 2>$null
    
    if ($UsesSqlite) {
        # Configure for SQLite
        az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroup --settings AZURE_STORAGE_CONNECTION_STRING="$storageConnString" AZURE_STORAGE_CONTAINER_NAME="uploads" DATABASE_TYPE="sqlite" SQLITE_DATABASE_PATH="./data/metadata.db" 2>$null
    } else {
        # Configure for Azure SQL with managed identity
        $sqlConnString = "Server=tcp:$SqlServer.database.windows.net,1433;Initial Catalog=$SqlDatabase;Authentication=Active Directory Default;"
        az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroup --settings AZURE_STORAGE_CONNECTION_STRING="$storageConnString" AZURE_STORAGE_CONTAINER_NAME="uploads" DATABASE_TYPE="azuresql" AZURE_SQL_CONNECTION_STRING="$sqlConnString" 2>$null
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Application settings configured" "Green"
        return $true
    } else {
        Write-ColorOutput "❌ Failed to configure application settings" "Red"
        return $false
    }
}

# Function to enable managed identity
function Enable-ManagedIdentity {
    param([string]$FunctionAppName, [string]$ResourceGroup)
    
    Write-ColorOutput "`n🔐 Enabling managed identity..." "Cyan"
    
    $identity = az functionapp identity assign --name $FunctionAppName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Managed identity enabled" "Green"
        Write-ColorOutput "   Principal ID: $($identity.principalId)" "Gray"
        return $identity.principalId
    } else {
        Write-ColorOutput "❌ Failed to enable managed identity" "Red"
        return $null
    }
}

# Function to deploy the function
function Deploy-Function {
    param([string]$FunctionAppName)
    
    Write-ColorOutput "`n🚀 Deploying function code..." "Cyan"
    
    # Check if func CLI is available
    try {
        func --version 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ Azure Functions Core Tools not found" "Red"
            Write-ColorOutput "Please install: npm install -g azure-functions-core-tools@4 --unsafe-perm true" "Yellow"
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Azure Functions Core Tools not found" "Red"
        return $false
    }
    
    # Deploy the function
    func azure functionapp publish $FunctionAppName --python
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "✅ Function deployed successfully" "Green"
        return $true
    } else {
        Write-ColorOutput "❌ Failed to deploy function" "Red"
        return $false
    }
}

# Main deployment script
function Main {
    Write-ColorOutput "Azure Function File Upload Service - Deployment Script" "White"
    Write-ColorOutput "=" * 65 "White"
    
    # Validate prerequisites
    if (!(Test-AzureCli)) { exit 1 }
    if (!(Test-AzureLogin)) { exit 1 }
    
    # Determine if using SQL
    $useSql = ![string]::IsNullOrEmpty($SqlServerName) -and ![string]::IsNullOrEmpty($SqlDatabaseName) -and !$UseSqlite
    
    Write-ColorOutput "`n📋 Deployment Configuration:" "White"
    Write-ColorOutput "   Resource Group: $ResourceGroupName" "Gray"
    Write-ColorOutput "   Storage Account: $StorageAccountName" "Gray"
    Write-ColorOutput "   Function App: $FunctionAppName" "Gray"
    Write-ColorOutput "   Location: $Location" "Gray"
    if ($useSql) {
        Write-ColorOutput "   SQL Server: $SqlServerName" "Gray"
        Write-ColorOutput "   SQL Database: $SqlDatabaseName" "Gray"
        Write-ColorOutput "   Database Type: Azure SQL" "Gray"
    } else {
        Write-ColorOutput "   Database Type: SQLite" "Gray"
    }
    
    # Confirm deployment
    $confirm = Read-Host "`nProceed with deployment? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-ColorOutput "Deployment cancelled" "Yellow"
        exit 0
    }
    
    # Create resources
    if (!(New-ResourceGroup -Name $ResourceGroupName -Location $Location)) { exit 1 }
    if (!(New-StorageAccount -Name $StorageAccountName -ResourceGroup $ResourceGroupName -Location $Location)) { exit 1 }
    
    if ($useSql) {
        if (!(New-SqlResources -ServerName $SqlServerName -DatabaseName $SqlDatabaseName -ResourceGroup $ResourceGroupName -Location $Location)) { exit 1 }
    }
    
    if (!(New-FunctionApp -Name $FunctionAppName -ResourceGroup $ResourceGroupName -StorageAccount $StorageAccountName -Location $Location)) { exit 1 }
    
    # Configure the function app
    $principalId = Enable-ManagedIdentity -FunctionAppName $FunctionAppName -ResourceGroup $ResourceGroupName
    if (!$principalId) { exit 1 }
    
    if (!(Set-AppSettings -FunctionAppName $FunctionAppName -ResourceGroup $ResourceGroupName -StorageAccount $StorageAccountName -SqlServer $SqlServerName -SqlDatabase $SqlDatabaseName -UsesSqlite (!$useSql))) { exit 1 }
    
    # Deploy function code
    if (!(Deploy-Function -FunctionAppName $FunctionAppName)) { exit 1 }
    
    # Summary
    Write-ColorOutput "`n" + "=" * 65 "White"
    Write-ColorOutput "🎉 Deployment completed successfully!" "Green"
    Write-ColorOutput "`n📋 Resource Information:" "White"
    Write-ColorOutput "   Function App URL: https://$FunctionAppName.azurewebsites.net" "Gray"
    Write-ColorOutput "   API Endpoints:" "Gray"
    Write-ColorOutput "     - POST https://$FunctionAppName.azurewebsites.net/api/upload" "Gray"
    Write-ColorOutput "     - GET  https://$FunctionAppName.azurewebsites.net/api/files/{id}" "Gray"
    Write-ColorOutput "     - GET  https://$FunctionAppName.azurewebsites.net/api/health" "Gray"
    
    if ($useSql) {
        Write-ColorOutput "`n⚠️  Important: Save the SQL Server admin credentials securely!" "Yellow"
    }
    
    Write-ColorOutput "`n📖 Test your deployment with the provided test script" "Cyan"
}

# Run the main function
Main