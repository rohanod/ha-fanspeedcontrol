"""Set up UI-configured, action-driven fans."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .const import DOMAIN

PLATFORMS = [Platform.FAN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Forward each fan configuration to the fan platform."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    if not hass.services.has_service(DOMAIN, "sync_state"):
        service.async_register_platform_entity_service(
            hass,
            DOMAIN,
            "sync_state",
            entity_domain="fan",
            func="async_sync_state",
            schema={
                vol.Required("percentage"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=100)
                ),
                vol.Optional("oscillating", default=False): cv.boolean,
            },
        )
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply Configure changes while preserving the fan's registry identity."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the fan and its pending actions."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
