# Scripts

This directory contains utility scripts, migration tools, and automation scripts for the project.

## Files

### Setup and Configuration
- **setup.py** - Main project setup script
- **setup_dependencies.py** - Dependency setup and validation script

### Database and Migration
- **check_database.py** - Database connectivity and schema validation
- **migrate_azure_search_chunks.py** - Migration script for Azure Search chunks

### Postman Collection Updates
- **update_postman_admin.py** - Updates Postman collection with admin endpoints
- **update_postman_deletion.py** - Updates Postman collection with deletion endpoints  
- **update_postman_index.py** - Updates Postman collection with index management endpoints

## Purpose

These scripts automate common tasks like:
- Project setup and dependency management
- Database operations and migrations
- API collection updates for testing
- System validation and health checks

## Usage

Most scripts can be run directly with Python:
```bash
python scripts/setup.py
python scripts/check_database.py
```

Some scripts may require environment variables or configuration files to be set up first.