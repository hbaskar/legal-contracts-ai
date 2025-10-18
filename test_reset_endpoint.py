"""
Test script for the Database Reset endpoint
Validates the safety and functionality of the reset functionality
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResetEndpointTester:
    def __init__(self, base_url="http://localhost:7071"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-User-ID": "test-user"
        }
        
    def test_safety_check(self):
        """Test that reset fails without proper confirmation"""
        logger.info("Testing safety check - should fail without confirmation")
        
        url = f"{self.base_url}/api/database/reset"
        payload = {"confirm": "no"}
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            logger.info(f"Safety check response: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                logger.info(f"✅ Safety check passed: {data.get('message', 'No message')}")
                return True
            else:
                logger.error(f"❌ Safety check failed: Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Safety check error: {e}")
            return False
    
    def test_url_parameter_method(self):
        """Test reset using URL parameters"""
        logger.info("Testing URL parameter reset method")
        
        url = f"{self.base_url}/api/database/reset?confirm=yes"
        
        try:
            response = requests.delete(url, headers=self.headers)
            logger.info(f"URL parameter reset response: {response.status_code}")
            
            if response.status_code in [200, 207]:
                data = response.json()
                logger.info(f"✅ URL parameter reset successful")
                logger.info(f"Tables reset: {data.get('tables_reset', [])}")
                logger.info(f"Records deleted: {data.get('total_records_deleted', 0)}")
                return True
            else:
                logger.error(f"❌ URL parameter reset failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ URL parameter reset error: {e}")
            return False
    
    def test_json_body_method(self):
        """Test reset using JSON body"""
        logger.info("Testing JSON body reset method")
        
        url = f"{self.base_url}/api/database/reset"
        payload = {"confirm": "yes", "force": False}
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            logger.info(f"JSON body reset response: {response.status_code}")
            
            if response.status_code in [200, 207]:
                data = response.json()
                logger.info(f"✅ JSON body reset successful")
                logger.info(f"Environment: {data.get('environment', 'unknown')}")
                logger.info(f"Summary: {data.get('summary', {})}")
                return True
            else:
                logger.error(f"❌ JSON body reset failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ JSON body reset error: {e}")
            return False
    
    def test_health_check_after_reset(self):
        """Verify system health after reset"""
        logger.info("Testing health check after reset")
        
        url = f"{self.base_url}/api/health"
        
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Health check passed after reset")
                logger.info(f"Database status: {data.get('database', {}).get('status', 'unknown')}")
                return True
            else:
                logger.error(f"❌ Health check failed after reset: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return False
    
    def run_all_tests(self):
        """Run comprehensive reset endpoint tests"""
        logger.info("🧪 Starting Reset Endpoint Tests")
        logger.info("=" * 50)
        
        results = {}
        
        # Test 1: Safety check
        results['safety_check'] = self.test_safety_check()
        time.sleep(1)
        
        # Test 2: URL parameter method
        results['url_parameter'] = self.test_url_parameter_method()
        time.sleep(1)
        
        # Test 3: Health check after reset
        results['health_after_reset'] = self.test_health_check_after_reset()
        time.sleep(1)
        
        # Test 4: JSON body method
        results['json_body'] = self.test_json_body_method()
        time.sleep(1)
        
        # Test 5: Final health check
        results['final_health'] = self.test_health_check_after_reset()
        
        # Summary
        logger.info("=" * 50)
        logger.info("🔍 Test Results Summary:")
        passed = sum(results.values())
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✅ PASS" if passed_test else "❌ FAIL"
            logger.info(f"  {test_name}: {status}")
        
        logger.info(f"\n📊 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All reset endpoint tests PASSED!")
        else:
            logger.warning(f"⚠️  {total - passed} test(s) FAILED")
        
        return results

def main():
    """Main test execution"""
    print("🔄 Fresh Start Document Processing - Reset Endpoint Tests")
    print("=" * 60)
    
    # Allow user to specify different base URL
    import sys
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7071"
    
    print(f"Testing against: {base_url}")
    print("⚠️  WARNING: This will reset database tables!")
    
    # Confirm before proceeding
    confirm = input("\nProceed with reset tests? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Tests cancelled by user")
        return
    
    # Run tests
    tester = ResetEndpointTester(base_url)
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if all(results.values()):
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()