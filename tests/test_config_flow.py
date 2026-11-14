"""Test the paste-code UI, defaults, compatibility and Configure flow."""

import json

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.loader import async_get_integration
from pytest_homeassistant.common import MockConfigEntry

from custom_components.fan_speed_control.config_flow import config_schema


async def test_setup_uses_current_bedroom_defaults(hass):
    result = await hass.config_entries.flow.async_init(
        "fan_speed_control", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    fields = {str(key): key for key in result["data_schema"].schema}
    assert "turn_on" not in fields
    assert fields["name"].default() == "Bedroom Fan"
    assert fields["remote_entity_id"].default() == "remote.bedroom"
    assert fields["power_on_command"].default().startswith("b64:JgBIAEkbGTU")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    config = result["data"]
    assert config["speed_count"] == 10
    assert config["turn_on"][0]["target"]["entity_id"] == "remote.bedroom"
    assert config["turn_on"] == config["turn_off"]
    json.dumps(config)
    await hass.async_block_till_done()


async def test_paste_codes_and_disable_oscillation(hass):
    result = await hass.config_entries.flow.async_init(
        "fan_speed_control", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "remote_entity_id": "remote.lounge",
            "power_on_command": "  b64:NEW_ON  ",
            "oscillate_command": "",
            "timing": {"command_delay": 2},
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["turn_on"] == [
        {
            "action": "remote.send_command",
            "target": {"entity_id": "remote.lounge"},
            "data": {"command": "b64:NEW_ON"},
        }
    ]
    assert "oscillate" not in result["data"]
    assert result["data"]["command_delay"] == 2
    await hass.async_block_till_done()


async def test_reconfigure_preserves_existing_codes(hass, fan_config):
    entry = MockConfigEntry(
        domain="fan_speed_control", data=fan_config, title=fan_config["name"]
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        "fan_speed_control",
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    fields = {str(key): key for key in result["data_schema"].schema}
    assert fields["power_on_command"].default() == "turn_on"
    assert fields["oscillate_command"].default() == ""
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"increase_command": "new_up"}
    )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["increase"][0]["data"]["command"] == "new_up"
    assert entry.data["turn_on"][0]["data"]["command"] == "turn_on"
    await hass.async_block_till_done()


async def test_configure_options_reload_same_entry(hass, fan_config):
    entry = MockConfigEntry(
        domain="fan_speed_control", data=fan_config, title=fan_config["name"]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_before = hass.states.get("fan.bedroom_fan")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"increase_command": "options_up"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["increase"][0]["data"]["command"] == "options_up"
    await hass.async_block_till_done()
    assert hass.states.get(entity_before.entity_id) is not None
    calls = []

    async def send(call):
        calls.append(call.data["command"])

    hass.services.async_register("remote", "send_command", send)
    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": entity_before.entity_id, "percentage": 20},
        blocking=True,
    )
    assert calls == ["turn_on", "options_up"]


async def test_invalid_code_or_delay_stays_in_form(hass):
    for patch in (
        {"increase_command": "  "},
        {"timing": {"command_delay": -1}},
        {"remote_entity_id": "light.wrong"},
    ):
        result = await hass.config_entries.flow.async_init(
            "fan_speed_control", context={"source": config_entries.SOURCE_USER}
        )
        if "increase_command" not in patch:
            with pytest.raises(InvalidData):
                await hass.config_entries.flow.async_configure(result["flow_id"], patch)
            continue
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], patch
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]


async def test_complex_legacy_actions_are_preserved(hass, fan_config):
    fan_config["turn_on"].append({"delay": 1})
    entry = MockConfigEntry(domain="fan_speed_control", data=fan_config)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "turn_on" in {str(key) for key in result["data_schema"].schema}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], fan_config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == fan_config


async def test_reject_invalid_runtime_config(hass, fan_config):
    for key, value in (
        ("speed_count", 0),
        ("command_delay", -1),
        ("startup_delay", float("nan")),
        ("power_on_percentage", 101),
        ("turn_on", []),
    ):
        with pytest.raises(vol.Invalid):
            config_schema()({**fan_config, key: value})


async def test_device_integration_registration(
    hass, fan_config, device_registry, entity_registry
):
    entry = MockConfigEntry(domain="fan_speed_control", data=fan_config)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity = entity_registry.async_get("fan.bedroom_fan")
    assert entity.device_id is not None
    assert device_registry.async_get(entity.device_id).name == "Bedroom Fan"
    assert (
        await async_get_integration(hass, "fan_speed_control")
    ).integration_type == "device"


async def test_saved_sync_template_is_serializable_and_preserved(hass, fan_config):
    fan_config["sync_percentage_template"] = "{{ states('sensor.actual_speed') }}"
    entry = MockConfigEntry(domain="fan_speed_control", data=fan_config)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert (
        result["data"]["sync_percentage_template"]
        == fan_config["sync_percentage_template"]
    )
    json.dumps(result["data"])
