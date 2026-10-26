#!/bin/bash
# test-backend.sh

echo "Testing backend connection..."

# Check if port 8000 is in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✓ Port 8000 is listening"
    
    # Test the status endpoint
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/status)
    if [ "$response" = "200" ]; then
        echo "✓ Backend is responding correctly"
    else
        echo "✗ Backend responded with HTTP $response"
    fi
else
    echo "✗ No service found on port 8000"
    echo "Please start your Python backend server:"
    echo "  cd /path/to/your/backend"
    echo "  python main.py"
fi