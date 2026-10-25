# Hive mind robots (Order From Chaos)

## Folders
- `module_source/index.ts` : the SpacetimeDB hive mind (tables + reducers). Gets copied into `module/` after `spacetime init`.
- `agents/` : Python. `hive.py` talks to the database, `agent.py` runs one robot, `make_job.py` creates test jobs, `watch.py` shows live state.
- `dashboard/` : judge screen (coming).
- `arduino/` : servo sketches.

## Fake demo, no hardware (4 Terminal windows)
1. `spacetime start`  (leave it running)
2. `cd ~/code/hivemind-robots/agents && python3 watch.py`
3. `cd ~/code/hivemind-robots/agents && python3 agent.py K9 --fake`
4. `cd ~/code/hivemind-robots/agents && python3 agent.py NR7 --fake`
Then in a 5th window: `python3 make_job.py far` (or `near`, `big`, `reset`).

## How the hive decides
Every online robot bids. When all have bid (or after 3 s), `decide_job` checks each bid against that robot's capability card.
Grab beats push, then the lowest ETA wins. If nothing passes, the job becomes `no_robot` and the hive alerts staff.
When K9 finishes a push, the hive itself opens a new job at the cube's new spot, and NR7 wins that one.
