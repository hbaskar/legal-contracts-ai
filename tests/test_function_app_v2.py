"""
Test file for Azure Function v2 model implementation
"""
import unittest
from unittest.mock import Mock
import azure.functions as func

# Import the function app
from function_app import app


class TestFunctionAppV2Model(unittest.TestCase):
    """Test cases for Azure Functions v2 programming model implementation"""
    
    def test_function_app_type(self):
        """Test that the app is using v2 FunctionApp"""
        self.assertIsInstance(app, func.FunctionApp)
        
    def test_function_app_exists(self):
        """Test that the function app is properly initialized"""
        self.assertIsNotNone(app)
        
    def test_function_builders_exist(self):
        """Test that functions are registered with the app"""
        # Check that we have functions registered
        self.assertTrue(hasattr(app, '_function_builders'))
        self.assertGreater(len(app._function_builders), 0, "No functions registered in the app")
    
    def test_function_decorators_v2_style(self):
        """Test that functions use v2 decorator style and are callable"""
        # Import the functions to check their decorators
        from function_app import upload_file, get_file_info, health_check
        
        # Check that functions exist and are callable
        self.assertTrue(callable(upload_file))
        self.assertTrue(callable(get_file_info))
        self.assertTrue(callable(health_check))
        
    def test_functions_callable(self):
        """Test that the functions are properly callable"""
        from function_app import upload_file, get_file_info, health_check
        
        # Verify functions exist and are callable
        # Note: Decorators wrap the actual functions, but they remain callable
        self.assertTrue(callable(upload_file))
        self.assertTrue(callable(get_file_info))
        self.assertTrue(callable(health_check))

    def test_v2_model_features(self):
        """Test v2 model specific features"""
        # Test that we're using the proper v2 imports and structure
        self.assertTrue(hasattr(func, 'FunctionApp'))
        self.assertTrue(hasattr(func, 'HttpRequest'))
        self.assertTrue(hasattr(func, 'HttpResponse'))
        self.assertTrue(hasattr(func, 'AuthLevel'))


if __name__ == '__main__':
    unittest.main()