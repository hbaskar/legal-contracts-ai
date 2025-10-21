#!/usr/bin/env python3
"""
Validate Postman collection JSON format and structure
"""

import json
import sys
from pathlib import Path

def validate_postman_collection():
    """Validate the Postman collection JSON"""
    try:
        collection_path = Path(__file__).parent.parent / "postman" / "Fresh_Start_Document_Processing_v2.postman_collection.json"
        
        # Load and validate JSON
        with open(collection_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✅ Postman collection JSON is valid")
        print(f"📊 Collection contains {len(data['item'])} main sections:")
        
        # List all main sections
        for i, section in enumerate(data['item'], 1):
            section_name = section.get('name', 'Unknown')
            item_count = len(section.get('item', []))
            print(f"   {i}. {section_name} ({item_count} requests)")
        
        # Find and validate admin operations
        admin_section = None
        for section in data['item']:
            if section.get('name') == 'Admin Operations':
                admin_section = section
                break
        
        if admin_section:
            print(f"\n🔧 Admin Operations section found with {len(admin_section['item'])} requests:")
            for item in admin_section['item']:
                request_name = item.get('name', 'Unknown')
                method = item.get('request', {}).get('method', 'Unknown')
                print(f"   - {request_name} ({method})")
        else:
            print("\n❌ Admin Operations section not found")
            return False
        
        # Check for reset endpoints
        reset_endpoints = [item for item in admin_section['item'] if 'reset' in item.get('name', '').lower()]
        print(f"\n🗑️ Found {len(reset_endpoints)} reset endpoints:")
        for endpoint in reset_endpoints:
            print(f"   - {endpoint.get('name')}")
        
        print(f"\n✅ Validation complete - Collection structure looks good!")
        return True
        
    except FileNotFoundError:
        print("❌ Postman collection file not found")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

if __name__ == "__main__":
    success = validate_postman_collection()
    sys.exit(0 if success else 1)