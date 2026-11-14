"""Device-page controls for reaching known fan speed endpoints."""

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory


async def async_setup_entry(hass, entry, async_add_entities):
    """Expose calibration without requiring Tools or YAML."""
    async_add_entities(
        [
            CalibrationButton(entry.runtime_data, direction)
            for direction in ("increase", "decrease")
        ]
    )


class CalibrationButton(ButtonEntity):
    """Reuse the fan's serialized calibration operation."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, fan, direction):
        self._fan = fan
        self._direction = direction
        self._attr_unique_id = f"{fan.unique_id}_calibrate_{direction}"
        self._attr_device_info = fan.device_info
        self._attr_name = (
            "Calibrate to maximum"
            if direction == "increase"
            else "Calibrate to minimum"
        )
        self._attr_icon = (
            "mdi:fan-chevron-up" if direction == "increase" else "mdi:fan-chevron-down"
        )

    async def async_press(self):
        self._fan.async_set_context(self._context)
        await self._fan.async_calibrate(self._direction)
