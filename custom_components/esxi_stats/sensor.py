"""Sensor platform for esxi_stats."""
import logging
from string import capwords
from datetime import timedelta
from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    DOMAIN_DATA,
    DEFAULT_NAME,
    DEFAULT_OPTIONS,
    MAP_TO_MEASUREMENT,
)

SCAN_INTERVAL = timedelta(seconds=15)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    """Set up sensor platform."""
    for cond in hass.data[DOMAIN_DATA]["monitored_conditions"]:
        for obj in hass.data[DOMAIN_DATA][cond]:
            async_add_entities([ESXiSensor(hass, discovery_info, cond, obj)], True)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up sensor platform."""
    config = config_entry.data
    entry_id = config_entry.entry_id
    sensors = []

    for cond in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for obj in hass.data[DOMAIN_DATA][entry_id][cond]:
            if cond == "vm":
                # Create individual sensors for each VM attribute
                vm_data = hass.data[DOMAIN_DATA][entry_id][cond][obj]
                for attr_key, attr_value in vm_data.items():
                    if attr_key not in ["uuid", "vm_name"]:  # Skip internal fields
                        sensors.append(ESXiSensor(hass, config, cond, obj, config_entry, attr_key))
            elif cond == "vmhost":
                # Create individual sensors for each host attribute
                host_data = hass.data[DOMAIN_DATA][entry_id][cond][obj]
                for attr_key, attr_value in host_data.items():
                    if attr_key not in ["original_name"]:  # Skip internal fields
                        sensors.append(ESXiSensor(hass, config, cond, obj, config_entry, attr_key))
            elif cond == "license":
                # License entities go to their respective host devices, except vCenter license
                if obj == "vcenter_license":
                    # vCenter license stays under ESXi Stats device
                    sensors.append(ESXiSensor(hass, config, cond, obj, config_entry))
                else:
                    # Host licenses go to their respective host devices
                    sensors.append(ESXiSensor(hass, config, cond, obj, config_entry))
            else:
                # Datastore and other entities stay under ESXi Stats device
                sensors.append(ESXiSensor(hass, config, cond, obj, config_entry))

    async_add_devices(sensors, True)


class ESXiSensor(Entity):
    """ESXi_stats Sensor class."""

    def __init__(self, hass, config, cond, obj, config_entry=None, attribute_key=None):
        """Init."""
        self.hass = hass
        self._attr = {}
        self._config_entry = config_entry
        self._state = None
        self.config = config
        self._attribute_key = attribute_key  # For individual attribute sensors

        # If configured via yaml, set options to defaults
        # This is likely a temporary fix because yaml config will likely be removed
        if config_entry is not None:
            self._entry_id = config_entry.entry_id
            self._options = config_entry.options
        else:
            self._entry_id = None
            self._options = DEFAULT_OPTIONS
        self._cond = cond
        self._obj = obj

    def update(self):
        """Update the sensor."""
        self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
        self._data = self.hass.data[DOMAIN_DATA][self._entry_id][self._cond][self._obj]

        if self._attribute_key:
            # For individual attribute sensors, state is the attribute value
            self._state = self._data.get(self._attribute_key, "Unknown")
            self._measurement = measure_format(self._attribute_key)
            # No additional attributes for individual sensors
            self._attr = {}
        else:
            # For legacy sensors (datastore, vCenter license), use configured state
            if self._options[self._cond] not in self._data.keys():
                self._state = "Error"
                self._measurement = ""
                _LOGGER.error(
                    "State is set to incorrect key. Check Options in Integration UI"
                )
            else:
                self._state = self._data[self._options[self._cond]]
                self._measurement = measure_format(self._options[self._cond])

            # Set attributes for legacy sensors
            for key, value in self._data.items():
                if key != "uuid":
                    self._attr[key] = value

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        if self._attribute_key:
            return "{}_{}_{}_{}_{}_{}".format(
                self.config["host"].replace(".", "_"), self._entry_id, self._cond, self._obj, "attr", self._attribute_key
            )
        else:
            return "{}_{}_{}_{}".format(
                self.config["host"].replace(".", "_"), self._entry_id, self._cond, self._obj
            )

    @property
    def should_poll(self):
        """Return the name of the sensor."""
        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        if self._attribute_key:
            # For individual attribute sensors, use cleaner names
            if self._cond == "vm":
                vm_name = self._data.get("vm_name", self._obj)
                return f"{vm_name} {capwords(self._attribute_key.replace('_', ' '))}"
            elif self._cond == "vmhost":
                return f"{self._obj.replace('_', ' ').title()} {capwords(self._attribute_key.replace('_', ' '))}"
            else:
                return f"{self._obj} {capwords(self._attribute_key.replace('_', ' '))}"
        else:
            # Legacy naming for datastore and vCenter license - make more user-friendly
            if self._cond == "datastore":
                return f"{DEFAULT_NAME} Datastore {self._obj.replace('_', ' ').title()}"
            elif self._cond == "license":
                if self._obj == "vcenter_license":
                    return f"{DEFAULT_NAME} vCenter License"
                else:
                    return f"{DEFAULT_NAME} License {self._obj.replace('_license', '').replace('_', ' ').title()}"
            else:
                return f"{DEFAULT_NAME} {self._cond.title()} {self._obj.replace('_', ' ').title()}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._measurement

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attr

    @property
    def device_info(self):
        """Return device info for this sensor."""
        if self._config_entry is None:
            identifier = {(DOMAIN, self.config["host"].replace(".", "_"))}
            device_name = "ESXi Stats"
            manufacturer = "VMware, Inc."
        else:
            if self._cond == "vm":
                # VM sensors go to VM device
                vm_data = self._data
                vm_name = vm_data.get("vm_name", self._obj)
                identifier = {(DOMAIN, f"vm_{self._obj}")}
                device_name = f"VM: {vm_name}"
                manufacturer = "VMware Virtual Machine"
            elif self._cond == "vmhost":
                # Host sensors go to host device
                host_data = self._data
                host_name = host_data.get("original_name", self._obj)
                identifier = {(DOMAIN, f"host_{self._obj}")}
                device_name = f"ESXi Host: {host_name}"
                manufacturer = "VMware ESXi"
            elif self._cond == "license" and self._obj != "vcenter_license":
                # Host license sensors go to their respective host device
                # Extract host name from license entity name
                host_name = self._obj.replace("_license", "").replace("_", " ").title()
                identifier = {(DOMAIN, f"host_{self._obj.replace('_license', '')}")}
                device_name = f"ESXi Host: {host_name}"
                manufacturer = "VMware ESXi"
            else:
                # Everything else stays under ESXi Stats device
                identifier = {(DOMAIN, self._config_entry.entry_id)}
                device_name = "ESXi Stats"
                manufacturer = "VMware, Inc."

        return {
            "identifiers": identifier,
            "name": device_name,
            "manufacturer": manufacturer,
        }


def measure_format(input):
    """Return measurement in readable form."""
    if input in MAP_TO_MEASUREMENT.keys():
        return MAP_TO_MEASUREMENT[input]
    else:
        return capwords(input.replace("_", " "))
