"""
Batch Policy Document Processor
Processes all policy documents in the policy_document directory
"""

import os
import requests
import base64
import json
from pathlib import Path

def process_policy_documents():
    """Process all policy documents in the policy_document directory"""
    
    print("🚀 BATCH POLICY DOCUMENT PROCESSING")
    print("=" * 60)
    
    # Configuration
    base_url = "http://localhost:7071"
    policy_dir = Path("policy_document")
    
    if not policy_dir.exists():
        print(f"❌ Policy directory not found: {policy_dir}")
        return
    
    # Find all policy documents
    policy_files = []
    for ext in ['*.docx', '*.pdf', '*.txt']:
        policy_files.extend(policy_dir.glob(ext))
    
    if not policy_files:
        print(f"📁 No policy documents found in {policy_dir}")
        return
    
    print(f"📁 Found {len(policy_files)} policy documents:")
    for file in policy_files:
        print(f"   - {file.name}")
    
    # Process each policy document
    results = []
    successful_uploads = 0
    
    for i, policy_file in enumerate(policy_files):
        print(f"\n📋 Processing {i+1}/{len(policy_files)}: {policy_file.name}")
        
        try:
            # Read the policy file
            with open(policy_file, 'rb') as f:
                file_content = f.read()
            
            # Encode file content
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # Determine groups based on filename
            groups = ["legal-team", "compliance"]
            if "german" in policy_file.name.lower():
                groups.append("german-legal")
                groups.append("international")
            if "governing" in policy_file.name.lower():
                groups.append("contracts")
                groups.append("jurisdiction")
            if "limitation" in policy_file.name.lower():
                groups.append("liability")
                groups.append("risk-management")
            
            # Prepare payload
            payload = {
                "filename": policy_file.name,
                "file_content": encoded_content,
                "groups": groups,
                "upload_to_search": True
            }
            
            # Process the policy document
            print(f"   🧠 Analyzing policy clauses with AI...")
            response = requests.post(
                f"{base_url}/api/process_policy",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120  # Extended timeout for larger documents
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Status: {result['status']}")
                print(f"   ✅ Policy ID: {result['policy_id']}")
                print(f"   ✅ Clauses Processed: {result['clauses_processed']}/{result['total_clauses']}")
                print(f"   ✅ Search Upload: {result['search_upload']['uploaded_count']} documents")
                
                # Database persistence info
                db_info = result.get('database_storage', {})
                if db_info.get('file_id'):
                    print(f"   💾 Database File ID: {db_info['file_id']}")
                
                results.append({
                    "filename": policy_file.name,
                    "status": "success",
                    "policy_id": result['policy_id'],
                    "clauses_processed": result['clauses_processed'],
                    "total_clauses": result['total_clauses'],
                    "search_uploaded": result['search_upload']['uploaded_count']
                })
                successful_uploads += 1
                
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                print(f"   ❌ Error: {response.text[:200]}...")
                results.append({
                    "filename": policy_file.name,
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text[:100]}"
                })
        
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            results.append({
                "filename": policy_file.name,
                "status": "error",
                "error": str(e)
            })
    
    # Summary report
    print(f"\n" + "=" * 60)
    print(f"📊 BATCH PROCESSING SUMMARY")
    print(f"=" * 60)
    print(f"📁 Total Files: {len(policy_files)}")
    print(f"✅ Successfully Processed: {successful_uploads}")
    print(f"❌ Failed: {len(policy_files) - successful_uploads}")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for result in results:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} {result['filename']}")
        
        if result['status'] == 'success':
            print(f"     Policy ID: {result['policy_id']}")
            print(f"     Clauses: {result['clauses_processed']}/{result['total_clauses']}")
            print(f"     Uploaded: {result['search_uploaded']} documents")
        else:
            print(f"     Error: {result.get('error', 'Unknown error')}")
    
    # Test search functionality
    if successful_uploads > 0:
        print(f"\n🔍 TESTING POLICY SEARCH...")
        try:
            search_response = requests.get(f"{base_url}/api/search/policies?q=*&limit=20")
            if search_response.status_code == 200:
                search_data = search_response.json()
                print(f"✅ Total Policies in Index: {search_data['total_policies']}")
                print(f"✅ Policies Found: {len(search_data['policies'])}")
                
                # Show some examples
                print(f"\n📋 Sample Policy Titles:")
                for policy in search_data['policies'][:5]:
                    print(f"   - {policy['title']} (Severity: {policy['severity']})")
            else:
                print(f"❌ Search test failed: {search_response.status_code}")
        except Exception as e:
            print(f"❌ Search test error: {e}")
    
    print(f"\n🎉 BATCH PROCESSING COMPLETED!")
    return results

if __name__ == "__main__":
    try:
        results = process_policy_documents()
    except Exception as e:
        print(f"💥 Batch processing failed: {e}")
        import traceback
        traceback.print_exc()