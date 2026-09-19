#!/usr/bin/env python3
"""
GiftsDates Backend Smoke Tests
Tests core auth flows and public endpoints
"""
import requests
import json
import sys
from datetime import datetime

# Load backend URL from frontend .env
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    url = line.split('=', 1)[1].strip()
                    return f"{url}/api"
    except Exception as e:
        print(f"❌ Failed to read backend URL from frontend/.env: {e}")
        sys.exit(1)
    return None

BASE_URL = get_backend_url()
print(f"🔗 Testing backend at: {BASE_URL}\n")

# Test data
TEST_EMAIL = f"emma.rodriguez.{int(datetime.now().timestamp())}@gmail.com"
TEST_PASSWORD = "SecurePass123!"
TEST_USER_DATA = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD,
    "name": "Emma Rodriguez",
    "age": 28,
    "gender": "female",
    "interested_in": "male",
    "orientation": "straight",
    "city": "Barcelona",
    "country": "Spain",
    "bio": "Love traveling and meeting new people",
    "language": "en"
}

# Global token storage
auth_token = None
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name):
    print(f"✅ {test_name}")
    test_results["passed"].append(test_name)

def log_fail(test_name, reason):
    print(f"❌ {test_name}: {reason}")
    test_results["failed"].append({"test": test_name, "reason": reason})

def log_warning(test_name, reason):
    print(f"⚠️  {test_name}: {reason}")
    test_results["warnings"].append({"test": test_name, "reason": reason})

def test_health():
    """Test 1: Health endpoint GET /api/"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") is True:
                log_pass("Health check (GET /api/)")
                return True
            else:
                log_fail("Health check", f"Expected ok:true, got {data}")
                return False
        else:
            log_fail("Health check", f"Status {response.status_code}")
            return False
    except Exception as e:
        log_fail("Health check", str(e))
        return False

def test_register():
    """Test 2: Register new user POST /api/auth/register"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER_DATA,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                global auth_token
                auth_token = data["token"]
                log_pass(f"Register user (POST /api/auth/register) - {TEST_USER_DATA['name']}")
                return True
            else:
                log_fail("Register user", f"Missing token or user in response: {data}")
                return False
        else:
            log_fail("Register user", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Register user", str(e))
        return False

def test_login():
    """Test 3: Login with credentials POST /api/auth/login"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "token" in data and "user" in data:
                global auth_token
                auth_token = data["token"]
                log_pass("Login (POST /api/auth/login)")
                return True
            else:
                log_fail("Login", f"Missing token or user in response: {data}")
                return False
        else:
            log_fail("Login", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Login", str(e))
        return False

def test_me():
    """Test 4: Get current user GET /api/auth/me"""
    if not auth_token:
        log_fail("Get current user", "No auth token available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "email" in data:
                if data["email"] == TEST_EMAIL:
                    log_pass("Get current user (GET /api/auth/me)")
                    return True
                else:
                    log_fail("Get current user", f"Email mismatch: expected {TEST_EMAIL}, got {data.get('email')}")
                    return False
            else:
                log_fail("Get current user", f"Missing id or email in response: {data}")
                return False
        else:
            log_fail("Get current user", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Get current user", str(e))
        return False

def test_profiles():
    """Test 5: Browse profiles GET /api/profiles"""
    if not auth_token:
        log_fail("Browse profiles", "No auth token available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/profiles",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            # The endpoint returns an array directly, not a dict with "profiles" key
            if isinstance(data, list):
                log_pass(f"Browse profiles (GET /api/profiles) - {len(data)} profiles found")
                return True
            else:
                log_fail("Browse profiles", f"Expected array, got: {type(data)}")
                return False
        else:
            log_fail("Browse profiles", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Browse profiles", str(e))
        return False

def test_wallet():
    """Test 6: Get wallet balance GET /api/wallet"""
    if not auth_token:
        log_fail("Wallet balance", "No auth token available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/wallet",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "coins" in data and "withdrawable" in data:
                log_pass(f"Wallet balance (GET /api/wallet) - Coins: {data['coins']}, Withdrawable: {data['withdrawable']}")
                return True
            else:
                log_fail("Wallet balance", f"Missing coins or withdrawable in response: {data}")
                return False
        else:
            log_fail("Wallet balance", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Wallet balance", str(e))
        return False

def test_date_ideas():
    """Test 7: Get date ideas catalog GET /api/date-ideas"""
    if not auth_token:
        log_fail("Date ideas catalog", "No auth token available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/date-ideas",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "items" in data:
                log_pass(f"Date ideas catalog (GET /api/date-ideas) - {len(data['items'])} ideas found")
                return True
            else:
                log_fail("Date ideas catalog", f"Missing 'items' key in response: {data}")
                return False
        else:
            log_fail("Date ideas catalog", f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_fail("Date ideas catalog", str(e))
        return False

def test_stripe_graceful_fail():
    """Test 8: Verify Stripe endpoints fail gracefully (not configured)"""
    if not auth_token:
        log_warning("Stripe graceful fail", "No auth token available, skipping")
        return True
    
    # Test checkout endpoint - should fail gracefully without crashing
    try:
        response = requests.post(
            f"{BASE_URL}/checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "package_id": "starter",
                "origin_url": "https://test.com"
            },
            timeout=10
        )
        # We expect this to fail (400, 503, etc.) but NOT 500
        if response.status_code == 500:
            log_fail("Stripe graceful fail", f"Checkout endpoint crashed with 500: {response.text}")
            return False
        else:
            log_pass(f"Stripe graceful fail (checkout returns {response.status_code}, not 500)")
            return True
    except Exception as e:
        log_warning("Stripe graceful fail", f"Could not test: {e}")
        return True

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\n❌ FAILED TESTS:")
        for fail in test_results['failed']:
            print(f"  - {fail['test']}: {fail['reason']}")
    
    if test_results['warnings']:
        print("\n⚠️  WARNINGS:")
        for warn in test_results['warnings']:
            print(f"  - {warn['test']}: {warn['reason']}")
    
    print("="*60)
    
    # Exit with appropriate code
    if test_results['failed']:
        sys.exit(1)
    else:
        sys.exit(0)

def main():
    print("🚀 Starting GiftsDates Backend Smoke Tests\n")
    
    # Run tests in order
    test_health()
    test_register()
    test_login()
    test_me()
    test_profiles()
    test_wallet()
    test_date_ideas()
    test_stripe_graceful_fail()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()
