# Deployment Configuration Guide

## Overview
This guide explains how to exclude development files (`tests/`, `test_files/`, `docs/`) from production deployments while keeping them in source control.

## Deployment Exclusions

### 1. Azure Functions Deployment (.funcignore)
The `.funcignore` file automatically excludes directories from Azure Functions deployment:

```plaintext
# Azure Functions deployment exclusions
.venv
.git
.gitignore
.pytest_cache
.vscode

# Development and testing files
tests/
test_files/
docs/
run_tests.py

# Development documentation
README.md
*.md

# Configuration templates
config/.env*.example
config/validate_config.py

# Postman collections (optional)
postman/
```

### 2. Azure DevOps Pipeline
If using Azure DevOps, add to your `azure-pipelines.yml`:

```yaml
steps:
- task: ArchiveFiles@2
  inputs:
    rootFolderOrFile: '$(System.DefaultWorkingDirectory)'
    includeRootFolder: false
    archiveType: 'zip'
    archiveFile: '$(Build.ArtifactStagingDirectory)/$(Build.BuildId).zip'
    excludePatterns: |
      tests/**
      test_files/**
      docs/**
      postman/**
      *.md
      run_tests.py
      config/.env*.example
```

### 3. GitHub Actions
For GitHub Actions deployment, use `.github/workflows/deploy.yml`:

```yaml
steps:
- name: Prepare deployment package
  run: |
    # Remove development files
    rm -rf tests/
    rm -rf test_files/
    rm -rf docs/
    rm -rf postman/
    rm -f run_tests.py
    rm -f *.md
    rm -f config/.env*.example
```

### 4. Manual Deployment
For manual deployments, exclude these directories:
- `tests/` - Unit tests and test scripts
- `test_files/` - Sample files for testing
- `docs/` - Documentation and guides
- `postman/` - API testing collections
- `run_tests.py` - Test runner script
- `*.md` files - Documentation files
- `config/.env*.example` - Configuration templates

## Production vs Development

### Files to Deploy ✅
```
function_app.py          # Main Azure Function
host.json               # Function host configuration
requirements.txt        # Python dependencies
.funcignore            # Deployment exclusions
blob/                  # Blob processing logic
config/                # Configuration management
  ├── config.py        # Configuration loader
  ├── database.py      # Database manager
  └── README.md        # Config documentation
contracts/             # Business logic
  ├── ai_services.py   # AI processing
  ├── storage.py       # Storage operations
  ├── index_creation.py# Search index management
  └── ...
scripts/               # Utility scripts (optional)
deployment/            # Deployment scripts
```

### Files NOT to Deploy ❌
```
tests/                 # Unit tests
test_files/           # Test data
docs/                 # Documentation
postman/              # API testing
run_tests.py          # Test runner
README.md            # Project documentation
config/.env*.example  # Configuration templates
config/validate_config.py # Development validation
.pytest_cache/        # Test cache
.vscode/             # IDE settings
```

## Environment Variables

### Development
```bash
# Local development uses .env file
DATABASE_TYPE=sqlite
SQLITE_DATABASE_PATH=./data/metadata.db
```

### Production
```bash
# Production uses Azure App Settings
DATABASE_TYPE=azuresql
AZURE_SQL_CONNECTION_STRING=Server=...
```

## Verification

### Check .funcignore is working:
```bash
# Test deployment size
func azure functionapp publish <app-name> --show-keys --dry-run
```

### Verify exclusions:
```bash
# Check what would be deployed
zip -r deployment.zip . -x@.funcignore
```

## Best Practices

1. **Keep .funcignore Updated**: Add new development directories as project grows
2. **Environment-Specific Config**: Use Azure App Settings for production secrets
3. **CI/CD Pipelines**: Automate exclusions in deployment pipelines
4. **Size Monitoring**: Monitor deployment package size to catch inclusion issues
5. **Testing**: Test deployments in staging environment first

## Deployment Commands

### Azure CLI
```bash
# Deploy with exclusions
func azure functionapp publish <function-app-name>
```

### Azure DevOps
```yaml
# Uses .funcignore automatically
- task: AzureFunctionApp@1
  inputs:
    azureSubscription: 'your-subscription'
    appType: 'functionAppLinux'
    appName: 'your-function-app'
    package: '$(Build.ArtifactStagingDirectory)/*.zip'
```

This configuration ensures your production deployment is lean and secure while keeping all development tools available in your source repository.