"""Validate native action configuration, including existing entries."""

import math

import voluptuous as vol
from homeassistant.helpers import config_validation as cv


def finite_delay(value):
    """Reject non-finite and negative delays."""
    value = vol.Coerce(float)(value)
    if not math.isfinite(value) or not 0 <= value <= 60:
        raise vol.Invalid("Delay must be between 0 and 60 seconds")
    return value


def config_schema():
    """Validate persisted input as well as browser submissions."""
    actions = vol.All(cv.SCRIPT_SCHEMA, vol.Length(min=1))
    return vol.Schema(
        {
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
            vol.Required("speed_count", default=10): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=100)
            ),
            vol.Required("power_on_percentage", default=10): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=100)
            ),
            vol.Required("command_delay", default=1.0): finite_delay,
            vol.Required("startup_delay", default=1.0): finite_delay,
            vol.Required("wrap_increase", default=False): cv.boolean,
            vol.Required("wrap_decrease", default=False): cv.boolean,
            **{
                vol.Required(key): actions
                for key in ("turn_on", "turn_off", "increase", "decrease")
            },
            vol.Optional("oscillate"): actions,
        }
    )
