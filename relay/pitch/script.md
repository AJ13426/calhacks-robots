# Relay pitch script

About 5 minutes. Stage directions are in brackets.

## Problem

Raise your hand if you've ever gotten a package that showed up broken.

[pause]

There's a good chance a robot did that, and probably not because anything was wrong with it, but because it had no idea what the robot next to it was doing. We built Relay for the people who run warehouses, where the robots usually come from different companies, with the arms from one maker and the carriers from another. Each robot works fine on its own, but they don't really work as a team, so when something changes on the floor, like the conveyor belt slowing down, the robots find out too late and the manager ends up stopping the whole line to clean up the mess.

## Evidence

Amazon gets around this because it builds all of its own robots and plans every move from one central system, but most warehouses don't have that option. They have to get robots from different makers to work together, and the standards those robots rely on only share where each robot is and how fast it's moving, without ever sharing what a robot sees or what it's about to do next.

## Cost

That gap ends up costing a huge amount of money, and Siemens found that unplanned downtime costs the world's 500 biggest companies about 1.4 trillion dollars a year, with a single stopped packing line losing around 36 thousand dollars every hour.

## Solution

Relay fixes this by letting robots share what they understand with each other instantly. Every modern robot has an AI model inside it that sees the world and decides what to do, and when robots share anything today, it's usually a sentence like "the belt is slowing down" that takes over a second to arrive. Relay skips that sentence completely and shares what the robot actually understands, which gets there in just a few milliseconds, and because every robot reads from the same place, they all see the same floor at the same moment.

## Demo

[belt slowdown, scripts]

This is a packing line running the way most of them do today, and right now the belt is slowing down without the picker arm knowing about it, so it reaches for a box that hasn't arrived yet. The loader doesn't know either, so it keeps loading until the line jams, and when the carrier drives away, the picker ends up dropping a glass item onto the floor.

[same line, Relay]

Now watch what happens on the same line with Relay, where every robot slows down right along with the belt, and when the carrier leaves, Relay pauses the line until it comes back so nothing gets dropped.

[two arms claim one spot]

Relay also keeps robots from getting in each other's way, so if two arms reach for the same spot at the same time, one of them goes first while the other waits for its turn.

[crews on tablet]

The manager stays in control the whole time, and from her tablet she can group robots into crews, like putting these arms and carriers together as the glass crew, while everyone on her team can see what each robot is doing right from their phones.

[full floor]

Here's a whole floor with all kinds of robots working together, and right now they keep bumping into each other and dropping things, so watch what happens when I turn on Relay.

[click Turn on Relay]

## Before and after

The difference is easy to see, because on the packing line the same 38 second run cost 446 dollars without Relay and nothing with it, and on the full floor the collisions stopped while the robots delivered almost twice as much. The robots in this demo are simulated, but everything they share runs through a real SpacetimeDB database.

## How it works and who we are

We built Relay on SpacetimeDB because it works as a database and a server at the same time, which lets robots connect to it directly. The safety rules run inside the database itself, so no robot can skip them, and each robot only receives the updates it actually needs the moment they happen, which is the same way the online game BitCraft runs its entire backend.

[one line per teammate about what you built]

Our next step is connecting Relay to real robot AI models, because robots don't need to talk to each other to work together, they just need to share what they know. We're Relay, and thank you.
