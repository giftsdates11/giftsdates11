#!/usr/bin/env python3
"""
Backend API Test Suite for GiftsDates Date/Invite Flow
Tests:
1. Location step works without scheduled_start (date/time fixed at invitation)
2. Transport refuse triggers 50/25/25 refund split
"""
import requests
import json
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

# Base URL from frontend/.env
BASE_URL = "https://secure-gifts-2.preview.emergentagent.com/api"

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

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

class DateFlowTester:
    def __init__(self):
        self.token_a = None
        self.token_b = None
        self.user_a_id = None
        self.user_b_id = None
        self.date_id = None
        self.proposed_start = None
        self.failed_tests = []
        self.passed_tests = []
        self.mongo_client = None
        self.db = None
        
    def connect_db(self):
        """Connect to MongoDB for direct updates"""
        try:
            self.mongo_client = MongoClient(MONGO_URL)
            self.db = self.mongo_client[DB_NAME]
            log_test("MongoDB connection", "PASS", f"Connected to {DB_NAME}")
            return True
        except Exception as e:
            log_test("MongoDB connection", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"MongoDB connection - {str(e)}")
            return False
    
    def register_user(self, name, email_prefix):
        """Register a new test user"""
        import random
        import time
        test_email = f"{email_prefix}.{int(time.time())}.{random.randint(100, 999)}@gmail.com"
        test_password = "DateTest123!"
        
        try:
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "name": name,
                    "age": 28,
                    "gender": "female",
                    "interested_in": "male",
                    "city": "Los Angeles",
                    "country": "USA"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "token" in data:
                    token = data["token"]
                    user_id = data.get("user", {}).get("id")
                    log_test(f"Register {name}", "PASS", f"Email: {test_email}, User ID: {user_id}")
                    return token, user_id, test_email
            
            log_test(f"Register {name}", "FAIL", f"Status: {response.status_code}, Response: {response.text[:200]}")
            self.failed_tests.append(f"Register {name} - HTTP {response.status_code}")
            return None, None, None
                
        except Exception as e:
            log_test(f"Register {name}", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Register {name} - Exception: {str(e)}")
            return None, None, None
    
    def grant_coins_db(self, user_id, coins):
        """Grant coins to user via direct DB update"""
        import time
        try:
            # Small delay to ensure user is in DB
            time.sleep(0.5)
            result = self.db.users.update_one(
                {"id": user_id},
                {"$set": {"coins": coins}}
            )
            if result.modified_count > 0 or result.matched_count > 0:
                log_test(f"Grant {coins} coins to user", "PASS", f"User ID: {user_id}")
                return True
            else:
                log_test(f"Grant coins", "FAIL", f"User not found: {user_id}")
                self.failed_tests.append(f"Grant coins - User not found")
                return False
        except Exception as e:
            log_test(f"Grant coins", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Grant coins - Exception: {str(e)}")
            return False
    
    def set_availability_db(self, user_id, date_price=50):
        """Set user availability via direct DB update"""
        import time
        try:
            # Small delay to ensure user is in DB
            time.sleep(0.5)
            # Set availability for tomorrow
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            result = self.db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "availability": [tomorrow],
                    "availability_time": {"from": "18:00", "to": "23:00"},
                    "date_price": date_price
                }}
            )
            if result.modified_count > 0 or result.matched_count > 0:
                log_test(f"Set availability", "PASS", 
                        f"Date: {tomorrow}, Time: 18:00-23:00, Price: {date_price} coins")
                return tomorrow
            else:
                log_test(f"Set availability", "FAIL", f"User not found: {user_id}")
                self.failed_tests.append(f"Set availability - User not found")
                return None
        except Exception as e:
            log_test(f"Set availability", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Set availability - Exception: {str(e)}")
            return None
    
    def create_invite(self, token, recipient_id, scheduled_start, coins):
        """Create a date invitation"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "recipient_id": recipient_id,
                "activity_option_1": "Romantic dinner at a cozy restaurant",
                "activity_option_2": "Evening walk along the beach",
                "activity_option_3": "Wine tasting at a local vineyard",
                "scheduled_start": scheduled_start,
                "coins": coins,
                "safety_ack": True
            }
            
            response = requests.post(
                f"{BASE_URL}/invites",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                date_id = data.get("id")
                status = data.get("status")
                
                if date_id and status == "INVITATION_SENT":
                    log_test("Create invitation", "PASS", 
                            f"Date ID: {date_id}, Status: {status}")
                    self.passed_tests.append("Create invitation")
                    return date_id
                else:
                    log_test("Create invitation", "FAIL", 
                            f"Invalid response - date_id: {date_id}, status: {status}")
                    self.failed_tests.append("Create invitation - Invalid response")
                    return None
            else:
                log_test("Create invitation", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Create invitation - HTTP {response.status_code}")
                return None
                
        except Exception as e:
            log_test("Create invitation", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Create invitation - Exception: {str(e)}")
            return None
    
    def choose_activity(self, token, date_id):
        """Recipient chooses a date activity"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"idea_id": "opt1"}
            
            response = requests.post(
                f"{BASE_URL}/invites/{date_id}/choose",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "DATE_ACTIVITY_SELECTED":
                    log_test("Choose activity", "PASS", f"Status: {status}")
                    self.passed_tests.append("Choose activity")
                    return True
                else:
                    log_test("Choose activity", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"Choose activity - Wrong status: {status}")
                    return False
            else:
                log_test("Choose activity", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Choose activity - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Choose activity", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Choose activity - Exception: {str(e)}")
            return False
    
    def set_location_without_scheduled_start(self, token, date_id):
        """Set location WITHOUT sending scheduled_start"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            # IMPORTANT: Send ONLY venue, address, city, country - NO scheduled_start
            payload = {
                "venue": "The Ivy Restaurant",
                "address": "123 Main Street",
                "city": "Los Angeles",
                "country": "USA"
            }
            
            response = requests.post(
                f"{BASE_URL}/invites/{date_id}/location",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "LOCATION_PROPOSED":
                    log_test("Set location (without scheduled_start)", "PASS", f"Status: {status}")
                    self.passed_tests.append("Set location without scheduled_start")
                    return True
                else:
                    log_test("Set location (without scheduled_start)", "FAIL", 
                            f"Unexpected status: {status}")
                    self.failed_tests.append(f"Set location - Wrong status: {status}")
                    return False
            else:
                log_test("Set location (without scheduled_start)", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Set location - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Set location (without scheduled_start)", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Set location - Exception: {str(e)}")
            return False
    
    def get_date_details(self, token, date_id):
        """Get date details to verify location.scheduled_start"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(
                f"{BASE_URL}/invites/{date_id}",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                log_test("Get date details", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Get date details - HTTP {response.status_code}")
                return None
                
        except Exception as e:
            log_test("Get date details", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Get date details - Exception: {str(e)}")
            return None
    
    def request_taxi(self, token, date_id, amount):
        """Recipient requests taxi"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"amount": amount}
            
            response = requests.post(
                f"{BASE_URL}/invites/{date_id}/taxi/request",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "TAXI_REQUESTED":
                    log_test("Request taxi", "PASS", f"Amount: {amount} coins, Status: {status}")
                    self.passed_tests.append("Request taxi")
                    return True
                else:
                    log_test("Request taxi", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"Request taxi - Wrong status: {status}")
                    return False
            else:
                log_test("Request taxi", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Request taxi - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Request taxi", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Request taxi - Exception: {str(e)}")
            return False
    
    def get_wallet(self, token):
        """Get wallet balances"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(
                f"{BASE_URL}/wallet",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "coins": data.get("coins", 0),
                    "withdrawable": data.get("withdrawable", 0),
                    "escrow": data.get("escrow", 0)
                }
            else:
                log_test("Get wallet", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                return None
                
        except Exception as e:
            log_test("Get wallet", "FAIL", f"Exception: {str(e)}")
            return None
    
    def refuse_transport(self, token, date_id):
        """Inviter refuses transport"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.post(
                f"{BASE_URL}/invites/{date_id}/transport/refuse",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "CANCELLED_TRANSPORTATION":
                    log_test("Refuse transport", "PASS", f"Status: {status}")
                    self.passed_tests.append("Refuse transport")
                    return True
                else:
                    log_test("Refuse transport", "FAIL", f"Unexpected status: {status}")
                    self.failed_tests.append(f"Refuse transport - Wrong status: {status}")
                    return False
            else:
                log_test("Refuse transport", "FAIL", 
                        f"Status: {response.status_code}, Response: {response.text[:300]}")
                self.failed_tests.append(f"Refuse transport - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            log_test("Refuse transport", "FAIL", f"Exception: {str(e)}")
            self.failed_tests.append(f"Refuse transport - Exception: {str(e)}")
            return False
    
    def run_part1_location_without_scheduled_start(self):
        """PART 1: Test location step without scheduled_start"""
        log_section("PART 1: Location WITHOUT scheduled_start (date/time fixed at invitation)")
        
        # Step 1: Register inviter A and recipient B
        log_section("Step 1: Register Users")
        self.token_a, self.user_a_id, email_a = self.register_user("Alice Inviter", "alice.inviter")
        if not self.token_a:
            return False
        
        self.token_b, self.user_b_id, email_b = self.register_user("Bob Recipient", "bob.recipient")
        if not self.token_b:
            return False
        
        self.passed_tests.append("Register users")
        
        # Step 2: Grant coins and set availability
        log_section("Step 2: Grant Coins & Set Availability")
        if not self.grant_coins_db(self.user_a_id, 1000):
            return False
        if not self.grant_coins_db(self.user_b_id, 500):
            return False
        
        tomorrow = self.set_availability_db(self.user_b_id, date_price=50)
        if not tomorrow:
            return False
        
        self.passed_tests.append("Grant coins and set availability")
        
        # Step 3: A invites B with proposed_start
        log_section("Step 3: Create Invitation with proposed_start")
        # Create a valid proposed_start inside B's availability (tomorrow at 19:00)
        self.proposed_start = f"{tomorrow}T19:00:00Z"
        
        self.date_id = self.create_invite(self.token_a, self.user_b_id, self.proposed_start, 250)
        if not self.date_id:
            return False
        
        # Step 4: B chooses activity
        log_section("Step 4: Recipient Chooses Activity")
        if not self.choose_activity(self.token_b, self.date_id):
            return False
        
        # Step 5: A sets location WITHOUT scheduled_start
        log_section("Step 5: Set Location WITHOUT scheduled_start")
        if not self.set_location_without_scheduled_start(self.token_a, self.date_id):
            return False
        
        # Step 6: Verify location.scheduled_start equals proposed_start
        log_section("Step 6: Verify location.scheduled_start == proposed_start")
        date_details = self.get_date_details(self.token_a, self.date_id)
        if not date_details:
            return False
        
        location = date_details.get("location", {})
        location_scheduled_start = location.get("scheduled_start")
        original_proposed_start = date_details.get("proposed_start")
        
        if location_scheduled_start and original_proposed_start:
            # Compare the datetime values (they should be equal)
            if location_scheduled_start == original_proposed_start:
                log_test("Verify location.scheduled_start == proposed_start", "PASS",
                        f"location.scheduled_start: {location_scheduled_start}\n"
                        f"      original proposed_start: {original_proposed_start}\n"
                        f"      ✅ Date/time preserved from invitation!")
                self.passed_tests.append("Verify scheduled_start preserved")
                return True
            else:
                log_test("Verify location.scheduled_start == proposed_start", "FAIL",
                        f"location.scheduled_start: {location_scheduled_start}\n"
                        f"      original proposed_start: {original_proposed_start}\n"
                        f"      ❌ Date/time NOT preserved!")
                self.failed_tests.append("Verify scheduled_start - Values don't match")
                return False
        else:
            log_test("Verify location.scheduled_start == proposed_start", "FAIL",
                    f"Missing fields - location.scheduled_start: {location_scheduled_start}, "
                    f"proposed_start: {original_proposed_start}")
            self.failed_tests.append("Verify scheduled_start - Missing fields")
            return False
    
    def run_part2_transport_refuse_refund_split(self):
        """PART 2: Test transport refuse triggers 50/25/25 refund split"""
        log_section("PART 2: Transport Refuse Triggers 50/25/25 Refund Split")
        
        # Continue from Part 1 - we already have a date with location set
        if not self.date_id:
            log_test("Part 2 prerequisite", "FAIL", "No date_id from Part 1")
            self.failed_tests.append("Part 2 - Missing date_id")
            return False
        
        # Step 7: B requests taxi
        log_section("Step 7: Recipient Requests Taxi")
        taxi_amount = 30
        if not self.request_taxi(self.token_b, self.date_id, taxi_amount):
            return False
        
        # Step 8: Record balances before refund
        log_section("Step 8: Record Balances Before Refund")
        wallet_a_before = self.get_wallet(self.token_a)
        wallet_b_before = self.get_wallet(self.token_b)
        
        if not wallet_a_before or not wallet_b_before:
            log_test("Record balances", "FAIL", "Failed to get wallet balances")
            self.failed_tests.append("Record balances - API error")
            return False
        
        log_test("Inviter A balance before", "INFO",
                f"Coins: {wallet_a_before['coins']}, "
                f"Withdrawable: {wallet_a_before['withdrawable']}, "
                f"Escrow: {wallet_a_before['escrow']}")
        log_test("Recipient B balance before", "INFO",
                f"Coins: {wallet_b_before['coins']}, "
                f"Withdrawable: {wallet_b_before['withdrawable']}, "
                f"Escrow: {wallet_b_before['escrow']}")
        
        # Get total_hold from date
        date_details = self.get_date_details(self.token_a, self.date_id)
        if not date_details:
            return False
        
        total_hold = date_details.get("total_hold", 0)
        log_test("Total hold on date", "INFO", f"{total_hold} coins")
        
        # Step 9: A refuses transport
        log_section("Step 9: Inviter Refuses Transport")
        if not self.refuse_transport(self.token_a, self.date_id):
            return False
        
        # Step 10: Verify refund split
        log_section("Step 10: Verify 50/25/25 Refund Split")
        wallet_a_after = self.get_wallet(self.token_a)
        wallet_b_after = self.get_wallet(self.token_b)
        
        if not wallet_a_after or not wallet_b_after:
            log_test("Verify refund", "FAIL", "Failed to get wallet balances after refund")
            self.failed_tests.append("Verify refund - API error")
            return False
        
        log_test("Inviter A balance after", "INFO",
                f"Coins: {wallet_a_after['coins']}, "
                f"Withdrawable: {wallet_a_after['withdrawable']}, "
                f"Escrow: {wallet_a_after['escrow']}")
        log_test("Recipient B balance after", "INFO",
                f"Coins: {wallet_b_after['coins']}, "
                f"Withdrawable: {wallet_b_after['withdrawable']}, "
                f"Escrow: {wallet_b_after['escrow']}")
        
        # Calculate expected refunds
        expected_inviter_refund = total_hold // 2  # 50%
        expected_recipient_compensation = total_hold // 4  # 25%
        expected_platform_fee = total_hold - expected_inviter_refund - expected_recipient_compensation  # 25%
        
        # Calculate actual changes
        actual_inviter_refund = wallet_a_after['coins'] - wallet_a_before['coins']
        actual_recipient_compensation = wallet_b_after['withdrawable'] - wallet_b_before['withdrawable']
        
        log_test("Expected refund split", "INFO",
                f"Total hold: {total_hold} coins\n"
                f"      Inviter (50%): {expected_inviter_refund} coins\n"
                f"      Recipient (25%): {expected_recipient_compensation} coins\n"
                f"      Platform (25%): {expected_platform_fee} coins")
        
        log_test("Actual refund split", "INFO",
                f"Inviter received: {actual_inviter_refund} coins\n"
                f"      Recipient received: {actual_recipient_compensation} coins (withdrawable)")
        
        # Verify the split
        all_correct = True
        
        if actual_inviter_refund == expected_inviter_refund:
            log_test("Inviter refund (50%)", "PASS",
                    f"Expected: {expected_inviter_refund}, Actual: {actual_inviter_refund}")
        else:
            log_test("Inviter refund (50%)", "FAIL",
                    f"Expected: {expected_inviter_refund}, Actual: {actual_inviter_refund}")
            self.failed_tests.append(f"Inviter refund - Expected {expected_inviter_refund}, got {actual_inviter_refund}")
            all_correct = False
        
        if actual_recipient_compensation == expected_recipient_compensation:
            log_test("Recipient compensation (25%)", "PASS",
                    f"Expected: {expected_recipient_compensation}, Actual: {actual_recipient_compensation}")
        else:
            log_test("Recipient compensation (25%)", "FAIL",
                    f"Expected: {expected_recipient_compensation}, Actual: {actual_recipient_compensation}")
            self.failed_tests.append(f"Recipient compensation - Expected {expected_recipient_compensation}, got {actual_recipient_compensation}")
            all_correct = False
        
        # Platform fee is implicit (we can't directly verify it, but if the other two are correct, it should be correct)
        log_test("Platform fee (25%)", "INFO",
                f"Expected: {expected_platform_fee} coins (implicit, not directly verifiable)")
        
        if all_correct:
            self.passed_tests.append("Verify 50/25/25 refund split")
            log_test("Overall refund split verification", "PASS",
                    "✅ 50% to inviter (coins), 25% to recipient (withdrawable), 25% platform fee")
            return True
        else:
            log_test("Overall refund split verification", "FAIL",
                    "❌ Refund split does not match expected 50/25/25")
            return False
    
    def run_all_tests(self):
        """Run all date flow tests"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}GiftsDates Date/Invite Flow Test Suite{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        print(f"Base URL: {BASE_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Connect to MongoDB
        if not self.connect_db():
            print(f"\n{RED}Cannot proceed without MongoDB connection{RESET}")
            return 1
        
        # Run Part 1
        part1_success = self.run_part1_location_without_scheduled_start()
        
        # Run Part 2 (only if Part 1 succeeded)
        part2_success = False
        if part1_success:
            part2_success = self.run_part2_transport_refuse_refund_split()
        else:
            log_section("PART 2: SKIPPED")
            log_test("Part 2", "SKIP", "Part 1 failed, skipping Part 2")
        
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
        
        # Close MongoDB connection
        if self.mongo_client:
            self.mongo_client.close()
        
        # Return exit code
        return 0 if len(self.failed_tests) == 0 else 1

if __name__ == "__main__":
    tester = DateFlowTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
