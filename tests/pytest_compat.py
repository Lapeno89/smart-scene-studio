"""Compatibility for the HA test fixture's copied logger helpers."""

from homeassistant.components import logger
from homeassistant.components.logger import helpers as logger_helpers

# pytest-homeassistant-custom-component 0.13.375 is copied from HA 2026.10.4.
# HA 2026.11 moved this helper into logger.helpers; expose the old import path
# for the fixture while keeping its cleanup behavior active.
if not hasattr(logger, "_clear_logger_overwrites"):
    logger._clear_logger_overwrites = logger_helpers._clear_logger_overwrites


