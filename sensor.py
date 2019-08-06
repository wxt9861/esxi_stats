"""Sensor platform for esxi_stats."""
import logging
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, DOMAIN_DATA

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Setup sensor platform."""

    for condition in hass.data[DOMAIN_DATA]["monitored_conditions"]:
        async_add_entities([esxiSensor(hass, discovery_info, condition)], True)

class esxiSensor(Entity):
    """esxi_stats Sensor class."""

    def __init__(self, hass, config, condition):
        self.hass = hass
        self.attr = {}
        self._state = None
        self._name = config["name"]
        self._condition = condition

    async def async_update(self):
        await self.hass.data[DOMAIN_DATA]["client"].update_data()

        # set state
        self._state = len(self.hass.data[DOMAIN_DATA][self._condition])

        # set host measurement/attirbutes
        if self._condition == "hosts":
            self._measurement = "host(s)"
            for key, value in self.hass.data[DOMAIN_DATA][self._condition].items():
                self.attr[key] = value

        # set datastore measurement/attirbutes
        if self._condition == "datastores":
            self._measurement = "datastore(s)"
            for key, value in self.hass.data[DOMAIN_DATA][self._condition].items():
                self.attr[key] = value

        # set vm measurement/attirbutes
        if self._condition == "vms":
            self._measurement = "Virtual Machone(s)"
            for key, value in self.hass.data[DOMAIN_DATA][self._condition].items():
                self.attr[key] = value

    @property
    def should_poll(self):
        """Return the name of the sensor."""
        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        #return self._name
        return "{} {}".format(self._name, self._condition)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._measurement

    #@property
    #def icon(self):
    #    """Return the icon of the sensor."""
    #    return ICON

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attr