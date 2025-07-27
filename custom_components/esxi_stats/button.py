"""Button platform for ESXi Stats integration."""
import logging
from datetime import datetime
from homeassistant.components.button import ButtonEntity

from .const import (
    DOMAIN,
    DOMAIN_DATA,
    DEFAULT_NAME,
)
from .esxi import host_pwr, vm_pwr, vm_snap_take, vm_snap_remove

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up button platform."""
    config = config_entry.data
    entry_id = config_entry.entry_id
    buttons = []

    # Create host buttons
    if "vmhost" in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for host_name in hass.data[DOMAIN_DATA][entry_id]["vmhost"]:
            buttons.append(ESXiHostRebootButton(hass, config, host_name, config_entry))

    # Create VM buttons
    if "vm" in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for vm_name in hass.data[DOMAIN_DATA][entry_id]["vm"]:
            buttons.append(ESXiVMRebootButton(hass, config, vm_name, config_entry))
            # Add snapshot buttons for each VM
            buttons.append(ESXiVMSnapshotCreateButton(hass, config, vm_name, config_entry))
            buttons.append(ESXiVMSnapshotRemoveAllButton(hass, config, vm_name, config_entry))
            buttons.append(ESXiVMSnapshotRemoveFirstButton(hass, config, vm_name, config_entry))
            buttons.append(ESXiVMSnapshotRemoveLastButton(hass, config, vm_name, config_entry))

    if buttons:
        async_add_entities(buttons, True)


class ESXiHostRebootButton(ButtonEntity):
    """ESXi Host Reboot Button."""

    def __init__(self, hass, config, host_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._host_name = host_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._host_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._host_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vmhost"][self._host_name]
        except KeyError:
            _LOGGER.error("Host %s not found in data", self._host_name)
            self._host_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        return f"{DEFAULT_NAME} Reboot {self._host_name.replace('_', ' ').title()}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_host_reboot_{self._host_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Only available if host is powered on
        if not self._host_data:
            return False
        host_state = self._host_data.get("state", "unknown")
        return host_state == "poweredOn"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"host_{self._host_name}")},
            "name": f"ESXi Host {self._host_name.replace('_', ' ').title()}",
            "manufacturer": "VMware",
            "model": "ESXi Host",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._host_data:
            # Only include reboot-related attributes that aren't available as individual sensors
            attrs_map = {
                "power_state": "state",  # Power state is relevant for reboot operations
                "maintenance_mode": "maintenance_mode",  # Important for reboot safety
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._host_data:
                    attrs[attr_name] = self._host_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            # Check if host is available and powered on
            if not self.available:
                _LOGGER.warning(
                    "Cannot reboot host %s: host is not powered on or unavailable",
                    self._host_name
                )
                return

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

            # Use reboot command without force - safer approach
            await self.hass.async_add_executor_job(
                host_pwr,
                self.hass,
                target_host,
                "reboot",
                conn_details,
                False,  # force=False - user should manually set maintenance mode first
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to reboot host %s: %s", self._host_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:restart"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button


class ESXiVMRebootButton(ButtonEntity):
    """ESXi VM Reboot Button."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._vm_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]
        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._vm_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} Reboot {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_reboot_{self._vm_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Only available if VM is powered on
        if not self._vm_data:
            return False
        vm_state = self._vm_data.get("state", "unknown")
        return vm_state == "running"

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM: {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            # Only include reboot-related attributes that aren't available as individual sensors
            attrs_map = {
                "power_state": "state",  # Power state is relevant for reboot operations
                "tools_status": "tools_status",  # Important for reboot method selection
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            # Check if VM is available and powered on
            if not self.available:
                _LOGGER.warning(
                    "Cannot reboot VM %s: VM is not powered on or unavailable",
                    self._vm_name
                )
                return

            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot reboot VM %s: UUID not found", self._vm_name)
                return

            # Determine reboot method based on VMware Tools status
            tools_status = self._vm_data.get("tools_status", "").lower()

            # Use graceful reboot if VMware Tools are available and functional
            # toolsOk = current and running, toolsOld = old version but functional
            if tools_status in ["toolsok", "toolsold"]:
                reboot_command = "reboot"
                reboot_method = f"graceful reboot (VMware Tools: {tools_status})"
            else:
                reboot_command = "reset"
                reboot_method = f"hard reset (VMware Tools: {tools_status})"

            _LOGGER.info("VM %s: Using %s", self._vm_name, reboot_method)

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
                reboot_command,
                conn_details,
                False  # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to reboot VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:restart"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button


class ESXiVMSnapshotCreateButton(ButtonEntity):
    """ESXi VM Create Snapshot Button."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._vm_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]
        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._vm_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} Create Snapshot {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_snapshot_create_{self._vm_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Available regardless of VM power state
        return self._vm_data is not None and "state" in self._vm_data

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM: {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            # Include snapshot-related attributes
            attrs_map = {
                "power_state": "state",
                "snapshots": "snapshots",
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot create snapshot for VM %s: UUID not found", self._vm_name)
                return

            vm_proper_name = self._vm_data.get("vm_name", self._vm_name)

            # Generate snapshot name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_name = f"HA_Snapshot_{timestamp}"
            description = f"Snapshot created by Home Assistant on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            _LOGGER.info("Creating snapshot '%s' for VM %s", snap_name, vm_proper_name)

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_snap_take,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                snap_name,
                description,
                False,  # memory - don't include memory in snapshot
                True,   # quiesce - quiesce file system if VMware Tools available
                conn_details,
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to create snapshot for VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:camera"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button


class ESXiVMSnapshotRemoveAllButton(ButtonEntity):
    """ESXi VM Remove All Snapshots Button."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._vm_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]
        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._vm_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} Remove All Snapshots {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_snapshot_remove_all_{self._vm_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Only available if VM has snapshots
        if not self._vm_data:
            return False
        snapshots = self._vm_data.get("snapshots", 0)
        return snapshots > 0

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM: {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            attrs_map = {
                "snapshots": "snapshots",
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            # Check if VM has snapshots
            if not self.available:
                _LOGGER.warning("Cannot remove snapshots for VM %s: no snapshots available", self._vm_name)
                return

            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot remove snapshots for VM %s: UUID not found", self._vm_name)
                return

            vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
            _LOGGER.info("Removing all snapshots for VM %s", vm_proper_name)

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_snap_remove,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                "all",
                conn_details,
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to remove all snapshots for VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:delete-sweep"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button


class ESXiVMSnapshotRemoveFirstButton(ButtonEntity):
    """ESXi VM Remove First Snapshot Button."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._vm_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]
        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._vm_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} Remove First Snapshot {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_snapshot_remove_first_{self._vm_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Only available if VM has snapshots
        if not self._vm_data:
            return False
        snapshots = self._vm_data.get("snapshots", 0)
        return snapshots > 0

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM: {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            attrs_map = {
                "snapshots": "snapshots",
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            # Check if VM has snapshots
            if not self.available:
                _LOGGER.warning("Cannot remove first snapshot for VM %s: no snapshots available", self._vm_name)
                return

            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot remove first snapshot for VM %s: UUID not found", self._vm_name)
                return

            vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
            _LOGGER.info("Removing first snapshot for VM %s", vm_proper_name)

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_snap_remove,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                "first",
                conn_details,
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to remove first snapshot for VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:delete-outline"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button


class ESXiVMSnapshotRemoveLastButton(ButtonEntity):
    """ESXi VM Remove Last Snapshot Button."""

    def __init__(self, hass, config, vm_name, config_entry):
        """Initialize the button."""
        self.hass = hass
        self.config = config
        self._vm_name = vm_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._vm_data = {}

    def update(self):
        """Update the button state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._vm_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vm"][self._vm_name]
        except KeyError:
            _LOGGER.error("VM %s not found in data", self._vm_name)
            self._vm_data = {}

    @property
    def name(self):
        """Return the name of the button."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return f"{DEFAULT_NAME} Remove Last Snapshot {vm_proper_name}"

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_vm_snapshot_remove_last_{self._vm_name}"

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        # Only available if VM has snapshots
        if not self._vm_data:
            return False
        snapshots = self._vm_data.get("snapshots", 0)
        return snapshots > 0

    @property
    def device_info(self):
        """Return device information."""
        vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
        return {
            "identifiers": {(DOMAIN, f"vm_{self._vm_name}")},
            "name": f"VM: {vm_proper_name}",
            "manufacturer": "VMware",
            "model": "Virtual Machine",
            "via_device": (DOMAIN, self.config["host"]),
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attrs = {}
        if self._vm_data:
            attrs_map = {
                "snapshots": "snapshots",
            }
            for attr_name, data_key in attrs_map.items():
                if data_key in self._vm_data:
                    attrs[attr_name] = self._vm_data[data_key]
        return attrs

    async def async_press(self, **kwargs):
        """Handle the button press."""
        try:
            # Check if VM has snapshots
            if not self.available:
                _LOGGER.warning("Cannot remove last snapshot for VM %s: no snapshots available", self._vm_name)
                return

            vm_uuid = self._vm_data.get("uuid")
            if not vm_uuid:
                _LOGGER.error("Cannot remove last snapshot for VM %s: UUID not found", self._vm_name)
                return

            vm_proper_name = self._vm_data.get("vm_name", self._vm_name)
            _LOGGER.info("Removing last snapshot for VM %s", vm_proper_name)

            conn_details = {
                "host": self.config["host"],
                "user": self.config["username"],
                "pwd": self.config["password"],
                "port": self.config["port"],
                "ssl": self.config["verify_ssl"],
            }

            await self.hass.async_add_executor_job(
                vm_snap_remove,
                self.hass,
                self.config["host"],
                self._vm_name,
                [vm_uuid],
                "last",
                conn_details,
                True    # notify
            )

            # Request immediate update
            await self.hass.async_add_executor_job(self.update)

        except Exception as e:
            _LOGGER.error("Failed to remove last snapshot for VM %s: %s", self._vm_name, e)

    @property
    def icon(self):
        """Return the icon for the button."""
        return "mdi:delete"

    @property
    def entity_category(self):
        """Return the entity category."""
        return None  # This is a control button, not a config button
