# Robot Communication Backend

Robots coordinate by talking to each other in plain English. This folder is the
communication layer: a message server, a "brain" that decides what each robot
says and does, and a demo with two fake robots.

| File | What it is |
|---|---|
| `server.py` | The robots' group chat: stores messages and streams them live to the website |
| `brain.py` | `decide()`: reads the task, what the robot sees, and its messages; returns what to say + an instruction for the robot's VLA model |
| `simulate.py` | Two fake robots sorting red and blue blocks, to prove it all works |
| `sim.html` | The visual simulation page (animated robot arms + live chat), at http://localhost:8000/sim |
| `Run Demo.command` | Double-click to set up and run the whole demo |
| `requirements.txt` | The Python packages this project needs |

---

## Quickest way: double-click

Open the `robot-backend` folder and double-click **Run Demo**. It installs everything the first time,
starts the server, opens the visual simulation in your browser, and runs the robots.
(If macOS blocks it: right-click it, choose Open, then Open again.)

Or from VS Code: Terminal > New Terminal, then type `bash "Run Demo.command"`.

The manual steps below do the same thing.

## 1. Install (Mac, one time)

Open **Terminal** (Cmd+Space, type "Terminal", press Enter) and paste these one at a time.

Check Python:
```
python3 --version
```
If a popup asks to install "command line developer tools", click **Install**, wait, then run it again.
You need Python 3.9 or higher. If the command still doesn't work, install Python from https://www.python.org/downloads/ and reopen Terminal.

Go to the project folder and set it up (this assumes the folder is on your Desktop):
```
cd ~/Desktop/robot-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
`(venv)` should now show at the start of the Terminal line.

**Every time you open a new Terminal window or tab for this project, first run:**
```
cd ~/Desktop/robot-backend
source venv/bin/activate
```

## 2. Start the server

```
uvicorn server:app --reload --port 8000
```
Leave this tab open. Check it in your browser:
- http://localhost:8000 should show `"status": "ok"`
- http://localhost:8000/messages lists every message
- http://localhost:8000/docs is a clickable test page for every endpoint

## 3. Run the demo

Open a **second** Terminal tab (Cmd+T), run the two "every time" lines above, then:
```
python simulate.py
```
Open **http://localhost:8000/sim** to watch the robot arms move blocks and chat live.
Terminal also prints what each robot sees, says, and sends to its VLA. Press **Ctrl+C** to stop anything.

By default the brain runs in **MOCK mode** (free, instant, no API key).
To use real Claude, run this in the same tab before `python simulate.py`:
```
export ANTHROPIC_API_KEY="paste-your-key-here"
```
To force mock mode even with a key set: `export BRAIN_MOCK=1`

---

## For the FRONTEND teammate

- **Live feed (WebSocket):** `ws://localhost:8000/ws/feed`
  On connect you get every past message, then each new one as it happens. One JSON object per WebSocket message.
- **All messages (HTTP):** `GET http://localhost:8000/messages`
- **World state (for drawing the scene):** `GET http://localhost:8000/world` returns blocks, robot arm positions and bins. `sim.html` is a working example that draws it.
- CORS is open, so your site can connect from any address.
- If you're on a different laptop, replace `localhost` with the backend laptop's IP address (System Settings > Wi-Fi > Details), and the server must be started with `--host 0.0.0.0` added.

Message format:
```json
{
  "from": "robot_a",
  "to": "robot_b",
  "message": "I'll take the red blocks.",
  "my_status": "pick up the nearest red block",
  "timestamp": 1792812963.12
}
```
`to` is a robot id or `"all"`. `timestamp` is unix time in seconds, set by the server.

Minimal example:
```js
const ws = new WebSocket("ws://localhost:8000/ws/feed");
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  console.log(`${msg.from} -> ${msg.to}: ${msg.message}`);
};
```

---

## For the ML teammate

Put `brain.py` next to your simulation code (or add this folder to your Python path).

**Simplest: just get the VLA instruction string**
```python
from brain import get_vla_instruction

instruction = get_vla_instruction(
    robot_id="robot_a",
    task="sort the red and blue blocks into two bins",
    observation_text="I see 2 red blocks and 1 blue block on the table.",
    new_messages=[],   # list of message dicts from the server
)
# instruction -> "pick up the nearest red block"
# feed it to your VLA as the language prompt
```

**Full version: also get the message to send to teammates**
```python
from brain import decide
import requests, time

SERVER = "http://localhost:8000"
last_seen = 0.0

new = requests.get(f"{SERVER}/messages/robot_a", params={"since": last_seen}).json()
if new:
    last_seen = max(m["timestamp"] for m in new)

result = decide("robot_a", task, observation_text, new)
requests.post(f"{SERVER}/messages", json={
    "from": "robot_a", "to": "all",
    "message": result["message_to_send"],
    "my_status": result["vla_instruction"],
    "timestamp": time.time(),
})
vla_prompt = result["vla_instruction"]
```

`observation_text` is whatever text description of the scene you can produce
(from the sim state, object detector, or a captioning model). `simulate.py` shows
a full working loop. When your real simulation is ready, it replaces `simulate.py`.

Notes:
- Uses `claude-haiku-5-5` (fast and cheap). Change with `export BRAIN_MODEL=claude-sonnet-5-5`.
- If a Claude call fails, `decide()` falls back to a mock answer instead of crashing.
- Messages are stored in memory, so they're cleared when the server restarts.
