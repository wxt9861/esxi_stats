"""ESXi Stats Integration."""

import logging
import os
from datetime import timedelta

from .esxi import (
    esx_connect,
    esx_disconnect,
    check_license,
    get_host_info,
    get_datastore_info,
    get_vm_info,
    vm_pwr,
)
from pyVmomi import vim  # pylint: disable=no-name-in-module
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_VERIFY_SSL,
    CONF_MONITORED_CONDITIONS,
)
from homeassistant.helpers import discovery
from homeassistant.util import Throttle
from .const import (
    AVAILABLE_CMND_VM_POWER,
    COMMAND,
    CONF_NAME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    DOMAIN_DATA,
    ISSUE_URL,
    PLATFORMS,
    REQUIRED_FILES,
    STARTUP,
    VERSION,
    VM,
)

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

CMND_VM_PWR_SCHEMA = vol.Schema(
    {vol.Required(VM): cv.string, vol.Required(COMMAND): cv.string}
)

MONITORED_CONDITIONS = {
    "hosts": ["ESXi Host", "", ""],
    "datastores": ["Datastores", "", ""],
    "vms": ["Virtual Machines", "", ""],
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
                vol.Optional(CONF_VERIFY_SSL, default=False): cv.boolean,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(CONF_MONITORED_CONDITIONS, default=["hosts"]): vol.All(
                    cv.ensure_list, [vol.In(MONITORED_CONDITIONS)]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up this integration using yaml."""
    if DOMAIN not in config:
        # Using config entries (UI COnfiguration)
        return True
    # startup message
    startup = STARTUP.format(name=DOMAIN, version=VERSION, issueurl=ISSUE_URL)
    _LOGGER.info(startup)

    # check all required files
    file_check = await check_files(hass)
    if not file_check:
        return False

    # create data dictionary
    hass.data[DOMAIN_DATA] = {}
    hass.data[DOMAIN_DATA]["configuration"] = "yaml"
    hass.data[DOMAIN_DATA]["hosts"] = {}
    hass.data[DOMAIN_DATA]["datastores"] = {}
    hass.data[DOMAIN_DATA]["vms"] = {}
    hass.data[DOMAIN_DATA]["monitored_conditions"] = config[DOMAIN].get(
        CONF_MONITORED_CONDITIONS
    )

    # get global config
    _LOGGER.debug("Setting up host %s", config[DOMAIN].get(CONF_HOST))
    hass.data[DOMAIN_DATA]["client"] = esxiStats(hass, config)

    try:
        conn_details = {
            "host": config[DOMAIN]["host"],
            "user": config[DOMAIN]["username"],
            "pwd": config[DOMAIN]["password"],
            "port": config[DOMAIN]["port"],
            "ssl": config[DOMAIN]["verify_ssl"],
        }
        conn = await esx_connect(**conn_details)

        # # get license type
        lic = check_license(conn.RetrieveContent().licenseManager)
    except Exception as exception:  # pylint: disable=broad-except
        _LOGGER.error(exception)
    finally:
        esx_disconnect(conn)

    # load platforms
    for platform in PLATFORMS:
        # Get platform specific configuration
        platform_config = config[DOMAIN]

        hass.async_create_task(
            discovery.async_load_platform(
                hass, platform, DOMAIN, platform_config, config
            )
        )

    # Tell HA that we used YAML for the configuration
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
        )
    )

    # if lisense allows API write, register services
    if lic:

        async def vm_power(call):
            vm = call.data["vm"]
            cmnd = call.data["command"]

            if cmnd in AVAILABLE_CMND_VM_POWER:
                try:
                    # await vm_pwr(vm, cmnd, conn_details)
                    hass.async_create_task(vm_pwr(vm, cmnd, conn_details))
                except Exception as e:
                    _LOGGER.error(str(e))
            else:
                _LOGGER.error("vm_power: '%s' is not a supported command", cmnd)

        hass.services.async_register(
            DOMAIN, "vm_power", vm_power, schema=CMND_VM_PWR_SCHEMA
        )
    else:
        _LOGGER.info(
            "Service calls are disabled - %s doesn't have a supported license",
            config[DOMAIN]["host"],
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI."""
    conf = hass.data.get(DOMAIN_DATA)
    if config_entry.source == config_entries.SOURCE_IMPORT:
        if conf is None:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
        # This is using YAML for configuration
        return False

    # check all required files
    file_check = await check_files(hass)
    if not file_check:
        return False

    config = {DOMAIN: config_entry.data}
    config[DOMAIN]["monitored_conditions"] = []

    # create data dictionary
    hass.data[DOMAIN_DATA] = {}
    hass.data[DOMAIN_DATA]["configuration"] = "config_flow"
    hass.data[DOMAIN_DATA]["hosts"] = {}
    hass.data[DOMAIN_DATA]["datastores"] = {}
    hass.data[DOMAIN_DATA]["vms"] = {}
    hass.data[DOMAIN_DATA]["monitored_conditions"] = []

    if config_entry.data["hosts"]:
        hass.data[DOMAIN_DATA]["monitored_conditions"].append("hosts")
        config[DOMAIN]["monitored_conditions"].append("hosts")
    if config_entry.data["datastores"]:
        hass.data[DOMAIN_DATA]["monitored_conditions"].append("datastores")
        config[DOMAIN]["monitored_conditions"].append("datastores")
    if config_entry.data["vms"]:
        hass.data[DOMAIN_DATA]["monitored_conditions"].append("vms")
        config[DOMAIN]["monitored_conditions"].append("vms")

    # get global config
    _LOGGER.debug("Setting up host %s", config[DOMAIN].get(CONF_HOST))
    hass.data[DOMAIN_DATA]["client"] = esxiStats(hass, config)

    try:
        conn_details = {
            "host": config[DOMAIN]["host"],
            "user": config[DOMAIN]["username"],
            "pwd": config[DOMAIN]["password"],
            "port": config[DOMAIN]["port"],
            "ssl": config[DOMAIN]["verify_ssl"],
        }
        conn = await esx_connect(**conn_details)

        # get license type
        lic = check_license(conn.RetrieveContent().licenseManager)
    except Exception as exception:  # pylint: disable=broad-except
        _LOGGER.error(exception)
        raise ConfigEntryNotReady
    finally:
        esx_disconnect(conn)

    # load platforms
    for platform in PLATFORMS:
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    # if lisense allows API write, register services
    if lic:

        async def vm_power(call):
            vm = call.data["vm"]
            cmnd = call.data["command"]

            if cmnd in AVAILABLE_CMND_VM_POWER:
                try:
                    await vm_pwr(vm, cmnd, conn_details)
                except Exception as e:
                    _LOGGER.error(str(e))
            else:
                _LOGGER.error("vm_power: '%s' is not a supported command", cmnd)

        hass.services.async_register(
            DOMAIN, "vm_power", vm_power, schema=CMND_VM_PWR_SCHEMA
        )
    else:
        _LOGGER.info(
            "Service calls are disabled - %s doesn't have a supported license",
            config[DOMAIN]["host"],
        )

    return True


class esxiStats:
    def __init__(self, hass, config):
        """Initialize the class."""
        self.hass = hass
        self.host = config[DOMAIN].get(CONF_HOST)
        self.user = config[DOMAIN].get(CONF_USERNAME)
        self.passwd = config[DOMAIN].get(CONF_PASSWORD)
        self.port = config[DOMAIN].get(CONF_PORT)
        self.ssl = config[DOMAIN].get(CONF_VERIFY_SSL)
        self.monitored_conditions = config[DOMAIN].get(CONF_MONITORED_CONDITIONS)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self):
        try:
            # connect and get data from host
            conn = await esx_connect(
                self.host, self.user, self.passwd, self.port, self.ssl
            )
            content = conn.RetrieveContent()

        except Exception as error:
            _LOGGER.error("ERROR: %s", error)

        else:
            # create/distroy view objects
            host_objview = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.HostSystem], True
            )
            ds_objview = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.Datastore], True
            )
            vm_objview = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.VirtualMachine], True
            )

            esxi_hosts = host_objview.view
            ds_list = ds_objview.view
            vm_list = vm_objview.view

            host_objview.Destroy()
            ds_objview.Destroy()
            vm_objview.Destroy()

            # get host stats
            if "hosts" in self.monitored_conditions:
                for esxi_host in esxi_hosts:
                    host_name = esxi_host.summary.config.name.replace(" ", "_").lower()

                    _LOGGER.debug("Getting stats for host: %s", host_name)
                    self.hass.data[DOMAIN_DATA]["hosts"][host_name] = get_host_info(
                        esxi_host
                    )

            # get datastore stats
            if "datastores" in self.monitored_conditions:
                for ds in ds_list:
                    ds_name = ds.summary.name.replace(" ", "_").lower()

                    _LOGGER.debug("Getting stats for datastore: %s", ds_name)
                    self.hass.data[DOMAIN_DATA]["datastores"][
                        ds_name
                    ] = get_datastore_info(ds)

            # get vm stats
            if "vms" in self.monitored_conditions:
                for vm in vm_list:
                    vm_name = vm.summary.config.name.replace(" ", "_").lower()

                    _LOGGER.debug("Getting stats for vm: %s", vm_name)
                    self.hass.data[DOMAIN_DATA]["vms"][vm_name] = get_vm_info(vm)

            esx_disconnect(conn)


async def check_files(hass):
    """Return bool that indicates if all files are present."""
    base = "{}/custom_components/{}/".format(hass.config.path(), DOMAIN)
    missing = []
    for file in REQUIRED_FILES:
        fullpath = "{}{}".format(base, file)
        if not os.path.exists(fullpath):
            missing.append(file)

    if missing:
        _LOGGER.critical("The following files are missing: %s", str(missing))
        returnvalue = False
    else:
        returnvalue = True

    return returnvalue


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    if hass.data.get(DOMAIN_DATA, {}).get("configuration") == "yaml":
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
            )
        )
    else:
        for plafrom in PLATFORMS:
            await hass.config_entries.async_forward_entry_unload(config_entry, plafrom)
        _LOGGER.info("Successfully removed the ESXi Stats integration")
