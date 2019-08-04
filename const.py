DOMAIN = "esxi_stats"
DOMAIN_DATA = "{}_data".format(DOMAIN)

PLATFORMS = ["sensor"]
REQUIRED_FILES = ["const.py", "manifest.json", "sensor.py"]
#REQUIRED_FILES = ["const.py"]
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/wxt9861/esxiStats/issues"

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