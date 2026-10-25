"""Create a test job without a camera.

  python3 make_job.py near       scenario 1: cube lands inside the arm zone
  python3 make_job.py far        scenario 2: cube lands far away (dog pushes, arm grabs)
  python3 make_job.py big        scenario 3: something too big for anyone
  python3 make_job.py 60 40      cube at x=60, y=40 cm
  python3 make_job.py 60 40 --size 12 --desc "water bottle"
  python3 make_job.py reset      clear all jobs, bids and thoughts
"""
import argparse
from hive import Hive

PRESETS = {
    "near": (10.0, 15.0, 3.0, "orange cube"),
    "far": (70.0, 60.0, 3.0, "orange cube"),
    "big": (50.0, 50.0, 25.0, "large box"),
}

ap = argparse.ArgumentParser()
ap.add_argument("where", help="near, far, big, reset, or an x value")
ap.add_argument("y", nargs="?", type=float)
ap.add_argument("--size", type=float, default=3.0, help="object size in cm")
ap.add_argument("--desc", default="orange cube")
a = ap.parse_args()

hive = Hive()
if a.where == "reset":
    hive.call("reset_demo")
    print("Cleared jobs, bids, thoughts and assignments.")
    raise SystemExit
if a.where in PRESETS:
    x, y, size, desc = PRESETS[a.where]
else:
    x, y, size, desc = float(a.where), a.y, a.size, a.desc
hive.call("create_job", "pick_up", desc, x, y, size, 0)
print(f"Created job: {desc} ({size:.0f} cm) at ({x:.0f}, {y:.0f})")
