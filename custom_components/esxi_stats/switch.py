"""Switch platform for ESXi Stats integration."""
import logging
from datetime import timedelta
from homeassistant.components.switch import SwitchEntity

from .const import (
    DOMAIN,
    DOMAIN_DATA,
    DEFAULT_NAME,
)
from .esxi import vm_pwr, host_pwr

SCAN_INTERVAL = timedelta(seconds=15)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up switch platform."""
    config = config_entry.data
    entry_id = config_entry.entry_id
    switches = []

    # Create VM switches
    if "vm" in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for vm_name in hass.data[DOMAIN_DATA][entry_id]["vm"]:
            switches.append(ESXiVMSwitch(hass, config, vm_name, config_entry))

    # Create host switches
    if "vmhost" in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for host_name in hass.data[DOMAIN_DATA][entry_id]["vmhost"]:
            switches.append(ESXiHostSwitch(hass, config, host_name, config_entry))

    if switches:
        async_add_entities(switches, True)


class ESXiVMSwitch(SwitchEntity):
    """ESXi VM Power Switch."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the switch."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._state = None
        self._vm_data = {}

    def update(self):
        """Update the switch state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]

            # Set state based on VM power state
            vm_state = self._vm_data.get("state", "unknown")
            self._state = vm_state == "running"

        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} VM {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_switch_{self._vm_name}"

    @property
    def is_on(self):
        """Return true if the VM is powered on."""
        return self._state

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        return self._vm_data is not None and "state" in self._vm_data

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            # Only include power-related attributes that aren't available as individual sensors
            # State is relevant since it's the power state of the VM
            attrs_map = {
                "state": "state",  # Power state is relevant to the power switch
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn the VM on."""
        try:
            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot power on VM %s: UUID not found", self._vm_name)
                return

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_pwr,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                "on",
                conn_details,
                False  # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to power on VM %s: %s", self._vm_name, e)

    async def async_turn_off(self, **kwargs):
        """Turn the VM off with smart shutdown logic."""
        try:
            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot power off VM %s: UUID not found", self._vm_name)
                return

            # Determine shutdown method based on VMware Tools status
            tools_status = self._vm_data.get("tools_status", "").lower()

            # Use graceful shutdown if VMware Tools are available and functional
            # toolsOk = current and running, toolsOld = old version but functional
            if tools_status in ["toolsok", "toolsold"]:
                power_command = "shutdown"
                shutdown_method = f"graceful shutdown (VMware Tools: {tools_status})"
            else:
                power_command = "off"
                shutdown_method = f"hard power off (VMware Tools: {tools_status})"

            _LOGGER.info("VM %s: Using %s", self._vm_name, shutdown_method)

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_pwr,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                power_command,
                conn_details,
                False  # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to power off VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the switch."""
        if self.is_on:
            return "mdi:server"
        return "mdi:server-off"


class ESXiHostSwitch(SwitchEntity):
    """ESXi Host Power Switch."""

    def __init__(self, hass, config, host_name, config_entry):
        """Initialize the switch."""
        self.hass = hass
        self.config = config
        self._host_name = host_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._state = None
        self._host_data = {}

    def update(self):
        """Update the switch state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._host_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vmhost"][self._host_name]

            # Set state based on host power state
            host_state = self._host_data.get("state", "unknown")
            self._state = host_state == "poweredOn"

        except KeyError:
            _LOGGER.error("Host %s not found in data", self._host_name)
            self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{DEFAULT_NAME} Host {self._host_name.replace('_', ' ').title()}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_host_switch_{self._host_name}"

    @property
    def is_on(self):
        """Return true if the host is powered on."""
        return self._state

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        return self._host_data is not None and "state" in self._host_data

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"host_{self._host_name}")},
            "name": f"ESXi Host {self._host_name.replace('_', ' ').title()}",
            "manufacturer": "VMware",
            "model": "ESXi Host",
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._host_data:
            # Only include power-related attributes that aren't available as individual sensors
            # State and shutdown capability are relevant to power control
            attrs_map = {
                "state": "state",  # Power state is relevant to the power switch
                "shutdown_supported": "shutdown_supported",  # Power capability info
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._host_data:
                    attrs[attr_name] = self._host_data[data_key]
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn the host on."""
        # Note: ESXi hosts typically cannot be powered on remotely
        # This is mainly for wake-on-LAN scenarios or integrated management
        _LOGGER.warning(
            "Power on command not supported for ESXi hosts. "
            "Use physical power button or management interface."
        )

    async def async_turn_off(self, **kwargs):
        """Turn the host off (shutdown)."""
        try:
            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            # Use the original host name from stored data for exact matching
            target_host = self._host_data.get("original_name", self._host_name)
            if not target_host:
                _LOGGER.error("Cannot determine target host name for %s", self._host_name)
                return

            # Use shutdown command without force - safer approach
            await self.hass.async_add_executor_job(
                host_pwr,
                self.hass,
                target_host,
                "shutdown",
                conn_details,
                False,  # force=False - user should manually set maintenance mode first
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to shutdown host %s: %s", self._host_name, e)

    @property
    def icon(self):
        """Return the icon for the switch."""
        if self.is_on:
            return "mdi:server-network"
        return "mdi:server-network-off"
