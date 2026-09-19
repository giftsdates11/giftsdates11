#!/usr/bin/env python3
"""
Backend test for GiftsDates: Reject locks availability slot flow
Tests that when a recipient rejects an invite, the slot gets locked and prevents rebooking.
"""
import requests
import os
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

# Get backend URL from frontend .env
with open('/app/frontend/.env', 'r') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            BACKEND_URL = line.split('=', 1)[1].strip()
            break

API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

print(f"Testing against: {API_BASE}")
print(f"MongoDB: {DB_NAME}")

# MongoDB client for direct coin granting
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]

def grant_coins(user_id, amount):
    """Grant coins to a user directly via MongoDB"""
    result = db.users.update_one(
        {"id": user_id},
        {"$inc": {"coins": amount}}
    )
    print(f"  ✓ Granted {amount} coins to user {user_id}")
    return result.modified_count > 0

def test_reject_locks_slot():
    """
    Test the complete flow:
    1. Register two users A (inviter) and B (recipient)
    2. Grant coins to both users
    3. Set B's availability with a future date and time window
    4. A invites B for a slot within B's availability
    5. B rejects the invite
    6. Verify B's slot is locked in availability endpoint
    7. A tries to invite B again for same slot -> expect SLOT_LOCKED
    """
    print("\n" + "="*80)
    print("TEST: Reject locks availability slot & blocks rebooking")
    print("="*80)
    
    # Step 1: Register User A (inviter)
    print("\n[Step 1] Registering User A (inviter)...")
    timestamp = int(datetime.now().timestamp())
    user_a_data = {
        "email": f"alice.inviter.{timestamp}@test.com",
        "password": "SecurePass123!",
        "name": "Alice Inviter",
        "age": 28,
        "gender": "female",
        "interested_in": "male",
        "city": "Barcelona",
        "country": "Spain",
        "bio": "Love to explore new places"
    }
    
    resp_a = requests.post(f"{API_BASE}/auth/register", json=user_a_data)
    if resp_a.status_code != 200:
        print(f"  ✗ FAILED: User A registration failed: {resp_a.status_code} - {resp_a.text}")
        return False
    
    data_a = resp_a.json()
    token_a = data_a["token"]
    user_a_id = data_a["user"]["id"]
    print(f"  ✓ User A registered: {user_a_id} ({user_a_data['email']})")
    
    # Step 2: Register User B (recipient)
    print("\n[Step 2] Registering User B (recipient)...")
    user_b_data = {
        "email": f"bob.recipient.{timestamp}@test.com",
        "password": "SecurePass123!",
        "name": "Bob Recipient",
        "age": 30,
        "gender": "male",
        "interested_in": "female",
        "city": "Barcelona",
        "country": "Spain",
        "bio": "Looking for meaningful connections"
    }
    
    resp_b = requests.post(f"{API_BASE}/auth/register", json=user_b_data)
    if resp_b.status_code != 200:
        print(f"  ✗ FAILED: User B registration failed: {resp_b.status_code} - {resp_b.text}")
        return False
    
    data_b = resp_b.json()
    token_b = data_b["token"]
    user_b_id = data_b["user"]["id"]
    print(f"  ✓ User B registered: {user_b_id} ({user_b_data['email']})")
    
    # Step 3: Grant coins to both users
    print("\n[Step 3] Granting coins to users...")
    grant_coins(user_a_id, 500)  # A needs coins to invite
    grant_coins(user_b_id, 100)  # B gets some coins too
    
    # Step 4: Set B's availability
    print("\n[Step 4] Setting User B's availability...")
    # Pick a future date (tomorrow) and set availability window
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    availability_data = {
        "availability": [tomorrow],
        "availability_time": {"from": "18:00", "to": "23:00"},
        "date_price": 200  # Set a date price
    }
    
    resp_avail = requests.patch(
        f"{API_BASE}/auth/me",
        json=availability_data,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    if resp_avail.status_code != 200:
        print(f"  ✗ FAILED: Setting availability failed: {resp_avail.status_code} - {resp_avail.text}")
        return False
    
    print(f"  ✓ User B availability set: {tomorrow} from 18:00 to 23:00")
    
    # Step 5: A invites B for a slot within B's availability
    print("\n[Step 5] User A invites User B...")
    # Pick a time within the availability window (e.g., 19:00)
    proposed_start = f"{tomorrow}T19:00:00Z"
    
    invite_data = {
        "recipient_id": user_b_id,
        "activity_option_1": "Romantic dinner at a cozy restaurant",
        "activity_option_2": "Evening walk along the beach",
        "activity_option_3": "Wine tasting at a local vineyard",
        "scheduled_start": proposed_start,
        "coins": 250,  # >= date_price (200) and INVITE_MIN_COINS (150)
        "safety_ack": True
    }
    
    resp_invite = requests.post(
        f"{API_BASE}/invites",
        json=invite_data,
        headers={"Authorization": f"Bearer {token_a}"}
    )
    if resp_invite.status_code != 200:
        print(f"  ✗ FAILED: Invite creation failed: {resp_invite.status_code} - {resp_invite.text}")
        return False
    
    invite_data_resp = resp_invite.json()
    invite_id = invite_data_resp["id"]
    print(f"  ✓ Invite created: {invite_id}, status: {invite_data_resp['status']}")
    
    if invite_data_resp["status"] != "INVITATION_SENT":
        print(f"  ✗ FAILED: Expected status INVITATION_SENT, got {invite_data_resp['status']}")
        return False
    
    # Step 6: B rejects the invite
    print("\n[Step 6] User B rejects the invite...")
    resp_cancel = requests.post(
        f"{API_BASE}/invites/{invite_id}/cancel",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    if resp_cancel.status_code != 200:
        print(f"  ✗ FAILED: Invite cancellation failed: {resp_cancel.status_code} - {resp_cancel.text}")
        return False
    
    cancel_data = resp_cancel.json()
    print(f"  ✓ Invite cancelled: status={cancel_data['status']}")
    
    if cancel_data["status"] != "CANCELLED":
        print(f"  ✗ FAILED: Expected status CANCELLED, got {cancel_data['status']}")
        return False
    
    # Verify coins were refunded to A
    resp_a_wallet = requests.get(
        f"{API_BASE}/wallet",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    if resp_a_wallet.status_code == 200:
        wallet_a = resp_a_wallet.json()
        print(f"  ✓ User A coins after refund: {wallet_a.get('coins', 0)}")
    
    # Step 7: Verify B's slot is locked in availability endpoint
    print("\n[Step 7] Verifying slot is locked in User B's availability...")
    resp_avail_check = requests.get(
        f"{API_BASE}/profiles/{user_b_id}/availability",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    if resp_avail_check.status_code != 200:
        print(f"  ✗ FAILED: Availability check failed: {resp_avail_check.status_code} - {resp_avail_check.text}")
        return False
    
    avail_data = resp_avail_check.json()
    locked_days = avail_data.get("locked_days", {})
    busy_slots = avail_data.get("busy_slots", {})
    
    print(f"  ✓ Availability retrieved")
    print(f"    - Locked days: {list(locked_days.keys())}")
    print(f"    - Busy slots: {list(busy_slots.keys())}")
    
    # Check if the day is in locked_days
    if tomorrow not in locked_days:
        print(f"  ✗ FAILED: Expected {tomorrow} in locked_days, but not found")
        print(f"    locked_days: {locked_days}")
        return False
    
    # Check if the locked slot has the locked=True flag
    locked_slot_found = False
    for slot in locked_days[tomorrow]:
        if slot.get("locked") == True:
            locked_slot_found = True
            print(f"  ✓ Locked slot found: {slot}")
            break
    
    if not locked_slot_found:
        print(f"  ✗ FAILED: No locked slot found in locked_days[{tomorrow}]")
        return False
    
    # Also check busy_slots includes the locked slot
    if tomorrow in busy_slots:
        for slot in busy_slots[tomorrow]:
            if slot.get("locked") == True:
                print(f"  ✓ Locked slot also in busy_slots: {slot}")
                break
    
    # Step 8: A tries to invite B again for the same slot -> expect SLOT_LOCKED
    print("\n[Step 8] User A tries to invite User B again for the same slot...")
    resp_invite2 = requests.post(
        f"{API_BASE}/invites",
        json=invite_data,  # Same invite data as before
        headers={"Authorization": f"Bearer {token_a}"}
    )
    
    if resp_invite2.status_code == 400:
        error_detail = resp_invite2.json().get("detail", "")
        if "SLOT_LOCKED" in error_detail:
            print(f"  ✓ SLOT_LOCKED error received as expected: {error_detail}")
            print("\n" + "="*80)
            print("✅ TEST PASSED: Reject locks availability slot flow works correctly!")
            print("="*80)
            return True
        else:
            print(f"  ✗ FAILED: Expected SLOT_LOCKED error, got: {error_detail}")
            return False
    else:
        print(f"  ✗ FAILED: Expected 400 status, got {resp_invite2.status_code}")
        print(f"    Response: {resp_invite2.text}")
        return False

if __name__ == "__main__":
    try:
        success = test_reject_locks_slot()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
