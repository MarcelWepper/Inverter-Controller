"""Config flow and Options flow for Inverter Controller."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    DOMAIN, 
    DEFAULT_MIN_POWER, 
    DEFAULT_MAX_POWER, 
    DEFAULT_STEP_SIZE, 
    DEFAULT_ALPHA,
    DEFAULT_BOOST_THRESHOLD,
    DEFAULT_EMPTY_THRESHOLD
)

def get_full_schema(defaults: dict | None = None) -> vol.Schema:
    """Centralized schema used for initial setup and reconfiguration."""
    if defaults is None: defaults = {}
    return vol.Schema({
        vol.Required("grid_sensor", default=defaults.get("grid_sensor")): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Required("soc_sensor", default=defaults.get("soc_sensor")): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Required("solar_sensor", default=defaults.get("solar_sensor")): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Required("inverter_limit_entity", default=defaults.get("inverter_limit_entity")): selector.EntitySelector(selector.EntitySelectorConfig(domain=["number", "input_number"])),
        # min_power is fully configurable here:
        vol.Optional("min_power", default=defaults.get("min_power", DEFAULT_MIN_POWER)): int,
        vol.Optional("max_power", default=defaults.get("max_power", DEFAULT_MAX_POWER)): int,
        vol.Optional("step_size", default=defaults.get("step_size", DEFAULT_STEP_SIZE)): int,
        vol.Optional("solar_ema_alpha", default=defaults.get("solar_ema_alpha", DEFAULT_ALPHA)): selector.NumberSelector(selector.NumberSelectorConfig(min=0.01, max=1.0, step=0.01, mode="box")),
        vol.Optional("boost_threshold", default=defaults.get("boost_threshold", DEFAULT_BOOST_THRESHOLD)): selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%", mode="box")),
        # New Empty Threshold configurable in UI:
        vol.Optional("empty_threshold", default=defaults.get("empty_threshold", DEFAULT_EMPTY_THRESHOLD)): selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode="box")),
    })

class InverterControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Inverter Controller."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> InverterControllerOptionsFlowHandler:
        return InverterControllerOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Inverter Controller", data=user_input)
        return self.async_show_form(step_id="user", data_schema=get_full_schema())

class InverterControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle editing variables."""
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current_config = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=get_full_schema(current_config))