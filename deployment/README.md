# Deployment

This directory contains deployment scripts and configuration for the Fresh Start Document Processing system.

## Files

- **deploy.ps1** - PowerShell deployment script for Azure resources

## Purpose

Deployment scripts handle:
- Azure resource provisioning
- Function App deployment
- Configuration setup
- Environment-specific deployments

## Usage

Run the deployment script with appropriate parameters:

```powershell
.\deployment\deploy.ps1
```

## Prerequisites

Before running deployment scripts:
- Ensure Azure CLI is installed and authenticated
- Set up required environment variables
- Configure deployment parameters
- Verify Azure subscription permissions

## Configuration

The deployment process may require:
- Azure subscription ID
- Resource group names
- Storage account configuration
- Search service settings
- Function App configuration