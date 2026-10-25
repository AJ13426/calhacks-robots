#!/bin/bash
# Double-click this file to run the whole demo.
# It sets everything up, starts the server, opens the live chat in your
# browser, and runs the two fake robots. Close this window to stop.

cd "$(dirname "$0")"

echo "=== Robot backend demo ==="

# 1. Make sure Python is installed.
if ! python3 --version >/dev/null 2>&1; then
  echo ""
  echo "Python isn't set up yet. If a pop-up asks to install 'command line"
  echo "developer tools', click Install, wait for it to finish, then"
  echo "double-click 'Run Demo' again."
  read -p "Press Enter to close."
  exit 1
fi

# 2. One-time setup: a private Python sandbox + the packages we need.
if [ ! -d venv ]; then
  echo "First run: setting things up (takes a minute)..."
  python3 -m venv venv || { read -p "Setup failed. Press Enter to close."; exit 1; }
fi
source venv/bin/activate
pip install -q -r requirements.txt || { read -p "Installing packages failed (are you online?). Press Enter to close."; exit 1; }

# 3. Start the server in the background, and stop it when this window closes.
# Pick any free port, so a leftover server from a previous run can't block us.
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
export SERVER_URL="http://localhost:$PORT"

uvicorn server:app --port $PORT --log-level warning &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT HUP INT TERM

echo "Starting server..."
for i in $(seq 1 30); do
  curl -s http://localhost:$PORT >/dev/null && break
  sleep 0.5
done

# 4. Open the visual simulation in your browser.
open http://localhost:$PORT/sim
sleep 3

# 5. Run the two fake robots.
python simulate.py

echo ""
echo "Demo finished. Double-click Run Demo again to replay it."
read -p "Press Enter to close (this also stops the server)."
