#!/usr/bin/env python3
"""
Test Runner for Fresh Start Document Processing System

This script provides a convenient way to run tests from the root directory
and organizes test execution by category.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_test(test_name, description=""):
    """Run a specific test and capture results"""
    test_path = Path("tests") / test_name
    
    if not test_path.exists():
        print(f"❌ Test file not found: {test_path}")
        return False
    
    print(f"\n🧪 Running {test_name}")
    if description:
        print(f"   {description}")
    print("=" * 70)
    
    try:
        result = subprocess.run([sys.executable, str(test_path)], 
                               capture_output=False, 
                               check=True)
        print(f"✅ {test_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {test_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run tests for Fresh Start Document Processing System")
    parser.add_argument("--category", choices=["all", "core", "search", "infrastructure", "reset", "document"], 
                       default="all", help="Test category to run")
    parser.add_argument("--test", help="Run a specific test file")
    parser.add_argument("--list", action="store_true", help="List available tests")
    
    args = parser.parse_args()
    
    # Test categories
    test_categories = {
        "core": [
            ("test_whole.py", "Comprehensive system test runner"),
            ("test_complete_workflow.py", "End-to-end workflow tests"),
            ("test_ai_processing.py", "AI document processing tests"),
            ("test_blob_trigger.py", "Blob trigger functionality"),
            ("quick_test.py", "Quick validation tests"),
        ],
        "search": [
            ("test_azure_search_content.py", "Azure Search content access"),
            ("test_search_chunks_content.py", "Search chunk content validation"),
            ("test_paragraph_persistence.py", "Paragraph data persistence"),
        ],
        "infrastructure": [
            ("test_index_creation.py", "Index creation and management"),
            ("test_document_deletion.py", "Document deletion functionality"),
            ("test_chunking_config.py", "Chunking configuration tests"),
        ],
        "reset": [
            ("test_reset_endpoint.py", "Database reset endpoint"),
            ("test_reset_endpoints.py", "Multiple reset endpoints"),
            ("test_reset_with_data.py", "Reset operations with data"),
        ],
        "document": [
            ("test_pdf_methods.py", "PDF processing methods"),
            ("test_upload.py", "File upload functionality"),
            ("test_database.py", "Database operations"),
        ]
    }
    
    if args.list:
        print("📋 Available Tests by Category:")
        print("=" * 50)
        for category, tests in test_categories.items():
            print(f"\n🏷️  {category.upper()}")
            for test_name, description in tests:
                print(f"   • {test_name:<30} - {description}")
        
        print(f"\n💡 Usage Examples:")
        print(f"   python run_tests.py --category core")
        print(f"   python run_tests.py --test test_index_creation.py")
        print(f"   python run_tests.py --category all")
        return
    
    if args.test:
        # Run specific test
        success = run_test(args.test)
        sys.exit(0 if success else 1)
    
    # Run tests by category
    if args.category == "all":
        categories_to_run = list(test_categories.keys())
    else:
        categories_to_run = [args.category]
    
    print("🚀 Fresh Start Document Processing Test Runner")
    print("=" * 70)
    print(f"📂 Running tests for category: {args.category}")
    
    total_tests = 0
    passed_tests = 0
    
    for category in categories_to_run:
        if category not in test_categories:
            print(f"❌ Unknown category: {category}")
            continue
            
        print(f"\n🏷️  {category.upper()} TESTS")
        print("-" * 50)
        
        for test_name, description in test_categories[category]:
            total_tests += 1
            if run_test(test_name, description):
                passed_tests += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        exit_code = 0
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed")
        exit_code = 1
    
    print("\n💡 Tips:")
    print("• Run 'python run_tests.py --list' to see all available tests")
    print("• Use '--category core' for essential functionality tests")
    print("• Use '--test test_name.py' to run a specific test")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    # Change to script directory to ensure relative paths work
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    main()