"""Adds config flow for ESXi Stats."""
import logging
from collections import OrderedDict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, DEFAULT_PORT
from .esxi import esx_connect, esx_disconnect


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class ESXIiStatslowHandler(config_entries.ConfigFlow):
    """Config flow for ESXi Stats."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input={}):
        """Handle a flow initialized by the user."""
        self._errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_communication(
                user_input["host"], user_input["port"], user_input["verify_ssl"],
                user_input["username"], user_input["password"])
            if valid:
                return self.async_create_entry(title=user_input["host"], data=user_input)
            else:
                self._errors["base"] = "communication"

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""

        # Defaults
        host = ""
        port = DEFAULT_PORT
        username = ""
        password = ""
        verify_ssl = False
        hosts = True
        datastores = False
        vms = False

        if user_input is not None:
            if "host" in user_input:
                host = user_input["host"]
            if "port" in user_input:
                port = user_input["port"]
            if "username" in user_input:
                username = user_input["username"]
            if "password" in user_input:
                password = user_input["password"]

            if "verify_ssl" in user_input:
                verify_ssl = user_input["verify_ssl"]
            if "hosts" in user_input:
                hosts = user_input["hosts"]
            if "datastores" in user_input:
                datastores = user_input["datastores"]
            if "vms" in user_input:
                vms = user_input["vms"]

        data_schema = OrderedDict()
        data_schema[vol.Required("host", default=host)] = str
        data_schema[vol.Required("port", default=port)] = int
        data_schema[vol.Required("username", default=username)] = str
        data_schema[vol.Required("password", default=password)] = str
        data_schema[vol.Optional("verify_ssl", default=verify_ssl)] = bool
        data_schema[vol.Optional("hosts", default=hosts)] = bool
        data_schema[vol.Optional("datastores", default=datastores)] = bool
        data_schema[vol.Optional("vms", default=vms)] = bool
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def async_step_import(self, user_input):
        """Import a config entry.
        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    async def _test_communication(self, host, port, verify_ssl, username, password):
        """Return true if the communication is ok."""
        try:
            conn = await esx_connect(
                host, username, password, port, verify_ssl
            )
            _LOGGER.debug(conn)

            esx_disconnect(conn)
            return True
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error(exception)
            return False
