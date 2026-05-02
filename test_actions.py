#!/usr/bin/env python3
"""
Test script to manually set mock actions for the Focus Buddy extension.
Usage: python test_actions.py <action> [score] [reason]
Examples:
  python test_actions.py allow
  python test_actions.py soft_alert 75 "You've been scrolling for 10 minutes"
  python test_actions.py hard_block 95 "YouTube is blocked during study hours"
"""

import requests
import sys
import json

BACKEND_URL = "http://127.0.0.1:8000"

def set_action(action: str, score: int = None, reason: str = None, confidence: float = None):
    """Set a mock action response"""
    if action not in ["allow", "soft_alert", "hard_block"]:
        print(f"❌ Invalid action: {action}")
        print("   Valid actions: allow, soft_alert, hard_block")
        return False
    
    payload = {
        "action": action,
        "procrastinationScore": score,
        "reason": reason,
        "confidence": confidence or (0.95 if action != "allow" else None),
    }
    
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    try:
        response = requests.post(f"{BACKEND_URL}/api/debug/set-mock-action", json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Mock action set: {json.dumps(result['mock_response'], indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def get_current_action():
    """Get the current mock action"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/debug/get-mock-action")
        response.raise_for_status()
        result = response.json()
        if result['mock_response']:
            print(f"📊 Current mock action: {json.dumps(result['mock_response'], indent=2)}")
        else:
            print("📊 No mock action set (using real classification)")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def reset_action():
    """Reset mock action"""
    try:
        response = requests.post(f"{BACKEND_URL}/api/debug/reset-mock-action")
        response.raise_for_status()
        result = response.json()
        print(f"✅ Mock action reset - now using real classification")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_actions.py <command> [args]")
        print("\nCommands:")
        print("  set <action> [score] [reason]     Set a mock action")
        print("  get                               Show current mock action")
        print("  reset                             Reset to real classification")
        print("\nExamples:")
        print("  python test_actions.py set allow")
        print("  python test_actions.py set soft_alert 75 \"Scrolling detected\"")
        print("  python test_actions.py set hard_block 95 \"YouTube blocked\"")
        print("  python test_actions.py get")
        print("  python test_actions.py reset")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "set":
        if len(sys.argv) < 3:
            print("❌ Missing action. Usage: python test_actions.py set <action> [score] [reason]")
            sys.exit(1)
        
        action = sys.argv[2]
        score = int(sys.argv[3]) if len(sys.argv) > 3 else None
        reason = sys.argv[4] if len(sys.argv) > 4 else None
        
        set_action(action, score, reason)
    
    elif command == "get":
        get_current_action()
    
    elif command == "reset":
        reset_action()
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
