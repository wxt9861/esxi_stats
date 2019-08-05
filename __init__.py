"""ESXi Integration."""

import atexit
import logging
import os
from datetime import timedelta, datetime, date
from .esxi import get_content, getvminfo, get_host_info

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT
from homeassistant.helpers import discovery
from homeassistant.util import Throttle

import voluptuous as vol

import atexit
#from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim #pylint: disable=no-name-in-module

from .const import (
    CONF_NAME,
    DEFAULT_NAME,
    DOMAIN,
    DOMAIN_DATA,
    ISSUE_URL,
    PLATFORMS,
    REQUIRED_FILES,
    STARTUP,
    VERSION,
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_PORT, default=443): cv.positive_int,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional("scan_interval", default=60): cv.positive_int,
                vol.Optional("categories", default=None): vol.All(cv.ensure_list),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    # startup message
    startup = STARTUP.format(name=DOMAIN, version=VERSION, issueurl=ISSUE_URL)
    _LOGGER.info(startup)

    # check all required files
    file_check = await check_files(hass)
    if not file_check:
        return False

    # create data dictionary
    hass.data[DOMAIN_DATA] = {}
    hass.data[DOMAIN_DATA]["hosts"] = {}
    hass.data[DOMAIN_DATA]["vms"] = {}

    # get global config
    _LOGGER.debug("Setting up host %s", config[DOMAIN].get(CONF_HOST))

    if config[DOMAIN].get("categories") is not None:
        categories = config[DOMAIN].get("categories")
        _LOGGER.debug("Monitoring categories - %s", categories)

    hass.data[DOMAIN_DATA]["client"] = esxiStats(hass, config)

    # load platforms
    for platform in PLATFORMS:
        # Get platform specific configuration
        platform_config = config[DOMAIN]

        hass.async_create_task(
            discovery.async_load_platform(
                hass, platform, DOMAIN, platform_config, config
            )
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
        self.categories = config[DOMAIN].get("categories")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self):
        try:
            #get data from host
            content = get_content(self.host, self.user, self.passwd, self.port)
            
            # create view objects
            host_objview = content.viewManager.CreateContainerView(content.rootFolder,[vim.HostSystem],True)
            vm_objview = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)

            # get host stats
            esxi_hosts = host_objview.view
            host_objview.Destroy()

            for esxi_host in esxi_hosts:
                host_name = esxi_host.summary.config.name.replace(" ", "_").lower()

                self.hass.data[DOMAIN_DATA]["hosts"][host_name] = get_host_info(esxi_host)
                _LOGGER.debug("Getting stats for host: %s", host_name)

                #print(esxi_host.summary)
                
            # get vm stats
            vm_list = vm_objview.view
            vm_objview.Destroy()

            for vm in vm_list:
                vm_name = vm.summary.config.name.replace(" ", "_").lower()

                vm_data = {
                    "vm_name": vm_name,
                    "vm_status": vm.summary.overallStatus,
                    "vm_state": vm.summary.runtime.powerState,
                    "vm_cpu": vm.summary.config.numCpu,
                    "vm_memory": vm.summary.config.memorySizeMB
                }
                self.hass.data[DOMAIN_DATA]["vms"][vm_name] = vm_data
                _LOGGER.debug("Getting stats for vm: %s", vm_name)

            print(self.hass.data[DOMAIN_DATA]["hosts"])
            print(self.hass.data[DOMAIN_DATA]["vms"])
        except Exception as error:
            _LOGGER.error("ERROR: %s", error)

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