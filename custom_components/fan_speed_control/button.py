"""Device-page controls for reaching known fan speed endpoints."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er


async def async_setup_entry(hass, entry, async_add_entities):
    """Expose calibration without requiring Tools or YAML."""
    registry = er.async_get(hass)
    if old_minimum := registry.async_get_entity_id(
        "button", "fan_speed_control", f"{entry.entry_id}_calibrate_decrease"
    ):
        registry.async_remove(old_minimum)
    async_add_entities([CalibrationButton(entry.runtime_data)])


class CalibrationButton(ButtonEntity):
    """Reuse the fan's serialized calibration operation."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, fan):
        self._fan = fan
        self._attr_unique_id = f"{fan.unique_id}_calibrate_increase"
        self._attr_device_info = fan.device_info
        self._attr_name = "Calibrate fan"
        self._attr_icon = "mdi:fan-chevron-up"

    async def async_press(self):
        self._fan.async_set_context(self._context)
        await self._fan.async_calibrate()
