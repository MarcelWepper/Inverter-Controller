"""Reactive logic for Inverter Controller."""
from __future__ import annotations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event
from .const import (
    DOMAIN, 
    LOGGER, 
    DEFAULT_MIN_POWER, 
    DEFAULT_MAX_POWER, 
    DEFAULT_STEP_SIZE, 
    DEFAULT_ALPHA,
    DEFAULT_BOOST_THRESHOLD,
    DEFAULT_EMPTY_THRESHOLD,
    DEFAULT_IMPORT_THRESHOLD,
    DEFAULT_EXPORT_THRESHOLD
)

class InverterCoordinator(DataUpdateCoordinator):
    """Processes grid/solar data and stores state for sensors."""

    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, name=DOMAIN)
        self.config_entry = entry
        self.solar_ema = None
        self.hard_boost = False
        self.enabled = True
        
        self.data = {
            "target_power": 100,
            "solar_ema": 0.0,
            "house_load": 0.0,
            "solar_yield": 0.0,
            "logic_state": "Initializing",
            "hard_boost": False,
            "guard_active": False,
        }

        self.config_entry.async_on_unload(
            async_track_state_change_event(
                hass, 
                [self.get_cfg("grid_sensor"), self.get_cfg("soc_sensor"), self.get_cfg("solar_sensor")], 
                self._async_handle_update
            )
        )

    def get_cfg(self, key, default=None):
        return self.config_entry.options.get(key, self.config_entry.data.get(key, default))

    async def _async_handle_update(self, event):
        try:
            grid_p = float(self.hass.states.get(self.get_cfg("grid_sensor")).state or 0)
            soc = float(self.hass.states.get(self.get_cfg("soc_sensor")).state or 0)
            solar_raw = float(self.hass.states.get(self.get_cfg("solar_sensor")).state or 0)
            limit_id = self.get_cfg("inverter_limit_entity")
            current = float(self.hass.states.get(limit_id).state or 100)
        except (ValueError, AttributeError, TypeError): return

        alpha = self.get_cfg("solar_ema_alpha", DEFAULT_ALPHA)
        house_load = current + grid_p
        yield_ratio = (current / solar_raw * 100) if solar_raw > 0 else 0

        if self.solar_ema is None: self.solar_ema = solar_raw
        else: self.solar_ema = (alpha * solar_raw) + ((1 - alpha) * self.solar_ema)

        boost_threshold = self.get_cfg("boost_threshold", DEFAULT_BOOST_THRESHOLD)
        if not self.hard_boost and soc >= boost_threshold: 
            self.hard_boost = True
        elif self.hard_boost and soc <= (boost_threshold - 2):
            self.hard_boost = False

        state_desc, desired = "Balanced", current
        step = self.get_cfg("step_size", DEFAULT_STEP_SIZE)
        empty_threshold = self.get_cfg("empty_threshold", DEFAULT_EMPTY_THRESHOLD)
        
        # Fetch the user-defined deadbands
        import_threshold = self.get_cfg("import_threshold", DEFAULT_IMPORT_THRESHOLD)
        export_threshold = self.get_cfg("export_threshold", DEFAULT_EXPORT_THRESHOLD)
        
        # Logic Loop
        if solar_raw < 10 and soc < empty_threshold:
            desired = self.get_cfg("min_power", DEFAULT_MIN_POWER)
            state_desc = f"Standby (Empty Battery)"
        elif self.hard_boost: 
            # Directly track incoming solar power (Solar Passthrough)
            desired = solar_raw 
            state_desc = f"Boosting (Solar Passthrough: {int(solar_raw)}W)"
        elif grid_p > import_threshold: 
            desired, state_desc = desired + step, "Importing (Increase)"
        elif grid_p < -export_threshold: 
            desired, state_desc = desired - step, "Exporting (Decrease)"

        # Constraints
        # This line automatically limits it to your configured max_power (e.g., 800) and min_power
        target = max(self.get_cfg("min_power", DEFAULT_MIN_POWER), min(self.get_cfg("max_power", DEFAULT_MAX_POWER), desired))

        if self.enabled and target != current:
            await self.hass.services.async_call(limit_id.split(".")[0], "set_value", {"entity_id": limit_id, "value": target})

        self.data.update({
            "target_power": target, 
            "solar_ema": round(self.solar_ema, 1),
            "house_load": round(house_load, 1),
            "solar_yield": round(yield_ratio, 1),
            "logic_state": state_desc, 
            "hard_boost": self.hard_boost, 
            "guard_active": False 
        })
        self.async_set_updated_data(self.data)