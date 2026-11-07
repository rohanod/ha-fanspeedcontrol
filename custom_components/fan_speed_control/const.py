"""Integration constants and the requested bedroom fan defaults."""

DOMAIN = "fan_speed_control"

DEFAULT_COMMAND_CONFIG = {
    "name": "Bedroom Fan",
    "remote_entity_id": "remote.bedroom",
    "speed_count": 10,
    "power_on_command": "b64:JgBIAEkbGTUYGxkbGTQZGxgbGBoZHRgcGBwYGxkbGRoZMxkbGAANDUkbGTUYGxkcGDQZGxgaGRoZHRgcGBsZGxgcGBoZNBgaGQANBQ==",
    "power_off_command": "b64:JgBIAEkbGTUYGxkbGTQZGxgbGBoZHRgcGBwYGxkbGRoZMxkbGAANDUkbGTUYGxkcGDQZGxgaGRoZHRgcGBsZGxgcGBoZNBgaGQANBQ==",
    "increase_command": "b64:JgBIAEkcGDQZHBgcGDQZGxgbGBsYHRg0GRwYNBkcGDQZGxgzGQAMu0kcGDQYHBgcGDQZGxgbGBsYHRg0GRwYNBkcGDQZGxgzGQANBQ==",
    "decrease_command": "b64:JgBIAEkbGTQZGxkbGTQZGxoZGhkZNRk0GTQZNBk0GTQZMxkaGQAM+kkbGTQZGxkbGTQZGxkaGRoZNRk0GTQZNBk0GTQZMxkaGgANBQ==",
    "oscillate_command": "b64:JgBIAEkcGDQZGxkbGTQZGxkaGBoZNRkbGTQZGxk0GRoZGhkaGQAM2kkcGDQZGxkbGTQZGhgbGRoZNRkbGTQZGxk0GRsZGxgbGAANBQ==",
    "timing": {
        "power_on_percentage": 10,
        "command_delay": 1.0,
        "startup_delay": 1.0,
        "wrap_increase": False,
        "wrap_decrease": False,
    },
}
