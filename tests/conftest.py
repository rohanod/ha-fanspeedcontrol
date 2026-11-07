"""Run against Home Assistant's real test fixtures."""

import pytest


@pytest.fixture
def fan_config():
    def action(command):
        return [
            {
                "action": "remote.send_command",
                "data": {"entity_id": "remote.bedroom", "command": command},
            }
        ]

    return {
        "name": "Bedroom Fan",
        "speed_count": 10,
        "command_delay": 0,
        "startup_delay": 0,
        "power_on_percentage": 10,
        "wrap_increase": False,
        "wrap_decrease": False,
        **{key: action(key) for key in ("turn_on", "turn_off", "increase", "decrease")},
    }
