"""
server.py - the "group chat" for the robots.

Think of this as a tiny chat app with no humans in it:
  - Robots POST messages to it.
  - Robots GET the messages addressed to them.
  - The frontend website listens on a live WebSocket and sees every message
    the instant it arrives, so it can show the robots "chatting".

Messages are kept in a plain Python list in memory. That means they vanish
when you stop the server. That's fine for a hackathon demo.

Start it with:
    uvicorn server:app --reload --port 8000
"""

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# The message format
# ---------------------------------------------------------------------------
class Message(BaseModel):
    """
    One robot message. On the wire (JSON) it looks exactly like:
        {
          "from": "robot_a",
          "to": "robot_b"  or  "all",
          "message": "natural language message",
          "my_status": "short description of what I'm doing",
          "timestamp": 1761279000.123
        }

    "from" is a reserved word in Python, so inside the code the field is
    called from_robot, but it is always read and written as "from" in JSON.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_robot: str = Field(alias="from")
    to: str = "all"
    message: str
    my_status: str = ""
    # Robots may send a timestamp, but the server replaces it with its own
    # clock when the message arrives. That way every message is stamped by
    # one clock, and "give me messages since X" never misses anything because
    # two laptops' clocks disagree.
    timestamp: Optional[float] = None

    def to_json(self) -> dict:
        """Turn the message into a plain dict using "from" (not from_robot)."""
        return self.model_dump(by_alias=True)


# ---------------------------------------------------------------------------
# The app itself
# ---------------------------------------------------------------------------
app = FastAPI(title="Robot message server")

# CORS lets a website running on a different address (like the frontend's
# localhost:3000) talk to this server. "*" means "allow anyone", which is
# fine for a hackathon but not for a real product.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# All messages ever sent, oldest first.
messages: list[dict] = []

# Every website/browser currently watching the live feed.
feed_listeners: set[WebSocket] = set()


@app.get("/")
def home():
    """A quick 'is it alive?' page."""
    return {"status": "ok", "message_count": len(messages), "live_viewers": len(feed_listeners)}


@app.post("/messages")
async def send_message(msg: Message):
    """A robot sends a message. It gets saved and pushed to the live feed."""
    msg.timestamp = time.time()  # server clock wins (see note above)
    record = msg.to_json()
    messages.append(record)

    # Push it to everyone watching the live feed. If a browser tab closed
    # without saying goodbye, sending fails, so we quietly drop it.
    for ws in list(feed_listeners):
        try:
            await ws.send_json(record)
        except Exception:
            feed_listeners.discard(ws)

    return {"ok": True, "saved": record}


@app.get("/messages")
def all_messages():
    """Every message, for debugging. Open http://localhost:8000/messages."""
    return messages


@app.get("/messages/{robot_id}")
def messages_for_robot(robot_id: str, since: float = 0.0):
    """
    New messages for one robot: anything sent to that robot or to "all",
    newer than `since` (a unix timestamp). A robot's own messages are left
    out so it doesn't "hear" itself.

    Example: /messages/robot_b?since=1761279000.5
    """
    return [
        m
        for m in messages
        if m["timestamp"] > since
        and m["to"] in (robot_id, "all")
        and m["from"] != robot_id
    ]


# ---------------------------------------------------------------------------
# The visual simulation
# ---------------------------------------------------------------------------
# The latest snapshot of the (fake) world: where every block and robot arm is.
# simulate.py posts it; the /sim web page reads it and draws it.
world_state: dict = {}

SIM_PAGE = Path(__file__).parent / "sim.html"


@app.post("/world")
def set_world(state: dict):
    """The simulation posts the current world snapshot here."""
    world_state.clear()
    world_state.update(state)
    return {"ok": True}


@app.get("/world")
def get_world():
    """The latest world snapshot (blocks, robot arms, bins)."""
    return world_state


@app.post("/reset")
def reset():
    """Wipe all messages and the world, for a fresh demo run."""
    messages.clear()
    world_state.clear()
    return {"ok": True}


@app.get("/sim")
def sim_page():
    """The visual simulation. Open http://localhost:8000/sim"""
    return HTMLResponse(SIM_PAGE.read_text())


@app.websocket("/ws/feed")
async def live_feed(ws: WebSocket):
    """
    The live feed for the frontend. When a browser connects, it first gets
    every message so far (so the chat isn't blank), then each new message
    as it arrives, one JSON object at a time.
    """
    await ws.accept()
    for m in messages:
        await ws.send_json(m)
    feed_listeners.add(ws)
    try:
        # We don't expect the browser to send anything; this just waits
        # until it disconnects.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        feed_listeners.discard(ws)
