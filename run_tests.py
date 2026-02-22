"""
Test Runner - Validates locally first, then runs on BrowserStack
"""

import subprocess
import sys
import os
from dotenv import load_dotenv

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(title.center(80))
    print("="*80 + "\n")

def check_credentials():
    """Check if BrowserStack credentials are configured"""
    load_dotenv('.env.browserstack')
    username = os.getenv('BROWSERSTACK_USERNAME')
    access_key = os.getenv('BROWSERSTACK_ACCESS_KEY')
    
    if not username or not access_key or 'your_' in username:
        print(" BrowserStack credentials not configured properly!")
        print("Please update .env.browserstack with your actual credentials")
        return False
    
    print(f"✓ BrowserStack Username: {username}")
    print(f"✓ BrowserStack Access Key: {'*' * len(access_key)}")
    return True

def run_local_test():
    """Run the scraper locally to validate functionality"""
    print_header("STEP 1: LOCAL VALIDATION")
    
    print("Running local scraper to validate functionality...")
    print("This will scrape 5 articles locally using your Chrome browser.\n")
    
    try:
        # Run local scraper with reduced article count
        result = subprocess.run(
            [sys.executable, "opinion_scraper.py"],
            capture_output=False,
            text=True,
            timeout=300  # 5 minutes timeout for local test
        )
        
        if result.returncode == 0:
            print("\n Local validation PASSED")
            return True
        else:
            print("\n Local validation FAILED")
            return False
    
    except subprocess.TimeoutExpired:
        print("\n Local test timed out (exceeded 5 minutes)")
        return False
    except Exception as e:
        print(f"\n Error running local test: {e}")
        return False

def run_browserstack_test():
    """Run the scraper on BrowserStack with 5 parallel threads"""
    print_header("STEP 2: BROWSERSTACK PARALLEL EXECUTION")
    
    print("Running scraper on BrowserStack with 5 parallel threads...")
    print("Testing on: Chrome (Win), Firefox (Win), Edge (Win), iPhone 14, Samsung S23\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "opinion_scraper_browserstack.py"],
            capture_output=False,
            text=True,
            timeout=600  # 10 minutes timeout for BrowserStack
        )
        
        if result.returncode == 0:
            print("\n BrowserStack execution PASSED")
            return True
        else:
            print("\n BrowserStack execution encountered issues")
            return False
    
    except subprocess.TimeoutExpired:
        print("\n BrowserStack test timed out")
        return False
    except Exception as e:
        print(f"\n Error running BrowserStack test: {e}")
        return False

def main():
    """Main test runner"""
    print_header("EL PAÍS SCRAPER - CROSS-BROWSER TEST RUNNER")
    
    print("This script will:")
    print("  1. Validate locally on your machine")
    print("  2. Run on BrowserStack with 5 parallel threads")
    print("  3. Generate comprehensive test reports\n")
    
    # Check credentials
    if not check_credentials():
        sys.exit(1)
    
    # Ask user for confirmation
    response = input("\nDo you want to run the full test suite? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\nTest cancelled by user.")
        sys.exit(0)
    
    # Run local validation
    local_success = run_local_test()
    
    if not local_success:
        print("\n Local validation failed. Do you still want to proceed with BrowserStack?")
        response = input("Continue? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("\nTest suite aborted.")
            sys.exit(1)
    
    # Run BrowserStack tests
    browserstack_success = run_browserstack_test()
    
    # Final summary
    print_header("FINAL SUMMARY")
    
    print("Test Results:")
    print(f"  Local Validation: {'✓ PASSED' if local_success else '✗ FAILED'}")
    print(f"  BrowserStack Test: {'✓ PASSED' if browserstack_success else '✗ FAILED'}")
    
    print("\nOutput Files:")
    print("  Local: output/ and output_translated/")
    print("  BrowserStack: output_browserstack/")
    
    print("\nBrowserStack Dashboard:")
    print("  https://automate.browserstack.com/dashboard")
    
    print("\n" + "="*80)
    
    if local_success and browserstack_success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
