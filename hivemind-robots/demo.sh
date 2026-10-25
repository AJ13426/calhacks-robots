#!/bin/bash
# Opens the fake demo in separate Terminal windows: server, live view, K9, NR7.
cd "$(dirname "$0")"; R="$(pwd)"
export PATH="$HOME/.local/bin:$PATH"
nc -z 127.0.0.1 3100 2>/dev/null || (nohup spacetime start --listen-addr 127.0.0.1:3100 > logs/server.log 2>&1 &) 
sleep 2
for c in "python3 watch.py" "python3 agent.py K9 --fake" "python3 agent.py NR7 --fake"; do
  osascript -e "tell application \"Terminal\" to do script \"cd '$R/agents' && $c\""
done
echo "Now type here:  cd agents && python3 make_job.py far"
