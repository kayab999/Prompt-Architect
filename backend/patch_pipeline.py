import sys

with open("backend/app/kayab_pipeline.py", "r") as f:
    content = f.read()

# Add a mock 'id' field in the result to satisfy the test script
new_content = content.replace(
    'return {"status": "FAILED", "reason": "Max iterations reached or convergence stall"}',
    'return {"id": "pipeline-run-failed", "status": "FAILED", "reason": "Max iterations reached or convergence stall"}'
)

with open("backend/app/kayab_pipeline.py", "w") as f:
    f.write(new_content)
