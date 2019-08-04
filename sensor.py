"""Sensor platform for ynab."""
import logging
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, DOMAIN_DATA

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Setup sensor platform."""
    async_add_entities([esxiSensor(hass, discovery_info)], True)

class esxiSensor(Entity):
    """esxi Sensor class."""

    def __init__(self, hass, config):
        self.hass = hass
        self.attr = {}
        self._state = None
        self._name = config["name"]

    async def async_update(self):
        await self.hass.data[DOMAIN_DATA]["client"].update_data()

    @property
    def should_poll(self):
        """Return the name of the sensor."""
        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    #@property
    #def unit_of_measurement(self):
    #    return self._measurement

    #@property
    #def icon(self):
    #    """Return the icon of the sensor."""
    #    return ICON

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attr