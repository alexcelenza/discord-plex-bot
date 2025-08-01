#!/usr/bin/env python3
"""
Test runner for Discord Plex Bot
Run this script to execute all tests locally
"""

import sys
import os
import subprocess
import unittest

def run_tests():
    """Run all tests"""
    print("🧪 Running Discord Plex Bot Tests")
    print("=" * 50)
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_linting():
    """Run basic linting checks"""
    print("\n🔍 Running Linting Checks")
    print("=" * 50)
    
    # Check for syntax errors
    try:
        subprocess.run([sys.executable, '-m', 'compileall', '.'], 
                      check=True, capture_output=True)
        print("✓ Syntax check passed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Syntax check failed: {e}")
        return False
    
    # Check imports
    try:
        subprocess.run([sys.executable, '-c', '''
import ast
import os

def check_imports(file_path):
    with open(file_path, "r") as f:
        tree = ast.parse(f.read())
    
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    
    return imports

# Check main files
files_to_check = ["bot.py", "plex_utils.py", "config.py"]
for file in files_to_check:
    if os.path.exists(file):
        imports = check_imports(file)
        print(f"{file} imports: {imports}")
'''], check=True)
        print("✓ Import analysis completed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Import analysis failed: {e}")
        return False
    
    return True

def run_security_checks():
    """Run security checks"""
    print("\n🔒 Running Security Checks")
    print("=" * 50)
    
    # Check for hardcoded secrets
    try:
        result = subprocess.run(['grep', '-r', 'sk-', '.', '--exclude-dir=.git', '--exclude-dir=__pycache__'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✗ Potential hardcoded secrets found:")
            print(result.stdout)
            return False
        else:
            print("✓ No hardcoded secrets found")
    except FileNotFoundError:
        print("⚠️  grep not available, skipping secret check")
    
    # Check for hardcoded tokens
    try:
        result = subprocess.run(['grep', '-r', 'token.*=', '.', '--exclude-dir=.git', '--exclude-dir=__pycache__', '--exclude-dir=tests'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✗ Potential hardcoded tokens found:")
            print(result.stdout)
            return False
        else:
            print("✓ No hardcoded tokens found")
    except FileNotFoundError:
        print("⚠️  grep not available, skipping token check")
    
    return True

def main():
    """Main test runner"""
    print("🚀 Starting Discord Plex Bot Test Suite")
    print("=" * 50)
    
    # Run linting
    linting_passed = run_linting()
    
    # Run security checks
    security_passed = run_security_checks()
    
    # Run unit tests
    tests_passed = run_tests()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"Linting: {'✓ PASSED' if linting_passed else '✗ FAILED'}")
    print(f"Security: {'✓ PASSED' if security_passed else '✗ FAILED'}")
    print(f"Unit Tests: {'✓ PASSED' if tests_passed else '✗ FAILED'}")
    
    overall_success = linting_passed and security_passed and tests_passed
    
    if overall_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 