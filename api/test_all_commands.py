#!/usr/bin/env python3
"""
Comprehensive test script for all LionChief Train API commands
Run with: python3 test_all_commands.py
"""

import requests
import time

BASE_URL = "http://localhost:8000"
USER_ID = "comprehensive-test"
USERNAME = "Comprehensive Tester"

def join_queue():
    """Join the queue to get control"""
    print("👤 Joining queue...")
    r = requests.post(f"{BASE_URL}/queue/join", json={"user_id": USER_ID, "username": USERNAME})
    result = r.json()
    print(f"   Response: {result}")
    print()
    return result

def leave_queue():
    """Leave the queue"""
    print("👋 Leaving queue...")
    r = requests.post(f"{BASE_URL}/queue/leave", json={"user_id": USER_ID})
    print(f"   Response: {r.json()}")
    print()

def get_queue_status():
    """Check queue status"""
    r = requests.get(f"{BASE_URL}/queue/status")
    return r.json()

def get_train_status():
    """Check train status"""
    r = requests.get(f"{BASE_URL}/train/status")
    return r.json()

def test_speed_range():
    """Test full speed range (0-31)"""
    print("\n" + "="*60)
    print("TESTING SPEED CONTROL (0-31)")
    print("="*60)

    # Test minimum speed
    print("🚂 Setting speed to 0 (stop)...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 0})
    print(f"   {r.json()}")
    time.sleep(1)

    # Test low speeds
    for speed in [5, 10, 15]:
        print(f"🚂 Setting speed to {speed}...")
        r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": speed})
        print(f"   {r.json()}")
        time.sleep(2)

    # Test medium speeds
    for speed in [20, 25]:
        print(f"🚂 Setting speed to {speed}...")
        r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": speed})
        print(f"   {r.json()}")
        time.sleep(2)

    # Test maximum speed (briefly)
    print(f"🚂 Setting speed to 31 (max)...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 31})
    print(f"   {r.json()}")
    time.sleep(2)

    # Return to stop
    print(f"🚂 Stopping (speed 0)...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 0})
    print(f"   {r.json()}")
    time.sleep(1)

def test_direction_control():
    """Test all direction commands"""
    print("\n" + "="*60)
    print("TESTING DIRECTION CONTROL")
    print("="*60)

    directions = ["forward", "reverse", "forward", "toggle", "toggle"]

    for direction in directions:
        print(f"↔️  Setting direction to {direction}...")
        r = requests.post(f"{BASE_URL}/train/direction", json={"user_id": USER_ID, "direction": direction})
        result = r.json()
        print(f"   {result}")
        time.sleep(1.5)

def test_horn():
    """Test horn"""
    print("\n" + "="*60)
    print("TESTING HORN")
    print("="*60)

    for i in range(3):
        print(f"📯 Blowing horn (attempt {i+1}/3)...")
        r = requests.post(f"{BASE_URL}/train/horn", json={"user_id": USER_ID})
        print(f"   {r.json()}")
        time.sleep(1.5)

def test_bell():
    """Test bell on/off"""
    print("\n" + "="*60)
    print("TESTING BELL")
    print("="*60)

    # Bell on
    print("🔔 Bell ON...")
    r = requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": True})
    print(f"   {r.json()}")
    time.sleep(3)

    # Bell off
    print("🔔 Bell OFF...")
    r = requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": False})
    print(f"   {r.json()}")
    time.sleep(1)

    # Bell on again
    print("🔔 Bell ON (second time)...")
    r = requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": True})
    print(f"   {r.json()}")
    time.sleep(2)

    # Bell off
    print("🔔 Bell OFF...")
    r = requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": False})
    print(f"   {r.json()}")
    time.sleep(1)

def test_emergency_stop():
    """Test emergency stop"""
    print("\n" + "="*60)
    print("TESTING EMERGENCY STOP")
    print("="*60)

    # Set some speed first
    print("🚂 Setting speed to 15...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 15})
    print(f"   {r.json()}")
    time.sleep(2)

    # Emergency stop
    print("🛑 EMERGENCY STOP!")
    r = requests.post(f"{BASE_URL}/train/emergency-stop", json={"user_id": USER_ID})
    print(f"   {r.json()}")
    time.sleep(1)

def test_combined_sequence():
    """Test a realistic sequence of commands"""
    print("\n" + "="*60)
    print("TESTING COMBINED SEQUENCE (Realistic Operation)")
    print("="*60)

    # Start forward, slow speed
    print("1️⃣ Setting direction forward...")
    requests.post(f"{BASE_URL}/train/direction", json={"user_id": USER_ID, "direction": "forward"})
    time.sleep(1)

    print("2️⃣ Starting at slow speed (5)...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 5})
    time.sleep(2)

    # Horn
    print("3️⃣ Blowing horn...")
    requests.post(f"{BASE_URL}/train/horn", json={"user_id": USER_ID})
    time.sleep(2)

    # Speed up
    print("4️⃣ Accelerating to speed 12...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 12})
    time.sleep(2)

    # Bell on
    print("5️⃣ Ringing bell...")
    requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": True})
    time.sleep(3)

    # Speed up more
    print("6️⃣ Accelerating to speed 18...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 18})
    time.sleep(3)

    # Bell off
    print("7️⃣ Stopping bell...")
    requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": False})
    time.sleep(1)

    # Slow down
    print("8️⃣ Slowing to speed 10...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 10})
    time.sleep(2)

    # Horn again
    print("9️⃣ Blowing horn...")
    requests.post(f"{BASE_URL}/train/horn", json={"user_id": USER_ID})
    time.sleep(2)

    # Slow to stop
    print("🔟 Slowing to speed 5...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 5})
    time.sleep(2)

    print("1️⃣1️⃣ Coming to a complete stop...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 0})
    time.sleep(2)

    # Reverse
    print("1️⃣2️⃣ Reversing direction...")
    requests.post(f"{BASE_URL}/train/direction", json={"user_id": USER_ID, "direction": "reverse"})
    time.sleep(1)

    # Slow reverse
    print("1️⃣3️⃣ Moving in reverse at speed 5...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 5})
    time.sleep(3)

    # Stop
    print("1️⃣4️⃣ Final stop...")
    requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 0})
    time.sleep(1)

def test_invalid_inputs():
    """Test error handling with invalid inputs"""
    print("\n" + "="*60)
    print("TESTING ERROR HANDLING (Invalid Inputs)")
    print("="*60)

    # Invalid speed (too high)
    print("❌ Testing invalid speed (100)...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 100})
    print(f"   {r.status_code}: {r.json()}")
    time.sleep(1)

    # Invalid speed (negative)
    print("❌ Testing invalid speed (-5)...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": -5})
    print(f"   {r.status_code}: {r.json()}")
    time.sleep(1)

    # Invalid direction
    print("❌ Testing invalid direction (sideways)...")
    r = requests.post(f"{BASE_URL}/train/direction", json={"user_id": USER_ID, "direction": "sideways"})
    print(f"   {r.status_code}: {r.json()}")
    time.sleep(1)

if __name__ == "__main__":
    print("=" * 70)
    print(" " * 15 + "COMPREHENSIVE TRAIN COMMAND TEST")
    print("=" * 70)
    print()

    # Check initial status
    print("📊 Initial train status:")
    status = get_train_status()
    print(f"   Connected: {status.get('connected')}")
    print(f"   Mock Mode: {status.get('mock_mode')}")
    print(f"   Train Address: {status.get('train_address')}")
    print(f"   Current Speed: {status.get('speed')}")
    print(f"   Current Direction: {status.get('direction')}")
    print()

    # Join queue
    join_result = join_queue()
    if not join_result.get('success', True):
        print("❌ Failed to join queue. Exiting.")
        exit(1)

    time.sleep(1)

    # Verify we have control
    queue_status = get_queue_status()
    current_controller = queue_status.get('current_controller')
    if current_controller != USER_ID:
        print(f"❌ We don't have control. Current controller: {current_controller}")
        print("   Waiting for control...")
        time.sleep(5)
        queue_status = get_queue_status()
        current_controller = queue_status.get('current_controller')
        if current_controller != USER_ID:
            print("❌ Still don't have control. Exiting.")
            leave_queue()
            exit(1)

    print(f"✅ We have control! Starting tests...\n")

    try:
        # Run all tests
        test_speed_range()
        test_direction_control()
        test_horn()
        test_bell()
        test_emergency_stop()
        test_combined_sequence()
        test_invalid_inputs()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
    finally:
        # Cleanup: ensure train is stopped
        print("\n" + "="*70)
        print("CLEANUP")
        print("="*70)
        print("🛑 Ensuring train is stopped...")
        requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": 0})
        time.sleep(1)

        # Leave queue
        leave_queue()

        # Final status
        print("📊 Final train status:")
        final_status = get_train_status()
        print(f"   Speed: {final_status.get('speed')}")
        print(f"   Direction: {final_status.get('direction')}")
        print(f"   Connected: {final_status.get('connected')}")

    print("\n" + "=" * 70)
    print(" " * 20 + "ALL TESTS COMPLETE!")
    print("=" * 70)
