"""Constants for ESXi Stats."""
DOMAIN = "esxi_stats"
DOMAIN_DATA = f"{DOMAIN}_data"

PLATFORMS = ["sensor", "switch", "button", "select"]
REQUIRED_FILES = [
    "const.py",
    "esxi.py",
    "manifest.json",
    "sensor.py",
    "switch.py",
    "button.py",
    "select.py",
    "config_flow.py",
    "services.yaml",
    "translations/en.json",
]
VERSION = "0.8.0"
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
CONF_DS_STATE = "datastore"
CONF_LIC_STATE = "license"
CONF_NOTIFY = "notify"

DEFAULT_NAME = "ESXi"
DEFAULT_PORT = 443
DEFAULT_DS_STATE = "free_space_gb"
DEFAULT_LIC_STATE = "status"

DEFAULT_OPTIONS = {
    "datastore": "free_space_gb",
    "license": "status",
    "notify": "true",
}

DATASTORE_STATES = [
    "connected_hosts",
    "free_space_gb",
    "total_space_gb",
    "type",
    "virtual_machines",
]

LICENSE_STATES = ["expiration_days", "status"]

MAP_TO_MEASUREMENT = {
    "cpu_count": "CPUs",
    "cpuusage_ghz": "GHz",
    "expiration_days": "Days",
    "free_space_gb": "GB",
    "memusage_gb": "GB",
    "total_space_gb": "GB",
    "uptime_hours": "Hours",
    "virtual_machines": "VMs",
    "vms": "VMs",
    "name": None,  # Name text, no unit

    # VM attributes
    "cpu_use_pct": "%",
    "memory_allocated_mb": "MB",
    "memory_used_mb": "MB",
    "memory_active_mb": "MB",
    "used_space_gb": "GB",
    "snapshots": None,  # Count, no unit
    "tools_status": None,  # Status text
    "guest_os": None,  # Text
    "guest_ip": None,  # IP address
    "status": None,  # Status text
    "state": None,  # State text
    "host_name": None,  # Text

    # Host attributes
    "cputotal_ghz": "GHz",
    "memtotal_gb": "GB",
    "version": None,  # Version text
    "build": None,  # Build text
    "maintenance_mode": None,  # Boolean
    "power_policy": None,  # Policy text
    "available_power_policies": None,  # List text
    "shutdown_supported": None,  # Boolean

    # Datastore attributes
    "connected_hosts": None,  # Count, no unit
    "type": None,  # Type text
}

SUPPORTED_PRODUCTS = ["VMware ESX Server", "VMware VirtualCenter Server"]
AVAILABLE_CMND_VM_POWER = ["on", "off", "reboot", "reset", "shutdown", "suspend"]
AVAILABLE_CMND_VM_SNAP = ["all", "first", "last"]
AVAILABLE_CMND_HOST_POWER = ["shutdown", "reboot"]
HOST = "host"
TARGET_HOST = "target_host"
VM = "vm"
COMMAND = "command"
FORCE = "force"
