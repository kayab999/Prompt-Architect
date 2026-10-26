import requests
import json
import sys

# Configuration
API_BASE = "http://127.0.0.1:8000"

def test_mask_machine():
    """Tests the /mask_machine endpoint."""
    print("--- Testing /mask_machine (The Feedback Loop) ---")
    
    payload = {
        "initial_prompt": "i want to create a service for clients",
        "intent": "business development",
        "refiner_model": "deepseek-r1:1.5b",
        "max_iterations": 2
    }
    
    try:
        response = requests.post(f"{API_BASE}/mask_machine", json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Iterations: {result['iterations']}")
        print(f"Success: {result['success']}")
        print("\n--- FINAL PROMPT ---\n")
        print(result['final_prompt'])
        print("\n--- HISTORY ---")
        for h in result['history']:
            it = h.get('iteration', '?')
            print(f"\nIteration {it}:")
            
            if 'error' in h:
                print(f"  ERROR: {h['error']}")
                continue

            # Print Diagnostics
            diagnostics = h.get('diagnostics', [])
            print(f"  Diagnostics found: {len(diagnostics)}")
            for d in diagnostics:
                code = d.get('code', 'UNK')
                msg = d.get('message', '')
                severity = d.get('severity', 'info').upper()
                print(f"    - [{code}] {severity}: {msg}")
            
            # Print Actions (AutoFixer/Refiner)
            actions = h.get('actions', [])
            if actions:
                print(f"  Actions taken:")
                for action in actions:
                    print(f"    -> {action}")
            
            # Print Cognitive Trace (Audit View)
            if 'cognitive_trace' in h:
                trace = h['cognitive_trace']
                preview = trace[:100] + "..." if len(trace) > 100 else trace
                print(f"  [AUDIT] Cognitive Trace: {preview}")

            # Print Prompts if available
            if 'stage_1_prompt' in h:
                 print(f"  [Prompt Start]: {h['stage_1_prompt'][:60]}...")
            if 'stage_3_prompt' in h:
                 print(f"  [Prompt End]  : {h['stage_3_prompt'][:60]}...")
                
    except requests.exceptions.RequestException as e:
        print(f"ERROR: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Detail: {e.response.text}")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        print(f"Raw Response: {response.text if 'response' in locals() else 'N/A'}")

if __name__ == "__main__":
    test_mask_machine()
