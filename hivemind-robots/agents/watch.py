"""Live view of the hive mind in the Terminal. Ctrl+C to stop."""
import time
from hive import Hive, HiveError

h = Hive()
while True:
    try:
        robots = h.sql("SELECT * FROM robot")
        jobs = sorted(h.sql("SELECT * FROM job"), key=lambda r: r["id"])[-6:]
        bids = sorted(h.sql("SELECT * FROM bid"), key=lambda r: r["id"])[-8:]
        thoughts = sorted(h.sql("SELECT * FROM thought"), key=lambda r: r["id"])[-10:]
        out = ["\033[2J\033[H=== HIVE MIND ===", "", "ROBOTS"]
        for r in robots:
            out.append(f"  {r['id']:<4} {r['status']:<8} at ({r['x']:5.1f}, {r['y']:5.1f})  battery {r['battery']:.0f}%")
        out += ["", "JOBS"]
        for j in jobs:
            out.append(f"  #{j['id']:<3} {j['status']:<9} {j['assigned_to']:<4} {j['description']} at ({j['x']:.0f}, {j['y']:.0f})  {j['note']}")
        out += ["", "BIDS"]
        for b in bids:
            out.append(f"  job {b['job_id']:<3} {b['robot_id']:<4} {b['action']:<13} eta {b['eta_s']:<5} {b['verdict']}")
        out += ["", "THOUGHTS"]
        for t in thoughts:
            out.append(f"  {t['robot_id']:<4} {t['observation']}  |  {t['reasoning']}")
        print("\n".join(out), flush=True)
    except HiveError as e:
        print(e)
    time.sleep(0.7)
