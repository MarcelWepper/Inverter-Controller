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
    DEFAULT_EXPORT_THRESHOLD,
    DEFAULT_SOLAR_MARGIN,
    DEFAULT_STARTUP_LIMITER
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
        import_threshold = self.get_cfg("import_threshold", DEFAULT_IMPORT_THRESHOLD)
        export_threshold = self.get_cfg("export_threshold", DEFAULT_EXPORT_THRESHOLD)
        solar_margin = self.get_cfg("solar_margin", DEFAULT_SOLAR_MARGIN)
        max_p = self.get_cfg("max_power", DEFAULT_MAX_POWER)
        startup_limiter = self.get_cfg("startup_limiter", DEFAULT_STARTUP_LIMITER)
        
        # 1. Base Logic: What does the house need right now?
        if grid_p > import_threshold: 
            desired, state_desc = current + step, "Importing (Increase)"
        elif grid_p < -export_threshold: 
            desired, state_desc = current - step, "Exporting (Decrease)"

        # 2. Battery Protection Limits
        resume_threshold = empty_threshold + 5
        allowed_batt_power = 0
        
        if startup_limiter:
            # NEW: Stepped Start-up Limiter
            if soc < 10:
                max_physical_limit = 100
            elif soc < 15:
                max_physical_limit = 200
            elif soc < 20:
                max_physical_limit = 300
            else:
                max_physical_limit = max_p
        else:
            # OLD: Stateless Proportional Battery Protection
            if soc <= empty_threshold:
                allowed_batt_power = 0
            elif soc >= resume_threshold:
                allowed_batt_power = max_p
            else:
                progress = (soc - empty_threshold) / (resume_threshold - empty_threshold)
                allowed_batt_power = max_p * progress
            
            max_physical_limit = solar_raw + allowed_batt_power

        # 3. Apply Overrides
        if self.hard_boost:
            passthrough = max(0, solar_raw - solar_margin)
            if passthrough > desired:
                desired = passthrough
                state_desc = f"Boosting (Passthrough: {int(passthrough)}W)"
            else:
                state_desc = "Boosting (Covering Load)"
                
        elif desired > max_physical_limit:
            desired = max_physical_limit
            
            if startup_limiter and soc < 20:
                state_desc = f"Start-up Limiter (Capped at {int(max_physical_limit)}W)"
            elif not startup_limiter and allowed_batt_power == 0:
                if solar_raw < 10:
                    state_desc = "Standby (Empty Battery)"
                else:
                    state_desc = f"Solar Only (Capped at {int(solar_raw)}W)"
            elif not startup_limiter:
                state_desc = f"Battery Protection (Capped at {int(max_physical_limit)}W)"

        # 4. Final Constraints
        target = max(self.get_cfg("min_power", DEFAULT_MIN_POWER), min(max_p, desired))

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