#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy application settings to Azure Function App

.DESCRIPTION
    This script deploys application settings from a JSON file to an Azure Function App

.PARAMETER FunctionAppName
    Name of the Azure Function App

.PARAMETER ResourceGroupName
    Name of the Azure Resource Group

.PARAMETER SettingsFile
    Path to the JSON file containing application settings (default: app-settings.json)

.PARAMETER DryRun
    Show what would be deployed without actually deploying

.EXAMPLE
    .\deploy-app-settings.ps1 -FunctionAppName "my-function-app" -ResourceGroupName "my-rg"

.EXAMPLE
    .\deploy-app-settings.ps1 -FunctionAppName "my-function-app" -ResourceGroupName "my-rg" -SettingsFile "app-settings-prod.json" -DryRun
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $false)]
    [string]$SettingsFile = "app-settings.json",
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Check if Azure CLI is installed
try {
    az --version | Out-Null
}
catch {
    Write-Error "Azure CLI is not installed or not in PATH. Please install Azure CLI first."
    exit 1
}

# Check if settings file exists
if (!(Test-Path $SettingsFile)) {
    Write-Error "Settings file '$SettingsFile' not found."
    exit 1
}

# Read and parse JSON file
Write-Host "📄 Reading settings from '$SettingsFile'..." -ForegroundColor Cyan
try {
    $settings = Get-Content $SettingsFile | ConvertFrom-Json
}
catch {
    Write-Error "Failed to parse JSON file: $_"
    exit 1
}

Write-Host "✅ Found $($settings.Count) application settings" -ForegroundColor Green

# Check if Function App exists
Write-Host "🔍 Checking if Function App '$FunctionAppName' exists..." -ForegroundColor Cyan
try {
    $functionApp = az functionapp show --name $FunctionAppName --resource-group $ResourceGroupName 2>$null | ConvertFrom-Json
    if (!$functionApp) {
        Write-Error "Function App '$FunctionAppName' not found in resource group '$ResourceGroupName'"
        exit 1
    }
    Write-Host "✅ Function App found: $($functionApp.defaultHostName)" -ForegroundColor Green
}
catch {
    Write-Error "Failed to check Function App: $_"
    exit 1
}

if ($DryRun) {
    Write-Host "🔍 DRY RUN - The following settings would be deployed:" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Yellow
    
    foreach ($setting in $settings) {
        $slotIndicator = if ($setting.slotSetting) { " (slot setting)" } else { "" }
        $maskedValue = if ($setting.name -match "(KEY|SECRET|PASSWORD|TOKEN|CONNECTION)") {
            $setting.value.Substring(0, [Math]::Min(8, $setting.value.Length)) + "***"
        } else {
            $setting.value
        }
        Write-Host "  $($setting.name) = $maskedValue$slotIndicator" -ForegroundColor White
    }
    
    Write-Host "================================================" -ForegroundColor Yellow
    Write-Host "Use without -DryRun to actually deploy these settings." -ForegroundColor Yellow
    exit 0
}

# Deploy settings
Write-Host "🚀 Deploying application settings to '$FunctionAppName'..." -ForegroundColor Cyan

$successCount = 0
$errorCount = 0

foreach ($setting in $settings) {
    try {
        $slotFlag = if ($setting.slotSetting) { "--slot-settings" } else { "--settings" }
        
        # Mask sensitive values in output
        $displayValue = if ($setting.name -match "(KEY|SECRET|PASSWORD|TOKEN|CONNECTION)") {
            $setting.value.Substring(0, [Math]::Min(8, $setting.value.Length)) + "***"
        } else {
            $setting.value
        }
        
        Write-Host "  Setting $($setting.name) = $displayValue" -ForegroundColor White
        
        # Deploy the setting
        az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName $slotFlag "$($setting.name)=$($setting.value)" --output none
        
        $successCount++
    }
    catch {
        Write-Error "Failed to set $($setting.name): $_"
        $errorCount++
    }
}

# Summary
Write-Host "================================================" -ForegroundColor Green
if ($errorCount -eq 0) {
    Write-Host "✅ Successfully deployed $successCount application settings!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Deployed $successCount settings with $errorCount errors." -ForegroundColor Yellow
}

Write-Host "🌐 Function App URL: https://$($functionApp.defaultHostName)" -ForegroundColor Cyan
Write-Host "📊 You can view settings in the Azure Portal:" -ForegroundColor Cyan
Write-Host "   https://portal.azure.com/#@/resource$($functionApp.id)/configuration" -ForegroundColor Blue