"""Config flow for the GrDF Gazpar integration."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from pygazpar.api_client import ServerError  # type: ignore
from pygazpar.client import Client  # type: ignore
from pygazpar.datasource import JsonWebDataSource  # type: ignore

from custom_components.gazpar.const import (
    CONF_DATASOURCE,
    CONF_LAST_N_DAYS,
    CONF_PCE_IDENTIFIER,
    CONF_TMPDIR,
    CONF_WAITTIME,
    DEFAULT_DATASOURCE,
    DEFAULT_LAST_N_DAYS,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TMPDIR,
    DEFAULT_WAITTIME,
    DOMAIN,
)


class InvalidAuth(Exception):
    """GrDF refused the username or the password."""


class CannotConnect(Exception):
    """GrDF could not be reached."""


class UnknownPce(Exception):
    """The PCE identifier does not belong to the account."""


def check_account(username: str, password: str, pce_identifier: str) -> None:
    """Log in to GrDF and check that the PCE belongs to the account. Runs in an executor job."""

    client = Client(JsonWebDataSource(username, password))
    try:
        pce_identifiers = client.get_pce_identifiers()
    except ServerError as error:
        # GrDF refuses the login with a server error, which is how a wrong username or password shows up.
        raise InvalidAuth from error
    except Exception as error:  # noqa: BLE001
        raise CannotConnect from error

    if pce_identifier not in pce_identifiers:
        raise UnknownPce


def entry_data_from_user(user_input: dict[str, Any]) -> dict[str, Any]:
    """The entry data of an account set up in the UI: the same keys as the YAML configuration."""

    return {
        **user_input,
        CONF_WAITTIME: DEFAULT_WAITTIME,
        CONF_TMPDIR: DEFAULT_TMPDIR,
        CONF_DATASOURCE: DEFAULT_DATASOURCE,
        CONF_SCAN_INTERVAL: int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        CONF_LAST_N_DAYS: DEFAULT_LAST_N_DAYS,
    }


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
        vol.Required(CONF_USERNAME): selector.TextSelector(),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_PCE_IDENTIFIER): selector.TextSelector(),
    }
)


class GazparOptionsFlow(OptionsFlow):
    """Change the update interval and the number of days downloaded."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the options, then store them."""

        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_LAST_N_DAYS: int(user_input[CONF_LAST_N_DAYS]),
                }
            )

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current[CONF_SCAN_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=600,
                        max=86400,
                        step=60,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(CONF_LAST_N_DAYS, default=current[CONF_LAST_N_DAYS]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=3650,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="days",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class GazparConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a GrDF account from the UI, or import the YAML configuration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the account, check it against GrDF, then create the entry."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    check_account,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_PCE_IDENTIFIER],
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except UnknownPce:
                errors[CONF_PCE_IDENTIFIER] = "unknown_pce"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_PCE_IDENTIFIER])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=entry_data_from_user(user_input))

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import the YAML configuration.

        While the YAML configuration is there, it is the source of the entry: an entry already created for the
        same PCE is updated from it, and the options set in the UI are cleared so that the YAML values apply.
        """

        existing = await self.async_set_unique_id(import_data[CONF_PCE_IDENTIFIER])
        if existing is not None:
            self.hass.config_entries.async_update_entry(existing, data=import_data, options={})
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title=import_data[CONF_NAME], data=import_data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GazparOptionsFlow:  # noqa: ARG004
        """Return the options flow of the entry."""

        return GazparOptionsFlow()
