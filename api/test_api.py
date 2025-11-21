#!/usr/bin/env python3
"""
Test script for LionChief Train Queue API
Run with: python3 test_api.py
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_status():
    """Check train status"""
    print("📊 Checking train status...")
    r = requests.get(f"{BASE_URL}/api/train/status")
    print(f"   Status: {r.json()}")
    print()

def test_discovery():
    """Scan for trains"""
    print("🔍 Scanning for trains...")
    r = requests.post(f"{BASE_URL}/api/train/scan")
    print(f"   Response: {r.json()}")
    print()

def test_connect(address=None):
    """Connect to train"""
    print(f"🔌 Connecting to train{' at ' + address if address else ''}...")
    data = {"address": address} if address else {}
    r = requests.post(f"{BASE_URL}/api/train/connect", json=data)
    print(f"   Response: {r.json()}")
    print()

def test_speed(speed):
    """Set train speed (0-31)"""
    print(f"🚂 Setting speed to {speed}...")
    r = requests.post(f"{BASE_URL}/api/train/speed", json={"speed": speed})
    print(f"   Response: {r.json()}")
    print()

def test_direction(direction):
    """Set direction (forward/reverse/toggle)"""
    print(f"↔️  Setting direction to {direction}...")
    r = requests.post(f"{BASE_URL}/api/train/direction", json={"direction": direction})
    print(f"   Response: {r.json()}")
    print()

def test_horn():
    """Blow the horn"""
    print("📯 Blowing horn...")
    r = requests.post(f"{BASE_URL}/api/train/horn")
    print(f"   Response: {r.json()}")
    print()

def test_bell(state):
    """Ring the bell"""
    print(f"🔔 Bell {'ON' if state else 'OFF'}...")
    r = requests.post(f"{BASE_URL}/api/train/bell", json={"state": state})
    print(f"   Response: {r.json()}")
    print()

def test_lights(state):
    """Control lights"""
    print(f"💡 Lights {'ON' if state else 'OFF'}...")
    r = requests.post(f"{BASE_URL}/api/train/lights", json={"state": state})
    print(f"   Response: {r.json()}")
    print()

def test_stop():
    """Emergency stop"""
    print("🛑 Emergency stop...")
    r = requests.post(f"{BASE_URL}/api/train/stop")
    print(f"   Response: {r.json()}")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("LionChief Train API Test")
    print("=" * 50)
    print()

    # Check status
    test_status()

    # Test basic controls (will work in mock mode or with real train)
    test_lights(True)
    time.sleep(1)

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

    test_lights(False)

    print("=" * 50)
    print("Test complete!")
    print("=" * 50)
