DOMAIN = "esxi_stats"
DOMAIN_DATA = "{}_data".format(DOMAIN)

PLATFORMS = ["sensor"]
REQUIRED_FILES = ["const.py", "esxi.py", "manifest.json", "sensor.py", "config_flow.py", ".translations/en.json"]
VERSION = "0.3.0"
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

DEFAULT_NAME = "ESXi Stats"
DEFAULT_PORT = 443

AVAILABLE_COMMANDS_VM = ["turn_on", "turn_off", "take_snapshot"]