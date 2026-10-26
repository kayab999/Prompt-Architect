import sys

with open("backend/app/kayab_pipeline.py", "r") as f:
    content = f.read()

# Replace the previous mock with one that satisfies the test script requirements
new_content = content.replace(
    'return {"id": "pipeline-run-failed", "status": "FAILED", "reason": "Max iterations reached or convergence stall"}',
    'return {"id": "pipeline-run-failed", "status": "FAILED", "reason": "Max iterations reached or convergence stall", "success_gate": {"passed": False}, "control_log": []}'
)

with open("backend/app/kayab_pipeline.py", "w") as f:
    f.write(new_content)
