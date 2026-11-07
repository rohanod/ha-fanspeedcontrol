"""Validate UI setup and reconfiguration with Home Assistant."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType


async def test_ui_setup(hass, fan_config):
    result = await hass.config_entries.flow.async_init(
        "fan_speed_control", context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], fan_config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == fan_config
    await hass.async_block_till_done()


async def test_reject_invalid_config(hass, fan_config):
    import pytest
    import voluptuous as vol

    from custom_components.fan_speed_control.config_flow import config_schema

    for key, value in (
        ("speed_count", 0),
        ("command_delay", -1),
        ("startup_delay", float("nan")),
        ("power_on_percentage", 101),
        ("turn_on", []),
    ):
        with pytest.raises(vol.Invalid):
            config_schema()({**fan_config, key: value})


async def test_reconfigure_keeps_identity(hass, fan_config):
    from pytest_homeassistant.common import MockConfigEntry

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
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**fan_config, "command_delay": 2}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert (
        hass.config_entries.async_get_entry(entry.entry_id).data["command_delay"] == 2
    )
    await hass.async_block_till_done()


async def test_invalid_actions_stay_in_form(hass, fan_config):
    result = await hass.config_entries.flow.async_init(
        "fan_speed_control", context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**fan_config, "increase": []}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_config"}
