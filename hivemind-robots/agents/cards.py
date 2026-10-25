"""Capability cards. One per robot. Adding a robot means adding a card here.

Coordinates are centimeters on the 100 x 100 table. The arm sits in corner A at (0,0).
"""
ARM_ZONE = {"x": 12.0, "y": 12.0, "r": 20.0}

CARDS = {
    "K9": {
        "id": "K9", "name": "K9 the robo dog", "type": "rolling robot",
        "can_move": True, "can_lift": False, "max_push_cm": 10,
        "speed_cm_per_s": 40, "reach": "entire table",
        "start": {"x": 75.0, "y": 75.0},
    },
    "NR7": {
        "id": "NR7", "name": "NR7 the robo nurse", "type": "fixed arm",
        "can_move": False, "can_lift": True, "max_object_cm": 5,
        "zone": ARM_ZONE, "reach": "20 cm circle around corner A",
        "start": {"x": 0.0, "y": 0.0},
    },
}
