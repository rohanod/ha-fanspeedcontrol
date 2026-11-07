"""Configure command sequences through Home Assistant's action editor."""

import math

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import DOMAIN


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


def form_schema(values):
    """Show native selectors without storing compiled template objects."""
    fields = {}
    for key in config_schema().schema:
        name = str(key)
        marker = type(key)(name, default=values[name]) if name in values else key
        if name in ("turn_on", "turn_off", "increase", "decrease", "oscillate"):
            fields[marker] = selector.ActionSelector()
        elif name.startswith("wrap_"):
            fields[marker] = selector.BooleanSelector()
        elif name == "name":
            fields[marker] = selector.TextSelector()
        else:
            fields[marker] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0 if name.endswith("delay") else 1,
                    max=60 if name.endswith("delay") else 100,
                    step=0.1 if name.endswith("delay") else 1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            )
    return vol.Schema(fields)


class FanSpeedControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One config entry per independently controlled fan."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create a fan, keeping raw serializable action data."""
        return await self._async_form("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        """Edit commands without replacing the entity's identity."""
        return await self._async_form("reconfigure", user_input)

    async def _async_form(self, step, user_input):
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        values = dict(entry.data) if entry else {}
        errors = {}
        if user_input is not None:
            values = user_input
            try:
                config_schema()(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_config"
            else:
                if entry:
                    return self.async_update_reload_and_abort(
                        entry, title=user_input["name"], data=user_input
                    )
                return self.async_create_entry(
                    title=user_input["name"], data=user_input
                )
        return self.async_show_form(
            step_id=step, data_schema=form_schema(values), errors=errors
        )
