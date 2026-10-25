"""
brain.py - the "thinking" part of each robot.

Every robot calls decide() over and over. You give it:
  - robot_id:          who this robot is, e.g. "robot_a"
  - task:              the shared goal, e.g. "sort the red and blue blocks into two bins"
  - observation_text:  what the robot currently sees, written as text
  - new_messages:      teammates' messages it hasn't read yet (list of dicts)

It gives back:
  {
    "message_to_send": "what to say to teammates",
    "vla_instruction": "short plain-English command for this robot's VLA model"
  }

Two modes:
  - REAL mode: asks Claude. Needs the ANTHROPIC_API_KEY environment variable.
  - MOCK mode: no API key needed. Returns canned but sensible answers, so you
    can test for free and instantly. Used automatically when there's no key,
    or force it with:  export BRAIN_MOCK=1

For the ML teammate, the one-line version is:
    from brain import get_vla_instruction
    instruction = get_vla_instruction("robot_a", task, observation_text, new_messages)
"""

import json
import os

# Haiku is Claude's fastest, cheapest model, a good fit for a loop that runs
# every couple of seconds. Change it with:  export BRAIN_MODEL=claude-sonnet-5-5
MODEL = os.environ.get("BRAIN_MODEL", "claude-haiku-5-5")


def use_mock() -> bool:
    """Mock mode if BRAIN_MOCK=1 is set or there's no API key."""
    return os.environ.get("BRAIN_MOCK") == "1" or not os.environ.get("ANTHROPIC_API_KEY")


# ---------------------------------------------------------------------------
# The main function
# ---------------------------------------------------------------------------
def decide(robot_id: str, task: str, observation_text: str, new_messages: list) -> dict:
    """Decide what to say and what to do next. See the top of the file."""
    if use_mock():
        return _mock_decide(robot_id, task, observation_text, new_messages)
    try:
        return _claude_decide(robot_id, task, observation_text, new_messages)
    except Exception as e:
        # If the internet or API hiccups mid-demo, don't crash the robot.
        print(f"[brain] Claude call failed ({e}); using mock answer instead.")
        return _mock_decide(robot_id, task, observation_text, new_messages)


def get_vla_instruction(robot_id: str, task: str, observation_text: str, new_messages: list) -> str:
    """
    The simple version for the ML teammate: returns ONLY the instruction
    string (e.g. "pick up the red block") to feed straight into the VLA.
    """
    return decide(robot_id, task, observation_text, new_messages)["vla_instruction"]


# ---------------------------------------------------------------------------
# REAL mode: ask Claude
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the decision-making brain of one robot on a team of robots.
The robots share one task and coordinate by sending short natural-language messages.

Each turn you get: your robot id, the shared task, what you currently see, and
new messages from teammates. Reply with ONLY a JSON object, no other text:
{"message_to_send": "...", "vla_instruction": "..."}

- message_to_send: one or two short sentences to your teammates. Claim sub-tasks,
  report progress, avoid duplicating work, and respond to what they said.
- vla_instruction: ONE short, concrete, physical command for your own robot arm,
  in the style a vision-language-action model expects, e.g. "pick up the red block",
  "place the block in the left bin", "move to the blue block". Under 12 words.
  If there is nothing to do, use "stay still"."""


def _claude_decide(robot_id, task, observation_text, new_messages) -> dict:
    import anthropic  # imported here so mock mode works even if it isn't installed

    if new_messages:
        inbox = "\n".join(
            f'- {m.get("from")} (status: {m.get("my_status", "")}): {m.get("message")}'
            for m in new_messages
        )
    else:
        inbox = "(no new messages)"

    user_prompt = (
        f"You are: {robot_id}\n"
        f"Shared task: {task}\n"
        f"What you see right now: {observation_text}\n"
        f"New messages from teammates:\n{inbox}"
    )

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY automatically
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text

    # Pull out the {...} part in case Claude adds anything around it.
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    return {
        "message_to_send": str(data["message_to_send"]).strip(),
        "vla_instruction": str(data["vla_instruction"]).strip(),
    }


# ---------------------------------------------------------------------------
# MOCK mode: simple rules, no AI, free and instant
# ---------------------------------------------------------------------------
def _mock_decide(robot_id, task, observation_text, new_messages) -> dict:
    """
    Pretends to think, using simple rules for the red/blue block demo:
      - robot_a handles red, every other robot handles blue
      - holding a block -> put it in its bin
      - sees a block of its color -> pick it up
      - otherwise -> wait
    """
    obs = observation_text.lower()
    color = "red" if robot_id.endswith("a") else "blue"

    # Acknowledge a teammate if one just spoke, so it reads like a conversation.
    reply = ""
    if new_messages:
        last = new_messages[-1]
        reply = f'Heard you, {last.get("from")}. '

    if f"holding a {color} block" in obs:
        instruction = f"place the {color} block in the {color} bin"
        message = f"{reply}Got a {color} block, dropping it in the {color} bin."
    elif _count_blocks(obs, color) > 0:
        instruction = f"pick up the nearest {color} block"
        message = f"{reply}I'm on the {color} blocks. Going for one now."
    else:
        instruction = "stay still"
        message = f"{reply}No {color} blocks left on my side. Done unless you need help."

    return {"message_to_send": message, "vla_instruction": instruction}


def _count_blocks(obs: str, color: str) -> int:
    """Find 'I see 2 red block(s)' style numbers. Assumes 1 if no number is given."""
    import re

    match = re.search(rf"(\d+) {color} block", obs)
    if match:
        return int(match.group(1))
    return 1 if re.search(rf"\b(a|an|one) {color} block", obs) else 0


# Quick self-test:  python brain.py
if __name__ == "__main__":
    print("Mock mode:", use_mock())
    print(decide(
        "robot_a",
        "sort the red and blue blocks into two bins",
        "I see 2 red blocks and 1 blue block on the table.",
        [{"from": "robot_b", "message": "I'll take blue.", "my_status": "moving"}],
    ))
