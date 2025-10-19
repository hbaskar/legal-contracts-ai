# Azure App Settings JSON Configuration

## Overview
This directory contains JSON files for deploying application settings to Azure Function Apps, generated from your `.env` file configuration.

## Files Generated

### 1. `app-settings.json`
**Purpose**: Direct conversion from your current `.env` file
**Usage**: Development/testing deployments with current values
**Contains**: 32 application settings from your `.env` file

### 2. `app-settings-template.json`
**Purpose**: Production-ready template with placeholders
**Usage**: Production deployments after replacing placeholder values
**Security**: Contains placeholder values that need to be replaced

### 3. `deploy-app-settings.ps1`
**Purpose**: PowerShell script to deploy settings to Azure Function App
**Features**: 
- Dry-run capability
- Masked sensitive values in output
- Slot setting support
- Error handling and validation

## JSON Structure

Each application setting follows this format:
```json
{
  "name": "SETTING_NAME",
  "value": "setting_value",
  "slotSetting": false
}
```

### Slot Settings (`slotSetting: true`)
These settings are marked as slot-specific and won't be swapped between deployment slots:
- `AZURE_SQL_PASSWORD`
- `AZURE_OPENAI_KEY`
- `AZURE_SEARCH_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_STORAGE_ACCOUNT_KEY`
- `AZURE_AI_SERVICES_KEY`
- `AZURE_SENDGRID_API_KEY`

## Usage Examples

### 1. Deploy Current Settings (Development)
```powershell
cd deployment
.\deploy-app-settings.ps1 -FunctionAppName "my-dev-function" -ResourceGroupName "my-dev-rg"
```

### 2. Dry Run (See what would be deployed)
```powershell
.\deploy-app-settings.ps1 -FunctionAppName "my-function" -ResourceGroupName "my-rg" -DryRun
```

### 3. Deploy Production Template
```powershell
# First, replace placeholders in app-settings-template.json
# Then deploy
.\deploy-app-settings.ps1 -FunctionAppName "my-prod-function" -ResourceGroupName "my-prod-rg" -SettingsFile "app-settings-template.json"
```

This configuration provides a complete solution for managing and deploying Azure Function App settings! 🚀