"""ESXi Integration."""

import atexit
import logging
import os
from datetime import timedelta, datetime, date
from .esxi import main

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_PORT
from homeassistant.helpers import discovery
from homeassistant.util import Throttle

import voluptuous as vol

import atexit
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim

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

MAX_DEPTH = 10
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
            si = None
            si = si = SmartConnectNoSSL(
                        host=self.host,
                        user=self.user,
                        pwd=self.passwd,
                        port=self.port)
            atexit.register(Disconnect, si)
            content = si.RetrieveContent()
            
            for child in content.rootFolder.childEntity:
                if hasattr(child, 'vmFolder'):
                    datacenter = child
                    vmfolder = datacenter.vmFolder
                    vmlist = vmfolder.childEntity

                    for vm in vmlist:
                        #print(vm)
                        vminfo = getvminfo(vm)
                        #print(vminfo.summary.overallStatus)
                        
                        #self.hass.data[DOMAIN_DATA]["vmname"] = vminfo.summary.overallStatus
                        #self.hass.data[DOMAIN_DATA].update([(vm.summary.config.name, vminfo.summary.overallStatus)])
                        self.hass.data[DOMAIN_DATA][vm.summary.config.name] = (vm.summary.config.name, vminfo.summary.overallStatus)

                        #print(self.hass.data[DOMAIN_DATA][vm.summary.config.name]["overallStatus"])
                        #print(self.hass.data[DOMAIN_DATA])
                        print(self.hass.data[DOMAIN_DATA][vm.summary.config.name])

            _LOGGER.info("Testing")

            print ("Just pfSense status: ", self.hass.data[DOMAIN_DATA]['pfSense'])
            #self.getvms = esxiConnect(self.host,self.user,self.passwd) 

            #self.hass.data[DOMAIN_DATA]["vminfo"] = self.getvms
        except Exception as error:
            _LOGGER.error("ERROR: %s", error)


def getvminfo(vm, depth=1):
    """
    Print information for a particular virtual machine or recurse into a folder
    with depth protection
    """

    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > MAX_DEPTH:
            return
        vmlist = vm.childEntity
        for child in vmlist:
            getvminfo(child, depth+1)
        return

    #summary = vm.summary
    return(vm)

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