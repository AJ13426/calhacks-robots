"""One robot agent connected to the hive mind.

Run one per robot, each in its own Terminal window:
  python3 agent.py K9 --fake
  python3 agent.py NR7 --fake

--fake  : no hardware. The robot "thinks" with simple rules from its card and "acts" by printing.
(real mode with the VLM, the Sphero and the Arduino comes later)
"""
import argparse
import json
import math
import time

from cards import ARM_ZONE, CARDS
from hive import Hive, HiveError

TICK = 0.5          # seconds between checks of the hive
HEARTBEAT = 2.0     # seconds between position/battery updates
DECIDE_AFTER = 3.0  # if not everyone has bid by then, ask the hive to decide anyway


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def say(robot_id, text):
    print(f"[{time.strftime('%H:%M:%S')}] {robot_id}: {text}", flush=True)


class Agent:
    def __init__(self, robot_id, fake=True):
        self.id = robot_id
        self.card = CARDS[robot_id]
        self.fake = fake
        self.hive = Hive()
        self.x = self.card["start"]["x"]
        self.y = self.card["start"]["y"]
        self.battery = 100.0
        self.bid_on = set()      # (job_id, attempts) we already bid on
        self.bid_time = {}       # job_id -> when we bid
        self.last_beat = 0.0

    # ---------- hive mind ----------
    def register(self):
        card = {k: v for k, v in self.card.items() if k != "start"}
        self.hive.call("register_robot", self.id, self.card["type"], json.dumps(card), self.x, self.y, self.battery)
        say(self.id, f"registered with the hive. Card: {json.dumps(card)}")

    def beat(self, force=False):
        if force or time.time() - self.last_beat > HEARTBEAT:
            self.hive.call("update_robot", self.id, self.x, self.y, self.battery)
            self.last_beat = time.time()

    # ---------- thinking ----------
    def think(self, job):
        if self.fake:
            return self.think_fake(job)
        raise NotImplementedError("Real VLM thinking gets added with vision.py")

    def think_fake(self, job):
        """Stand in for the VLM. Gives the same shape of answer the VLM will give."""
        jx, jy, size, desc = job["x"], job["y"], job["object_cm"], job["description"]
        to_zone = dist(jx, jy, ARM_ZONE["x"], ARM_ZONE["y"])
        in_zone = to_zone <= ARM_ZONE["r"]
        c = self.card
        if c["can_move"]:  # K9
            obs = f"{desc} at ({jx:.0f}, {jy:.0f}) cm, {to_zone:.0f} cm from the arm"
            if size > c.get("max_push_cm", 999):
                return dict(observation=obs, can_help=False, action="none", eta_s=0, plan="",
                            reasoning=f"It is {size:.0f} cm. Too big for me to push and I can't lift.")
            if in_zone:
                return dict(observation=obs, can_help=False, action="none", eta_s=0, plan="",
                            reasoning="It's already inside the arm zone. NR7 can grab it. I can't lift.")
            travel = dist(self.x, self.y, jx, jy) + to_zone
            return dict(observation=obs, can_help=True, action="push_to_zone",
                        eta_s=round(travel / c["speed_cm_per_s"], 1), plan="push the cube into the arm zone",
                        reasoning="The arm can't reach that spot. I can roll there and push it over.")
        else:  # NR7
            if not in_zone:
                return dict(observation="Nothing in my corner. I only know about this from the hive.",
                            can_help=False, action="none", eta_s=0, plan="",
                            reasoning=f"It's {to_zone:.0f} cm from my base and my reach is {ARM_ZONE['r']:.0f} cm. Out of reach.")
            obs = f"{desc} inside my zone, {to_zone:.0f} cm from my base"
            if size > c.get("max_object_cm", 999):
                return dict(observation=obs, can_help=False, action="none", eta_s=0, plan="",
                            reasoning=f"It is {size:.0f} cm. My claw opens to {c['max_object_cm']} cm.")
            return dict(observation=obs, can_help=True, action="grab", eta_s=2.5, plan="grab the cube",
                        reasoning="It's in reach and small enough for my claw.")

    # ---------- acting ----------
    def act(self, job, assignment):
        if not self.fake:
            raise NotImplementedError("Real actions get added when the hardware arrives")
        action = assignment["action"]
        say(self.id, f">>> I WON job {job['id']}. Action: {action}. Plan: {assignment['plan']}")
        if action == "push_to_zone":
            jx, jy = job["x"], job["y"]
            # point behind the cube, on the side away from the arm
            dx, dy = jx - ARM_ZONE["x"], jy - ARM_ZONE["y"]
            n = math.hypot(dx, dy) or 1
            bx, by = jx + dx / n * 6, jy + dy / n * 6
            self.drive_to(bx, by, "driving behind the cube")
            tx, ty = ARM_ZONE["x"] + dx / n * 6, ARM_ZONE["y"] + dy / n * 6  # cube ends up inside the zone
            self.drive_to(tx + dx / n * 6, ty + dy / n * 6, "pushing the cube toward the arm")
            say(self.id, f"cube delivered at ({tx:.0f}, {ty:.0f})")
            self.hive.call("complete_job", job["id"], self.id, "Cube pushed into the arm zone", tx, ty)
        elif action == "grab":
            for step in ("rotate base toward the cube", "lower the arm", "close the claw", "lift"):
                say(self.id, f"  {step}")
                time.sleep(0.6)
                self.beat(force=True)
            self.hive.call("complete_job", job["id"], self.id, "Cube grabbed and lifted", job["x"], job["y"])
            say(self.id, "done. Cube is in my claw.")
        else:
            self.hive.call("fail_job", job["id"], self.id, f"don't know how to {action}", job["x"], job["y"])

    def drive_to(self, tx, ty, label):
        say(self.id, f"  {label} ({tx:.0f}, {ty:.0f})")
        speed = self.card["speed_cm_per_s"]
        while True:
            d = dist(self.x, self.y, tx, ty)
            if d < 1:
                break
            step = min(d, speed * 0.25)
            self.x += (tx - self.x) / d * step
            self.y += (ty - self.y) / d * step
            self.battery = max(0.0, self.battery - 0.05)
            self.beat(force=True)
            time.sleep(0.25)

    # ---------- main loop ----------
    def step(self):
        self.beat()
        for job in self.hive.sql("SELECT * FROM job WHERE status = 'open'"):
            key = (job["id"], job["attempts"])
            if key in self.bid_on:
                if time.time() - self.bid_time.get(job["id"], 0) > DECIDE_AFTER:
                    self.hive.call("decide_job", job["id"])
                continue
            t = self.think(job)
            self.hive.call("post_thought", self.id, job["id"], t["observation"], t["reasoning"])
            self.hive.call("submit_bid", job["id"], self.id, t["can_help"], t["action"], float(t["eta_s"]), t["plan"], t["reasoning"])
            self.bid_on.add(key)
            self.bid_time[job["id"]] = time.time()
            word = f"BID {t['action']} eta {t['eta_s']}s" if t["can_help"] else "PASS"
            say(self.id, f"job {job['id']}: {word}. {t['reasoning']}")
        mine = self.hive.sql(f"SELECT * FROM assignment WHERE robot_id = '{self.id}' AND status = 'active'")
        for a in mine:
            jobs = self.hive.sql(f"SELECT * FROM job WHERE id = {a['job_id']}")
            if jobs:
                self.act(jobs[0], a)

    def run(self):
        self.register()
        say(self.id, "watching the hive for jobs. Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    self.step()
                except HiveError as e:
                    say(self.id, f"hive error: {e}")
                    time.sleep(2)
                time.sleep(TICK)
        except KeyboardInterrupt:
            try:
                self.hive.call("set_robot_offline", self.id)
            except Exception:
                pass
            say(self.id, "offline. Bye.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("robot", choices=sorted(CARDS))
    ap.add_argument("--fake", action="store_true", help="no hardware, rule based thinking, printed actions")
    args = ap.parse_args()
    if not args.fake:
        raise SystemExit("Only --fake works right now. Real mode comes with the hardware.")
    Agent(args.robot, fake=True).run()
