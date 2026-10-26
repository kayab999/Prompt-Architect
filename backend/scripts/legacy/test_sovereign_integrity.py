import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def test_endpoint(name, payload, expected_status=200):
    print(f"\nTesting Module: {name}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start_time = time.time()
    try:
        response = requests.post(f"{BASE_URL}/mask_machine", json=payload)
        duration = time.time() - start_time
        
        if response.status_code == expected_status:
            print(f"✔ SUCCESS (Status {response.status_code}) - {duration:.2f}s")
            return response.json()
        else:
            print(f"✘ FAILED (Status {response.status_code})")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"✘ EXCEPTION: {e}")
        return None

def analyze_result(result, flavor):
    if not result: return

    print(f"\n--- Audit Report ({flavor}) ---")
    print(f"ID: {result.get('id')}")
    print(f"Success: {result.get('success')}")
    print(f"Iterations: {result.get('iterations')}")
    
    history = result.get('history', [])
    print(f"History Entries: {len(history)}")
    
    if history:
        last_entry = history[-1]
        print(f"Last Confidence: {last_entry.get('confidence')}")
        
    sig = result.get('integrity_signature')
    if sig:
        print(f"Integrity Signature: {sig.get('hash')[:10]}...")

if __name__ == "__main__":
    print_section("KAYAB SOVEREIGN GOVERNOR INTEGRITY TEST")
    
    # Test 1: Technical Flavor (Subjective Input)
    payload_tech = {
        "user_input": "make the code better",
        "flavor": "technical",
        "max_iterations": 2,
        "refiner_model": "deepseek-r1:1.5b"
    }
    result_tech = test_endpoint("Technical Flavor (Constraint Check)", payload_tech)
    analyze_result(result_tech, "Technical")
    
    # Test 2: Creative Flavor (Permissive Check)
    payload_creative = {
        "user_input": "make the story better",
        "flavor": "creative",
        "max_iterations": 2,
        "refiner_model": "deepseek-r1:1.5b"
    }
    result_creative = test_endpoint("Creative Flavor (Permissive Check)", payload_creative)
    analyze_result(result_creative, "Creative")