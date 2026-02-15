#!/bin/bash
# Start iamtoxico Shopping Valet locally

cd "$(dirname "$0")"

echo "🖤 iamtoxico valet starting..."
echo ""

# Check if venv exists, if not use system python
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Using local venv"
elif [ -d "/Users/jasonjenkins/Desktop/localmodels/.venv" ]; then
    source /Users/jasonjenkins/Desktop/localmodels/.venv/bin/activate
    echo "Using localmodels venv"
else
    echo "Using system Python"
fi

# Check for required packages
python -c "import flask" 2>/dev/null || pip install flask flask-cors requests python-dotenv

# Start server
echo ""
echo "Server starting at: http://localhost:8080"
echo "Valet interface at: http://localhost:8080/valet.html"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python server.py
