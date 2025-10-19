#!/usr/bin/env python3
"""
Environment Variable Logging Test Script
Run this script to see all environment variables loaded by the application
"""

import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Main function to test environment variable logging"""
    print("🔍 Testing Environment Variable Logging")
    print("=" * 50)
    
    try:
        # Import config which will trigger automatic logging
        from config.config import Config, log_environment_variables, log_config_summary
        
        print("\n📊 Manual Environment Variables Log:")
        log_environment_variables()
        
        print("\n📋 Configuration Summary:")
        log_config_summary()
        
        print("\n✅ Environment variable logging test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())