"""
simulate.py - a fake two-robot demo you can WATCH.

There's no physics here. We fake a table with red and blue blocks and two
robot arms. Each round:
  1. each robot checks the server for new messages addressed to it
  2. calls decide() from brain.py
  3. posts its message to the server (the robots "talk")
  4. its arm moves toward the block or bin its VLA instruction names
  5. once the arm arrives, the block is picked up or dropped
The world is posted to the server after every step, and the page at
http://localhost:8000/sim draws it live.

Run it (with the server already running):
    python simulate.py
Stop it any time with Ctrl+C.
"""

import math
import os
import random
import time

import requests

from brain import decide, use_mock

SERVER = os.environ.get("SERVER_URL", "http://localhost:8000")
TASK = "sort the red and blue blocks into two bins"
MAX_ROUNDS = int(os.environ.get("ROUNDS", "20"))
MOVE_SECONDS = 1.3   # time for an arm to travel to its target
PAUSE_SECONDS = 0.9  # pause after grabbing / dropping

# ---------------------------------------------------------------------------
# The fake world, on a 100 x 70 grid (the web page scales it to the screen)
# ---------------------------------------------------------------------------
BINS = {"red": [14, 13], "blue": [86, 13]}


def make_blocks():
    """Scatter 4 red and 3 blue blocks across the middle of the table."""
    rng = random.Random(7)  # fixed seed: same layout every run
    blocks = []
    for i, color in enumerate(["red"] * 4 + ["blue"] * 3):
        while True:
            x, y = rng.uniform(30, 70), rng.uniform(24, 44)
            if all(math.hypot(x - b["x"], y - b["y"]) > 8 for b in blocks):
                break
        blocks.append({"id": i, "color": color, "x": round(x, 1), "y": round(y, 1), "where": "table"})
    return blocks


blocks = make_blocks()
robots = {
    "robot_a": {"base": [27, 62], "home": [30, 46], "target": [30, 46], "holding": None, "instruction": ""},
    "robot_b": {"base": [73, 62], "home": [70, 46], "target": [70, 46], "holding": None, "instruction": ""},
}
pending = {"robot_a": None, "robot_b": None}  # what each arm does once it arrives
last_seen = {"robot_a": 0.0, "robot_b": 0.0}  # newest message time each robot has read


def block_by_id(i):
    return next(b for b in blocks if b["id"] == i)


def count(color, where):
    return sum(1 for b in blocks if b["color"] == color and b["where"] == where)


def post_world(round_number, done=False):
    requests.post(f"{SERVER}/world", timeout=5, json={
        "task": TASK, "round": round_number, "done": done,
        "blocks": blocks, "robots": robots, "bins": BINS,
    })


def describe_world(robot_id):
    """Write what the robot 'sees' as a sentence, like a captioned camera view."""
    parts = []
    held = robots[robot_id]["holding"]
    if held is not None:
        parts.append(f"I am holding a {block_by_id(held)['color']} block.")
    parts.append(f"On the table I see {count('red', 'table')} red block(s) and {count('blue', 'table')} blue block(s).")
    parts.append(f"The red bin has {count('red', 'bin')}, the blue bin has {count('blue', 'bin')}.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Turning a plain-English VLA instruction into fake arm motion
# ---------------------------------------------------------------------------
def plan_motion(robot_id, instruction):
    """Pick where the arm should go, based on the words in the instruction."""
    r = robots[robot_id]
    text = instruction.lower()
    colors = [c for c in ("red", "blue") if c in text]

    if any(w in text for w in ("place", "drop", "put")) and r["holding"] is not None:
        b = block_by_id(r["holding"])
        slot = count(b["color"], "bin")  # arrange blocks in the bin in a grid
        bx, by = BINS[b["color"]]
        r["target"] = [bx - 6 + (slot % 3) * 6, by - 3 + (slot // 3) * 6]
        pending[robot_id] = ("place", b["id"])
    elif any(w in text for w in ("pick", "grab", "get", "take")) and r["holding"] is None:
        options = [b for b in blocks if b["where"] == "table" and (not colors or b["color"] in colors)]
        if options:
            hx, hy = r["target"]
            b = min(options, key=lambda b: math.hypot(b["x"] - hx, b["y"] - hy))
            b["where"] = "reserved"  # so the other robot doesn't grab the same one
            r["target"] = [b["x"], b["y"]]
            pending[robot_id] = ("pick", b["id"])
    else:
        r["target"] = list(r["home"])
        pending[robot_id] = None


def finish_motion(robot_id):
    """The arm has arrived: actually grab or drop the block."""
    action = pending[robot_id]
    if not action:
        return
    kind, block_id = action
    b = block_by_id(block_id)
    if kind == "pick":
        b["where"] = "held"
        robots[robot_id]["holding"] = block_id
    else:
        b["where"] = "bin"
        b["x"], b["y"] = robots[robot_id]["target"]
        robots[robot_id]["holding"] = None
    pending[robot_id] = None


# ---------------------------------------------------------------------------
# One robot's turn: read, think, talk
# ---------------------------------------------------------------------------
def robot_turn(robot_id):
    new = requests.get(f"{SERVER}/messages/{robot_id}", params={"since": last_seen[robot_id]}, timeout=5).json()
    if new:
        last_seen[robot_id] = max(m["timestamp"] for m in new)

    observation = describe_world(robot_id)
    result = decide(robot_id, TASK, observation, new)

    requests.post(f"{SERVER}/messages", timeout=5, json={
        "from": robot_id, "to": "all",
        "message": result["message_to_send"],
        "my_status": result["vla_instruction"],
        "timestamp": time.time(),
    })
    robots[robot_id]["instruction"] = result["vla_instruction"]

    print(f"  {robot_id} sees:  {observation}")
    print(f"  {robot_id} says:  {result['message_to_send']}")
    print(f"  {robot_id} VLA -> {result['vla_instruction']}\n")
    plan_motion(robot_id, result["vla_instruction"])


def main():
    try:
        requests.post(f"{SERVER}/reset", timeout=3)
    except requests.exceptions.ConnectionError:
        print(f"Can't reach the server at {SERVER}. Start it first in another Terminal tab:")
        print("    uvicorn server:app --port 8000")
        return

    print(f"Brain mode: {'MOCK (free, no API key)' if use_mock() else 'REAL (calling Claude)'}")
    print(f"Task: {TASK}")
    print(f"Watch it at {SERVER}/sim\n")
    post_world(0)
    time.sleep(1.5)

    for round_number in range(1, MAX_ROUNDS + 1):
        print(f"--- Round {round_number} ---")
        for robot_id in robots:
            robot_turn(robot_id)
        post_world(round_number)          # arms start moving
        time.sleep(MOVE_SECONDS)
        for robot_id in robots:
            finish_motion(robot_id)
        post_world(round_number)          # blocks grabbed / dropped
        time.sleep(PAUSE_SECONDS)

        if all(b["where"] == "bin" for b in blocks):
            for r in robots.values():
                r["target"] = list(r["home"])
                r["instruction"] = "stay still"
            post_world(round_number, done=True)
            print(f"All blocks sorted! Red bin: {count('red', 'bin')}, blue bin: {count('blue', 'bin')}")
            break


if __name__ == "__main__":
    main()
