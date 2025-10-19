"""
Simple test document to process and populate the database
"""

# Create base64 encoded test content
import base64

test_content = """EMPLOYEE HANDBOOK

SECTION 1: INTRODUCTION
This handbook provides important information about our company policies and procedures.

SECTION 2: WORK HOURS  
Regular work hours are Monday through Friday, 9 AM to 5 PM.

SECTION 3: BENEFITS
We offer health insurance, dental coverage, and retirement plans."""

# Encode to base64
encoded_content = base64.b64encode(test_content.encode('utf-8')).decode('utf-8')
print("Base64 encoded content:")
print(encoded_content)