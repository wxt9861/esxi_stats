"""ESXi Stats select platform."""
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DOMAIN_DATA
from .esxi import esx_connect, esx_disconnect

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ESXi Stats select entities."""
    config = config_entry.data
    entry_id = config_entry.entry_id
    selects = []

    # Create power policy select entities for each host
    if "vmhost" in hass.data[DOMAIN_DATA][entry_id]["monitored_conditions"]:
        for host_name in hass.data[DOMAIN_DATA][entry_id]["vmhost"]:
            host_data = hass.data[DOMAIN_DATA][entry_id]["vmhost"][host_name]
            # Create select entity if host is available - availability will be checked in the entity itself
            _LOGGER.debug("Creating power policy select for host: %s, available policies: %s",
                         host_name, host_data.get("available_power_policies", []))
            selects.append(ESXiPowerPolicySelect(hass, config, host_name, config_entry))

    if selects:
        _LOGGER.debug("Adding %d power policy select entities", len(selects))
        async_add_entities(selects, True)
    else:
        _LOGGER.debug("No power policy select entities to add")


class ESXiPowerPolicySelect(SelectEntity):
    """ESXi Power Policy Select Entity."""

    def __init__(self, hass, config, host_name, config_entry):
        """Initialize the select entity."""
        self.hass = hass
        self.config = config
        self._host_name = host_name
        self._config_entry = config_entry
        self._entry_id = config_entry.entry_id
        self._host_data = {}
        self._friendly_name = host_name.replace("_", " ").title()

        # Get initial host data
        try:
            self._host_data = hass.data[DOMAIN_DATA][self._entry_id]["vmhost"][self._host_name]
        except KeyError:
            _LOGGER.warning("Host %s not found in data during initialization", self._host_name)
            self._host_data = {}

    @property
    def name(self):
        """Return the name of the select entity."""
        return f"{self._friendly_name} Power Policy"

    @property
    def unique_id(self):
        """Return a unique ID for this entity."""
        return f"{self.config['host'].replace('.', '_')}_{self._entry_id}_select_power_policy_{self._host_name}"

    @property
    def icon(self):
        """Return the icon for this entity."""
        return "mdi:power-settings"

    @property
    def entity_category(self):
        """Return the entity category."""
        # Using None instead of "config" to ensure visibility
        return None

    def update(self):
        """Update the select state."""
        try:
            # Get fresh data from the coordinator
            self.hass.data[DOMAIN_DATA][self._entry_id]["client"].update_data()
            self._host_data = self.hass.data[DOMAIN_DATA][self._entry_id]["vmhost"][self._host_name]
        except KeyError:
            _LOGGER.error("Host %s not found in data", self._host_name)
            self._host_data = {}

    @property
    def device_info(self):
        """Return device information."""
        host_data = self._host_data or {}
        host_original_name = host_data.get("original_name", self._host_name)
        return {
            "identifiers": {(DOMAIN, f"host_{self._host_name}")},
            "name": f"ESXi Host: {host_original_name}",
            "manufacturer": "VMware ESXi",
            "model": "ESXi Host",
            "sw_version": host_data.get("version", "Unknown"),
        }

    @property
    def current_option(self) -> str | None:
        """Return the current power policy."""
        if self._host_data:
            current_policy = self._host_data.get("power_policy")
            _LOGGER.debug("Host %s current power policy: %s", self._host_name, current_policy)
            # Return None if it's "n/a" or not available
            if current_policy and current_policy != "n/a":
                return current_policy
        return None

    @property
    def options(self) -> list[str]:
        """Return the list of available power policies."""
        if self._host_data:
            policies = self._host_data.get("available_power_policies", [])
            _LOGGER.debug("Host %s available power policies: %s", self._host_name, policies)
            return policies
        return []

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if self._host_data is None:
            _LOGGER.debug("Host %s: no host data available", self._host_name)
            return False

        host_state = self._host_data.get("state")
        available_policies = self._host_data.get("available_power_policies", [])

        _LOGGER.debug("Host %s availability check: state=%s, policies=%s",
                     self._host_name, host_state, available_policies)

        # Entity is available if host is powered on AND has power policies
        # But we show it even if temporarily unavailable for better UX
        is_available = (host_state == "poweredOn" and len(available_policies) > 0)

        if not is_available:
            _LOGGER.debug("Host %s is not available: state=%s, policy_count=%d",
                         self._host_name, host_state, len(available_policies))

        return is_available

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    async def async_select_option(self, option: str) -> None:
        """Change the power policy."""
        _LOGGER.info("Changing power policy for %s to %s", self._host_name, option)

        success = await self.hass.async_add_executor_job(
            self._set_power_policy, option
        )

        if success:
            # Trigger a data update to refresh the UI
            await self.hass.async_add_executor_job(self.update)

            # Show notification
            try:
                from homeassistant.components import persistent_notification
                persistent_notification.create(
                    self.hass,
                    f"Power policy changed to '{option}' for host {self._friendly_name}",
                    title="ESXi Power Policy Changed",
                    notification_id=f"esxi_power_policy_{self._host_name}"
                )
            except Exception as e:
                _LOGGER.debug("Could not create notification: %s", e)
        else:
            _LOGGER.error("Failed to change power policy for %s", self._host_name)

    def _set_power_policy(self, policy: str) -> bool:
        """Set the power policy on the ESXi host."""
        try:
            # Get connection details from config
            conn_details = {
                "host": self.config.get("host"),
                "user": self.config.get("username"),
                "pwd": self.config.get("password"),
                "port": self.config.get("port", 443),
                "ssl": self.config.get("verify_ssl", False),
            }

            conn = esx_connect(**conn_details)
            if not conn:
                _LOGGER.error("Failed to connect to ESXi host %s", self._host_name)
                return False

            try:
                from pyVmomi import vim, vmodl

                content = conn.RetrieveContent()
                obj_view = content.viewManager.CreateContainerView(
                    content.rootFolder, [vim.HostSystem], True
                )
                esxi_hosts = obj_view.view
                obj_view.Destroy()

                # Find our specific host using original name
                target_host = None
                original_host_name = self._host_data.get("original_name", self._host_name)
                for host in esxi_hosts:
                    if original_host_name and (
                        host.summary.config.name.lower() == original_host_name.lower() or
                        host.name.lower() == original_host_name.lower()):
                        target_host = host
                        break

                if not target_host:
                    _LOGGER.error("Host %s not found", self._host_name)
                    return False

                # Check if host supports power system capability
                if (not hasattr(target_host.config, 'powerSystemCapability') or
                    not target_host.config.powerSystemCapability):
                    _LOGGER.error("Host %s does not support power policy configuration", self._host_name)
                    return False

                # Find the policy key
                policy_key = None
                for available_policy in target_host.config.powerSystemCapability.availablePolicy:
                    if available_policy.shortName == policy:
                        policy_key = available_policy.key
                        break

                if not policy_key:
                    available_policies = [p.shortName for p in target_host.config.powerSystemCapability.availablePolicy]
                    _LOGGER.error(
                        "Power policy '%s' not found for host %s. Available policies: %s",
                        policy, self._host_name, available_policies
                    )
                    return False

                # Apply the power policy
                target_host.configManager.powerSystem.ConfigurePowerPolicy(policy_key)
                _LOGGER.info("Successfully changed power policy to '%s' for host %s", policy, self._host_name)
                return True

            except vmodl.MethodFault as error:
                _LOGGER.error("VMware method fault while setting power policy: %s", error.msg)
                return False
            except Exception as error:
                _LOGGER.error("Unexpected error while setting power policy: %s", error)
                return False
            finally:
                esx_disconnect(conn)

        except Exception as error:
            _LOGGER.error("Error setting power policy for %s: %s", self._host_name, error)
            return False
