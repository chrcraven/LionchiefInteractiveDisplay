#!/usr/bin/env python3
"""
Test script for LionChief Train Queue API
Run with: python3 test_api.py
"""

import requests
import time

BASE_URL = "http://localhost:8000"
USER_ID = "test-user"

def join_queue():
    """Join the queue to get control"""
    print("👤 Joining queue...")
    r = requests.post(f"{BASE_URL}/queue/join", json={"user_id": USER_ID})
    print(f"   Response: {r.json()}")
    print()
    return r.json()

def leave_queue():
    """Leave the queue"""
    print("👋 Leaving queue...")
    r = requests.post(f"{BASE_URL}/queue/leave", json={"user_id": USER_ID})
    print(f"   Response: {r.json()}")
    print()

def test_queue_status():
    """Check queue status"""
    print("📋 Checking queue status...")
    r = requests.get(f"{BASE_URL}/queue/status")
    print(f"   Status: {r.json()}")
    print()

def test_status():
    """Check train status"""
    print("📊 Checking train status...")
    r = requests.get(f"{BASE_URL}/train/status")
    print(f"   Status: {r.json()}")
    print()

def test_discovery():
    """Scan for trains"""
    print("🔍 Scanning for trains...")
    r = requests.get(f"{BASE_URL}/train/scan", params={"duration": 10})
    print(f"   Response: {r.json()}")
    print()

def test_connect(address=None):
    """Connect to train"""
    print(f"🔌 Connecting to train{' at ' + address if address else ''}...")
    data = {"address": address} if address else {}
    r = requests.post(f"{BASE_URL}/train/connect", json=data)
    print(f"   Response: {r.json()}")
    print()

def test_speed(speed):
    """Set train speed (0-31)"""
    print(f"🚂 Setting speed to {speed}...")
    r = requests.post(f"{BASE_URL}/train/speed", json={"user_id": USER_ID, "speed": speed})
    print(f"   Response: {r.json()}")
    print()

def test_direction(direction):
    """Set direction (forward/reverse/toggle)"""
    print(f"↔️  Setting direction to {direction}...")
    r = requests.post(f"{BASE_URL}/train/direction", json={"user_id": USER_ID, "direction": direction})
    print(f"   Response: {r.json()}")
    print()

def test_horn():
    """Blow the horn"""
    print("📯 Blowing horn...")
    r = requests.post(f"{BASE_URL}/train/horn", json={"user_id": USER_ID})
    print(f"   Response: {r.json()}")
    print()

def test_bell(state):
    """Ring the bell"""
    print(f"🔔 Bell {'ON' if state else 'OFF'}...")
    r = requests.post(f"{BASE_URL}/train/bell", json={"user_id": USER_ID, "state": state})
    print(f"   Response: {r.json()}")
    print()

def test_stop():
    """Emergency stop"""
    print("🛑 Emergency stop...")
    r = requests.post(f"{BASE_URL}/train/emergency-stop", json={"user_id": USER_ID})
    print(f"   Response: {r.json()}")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("LionChief Train API Test")
    print("=" * 50)
    print()

    # Check status
    test_status()
    test_queue_status()

    # Join queue to get control
    join_queue()
    time.sleep(1)

    # Test basic controls (will work in mock mode or with real train)
    test_speed(10)
    time.sleep(1)

    test_horn()
    time.sleep(1)

    test_bell(True)
    time.sleep(2)
    test_bell(False)

    test_direction("forward")
    time.sleep(1)

    test_speed(15)
    time.sleep(2)

    test_stop()
    time.sleep(1)

    # Leave queue
    leave_queue()

    print("=" * 50)
    print("Test complete!")
    print("=" * 50)
