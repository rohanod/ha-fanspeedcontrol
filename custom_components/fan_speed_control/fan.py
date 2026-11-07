"""A serialized, optimistic fan driven by native HA action sequences."""

import asyncio
import logging
from contextlib import asynccontextmanager

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.script import Script

from .config_flow import config_schema
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def percentage_to_step(percentage, count):
    """Keep the legacy script's nearest-step mapping."""
    return (
        int(max(1, min(count, (percentage * count + 50) // 100))) if percentage else 0
    )


def step_to_percentage(step, count):
    """Expose a discrete step as an integer percentage."""
    return max(1, min(100, (step * 100 + count // 2) // count)) if step else 0


def choose_direction(current, target, count, wrap_increase, wrap_decrease):
    """Use shortest permitted path; ties prefer the direct path."""
    direction = "increase" if target >= current else "decrease"
    presses = abs(target - current)
    if (
        (direction == "increase" and wrap_decrease)
        or (direction == "decrease" and wrap_increase)
    ) and count - presses < presses:
        return ("decrease" if direction == "increase" else "increase"), count - presses
    return direction, presses


async def async_setup_entry(hass, entry, async_add_entities):
    """Validate and add a fan without transmitting at startup."""
    config = config_schema()(dict(entry.data))
    async_add_entities([ActionFan(hass, entry.entry_id, config)])


class ActionFan(FanEntity, RestoreEntity):
    """Own power/speed state; never call back into this fan's services."""

    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_is_on = False
    _attr_percentage = 0
    _attr_oscillating = False
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, hass, unique_id, config):
        self._attr_name = config["name"]
        self._attr_unique_id = unique_id
        self._config = config
        self._attr_speed_count = config["speed_count"]
        self._lock = asyncio.Lock()
        self._removing = False
        self._scripts = {
            key: Script(hass, config[key], f"{unique_id}_{key}", DOMAIN, logger=_LOGGER)
            for key in ("turn_on", "turn_off", "increase", "decrease", "oscillate")
            if key in config
        }
        if "oscillate" in self._scripts:
            self._attr_supported_features |= FanEntityFeature.OSCILLATE

    async def async_added_to_hass(self):
        """Restore estimates only; a restart never presses remote buttons."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state and state.state not in (STATE_ON, STATE_OFF):
            self._attr_is_on = None
            self._attr_percentage = None
        if state and state.state in (
            STATE_ON,
            STATE_OFF,
        ):
            self._attr_is_on = state.state == STATE_ON
            percentage = state.attributes.get("percentage")
            self._attr_percentage = (
                (
                    percentage
                    if isinstance(percentage, (int, float)) and 1 <= percentage <= 100
                    else None
                )
                if self._attr_is_on
                else 0
            )
            self._attr_oscillating = state.attributes.get("oscillating", False) is True

    async def async_will_remove_from_hass(self):
        """Stop scripts and wait for commands to leave their critical section."""
        self._removing = True
        await asyncio.gather(
            *(script.async_unload() for script in self._scripts.values())
        )
        async with self._lock:
            pass
        await super().async_will_remove_from_hass()

    @asynccontextmanager
    async def _operation(self):
        async with self._lock:
            if self._removing:
                raise HomeAssistantError("Fan is unloading")
            try:
                yield
            finally:
                self.async_write_ha_state()

    async def _run(self, action, **variables):
        if self._removing:
            raise HomeAssistantError("Fan is unloading")
        result = await self._scripts[action].async_run(variables, context=self._context)
        if result is None:
            raise HomeAssistantError(f"Fan action {action} did not complete")

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        async with self._operation():
            await self._set_percentage(
                percentage
                if percentage is not None
                else (
                    self._attr_percentage
                    if self._attr_is_on
                    else self._config["power_on_percentage"]
                )
            )

    async def async_turn_off(self, **kwargs):
        async with self._operation():
            await self._set_percentage(0)

    async def async_set_percentage(self, percentage):
        async with self._operation():
            await self._set_percentage(percentage)

    async def _set_percentage(self, percentage):
        if percentage is None:
            raise HomeAssistantError(
                "Speed unknown; turn the fan off then on to resynchronize"
            )
        target = percentage_to_step(percentage, self.speed_count)
        try:
            if target == 0:
                if self._attr_is_on is not False:
                    await self._run("turn_off")
                self._attr_is_on = False
                self._attr_percentage = 0
                return
            if self._attr_is_on is None:
                raise HomeAssistantError(
                    "Power unknown; verify physical state before retrying"
                )
            if not self._attr_is_on:
                await self._run("turn_on")
                self._attr_is_on = True
                self._attr_percentage = self._config["power_on_percentage"]
                await asyncio.sleep(self._config["startup_delay"])
            if self._attr_percentage is None:
                raise HomeAssistantError(
                    "Speed unknown; turn the fan off then on to resynchronize"
                )
            current = percentage_to_step(self._attr_percentage, self.speed_count)
            direction, presses = choose_direction(
                current,
                target,
                self.speed_count,
                self._config["wrap_increase"],
                self._config["wrap_decrease"],
            )
            for index in range(presses):
                await self._run(direction)
                if index + 1 < presses:
                    await asyncio.sleep(self._config["command_delay"])
            self._attr_percentage = step_to_percentage(target, self.speed_count)
        except (Exception, asyncio.CancelledError):
            self._attr_percentage = None
            # Even a service error can occur after transmission. Never claim power.
            if target == 0 or self._attr_is_on is False:
                self._attr_is_on = None
            raise

    async def async_oscillate(self, oscillating):
        async with self._operation():
            if not self._attr_is_on:
                raise HomeAssistantError("Turn the fan on before changing oscillation")
            if self._attr_oscillating == oscillating:
                return
            try:
                await self._run("oscillate", oscillating=oscillating)
            except (Exception, asyncio.CancelledError):
                self._attr_oscillating = None
                raise
            self._attr_oscillating = oscillating

    async def async_sync_state(self, percentage, oscillating=False):
        """Record a physically verified state without sending commands."""
        async with self._operation():
            self._attr_is_on = percentage > 0
            self._attr_percentage = step_to_percentage(
                percentage_to_step(percentage, self.speed_count), self.speed_count
            )
            self._attr_oscillating = oscillating if percentage else False
