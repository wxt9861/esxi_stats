"""Constants for ESXi Stats."""
DOMAIN = "esxi_stats"
DOMAIN_DATA = "{}_data".format(DOMAIN)

PLATFORMS = ["sensor"]
REQUIRED_FILES = [
    "const.py",
    "esxi.py",
    "manifest.json",
    "sensor.py",
    "config_flow.py",
    "services.yaml",
    ".translations/en.json",
]
VERSION = "0.5.0"
ISSUE_URL = "https://github.com/wxt9861/esxi_stats/issues"

STARTUP = """
-------------------------------------------------------------------
{name}
Version: {version}
This is a custom component
If you have any issues with this you need to open an issue here:
{issueurl}
-------------------------------------------------------------------
"""

CONF_NAME = "name"
CONF_DS_STATE = "ds_state"
CONF_HOST_STATE = "host_state"
CONF_LIC_STATE = "license_state"
CONF_VM_STATE = "vm_state"

# DEFAULT_NAME = "ESXi Stats"
DEFAULT_NAME = "ESXi"
DEFAULT_PORT = 443
DEFAULT_DS_STATE = "free_space_gb"
DEFAULT_HOST_STATE = "vms"
DEFAULT_LIC_STATE = "status"
DEFAULT_VM_STATE = "state"

# used to set default states for yaml config.
DEFAULT_OPTIONS = {
    "ds_state": "free_space_gb",
    "host_state": "vms",
    "license_state": "status",
    "vm_state": "state"
}

SUPPORTED_PRODUCTS = ["VMware ESX Server", "VMware VirtualCenter Server"]
AVAILABLE_CMND_VM_POWER = ["on", "off", "reboot", "reset", "shutdown", "suspend"]
AVAILABLE_CMND_VM_SNAP = ["all", "first", "last"]
VM = "vm"
COMMAND = "command"
