"""Constants for the Inverter Controller integration."""
import logging

DOMAIN = "inverter_controller"
LOGGER = logging.getLogger(__package__)

DEFAULT_MIN_POWER = 100
DEFAULT_MAX_POWER = 800
DEFAULT_STEP_SIZE = 50
DEFAULT_ALPHA = 0.3
DEFAULT_BOOST_THRESHOLD = 95
DEFAULT_EMPTY_THRESHOLD = 10
DEFAULT_IMPORT_THRESHOLD = 10 # Start increasing if importing > 10W
DEFAULT_EXPORT_THRESHOLD = 20 # Start decreasing if exporting > 20W