"""Exercise real fan services, config entries, restoration and concurrency."""

import asyncio

import pytest
from homeassistant.core import ServiceCall, State
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant.common import (
    MockConfigEntry,
    mock_restore_cache,
)


async def setup_fan(hass, config, previous=None):
    calls = []

    async def send(call: ServiceCall):
        calls.append(call.data["command"])

    hass.services.async_register("remote", "send_command", send)
    if previous:
        mock_restore_cache(hass, [previous])
    entry = MockConfigEntry(
        domain="fan_speed_control", title=config["name"], data=config
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


async def command(hass, service, **data):
    await hass.services.async_call(
        "fan", service, {"entity_id": "fan.bedroom_fan", **data}, blocking=True
    )


async def test_startup_steps_off_and_unload(hass, fan_config):
    entry, calls = await setup_fan(hass, fan_config)
    await command(hass, "set_percentage", percentage=50)
    assert calls == ["turn_on"] + ["increase"] * 4
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 50
    await command(hass, "set_percentage", percentage=20)
    assert calls[-3:] == ["decrease"] * 3
    await command(hass, "set_percentage", percentage=0)
    assert calls[-1] == "turn_off"
    assert hass.states.get("fan.bedroom_fan").state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get("fan.bedroom_fan").state == "unavailable"


async def test_concurrent_changes_are_serialized(hass, fan_config):
    _, calls = await setup_fan(hass, fan_config)
    await asyncio.gather(
        command(hass, "set_percentage", percentage=50),
        command(hass, "set_percentage", percentage=20),
    )
    assert calls == ["turn_on"] + ["increase"] * 4 + ["decrease"] * 3
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 20


async def test_restore_without_transmitting(hass, fan_config):
    _, calls = await setup_fan(
        hass, fan_config, State("fan.bedroom_fan", "on", {"percentage": 70.0})
    )
    assert calls == []
    await command(hass, "set_percentage", percentage=100)
    assert calls == ["increase"] * 3


async def test_wrap_is_explicit(hass, fan_config):
    fan_config["wrap_decrease"] = True
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "set_percentage", percentage=100)
    assert calls == ["turn_on", "decrease"]


async def test_failed_command_does_not_claim_target(hass, fan_config):
    await setup_fan(hass, fan_config)
    await command(hass, "turn_on")

    async def fail(call):
        raise HomeAssistantError("transmitter failed")

    hass.services.async_register("remote", "send_command", fail)
    with pytest.raises(HomeAssistantError):
        await command(hass, "set_percentage", percentage=50)
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] is None


async def test_oscillation_receives_desired_state(hass, fan_config):
    fan_config["oscillate"] = [
        {
            "action": "remote.send_command",
            "data": {"command": "{{ 'osc_on' if oscillating else 'osc_off' }}"},
        }
    ]
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "turn_on")
    await command(hass, "oscillate", oscillating=True)
    await command(hass, "oscillate", oscillating=True)
    assert calls == ["turn_on", "osc_on"]


async def test_sync_state_does_not_transmit(hass, fan_config):
    _, calls = await setup_fan(hass, fan_config)
    await hass.services.async_call(
        "fan_speed_control",
        "sync_state",
        {
            "entity_id": "fan.bedroom_fan",
            "percentage": 60,
            "oscillating": True,
        },
        blocking=True,
    )
    assert calls == []
    assert hass.states.get("fan.bedroom_fan").state == "on"
    await command(hass, "set_percentage", percentage=80)
    assert calls == ["increase", "increase"]


async def test_repeated_power_commands_are_idempotent(hass, fan_config):
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "turn_off")
    await command(hass, "turn_on")
    await command(hass, "turn_on")
    await command(hass, "turn_off")
    await command(hass, "turn_off")
    assert calls == ["turn_on", "turn_off"]


async def test_recover_speed_failure_by_sync(hass, fan_config):
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "turn_on")

    async def fail(call):
        raise HomeAssistantError("lost command")

    hass.services.async_register("remote", "send_command", fail)
    with pytest.raises(HomeAssistantError):
        await command(hass, "set_percentage", percentage=50)
    with pytest.raises(HomeAssistantError, match="Speed unknown"):
        await command(hass, "set_percentage", percentage=50)
    await hass.services.async_call(
        "fan_speed_control",
        "sync_state",
        {
            "entity_id": "fan.bedroom_fan",
            "percentage": 0,
        },
        blocking=True,
    )
    assert calls == ["turn_on"]
    assert hass.states.get("fan.bedroom_fan").state == "off"


async def test_restore_unknown_does_not_assume_off(hass, fan_config):
    _, calls = await setup_fan(hass, fan_config, State("fan.bedroom_fan", "unknown"))
    with pytest.raises(HomeAssistantError, match="Power unknown"):
        await command(hass, "turn_on")
    assert calls == []


async def test_registry_rename_keeps_actions_usable(hass, fan_config, entity_registry):
    _, calls = await setup_fan(hass, fan_config)
    entity_registry.async_update_entity("fan.bedroom_fan", new_entity_id="fan.renamed")
    await hass.async_block_till_done()
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {
            "entity_id": "fan.renamed",
            "percentage": 30,
        },
        blocking=True,
    )
    assert calls == ["turn_on", "increase", "increase"]
    assert hass.states.get("fan.renamed").attributes["percentage"] == 30


async def test_reload_restores_current_state(hass, fan_config):
    entry, calls = await setup_fan(hass, fan_config)
    await command(hass, "set_percentage", percentage=50)
    before = list(calls)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("fan.bedroom_fan").state == "on"
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 50
    assert calls == before


