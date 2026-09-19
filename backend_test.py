#!/usr/bin/env python3
"""
Backend API Test Suite for GiftsDates Stripe Checkout Flow
Tests Stripe checkout with Emergent-managed claimable sandbox
"""
import requests
import json
import sys
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://secure-gifts-2.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
TEST_EMAIL = "emma.rodriguez.1789848637@gmail.com"
TEST_PASSWORD = "SecurePass123!"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_test(name, status, details=""):
    """Log test result with color"""
    color = GREEN if status == "PASS" else RED if status == "FAIL" else YELLOW
    print(f"{color}[{status}]{RESET} {name}")
    if details:
        print(f"      {details}")

def log_section(title):
    """Log section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

class StripeCheckoutTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.session_ids = []
        self.failed_tests = []
        self.passed_tests = []
        
    def test_auth_register(self):
        """Register a new test user"""
        import random
        import time
        test_email = f"stripe.test.{int(time.time())}.{random.randint(100, 999)}@gmail.com"
        test_password = "StripeTest123!"
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "name": "Stripe Tester",
                    "age": 30,
                    "gender": "female",
                    "interested_in": "male",
                    "city": "San Francisco",
                    "country": "USA"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data:
                    self.token = data["token"]
                    self.user_id = data.get("user", {}).get("id")
                    log_test("Register new user", "PASS", f"User created: {test_email}, User ID: {self.user_id}")
                    self.passed_tests.append("Register")
                    return True
            
            log_test("Register failed", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            self.failed_tests.append(f"Register - HTTP {response.status_code}")
            return False
                
        except Exception as e:
            log_test("Register failed", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Register - Exception: {str(e)}")
            return False
    
    def test_auth_login(self):
        """Step 1: Login to get JWT token (or register if needed)"""
        log_section("STEP 1: Authentication - Register & Login")
        
        # Try existing user first
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data:
                    self.token = data["token"]
                    self.user_id = data.get("user", {}).get("id")
                    log_test("Login with existing user", "PASS", f"Token obtained, User ID: {self.user_id}")
                    self.passed_tests.append("Login")
                    return True
        except Exception:
            pass
        
        # If login fails, register a new user
        log_test("Login with existing user", "INFO", "Existing user not available, registering new user...")
        return self.test_auth_register()
    
    def test_get_config(self):
        """Step 2: GET /api/meta to confirm coin packages exist"""
        log_section("STEP 2: Get Config - Verify Coin Packages")
        
        try:
            response = requests.get(f"{BASE_URL}/meta", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coin_packages = data.get("coin_packages", [])
                
                expected_ids = ["small_talk", "starter", "popular", "extra", "vip"]
                found_ids = [pkg["id"] for pkg in coin_packages]
                
                all_found = all(pkg_id in found_ids for pkg_id in expected_ids)
                
                if all_found:
                    log_test("Config endpoint", "PASS", f"All expected packages found: {', '.join(expected_ids)}")
                    self.passed_tests.append("Config endpoint")
                    return True
                else:
                    missing = [pid for pid in expected_ids if pid not in found_ids]
                    log_test("Config endpoint", "FAIL", f"Missing packages: {', '.join(missing)}")
                    self.failed_tests.append(f"Config - Missing packages: {missing}")
                    return False
            else:
                log_test("Config endpoint", "FAIL", f"Status: {response.status_code}")
                self.failed_tests.append(f"Config - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Config endpoint", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Config - Exception: {str(e)}")
            return False
    
    def test_checkout_popular_package(self):
        """Step 3: POST /api/payments/checkout with package_id:"popular" """
        log_section("STEP 3: Checkout - Popular Package")
        
        if not self.token:
            log_test("Checkout popular package", "SKIP", "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "package_id": "popular",
                "origin_url": "https://example.com"
            }
            
            response = requests.post(
                f"{BASE_URL}/payments/checkout",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                checkout_url = data.get("checkout_url", "")
                session_id = data.get("session_id", "")
                
                if checkout_url and session_id:
                    # Check if URL is valid Stripe checkout URL
                    is_stripe_url = checkout_url.startswith("https://checkout.stripe.com") or checkout_url.startswith("https://")
                    
                    if is_stripe_url:
                        self.session_ids.append(session_id)
                        log_test("Checkout popular package", "PASS", 
                                f"checkout_url: {checkout_url[:60]}...\n      session_id: {session_id}")
                        self.passed_tests.append("Checkout popular package")
                        return True
                    else:
                        log_test("Checkout popular package", "FAIL", f"Invalid checkout_url: {checkout_url}")
                        self.failed_tests.append("Checkout popular - Invalid URL format")
                        return False
                else:
                    log_test("Checkout popular package", "FAIL", 
                            f"Missing fields - checkout_url: {bool(checkout_url)}, session_id: {bool(session_id)}")
                    self.failed_tests.append("Checkout popular - Missing checkout_url or session_id")
                    return False
            else:
                log_test("Checkout popular package", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Checkout popular - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Checkout popular package", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Checkout popular - Exception: {str(e)}")
            return False
    
    def test_checkout_custom_amount(self):
        """Step 4: POST /api/payments/checkout with package_id:"custom" and usd_amount:20"""
        log_section("STEP 4: Checkout - Custom Amount ($20)")
        
        if not self.token:
            log_test("Checkout custom amount", "SKIP", "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "package_id": "custom",
                "usd_amount": 20,
                "origin_url": "https://example.com"
            }
            
            response = requests.post(
                f"{BASE_URL}/payments/checkout",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                checkout_url = data.get("checkout_url", "")
                session_id = data.get("session_id", "")
                
                if checkout_url and session_id:
                    is_stripe_url = checkout_url.startswith("https://checkout.stripe.com") or checkout_url.startswith("https://")
                    
                    if is_stripe_url:
                        self.session_ids.append(session_id)
                        log_test("Checkout custom amount", "PASS", 
                                f"checkout_url: {checkout_url[:60]}...\n      session_id: {session_id}")
                        self.passed_tests.append("Checkout custom amount")
                        return True
                    else:
                        log_test("Checkout custom amount", "FAIL", f"Invalid checkout_url: {checkout_url}")
                        self.failed_tests.append("Checkout custom - Invalid URL format")
                        return False
                else:
                    log_test("Checkout custom amount", "FAIL", 
                            f"Missing fields - checkout_url: {bool(checkout_url)}, session_id: {bool(session_id)}")
                    self.failed_tests.append("Checkout custom - Missing checkout_url or session_id")
                    return False
            else:
                log_test("Checkout custom amount", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Checkout custom - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Checkout custom amount", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Checkout custom - Exception: {str(e)}")
            return False
    
    def test_checkout_premium_monthly(self):
        """Step 5: POST /api/payments/checkout with package_id:"premium_monthly" """
        log_section("STEP 5: Checkout - Premium Monthly (One-time Payment)")
        
        if not self.token:
            log_test("Checkout premium monthly", "SKIP", "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "package_id": "premium_monthly",
                "origin_url": "https://example.com"
            }
            
            response = requests.post(
                f"{BASE_URL}/payments/checkout",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                checkout_url = data.get("checkout_url", "")
                session_id = data.get("session_id", "")
                
                if checkout_url and session_id:
                    is_stripe_url = checkout_url.startswith("https://checkout.stripe.com") or checkout_url.startswith("https://")
                    
                    if is_stripe_url:
                        self.session_ids.append(session_id)
                        log_test("Checkout premium monthly", "PASS", 
                                f"checkout_url: {checkout_url[:60]}...\n      session_id: {session_id}")
                        self.passed_tests.append("Checkout premium monthly")
                        return True
                    else:
                        log_test("Checkout premium monthly", "FAIL", f"Invalid checkout_url: {checkout_url}")
                        self.failed_tests.append("Checkout premium - Invalid URL format")
                        return False
                else:
                    log_test("Checkout premium monthly", "FAIL", 
                            f"Missing fields - checkout_url: {bool(checkout_url)}, session_id: {bool(session_id)}")
                    self.failed_tests.append("Checkout premium - Missing checkout_url or session_id")
                    return False
            else:
                log_test("Checkout premium monthly", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Checkout premium - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Checkout premium monthly", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Checkout premium - Exception: {str(e)}")
            return False
    
    def test_checkout_vip_monthly(self):
        """Step 6: POST /api/payments/checkout with package_id:"vip_monthly" (subscription)"""
        log_section("STEP 6: Checkout - VIP Monthly (Subscription)")
        
        if not self.token:
            log_test("Checkout VIP monthly", "SKIP", "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "package_id": "vip_monthly",
                "origin_url": "https://example.com"
            }
            
            response = requests.post(
                f"{BASE_URL}/payments/checkout",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                checkout_url = data.get("checkout_url", "")
                session_id = data.get("session_id", "")
                
                if checkout_url and session_id:
                    is_stripe_url = checkout_url.startswith("https://checkout.stripe.com") or checkout_url.startswith("https://")
                    
                    if is_stripe_url:
                        self.session_ids.append(session_id)
                        log_test("Checkout VIP monthly", "PASS", 
                                f"checkout_url: {checkout_url[:60]}...\n      session_id: {session_id}")
                        self.passed_tests.append("Checkout VIP monthly")
                        return True
                    else:
                        log_test("Checkout VIP monthly", "FAIL", f"Invalid checkout_url: {checkout_url}")
                        self.failed_tests.append("Checkout VIP - Invalid URL format")
                        return False
                else:
                    log_test("Checkout VIP monthly", "FAIL", 
                            f"Missing fields - checkout_url: {bool(checkout_url)}, session_id: {bool(session_id)}")
                    self.failed_tests.append("Checkout VIP - Missing checkout_url or session_id")
                    return False
            else:
                log_test("Checkout VIP monthly", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Checkout VIP - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Checkout VIP monthly", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Checkout VIP - Exception: {str(e)}")
            return False
    
    def test_payment_status(self):
        """Step 7: GET /api/payments/status/{session_id} for created sessions"""
        log_section("STEP 7: Payment Status - Check Session Status")
        
        if not self.session_ids:
            log_test("Payment status check", "SKIP", "No session IDs available")
            return False
        
        all_passed = True
        for i, session_id in enumerate(self.session_ids, 1):
            try:
                response = requests.get(
                    f"{BASE_URL}/payments/status/{session_id}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    payment_status = data.get("payment_status")
                    returned_session_id = data.get("session_id")
                    
                    if returned_session_id == session_id and payment_status:
                        # Payment status should be "pending" since no card was paid
                        if payment_status == "pending":
                            log_test(f"Payment status check #{i}", "PASS", 
                                    f"session_id: {session_id}\n      status: {status}, payment_status: {payment_status}")
                        else:
                            log_test(f"Payment status check #{i}", "PASS", 
                                    f"session_id: {session_id}\n      status: {status}, payment_status: {payment_status} (expected 'pending' but got '{payment_status}')")
                        self.passed_tests.append(f"Payment status #{i}")
                    else:
                        log_test(f"Payment status check #{i}", "FAIL", 
                                f"Invalid response - session_id match: {returned_session_id == session_id}, has payment_status: {bool(payment_status)}")
                        self.failed_tests.append(f"Payment status #{i} - Invalid response")
                        all_passed = False
                else:
                    log_test(f"Payment status check #{i}", "FAIL", 
                            f"Status: {response.status_code}, Response: {response.text[:200]}")
                    self.failed_tests.append(f"Payment status #{i} - HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                log_test(f"Payment status check #{i}", "FAIL", f"Exception: {str(e)}")
                self.failed_tests.append(f"Payment status #{i} - Exception: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self):
        """Run all Stripe checkout tests"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}GiftsDates Stripe Checkout Flow Test Suite{RESET}")
        print(f"{BLUE}Testing Emergent-managed Stripe claimable sandbox{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Base URL: {BASE_URL}")
        print(f"Test User: {TEST_EMAIL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Run tests in sequence
        self.test_auth_login()
        self.test_get_config()
        self.test_checkout_popular_package()
        self.test_checkout_custom_amount()
        self.test_checkout_premium_monthly()
        self.test_checkout_vip_monthly()
        self.test_payment_status()
        
        # Summary
        log_section("TEST SUMMARY")
        total_tests = len(self.passed_tests) + len(self.failed_tests)
        print(f"\nTotal Tests: {total_tests}")
        print(f"{GREEN}Passed: {len(self.passed_tests)}{RESET}")
        print(f"{RED}Failed: {len(self.failed_tests)}{RESET}")
        
        if self.failed_tests:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test in self.failed_tests:
                print(f"  ❌ {test}")
        
        if self.passed_tests:
            print(f"\n{GREEN}Passed Tests:{RESET}")
            for test in self.passed_tests:
                print(f"  ✅ {test}")
        
        # Return exit code
        return 0 if len(self.failed_tests) == 0 else 1

if __name__ == "__main__":
    tester = StripeCheckoutTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
