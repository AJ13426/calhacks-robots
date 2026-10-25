#!/bin/bash
# One shot setup and self test for the hive mind. Safe to run again.
# Everything it prints is also saved to setup.log.
cd "$(dirname "$0")"
ROOT="$(pwd)"
mkdir -p logs
exec > >(tee setup.log) 2>&1
export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/current/bin:$PATH"
step(){ echo; echo "===== $* ====="; }
fail(){ echo; echo "SETUP STOPPED: $*"; echo "Tell Claude it stopped."; exit 1; }

step "1. Python"
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install
  fail "macOS is installing developer tools in a popup window. Click Install, wait for it to finish, then run this again."
fi
python3 --version || fail "python3 not working"

step "2. Node.js"
if ! command -v node >/dev/null; then
  echo "Node missing. Installing it with nvm (no password needed)."
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash || fail "nvm install failed"
fi
export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
if ! command -v node >/dev/null; then nvm install --lts || fail "node install failed"; fi
node --version; npm --version

step "3. SpacetimeDB CLI"
if ! command -v spacetime >/dev/null; then
  curl -sSf https://install.spacetimedb.com | sh -s -- --yes || curl -sSf https://install.spacetimedb.com | sh || fail "spacetime install failed"
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v spacetime || fail "spacetime installed but not found on PATH"
spacetime --version

step "4. Module project"
if [ ! -d module ] || [ -z "$(ls -A module 2>/dev/null)" ]; then
  spacetime init --local --non-interactive --server-only --lang typescript --project-path module hivemind </dev/null || fail "spacetime init failed"
fi
IDX="$(grep -rl --include=index.ts "spacetimedb/server" module | grep -v node_modules | head -1)"
[ -n "$IDX" ] || IDX="$(find module -path '*/src/index.ts' -not -path '*/node_modules/*' | head -1)"
[ -n "$IDX" ] || fail "could not find the module's src/index.ts. Folder looks like: $(find module -maxdepth 3 -not -path '*/node_modules*')"
MODDIR="$(dirname "$(dirname "$IDX")")"
cp module_source/index.ts "$IDX"
echo "Module code placed at $IDX"
if [ -f "$MODDIR/package.json" ]; then (cd "$MODDIR" && npm install --silent) || fail "npm install failed"; fi
[ -f module/package.json ] && [ "$MODDIR" != "module" ] && (cd module && npm install --silent)

step "5. Local SpacetimeDB server"
if nc -z 127.0.0.1 3100 2>/dev/null; then echo "already running"; else
  nohup spacetime start --listen-addr 127.0.0.1:3100 > logs/server.log 2>&1 &
  for i in $(seq 1 30); do nc -z 127.0.0.1 3100 2>/dev/null && break; sleep 1; done
  nc -z 127.0.0.1 3100 || fail "server did not start. See logs/server.log"
  echo "server started"
fi

step "6. Publish hivemind"
spacetime publish --server local --module-path "$MODDIR" hivemind -y </dev/null \
 || spacetime publish --server local --module-path "$MODDIR" hivemind -y --delete-data </dev/null \
 || fail "publish failed"
echo "$MODDIR" > logs/moddir.txt

step "7. Quick reducer test"
spacetime call --server local hivemind reset_demo </dev/null || fail "reset_demo call failed"
spacetime sql --server local hivemind "SELECT * FROM robot" </dev/null || fail "sql failed"

step "8. Full loop with fake robots"
cd agents
python3 -u agent.py K9 --fake > ../logs/K9.log 2>&1 & K9=$!
python3 -u agent.py NR7 --fake > ../logs/NR7.log 2>&1 & NR7=$!
sleep 4
python3 make_job.py far; sleep 14
python3 make_job.py big; sleep 6
kill $K9 $NR7 2>/dev/null; sleep 1
echo "--- K9 said:"; cat ../logs/K9.log
echo "--- NR7 said:"; cat ../logs/NR7.log
echo "--- Hive mind contents:"; python3 hive.py
cd "$ROOT"
step "SETUP FINISHED"
