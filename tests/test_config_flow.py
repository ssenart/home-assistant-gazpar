"""The config flow, the YAML import and the entry setup, run in a Home Assistant instance."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pygazpar.datasource import TestDataSource  # type: ignore
from pytest_homeassistant_custom_component.common import MockConfigEntry  # type: ignore

import custom_components.gazpar.sensor as sensor_module
from custom_components.gazpar.config_flow import CannotConnect, InvalidAuth, UnknownPce
from custom_components.gazpar.const import (
    CONF_DATASOURCE,
    CONF_LAST_N_DAYS,
    CONF_PCE_IDENTIFIER,
    CONF_TMPDIR,
    CONF_WAITTIME,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations", "offline")

USER_INPUT = {CONF_NAME: "gazpar", CONF_USERNAME: "user", CONF_PASSWORD: "secret", CONF_PCE_IDENTIFIER: "123"}


@pytest.fixture
def offline():
    """No login to GrDF: the account is accepted, and the data comes from the bundled test datasource."""

    with (
        patch("custom_components.gazpar.config_flow.check_account"),
        patch.object(sensor_module, "JsonWebDataSource", lambda *_args, **_kwargs: TestDataSource()),
    ):
        yield


def entry_data(name: str = "maison", pce: str = "7") -> dict:
    """The data of an entry, as the UI or the YAML import creates it."""

    return {
        CONF_NAME: name,
        CONF_USERNAME: "user",
        CONF_PASSWORD: "secret",
        CONF_PCE_IDENTIFIER: pce,
        CONF_WAITTIME: 30,
        CONF_TMPDIR: "/tmp",
        CONF_DATASOURCE: "test",
        CONF_SCAN_INTERVAL: 600,
        CONF_LAST_N_DAYS: 365,
    }


def yaml_config(scan_interval: int = 600) -> dict:
    """A YAML configuration, as the platform receives it after validation."""

    return {**entry_data(name="gazpar", pce="0"), CONF_SCAN_INTERVAL: scan_interval}


async def start_user_flow(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def import_yaml(hass, config: dict) -> None:
    await sensor_module.async_setup_platform(hass, config, lambda *_args, **_kwargs: None)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_the_ui_creates_the_entry(hass):
    result = await start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.unique_id == "123"
    assert entry.data[CONF_SCAN_INTERVAL] == 14400
    assert entry.data[CONF_LAST_N_DAYS] == 1095
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (InvalidAuth(), {"base": "invalid_auth"}),
        (UnknownPce(), {CONF_PCE_IDENTIFIER: "unknown_pce"}),
        (CannotConnect(), {"base": "cannot_connect"}),
    ],
)
async def test_the_ui_reports_what_grdf_refused(hass, error, expected):
    with patch("custom_components.gazpar.config_flow.check_account", side_effect=error):
        result = await start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == expected


@pytest.mark.asyncio
async def test_a_meter_is_configured_only_once(hass):
    MockConfigEntry(domain=DOMAIN, unique_id="123", data=entry_data(pce="123")).add_to_hass(hass)

    result = await start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_the_yaml_configuration_is_imported_into_an_entry(hass):
    await import_yaml(hass, yaml_config())

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].source == config_entries.SOURCE_IMPORT
    assert entries[0].unique_id == "0"
    assert entries[0].state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.gazpar") is not None


@pytest.mark.asyncio
async def test_a_second_import_updates_the_same_entry(hass):
    await import_yaml(hass, yaml_config(scan_interval=600))
    await import_yaml(hass, yaml_config(scan_interval=3600))

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data[CONF_SCAN_INTERVAL] == 3600


@pytest.mark.asyncio
async def test_the_yaml_clears_the_options_set_in_the_ui(hass):
    await import_yaml(hass, yaml_config(scan_interval=600))
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    hass.config_entries.async_update_entry(entry, options={CONF_SCAN_INTERVAL: 7200, CONF_LAST_N_DAYS: 30})
    await hass.async_block_till_done()

    await import_yaml(hass, yaml_config(scan_interval=600))

    assert entry.options == {}
    assert entry.data[CONF_SCAN_INTERVAL] == 600


@pytest.mark.asyncio
async def test_the_entry_creates_the_sensor_grouped_in_a_device(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="7", data=entry_data())
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry_entry = er.async_get(hass).async_get("sensor.maison")
    assert registry_entry is not None
    assert registry_entry.unique_id == "7"
    assert registry_entry.device_id is not None


@pytest.mark.asyncio
async def test_the_options_change_reloads_the_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="7", data=entry_data())
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 3600, CONF_LAST_N_DAYS: 365}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 3600, CONF_LAST_N_DAYS: 365}
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.asyncio
async def test_unloading_the_entry_removes_the_sensor(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="7", data=entry_data())
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert er.async_get(hass).async_get("sensor.maison") is not None
