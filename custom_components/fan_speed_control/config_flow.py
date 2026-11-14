"""Set up and edit a remote-controlled fan with plain command fields."""

from copy import deepcopy

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .config import config_schema
from .const import DEFAULT_COMMAND_CONFIG, DOMAIN

COMMAND_ACTIONS = {
    "power_on_command": "turn_on",
    "power_off_command": "turn_off",
    "increase_command": "increase",
    "decrease_command": "decrease",
    "oscillate_command": "oscillate",
}


def command_values(config):
    """Show existing simple commands; keep complex sequences in their action editor."""
    if not config:
        return deepcopy(DEFAULT_COMMAND_CONFIG)
    result = {
        "name": config["name"],
        "speed_count": config["speed_count"],
        "sync_percentage_template": config.get("sync_percentage_template", ""),
        "timing": {
            key: config.get(key, default)
            for key, default in DEFAULT_COMMAND_CONFIG["timing"].items()
        },
    }
    remotes = set()
    for field, action in COMMAND_ACTIONS.items():
        steps = config.get(action, [])
        if not steps and action == "oscillate":
            result[field] = ""
            continue
        if len(steps) != 1:
            return None
        step = steps[0]
        if set(step) - {"action", "service", "target", "data", "metadata"}:
            return None
        if step.get("action", step.get("service")) != "remote.send_command":
            return None
        data = step.get("data", {})
        target = step.get("target", {})
        if set(data) - {"command", "entity_id"} or set(target) - {"entity_id"}:
            return None
        remote = target.get("entity_id", data.get("entity_id"))
        if isinstance(remote, list) and len(remote) == 1:
            remote = remote[0]
        if not isinstance(remote, str) or not isinstance(data.get("command"), str):
            return None
        remotes.add(remote)
        result[field] = data["command"]
    if len(remotes) != 1:
        return None
    result["remote_entity_id"] = remotes.pop()
    return result


def commands_to_config(values):
    """Compile plain codes into the existing action engine's configuration."""
    remote = cv.entity_id(values["remote_entity_id"])
    if not remote.startswith("remote."):
        raise vol.Invalid("Select a remote entity")
    config = {
        "name": values["name"],
        "speed_count": values["speed_count"],
        **values["timing"],
    }
    if sync_template := values.get("sync_percentage_template", "").strip():
        config["sync_percentage_template"] = sync_template
    for field, action in COMMAND_ACTIONS.items():
        command = cv.string(values[field]).strip()
        if not command:
            if action == "oscillate":
                continue
            raise vol.Invalid("A command is required", path=[field])
        config[action] = [
            {
                "action": "remote.send_command",
                "target": {"entity_id": remote},
                "data": {"command": command},
            }
        ]
    config_schema()(config)
    return config


def command_schema(values):
    """Native remote picker, paste-code fields, and collapsed tuning settings."""
    timing = {}
    for key, value in values["timing"].items():
        timing[vol.Required(key, default=value)] = (
            selector.BooleanSelector()
            if key.startswith("wrap_")
            else selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0 if key.endswith("delay") else 1,
                    max=60 if key.endswith("delay") else 100,
                    step=0.1 if key.endswith("delay") else 1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            )
        )
    return vol.Schema(
        {
            vol.Required("name", default=values["name"]): selector.TextSelector(),
            vol.Required(
                "remote_entity_id", default=values["remote_entity_id"]
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="remote")),
            vol.Required(
                "speed_count", default=values["speed_count"]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=100, mode=selector.NumberSelectorMode.BOX
                )
            ),
            **{
                (vol.Optional if key == "oscillate_command" else vol.Required)(
                    key, default=values[key]
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True))
                for key in COMMAND_ACTIONS
            },
            vol.Optional("timing", default=values["timing"]): section(
                vol.Schema(timing), {"collapsed": True}
            ),
            vol.Optional(
                "sync_percentage_template",
                default=values.get("sync_percentage_template", ""),
            ): selector.TemplateSelector(),
        }
    )


def advanced_schema(values):
    """Show native selectors without storing compiled template objects."""
    fields = {}
    for key in config_schema().schema:
        name = str(key)
        marker = type(key)(name, default=values[name]) if name in values else key
        if name in ("turn_on", "turn_off", "increase", "decrease", "oscillate"):
            fields[marker] = selector.ActionSelector()
        elif name.startswith("wrap_"):
            fields[marker] = selector.BooleanSelector()
        elif name == "sync_percentage_template":
            fields[marker] = selector.TemplateSelector()
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


class FanConfigurationForm:
    """Share setup, reconfigure and Configure behavior without duplicating validation."""

    async def _async_form(self, step, user_input, entry=None):
        current = dict(entry.options or entry.data) if entry else {}
        values = command_values(current)
        errors = {}
        if user_input is not None:
            if values is None:
                draft = {**current, **user_input}
            else:
                values = {
                    **values,
                    **user_input,
                    "timing": {**values["timing"], **user_input.get("timing", {})},
                }
            try:
                if values is not None:
                    draft = commands_to_config(values)
                config_schema()(draft)
            except vol.Invalid:
                errors["base"] = "invalid_config"
            else:
                if step == "init":
                    return self.async_create_entry(title="", data=draft)
                if entry:
                    return self.async_update_reload_and_abort(
                        entry, title=draft["name"], data=draft, options={}
                    )
                return self.async_create_entry(title=draft["name"], data=draft)
        return self.async_show_form(
            step_id=step,
            data_schema=advanced_schema(current)
            if values is None
            else command_schema(values),
            errors=errors,
        )


class FanSpeedControlConfigFlow(
    FanConfigurationForm, config_entries.ConfigFlow, domain=DOMAIN
):
    """One device integration entry per fan."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FanSpeedControlOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._async_form("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._async_form(
            "reconfigure", user_input, self._get_reconfigure_entry()
        )


class FanSpeedControlOptionsFlow(FanConfigurationForm, config_entries.OptionsFlow):
    """The integration's normal Configure button."""

    async def async_step_init(self, user_input=None):
        return await self._async_form("init", user_input, self.config_entry)
