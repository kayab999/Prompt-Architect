import requests
import json

# Configuration
API_BASE = "http://127.0.0.1:8000"

def test_status():
    """Tests the /status endpoint."""
    print("--- Testing /status ---")
    try:
        response = requests.get(f"{API_BASE}/status")
        response.raise_for_status() # Raise an exception for bad status codes
        print("Status: OK")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect to backend. Is it running? \n{e}")

def test_models():
    """Tests the /models endpoint."""
    print("\n--- Testing /models ---")
    try:
        response = requests.get(f"{API_BASE}/models")
        response.raise_for_status()
        print("Status: OK")
        print(json.dumps(response.json(), indent=2))
        return response.json() # Return models for the next test
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect to backend. \n{e}")
        return []

def test_optimize(model: str):
    """Tests the /optimize endpoint with a sample prompt."""
    print(f"\n--- Testing /optimize with model: {model} ---")
    if not model:
        print("SKIPPING: No model available for test.")
        return

    payload = {
        "prompt": "Write a short python script to list files in a directory.",
        "model": model,
        "intent": "coding"
    }
    try:
        response = requests.post(f"{API_BASE}/optimize", json=payload)
        response.raise_for_status()
        print("Status: OK")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect or received bad status. \n{e}")

if __name__ == "__main__":
    print("==================================")
    print("  Prompt Architect Backend Tester   ")
    print("==================================")
    test_status()
    available_models = test_models()
    if available_models:
        # Test with the first available model
        test_optimize(available_models[0])
    else:
        print("\nCould not retrieve any models to test the /optimize endpoint.")