@pytest.mark.parametrize("off_service", ["turn_off", "set_percentage"])
async def test_turn_on_resumes_previous_speed(hass, fan_config, off_service):
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "set_percentage", percentage=60)
    await command(
        hass,
        off_service,
        **({"percentage": 0} if off_service == "set_percentage" else {}),
    )
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 0
    calls.clear()
    await command(hass, "turn_on")
    assert calls == ["turn_on"] + ["increase"] * 5
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 60


async def test_off_speed_survives_reload_and_explicit_target_wins(hass, fan_config):
    entry, calls = await setup_fan(hass, fan_config)
    await command(hass, "set_percentage", percentage=70)
    await command(hass, "turn_off")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    calls.clear()
    await command(hass, "turn_on")
    assert calls == ["turn_on"] + ["increase"] * 6
    await command(hass, "turn_off")
    calls.clear()
    await command(hass, "turn_on", percentage=30)
    assert calls == ["turn_on", "increase", "increase"]
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 30


async def test_saved_off_speed_restores_without_transmitting(hass, fan_config):
    _, calls = await setup_fan(
        hass,
        fan_config,
        State("fan.bedroom_fan", "off", {"percentage": 0, "last_percentage": 80}),
    )
    assert calls == []
    await command(hass, "turn_on")
    assert calls == ["turn_on"] + ["increase"] * 7


@pytest.mark.parametrize(
    ("direction", "expected"), [("increase", 100), ("decrease", 10)]
)
async def test_calibrate_reaches_endpoint(hass, fan_config, direction, expected):
    from unittest.mock import patch

    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "turn_on")
    calls.clear()
    with patch(
        "custom_components.fan_speed_control.fan.monotonic", side_effect=[0, *range(11)]
    ):
        await hass.services.async_call(
            "fan_speed_control",
            "calibrate",
            {"entity_id": "fan.bedroom_fan", "direction": direction},
            blocking=True,
        )
    assert calls == [direction] * 10
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == expected
    assert hass.states.get("fan.bedroom_fan").attributes["last_percentage"] == expected


async def test_calibration_refuses_wrapping(hass, fan_config):
    fan_config["wrap_increase"] = True
    _, calls = await setup_fan(hass, fan_config)
    with pytest.raises(HomeAssistantError, match="wrap"):
        await hass.services.async_call(
            "fan_speed_control",
            "calibrate",
            {"entity_id": "fan.bedroom_fan", "direction": "increase"},
            blocking=True,
        )
    assert calls == []


async def test_calibration_failure_invalidates_speed(hass, fan_config):
    await setup_fan(hass, fan_config)
    await command(hass, "turn_on")

    async def fail(call):
        raise HomeAssistantError("transmitter failed")

    hass.services.async_register("remote", "send_command", fail)
    with pytest.raises(HomeAssistantError, match="transmitter failed"):
        await hass.services.async_call(
            "fan_speed_control",
            "calibrate",
            {"entity_id": "fan.bedroom_fan", "direction": "decrease"},
            blocking=True,
        )
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] is None


async def test_sync_action_template_rejects_unavailable(hass, fan_config):
    hass.states.async_set("sensor.actual_speed", "60")
    _, calls = await setup_fan(hass, fan_config)
    data = {
        "entity_id": "fan.bedroom_fan",
        "percentage_template": "{{ states('sensor.actual_speed') }}",
    }
    await hass.services.async_call(
        "fan_speed_control", "sync_state", data, blocking=True
    )
    assert calls == []
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 60
    hass.states.async_set("sensor.actual_speed", "unavailable")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "fan_speed_control", "sync_state", data, blocking=True
        )
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 60


async def test_calibration_sends_enough_steps_even_after_ten_seconds(hass, fan_config):
    from unittest.mock import patch

    fan_config["speed_count"] = 20
    _, calls = await setup_fan(hass, fan_config)
    await command(hass, "turn_on")
    calls.clear()
    with patch(
        "custom_components.fan_speed_control.fan.monotonic", side_effect=[0] + [20] * 21
    ):
        await hass.services.async_call(
            "fan_speed_control",
            "calibrate",
            {"entity_id": "fan.bedroom_fan", "direction": "decrease"},
            blocking=True,
        )
    assert calls == ["decrease"] * 19
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 5


async def test_sync_speed_keeps_oscillation_when_omitted(hass, fan_config):
    fan_config["oscillate"] = fan_config["increase"]
    _, calls = await setup_fan(hass, fan_config)
    await hass.services.async_call(
        "fan_speed_control",
        "sync_state",
        {"entity_id": "fan.bedroom_fan", "percentage": 40, "oscillating": True},
        blocking=True,
    )
    await hass.services.async_call(
        "fan_speed_control",
        "sync_state",
        {"entity_id": "fan.bedroom_fan", "percentage": 60},
        blocking=True,
    )
    assert calls == []
    assert hass.states.get("fan.bedroom_fan").attributes["oscillating"] is True


async def test_sync_template_works_in_native_action_engine(hass, fan_config):
    from homeassistant.helpers.script import Script

    _, calls = await setup_fan(hass, fan_config)
    script = Script(
        hass,
        [
            {
                "action": "fan_speed_control.sync_state",
                "target": {"entity_id": "fan.bedroom_fan"},
                "data": {"percentage_template": "{{ 30 + 20 }}"},
            }
        ],
        "Synchronize",
        "test",
    )
    try:
        await script.async_run()
    finally:
        await script.async_unload()
    assert calls == []
    assert hass.states.get("fan.bedroom_fan").attributes["percentage"] == 50
