#!/usr/bin/env python3
"""
Test GET /api/invites/cancelled endpoint
Tests cancelled/refused dates with refund amounts for both inviter and recipient
"""
import requests
import json
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# Base URL from frontend/.env
BASE_URL = "https://secure-gifts-2.preview.emergentagent.com/api"

# MongoDB connection
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

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
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

class CancelledEndpointTester:
    def __init__(self):
        self.token_a = None
        self.token_b = None
        self.user_a_id = None
        self.user_b_id = None
        self.user_a_name = None
        self.user_b_name = None
        self.date_id_1 = None  # Transport refuse
        self.date_id_2 = None  # Recipient reject
        self.failed_tests = []
        self.passed_tests = []
        self.mongo_client = None
        self.db = None
        
    def connect_db(self):
        """Connect to MongoDB"""
        try:
            self.mongo_client = MongoClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            log_test("MongoDB connection", "PASS", f"Connected to {DB_NAME}")
            return True
        except Exception as e:
            log_test("MongoDB connection", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"MongoDB connection - {str(e)}")
            return False
    
    def register_user(self, email, password, name, gender="female"):
        """Register a new user"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "name": name,
                    "age": 28,
                    "gender": gender,
                    "interested_in": "male" if gender == "female" else "female",
                    "city": "Barcelona",
                    "country": "Spain"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("token"), data.get("user", {}).get("id")
            else:
                log_test(f"Register {name}", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
                return None, None
                
        except Exception as e:
            log_test(f"Register {name}", "FAIL", f"Exception: {str(e)}")
            return None, None
    
    def setup_users(self):
        """Step 1: Register inviter A and recipient B"""
        log_section("STEP 1: Setup Users - Register Inviter A and Recipient B")
        
        import time
        timestamp = int(time.time())
        
        # Register User A (inviter)
        email_a = f"inviter_a_{timestamp}@test.com"
        password_a = "InviterPass123!"
        self.user_a_name = "Alice Inviter"
        
        self.token_a, self.user_a_id = self.register_user(email_a, password_a, self.user_a_name, "female")
        
        if self.token_a and self.user_a_id:
            log_test("Register User A (inviter)", "PASS", f"Email: {email_a}, ID: {self.user_a_id}")
            self.passed_tests.append("Register User A")
        else:
            self.failed_tests.append("Register User A")
            return False
        
        # Register User B (recipient)
        email_b = f"recipient_b_{timestamp}@test.com"
        password_b = "RecipientPass123!"
        self.user_b_name = "Bob Recipient"
        
        self.token_b, self.user_b_id = self.register_user(email_b, password_b, self.user_b_name, "male")
        
        if self.token_b and self.user_b_id:
            log_test("Register User B (recipient)", "PASS", f"Email: {email_b}, ID: {self.user_b_id}")
            self.passed_tests.append("Register User B")
        else:
            self.failed_tests.append("Register User B")
            return False
        
        return True
    
    def grant_coins(self):
        """Step 2: Grant coins to User A via direct DB update"""
        log_section("STEP 2: Grant Coins - Direct DB Update for User A")
        
        try:
            # Grant 1000 coins to User A
            result = self.db.users.update_one(
                {"id": self.user_a_id},
                {"$set": {"coins": 1000}}
            )
            
            if result.modified_count > 0 or result.matched_count > 0:
                log_test("Grant coins to User A", "PASS", "Granted 1000 coins to User A")
                self.passed_tests.append("Grant coins")
                return True
            else:
                log_test("Grant coins to User A", "FAIL", "Failed to update user coins")
                self.failed_tests.append("Grant coins - DB update failed")
                return False
                
        except Exception as e:
            log_test("Grant coins to User A", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Grant coins - {str(e)}")
            return False
    
    def set_availability(self):
        """Step 3: Set User B's availability"""
        log_section("STEP 3: Set Availability - User B for tomorrow")
        
        try:
            # Calculate tomorrow's date
            tomorrow = datetime.now() + timedelta(days=1)
            date_str = tomorrow.strftime("%Y-%m-%d")
            
            headers = {"Authorization": f"Bearer {self.token_b}"}
            payload = {
                "availability": [date_str],
                "availability_time": {"from": "18:00", "to": "23:00"},
                "date_price": 150
            }
            
            response = requests.patch(
                f"{BASE_URL}/auth/me",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                log_test("Set User B availability", "PASS", 
                        f"Date: {date_str}, Time: 18:00-23:00, Price: 150 coins")
                self.passed_tests.append("Set availability")
                return True
            else:
                log_test("Set User B availability", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Set availability - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Set User B availability", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Set availability - {str(e)}")
            return False
    
    def create_date_transport_refuse(self):
        """Step 4: Create Date 1 - Transport refuse scenario (CANCELLED_TRANSPORTATION)"""
        log_section("STEP 4: Create Date 1 - Transport Refuse Scenario")
        
        # Calculate proposed start time (tomorrow at 19:00)
        tomorrow = datetime.now() + timedelta(days=1)
        proposed_start = tomorrow.replace(hour=19, minute=0, second=0, microsecond=0).isoformat() + "Z"
        proposed_end = tomorrow.replace(hour=22, minute=0, second=0, microsecond=0).isoformat() + "Z"
        
        # 4a. A invites B
        try:
            headers_a = {"Authorization": f"Bearer {self.token_a}"}
            invite_payload = {
                "recipient_id": self.user_b_id,
                "scheduled_start": proposed_start,
                "activity_option_1": "Romantic dinner at Italian restaurant",
                "activity_option_2": "Wine tasting at local vineyard",
                "activity_option_3": "Sunset walk along the beach",
                "coins": 250,
                "safety_ack": True
            }
            
            response = requests.post(
                f"{BASE_URL}/invites",
                json=invite_payload,
                headers=headers_a,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.date_id_1 = data.get("id")
                status = data.get("status")
                
                if self.date_id_1 and status == "INVITATION_SENT":
                    log_test("4a. A invites B", "PASS", 
                            f"Date ID: {self.date_id_1}, Status: {status}, Coins: 250")
                    self.passed_tests.append("Create invitation (Date 1)")
                else:
                    log_test("4a. A invites B", "FAIL", f"Invalid response: {data}")
                    self.failed_tests.append("Create invitation (Date 1) - Invalid response")
                    return False
            else:
                log_test("4a. A invites B", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Create invitation (Date 1) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("4a. A invites B", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Create invitation (Date 1) - {str(e)}")
            return False
        
        # 4b. B chooses activity
        try:
            headers_b = {"Authorization": f"Bearer {self.token_b}"}
            activity_payload = {
                "idea_id": "opt1"
            }
            
            response = requests.post(
                f"{BASE_URL}/invites/{self.date_id_1}/choose",
                json=activity_payload,
                headers=headers_b,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "DATE_ACTIVITY_SELECTED":
                    log_test("4b. B chooses activity", "PASS", f"Status: {status}")
                    self.passed_tests.append("B chooses activity (Date 1)")
                else:
                    log_test("4b. B chooses activity", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"B chooses activity (Date 1) - Wrong status: {status}")
                    return False
            else:
                log_test("4b. B chooses activity", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"B chooses activity (Date 1) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("4b. B chooses activity", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"B chooses activity (Date 1) - {str(e)}")
            return False
        
        # 4c. A posts location (venue only, no scheduled_start)
        try:
            location_payload = {
                "venue": "La Bella Vista Restaurant",
                "address": "Carrer de Mallorca, 123",
                "city": "Barcelona",
                "country": "Spain"
            }
            
            response = requests.post(
                f"{BASE_URL}/invites/{self.date_id_1}/location",
                json=location_payload,
                headers=headers_a,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "LOCATION_PROPOSED":
                    log_test("4c. A posts location", "PASS", f"Status: {status}")
                    self.passed_tests.append("A posts location (Date 1)")
                else:
                    log_test("4c. A posts location", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"A posts location (Date 1) - Wrong status: {status}")
                    return False
            else:
                log_test("4c. A posts location", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"A posts location (Date 1) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("4c. A posts location", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"A posts location (Date 1) - {str(e)}")
            return False
        
        # 4d. B requests taxi
        try:
            taxi_payload = {
                "amount": 30
            }
            
            response = requests.post(
                f"{BASE_URL}/invites/{self.date_id_1}/taxi/request",
                json=taxi_payload,
                headers=headers_b,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "TAXI_REQUESTED":
                    log_test("4d. B requests taxi", "PASS", f"Status: {status}, Amount: 30 coins")
                    self.passed_tests.append("B requests taxi (Date 1)")
                else:
                    log_test("4d. B requests taxi", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"B requests taxi (Date 1) - Wrong status: {status}")
                    return False
            else:
                log_test("4d. B requests taxi", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"B requests taxi (Date 1) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("4d. B requests taxi", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"B requests taxi (Date 1) - {str(e)}")
            return False
        
        # 4e. A refuses transport
        try:
            response = requests.post(
                f"{BASE_URL}/invites/{self.date_id_1}/transport/refuse",
                headers=headers_a,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "CANCELLED_TRANSPORTATION":
                    log_test("4e. A refuses transport", "PASS", 
                            f"Status: {status} (50/25/25 split applied)")
                    self.passed_tests.append("A refuses transport (Date 1)")
                    return True
                else:
                    log_test("4e. A refuses transport", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"A refuses transport (Date 1) - Wrong status: {status}")
                    return False
            else:
                log_test("4e. A refuses transport", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"A refuses transport (Date 1) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("4e. A refuses transport", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"A refuses transport (Date 1) - {str(e)}")
            return False
    
    def create_date_recipient_reject(self):
        """Step 5: Create Date 2 - Recipient reject scenario (CANCELLED)"""
        log_section("STEP 5: Create Date 2 - Recipient Reject Scenario")
        
        # Calculate proposed start time (tomorrow at 20:00)
        tomorrow = datetime.now() + timedelta(days=1)
        proposed_start = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0).isoformat() + "Z"
        proposed_end = tomorrow.replace(hour=23, minute=0, second=0, microsecond=0).isoformat() + "Z"
        
        # 5a. A invites B again
        try:
            headers_a = {"Authorization": f"Bearer {self.token_a}"}
            invite_payload = {
                "recipient_id": self.user_b_id,
                "scheduled_start": proposed_start,
                "activity_option_1": "Concert at music hall",
                "activity_option_2": "Art gallery exhibition",
                "activity_option_3": "Cooking class together",
                "coins": 200,
                "safety_ack": True
            }
            
            response = requests.post(
                f"{BASE_URL}/invites",
                json=invite_payload,
                headers=headers_a,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.date_id_2 = data.get("id")
                status = data.get("status")
                
                if self.date_id_2 and status == "INVITATION_SENT":
                    log_test("5a. A invites B (2nd time)", "PASS", 
                            f"Date ID: {self.date_id_2}, Status: {status}, Coins: 200")
                    self.passed_tests.append("Create invitation (Date 2)")
                else:
                    log_test("5a. A invites B (2nd time)", "FAIL", f"Invalid response: {data}")
                    self.failed_tests.append("Create invitation (Date 2) - Invalid response")
                    return False
            else:
                log_test("5a. A invites B (2nd time)", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Create invitation (Date 2) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("5a. A invites B (2nd time)", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Create invitation (Date 2) - {str(e)}")
            return False
        
        # 5b. B rejects the invitation
        try:
            headers_b = {"Authorization": f"Bearer {self.token_b}"}
            
            response = requests.post(
                f"{BASE_URL}/invites/{self.date_id_2}/cancel",
                headers=headers_b,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "CANCELLED":
                    log_test("5b. B rejects invitation", "PASS", 
                            f"Status: {status} (Full refund to A)")
                    self.passed_tests.append("B rejects invitation (Date 2)")
                    return True
                else:
                    log_test("5b. B rejects invitation", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"B rejects invitation (Date 2) - Wrong status: {status}")
                    return False
            else:
                log_test("5b. B rejects invitation", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"B rejects invitation (Date 2) - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("5b. B rejects invitation", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"B rejects invitation (Date 2) - {str(e)}")
            return False
    
    def verify_cancelled_endpoint_as_a(self):
        """Step 6: Verify GET /api/invites/cancelled as User A (inviter)"""
        log_section("STEP 6: Verify GET /api/invites/cancelled as User A (Inviter)")
        
        try:
            headers_a = {"Authorization": f"Bearer {self.token_a}"}
            
            response = requests.get(
                f"{BASE_URL}/invites/cancelled",
                headers=headers_a,
                timeout=10
            )
            
            if response.status_code != 200:
                log_test("GET /api/invites/cancelled (as A)", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"GET cancelled (as A) - HTTP {response.status_code}")
                return False
            
            data = response.json()
            items = data.get("items", [])
            total = data.get("total", 0)
            
            # Check total count
            if total < 2:
                log_test("GET /api/invites/cancelled (as A)", "FAIL", 
                        f"Expected total >= 2, got {total}")
                self.failed_tests.append(f"GET cancelled (as A) - Total count {total} < 2")
                return False
            
            # Find our two dates
            date_1 = None
            date_2 = None
            
            for item in items:
                if item.get("id") == self.date_id_1:
                    date_1 = item
                elif item.get("id") == self.date_id_2:
                    date_2 = item
            
            all_passed = True
            
            # Verify Date 1 (transport refuse)
            if not date_1:
                log_test("Date 1 in response (as A)", "FAIL", "Date 1 not found in cancelled list")
                self.failed_tests.append("Date 1 not in cancelled list (as A)")
                all_passed = False
            else:
                # Check role
                if date_1.get("role") != "inviter":
                    log_test("Date 1 role (as A)", "FAIL", f"Expected 'inviter', got '{date_1.get('role')}'")
                    self.failed_tests.append(f"Date 1 role (as A) - Wrong role")
                    all_passed = False
                else:
                    log_test("Date 1 role (as A)", "PASS", "role = 'inviter'")
                
                # Check other.name
                other_name = date_1.get("other", {}).get("name")
                if other_name != self.user_b_name:
                    log_test("Date 1 other.name (as A)", "FAIL", 
                            f"Expected '{self.user_b_name}', got '{other_name}'")
                    self.failed_tests.append(f"Date 1 other.name (as A) - Wrong name")
                    all_passed = False
                else:
                    log_test("Date 1 other.name (as A)", "PASS", f"other.name = '{other_name}'")
                
                # Check total_hold
                total_hold = date_1.get("total_hold")
                if total_hold != 250:
                    log_test("Date 1 total_hold (as A)", "FAIL", 
                            f"Expected 250, got {total_hold}")
                    self.failed_tests.append(f"Date 1 total_hold (as A) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 1 total_hold (as A)", "PASS", f"total_hold = {total_hold}")
                
                # Check refund_amount (should be 50% of 250 = 125)
                refund_amount = date_1.get("refund_amount")
                expected_refund = 125  # 50% of 250
                if refund_amount != expected_refund:
                    log_test("Date 1 refund_amount (as A)", "FAIL", 
                            f"Expected {expected_refund} (50% of 250), got {refund_amount}")
                    self.failed_tests.append(f"Date 1 refund_amount (as A) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 1 refund_amount (as A)", "PASS", 
                            f"refund_amount = {refund_amount} (50% of {total_hold})")
                
                # Check status
                status = date_1.get("status")
                if status != "CANCELLED_TRANSPORTATION":
                    log_test("Date 1 status (as A)", "FAIL", 
                            f"Expected 'CANCELLED_TRANSPORTATION', got '{status}'")
                    self.failed_tests.append(f"Date 1 status (as A) - Wrong status")
                    all_passed = False
                else:
                    log_test("Date 1 status (as A)", "PASS", f"status = '{status}'")
            
            # Verify Date 2 (recipient reject)
            if not date_2:
                log_test("Date 2 in response (as A)", "FAIL", "Date 2 not found in cancelled list")
                self.failed_tests.append("Date 2 not in cancelled list (as A)")
                all_passed = False
            else:
                # Check role
                if date_2.get("role") != "inviter":
                    log_test("Date 2 role (as A)", "FAIL", f"Expected 'inviter', got '{date_2.get('role')}'")
                    self.failed_tests.append(f"Date 2 role (as A) - Wrong role")
                    all_passed = False
                else:
                    log_test("Date 2 role (as A)", "PASS", "role = 'inviter'")
                
                # Check other.name
                other_name = date_2.get("other", {}).get("name")
                if other_name != self.user_b_name:
                    log_test("Date 2 other.name (as A)", "FAIL", 
                            f"Expected '{self.user_b_name}', got '{other_name}'")
                    self.failed_tests.append(f"Date 2 other.name (as A) - Wrong name")
                    all_passed = False
                else:
                    log_test("Date 2 other.name (as A)", "PASS", f"other.name = '{other_name}'")
                
                # Check total_hold
                total_hold = date_2.get("total_hold")
                if total_hold != 200:
                    log_test("Date 2 total_hold (as A)", "FAIL", 
                            f"Expected 200, got {total_hold}")
                    self.failed_tests.append(f"Date 2 total_hold (as A) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 2 total_hold (as A)", "PASS", f"total_hold = {total_hold}")
                
                # Check refund_amount (should be 100% of 200 = 200)
                refund_amount = date_2.get("refund_amount")
                expected_refund = 200  # 100% of 200
                if refund_amount != expected_refund:
                    log_test("Date 2 refund_amount (as A)", "FAIL", 
                            f"Expected {expected_refund} (100% of 200), got {refund_amount}")
                    self.failed_tests.append(f"Date 2 refund_amount (as A) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 2 refund_amount (as A)", "PASS", 
                            f"refund_amount = {refund_amount} (100% of {total_hold})")
                
                # Check status
                status = date_2.get("status")
                if status != "CANCELLED":
                    log_test("Date 2 status (as A)", "FAIL", 
                            f"Expected 'CANCELLED', got '{status}'")
                    self.failed_tests.append(f"Date 2 status (as A) - Wrong status")
                    all_passed = False
                else:
                    log_test("Date 2 status (as A)", "PASS", f"status = '{status}'")
            
            if all_passed:
                self.passed_tests.append("GET cancelled endpoint (as A)")
                log_test("GET /api/invites/cancelled (as A)", "PASS", 
                        f"All checks passed. Total: {total}, Both dates verified.")
                return True
            else:
                return False
                
        except Exception as e:
            log_test("GET /api/invites/cancelled (as A)", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"GET cancelled (as A) - {str(e)}")
            return False
    
    def verify_cancelled_endpoint_as_b(self):
        """Step 7: Verify GET /api/invites/cancelled as User B (recipient)"""
        log_section("STEP 7: Verify GET /api/invites/cancelled as User B (Recipient)")
        
        try:
            headers_b = {"Authorization": f"Bearer {self.token_b}"}
            
            response = requests.get(
                f"{BASE_URL}/invites/cancelled",
                headers=headers_b,
                timeout=10
            )
            
            if response.status_code != 200:
                log_test("GET /api/invites/cancelled (as B)", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"GET cancelled (as B) - HTTP {response.status_code}")
                return False
            
            data = response.json()
            items = data.get("items", [])
            total = data.get("total", 0)
            
            # Check total count
            if total < 2:
                log_test("GET /api/invites/cancelled (as B)", "FAIL", 
                        f"Expected total >= 2, got {total}")
                self.failed_tests.append(f"GET cancelled (as B) - Total count {total} < 2")
                return False
            
            # Find our two dates
            date_1 = None
            date_2 = None
            
            for item in items:
                if item.get("id") == self.date_id_1:
                    date_1 = item
                elif item.get("id") == self.date_id_2:
                    date_2 = item
            
            all_passed = True
            
            # Verify Date 1 (transport refuse - B gets 25%)
            if not date_1:
                log_test("Date 1 in response (as B)", "FAIL", "Date 1 not found in cancelled list")
                self.failed_tests.append("Date 1 not in cancelled list (as B)")
                all_passed = False
            else:
                # Check role
                if date_1.get("role") != "recipient":
                    log_test("Date 1 role (as B)", "FAIL", f"Expected 'recipient', got '{date_1.get('role')}'")
                    self.failed_tests.append(f"Date 1 role (as B) - Wrong role")
                    all_passed = False
                else:
                    log_test("Date 1 role (as B)", "PASS", "role = 'recipient'")
                
                # Check other.name
                other_name = date_1.get("other", {}).get("name")
                if other_name != self.user_a_name:
                    log_test("Date 1 other.name (as B)", "FAIL", 
                            f"Expected '{self.user_a_name}', got '{other_name}'")
                    self.failed_tests.append(f"Date 1 other.name (as B) - Wrong name")
                    all_passed = False
                else:
                    log_test("Date 1 other.name (as B)", "PASS", f"other.name = '{other_name}'")
                
                # Check refund_amount (should be 25% of 250 = 62)
                refund_amount = date_1.get("refund_amount")
                expected_refund = 62  # 25% of 250 (250 // 4 = 62)
                if refund_amount != expected_refund:
                    log_test("Date 1 refund_amount (as B)", "FAIL", 
                            f"Expected {expected_refund} (25% of 250), got {refund_amount}")
                    self.failed_tests.append(f"Date 1 refund_amount (as B) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 1 refund_amount (as B)", "PASS", 
                            f"refund_amount = {refund_amount} (25% compensation)")
                
                # Check status
                status = date_1.get("status")
                if status != "CANCELLED_TRANSPORTATION":
                    log_test("Date 1 status (as B)", "FAIL", 
                            f"Expected 'CANCELLED_TRANSPORTATION', got '{status}'")
                    self.failed_tests.append(f"Date 1 status (as B) - Wrong status")
                    all_passed = False
                else:
                    log_test("Date 1 status (as B)", "PASS", f"status = '{status}'")
            
            # Verify Date 2 (recipient reject - B gets 0)
            if not date_2:
                log_test("Date 2 in response (as B)", "FAIL", "Date 2 not found in cancelled list")
                self.failed_tests.append("Date 2 not in cancelled list (as B)")
                all_passed = False
            else:
                # Check role
                if date_2.get("role") != "recipient":
                    log_test("Date 2 role (as B)", "FAIL", f"Expected 'recipient', got '{date_2.get('role')}'")
                    self.failed_tests.append(f"Date 2 role (as B) - Wrong role")
                    all_passed = False
                else:
                    log_test("Date 2 role (as B)", "PASS", "role = 'recipient'")
                
                # Check other.name
                other_name = date_2.get("other", {}).get("name")
                if other_name != self.user_a_name:
                    log_test("Date 2 other.name (as B)", "FAIL", 
                            f"Expected '{self.user_a_name}', got '{other_name}'")
                    self.failed_tests.append(f"Date 2 other.name (as B) - Wrong name")
                    all_passed = False
                else:
                    log_test("Date 2 other.name (as B)", "PASS", f"other.name = '{other_name}'")
                
                # Check refund_amount (should be 0 - recipient rejected, no compensation)
                refund_amount = date_2.get("refund_amount")
                expected_refund = 0
                if refund_amount != expected_refund:
                    log_test("Date 2 refund_amount (as B)", "FAIL", 
                            f"Expected {expected_refund} (recipient rejected), got {refund_amount}")
                    self.failed_tests.append(f"Date 2 refund_amount (as B) - Wrong amount")
                    all_passed = False
                else:
                    log_test("Date 2 refund_amount (as B)", "PASS", 
                            f"refund_amount = {refund_amount} (no compensation for rejecting)")
                
                # Check status
                status = date_2.get("status")
                if status != "CANCELLED":
                    log_test("Date 2 status (as B)", "FAIL", 
                            f"Expected 'CANCELLED', got '{status}'")
                    self.failed_tests.append(f"Date 2 status (as B) - Wrong status")
                    all_passed = False
                else:
                    log_test("Date 2 status (as B)", "PASS", f"status = '{status}'")
            
            if all_passed:
                self.passed_tests.append("GET cancelled endpoint (as B)")
                log_test("GET /api/invites/cancelled (as B)", "PASS", 
                        f"All checks passed. Total: {total}, Both dates verified.")
                return True
            else:
                return False
                
        except Exception as e:
            log_test("GET /api/invites/cancelled (as B)", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"GET cancelled (as B) - {str(e)}")
            return False
    
    def verify_route_resolution(self):
        """Step 8: Verify route resolves correctly (not treating 'cancelled' as date ID)"""
        log_section("STEP 8: Verify Route Resolution")
        
        try:
            headers_a = {"Authorization": f"Bearer {self.token_a}"}
            
            # This should hit the /invites/cancelled endpoint, not /invites/{did}
            response = requests.get(
                f"{BASE_URL}/invites/cancelled",
                headers=headers_a,
                timeout=10
            )
            
            # If it treats "cancelled" as a date ID, it would return 404 or 500
            # If it correctly routes to the cancelled endpoint, it returns 200 with items/total
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has the expected structure for cancelled endpoint
                if "items" in data and "total" in data:
                    log_test("Route resolution", "PASS", 
                            "Route correctly resolves to /invites/cancelled endpoint (not treating 'cancelled' as date ID)")
                    self.passed_tests.append("Route resolution")
                    return True
                else:
                    log_test("Route resolution", "FAIL", 
                            f"Response structure doesn't match cancelled endpoint: {data}")
                    self.failed_tests.append("Route resolution - Wrong response structure")
                    return False
            elif response.status_code == 404:
                log_test("Route resolution", "FAIL", 
                        "Got 404 - route is treating 'cancelled' as a date ID instead of endpoint")
                self.failed_tests.append("Route resolution - 404 (treating as date ID)")
                return False
            elif response.status_code == 500:
                log_test("Route resolution", "FAIL", 
                        f"Got 500 - server error: {response.text[:200]}")
                self.failed_tests.append("Route resolution - 500 server error")
                return False
            else:
                log_test("Route resolution", "FAIL", 
                        f"Unexpected status: {response.status_code}, Response: {response.text[:200]}")
                self.failed_tests.append(f"Route resolution - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Route resolution", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Route resolution - {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all tests for GET /api/invites/cancelled endpoint"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Test GET /api/invites/cancelled Endpoint{RESET}")
        print(f"{BLUE}GiftsDates Backend - Cancelled/Refused Dates with Refund Amounts{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        print(f"Base URL: {BASE_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Connect to DB
        if not self.connect_db():
            print(f"\n{RED}Cannot proceed without database connection{RESET}")
            return 1
        
        # Run tests in sequence
        if not self.setup_users():
            print(f"\n{RED}Cannot proceed without users{RESET}")
            return 1
        
        if not self.grant_coins():
            print(f"\n{RED}Cannot proceed without coins{RESET}")
            return 1
        
        if not self.set_availability():
            print(f"\n{RED}Cannot proceed without availability{RESET}")
            return 1
        
        if not self.create_date_transport_refuse():
            print(f"\n{RED}Cannot proceed without Date 1{RESET}")
            return 1
        
        if not self.create_date_recipient_reject():
            print(f"\n{RED}Cannot proceed without Date 2{RESET}")
            return 1
        
        # Now test the cancelled endpoint
        self.verify_cancelled_endpoint_as_a()
        self.verify_cancelled_endpoint_as_b()
        self.verify_route_resolution()
        
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
        
        # Close DB connection
        if self.mongo_client:
            self.mongo_client.close()
        
        # Return exit code
        return 0 if len(self.failed_tests) == 0 else 1

if __name__ == "__main__":
    tester = CancelledEndpointTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
