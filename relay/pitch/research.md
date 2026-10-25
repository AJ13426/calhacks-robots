# Relay research notes

## Problem statement

Warehouse robots are coordinated by central plans and fixed scripts, so when something unexpected happens on the floor, they can't adapt together, and the mistakes cost companies time, inventory, and money.

Relay lets robots share what their models see and plan through one live SpacetimeDB database, so they adapt to each other in the moment, even across different makers.

## Key numbers

- Unplanned downtime costs the Fortune Global 500 about $1.4 trillion a year, around 11% of revenue. (Siemens, The True Cost of Downtime 2024)
- A stopped consumer goods line costs about $36,000 an hour. Automotive is about $2.3 million an hour. (Siemens 2024)
- A cobot arm is about 40 to 50% of what a deployed robot cell costs. The rest is integration.
- Amazon has deployed over 1 million robots and coordinates them with a central model called DeepFleet, which improved travel efficiency by about 10%. ([Digital Commerce 360](https://www.digitalcommerce360.com/2025/07/03/amazon-deepfleet-ai-model-for-robotics/))
- Fleet standards like MassRobotics and VDA 5050 share location, speed, and status, not what a robot sees or plans.

## Can small warehouses afford this?

- Relay is software. It adds no sensors or cameras and works with the robots a warehouse already has.
- Simple robots can still join and share basic status. Robots with AI models share more.
- One robot with a good camera can share what it sees with cheaper robots nearby, so not every robot needs a camera.
- Cobot arms cost about $25,000 to $60,000, and some sellers rent them with monthly plans starting around $1,000 to $3,000. ([Standard Bots](https://standardbots.com/guides/collaborative-robot-prices-the-ultimate-guide))
- Companies like Unbox Robotics rent warehouse robots to small and medium warehouses for a monthly fee. ([Maritime Gateway](https://www.maritimegateway.com/robotics-as-a-service-for-warehouse-automation/))
- First customers would be medium sized warehouses that already mix robots from different makers.

## Related research and how Relay is different

- **Latent Telepathy** (Columbia and MIT, 2026). Robots share a 64 number latent from their vision encoder. It worked in a hazard avoidance test, but every robot had to run the same frozen model, in one simple scene. ([arXiv](https://arxiv.org/pdf/2609.23269))
- **CHORUS** (Stanford, 2026). Several robots run copies of one VLA and collaborate with no communication at all, by watching each other. ([arXiv](https://arxiv.org/pdf/2606.12352))
- **LatentMAS** (2025). AI agents share hidden states instead of text, about 4x faster with far fewer tokens. ([Hugging Face](https://huggingface.co/papers/2511.20639))

These show that sharing what a model sees works in a lab. Relay is the layer that makes it work on a real floor:

- It handles mixed robots. Same model robots share latents, different makers share embeddings, simple robots share status, and people get language.
- Rules run inside SpacetimeDB reducers, so two robots can never both claim the same spot.
- Managers set up crews from a tablet, staff see every robot on their phones, and a scheduled heartbeat check catches robots that go offline.

Open problem to be honest about: getting robots with different models to understand each other's latents. Relay falls back to embeddings and status for those.

## VLA anatomy (OpenVLA example)

- Vision encoders: SigLIP and DINOv2, which produce patch embeddings (embedding tap).
- Language backbone: Llama 2 7B, which reads the image and the instruction (latent tap is its hidden state).
- Action head: actions as tokens, 256 bins per dimension.
- Speed: about 3 Hz on an RTX 4090.

## SpacetimeDB facts used

- A relational database that is also a server. Clients connect directly.
- State lives in memory with a commit log on disk, and it's ACID.
- Reducers are the only way to change data and run as transactions.
- Subscriptions are SQL queries. Clients get matching rows, then every change pushed to a local cache.
- Schedule tables run reducers on a timer.
- The entire backend of BitCraft Online runs as one SpacetimeDB module.
