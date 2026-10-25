# Relay

Relay lets robots share what their AI models see and plan through one live SpacetimeDB database, so they adapt to each other in the moment, even when they come from different makers. Built at Cal Hacks 13.0 for the Spacetime track.

## What's in here

- `relay/demo/keynote.html` is the presenter controlled 3D keynote. Open it in a browser and use the arrow keys. Press N for speaker notes.
- `relay/demo/brick-demo.html` is the first 3D demo, two robot arms building a wall with no coordination, language, and Relay.
- `relay/pitch/script.md` is the 5 minute pitch script.
- `relay/pitch/research.md` has the problem statement, key numbers, related research, and sources.
- `hivemind-robots/` is the robot coordination module running on SpacetimeDB, with simulated robot agents.
- `robot-backend/` is the earlier version where robots talk in plain English through an LLM.

See each folder's README for setup.

## What's real and what's simulated

The coordination module in `hivemind-robots/` runs on a real SpacetimeDB database. The robots in the demos are simulated, and the shared latents are simulated too. Connecting Relay to real VLA models is the next step.
