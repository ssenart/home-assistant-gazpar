"""Support for Gazpar."""

import asyncio
import json
import logging
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from pygazpar.client import Client  # type: ignore
from pygazpar.datasource import (  # type: ignore
    ExcelWebDataSource,
    JsonWebDataSource,
    TestDataSource,
)
from pygazpar.enum import Frequency, PropertyName  # type: ignore

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
    DEFAULT_WAITTIME,
    DOMAIN,
)
from custom_components.gazpar.manifest import Manifest
from custom_components.gazpar.util import Util

_LOGGER = logging.getLogger(__name__)

LAST_INDEX = -1

# Keeps the sensor attributes well under the 16 KB limit Home Assistant enforces on state attributes.
MAX_ERROR_MESSAGE_LENGTH = 500

HA_ATTRIBUTION = "Data provided by GrDF"

ICON_GAS = "mdi:fire"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,  # type: ignore
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_PCE_IDENTIFIER): cv.string,
        vol.Optional(CONF_WAITTIME, default=DEFAULT_WAITTIME): int,  # type: ignore
        vol.Required(CONF_TMPDIR): cv.string,
        vol.Optional(CONF_DATASOURCE, default=DEFAULT_DATASOURCE): cv.string,  # type: ignore
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,  # type: ignore
        vol.Optional(CONF_LAST_N_DAYS, default=DEFAULT_LAST_N_DAYS): int,  # type: ignore
    }
)


# --------------------------------------------------------------------------------------------
def entry_data_from_yaml(config: dict[str, Any]) -> dict[str, Any]:
    """The entry data of a YAML configuration: the same keys as the UI, with the interval in seconds."""

    scan_interval = config[CONF_SCAN_INTERVAL]
    if isinstance(scan_interval, timedelta):
        scan_interval = scan_interval.total_seconds()

    return {
        CONF_NAME: config[CONF_NAME],
        CONF_USERNAME: config[CONF_USERNAME],
        CONF_PASSWORD: config[CONF_PASSWORD],
        CONF_PCE_IDENTIFIER: config[CONF_PCE_IDENTIFIER],
        CONF_WAITTIME: config[CONF_WAITTIME],
        CONF_TMPDIR: config[CONF_TMPDIR],
        CONF_DATASOURCE: config[CONF_DATASOURCE],
        CONF_SCAN_INTERVAL: int(scan_interval),
        CONF_LAST_N_DAYS: config[CONF_LAST_N_DAYS],
    }


# --------------------------------------------------------------------------------------------
async def async_setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):  # noqa: ARG001
    """Import the YAML configuration into a config entry, so that existing setups keep working.

    The config entry creates the sensor, so the YAML platform adds no entity of its own.
    """

    _LOGGER.debug("Importing the Gazpar YAML configuration")

    try:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=entry_data_from_yaml(config)
            )
        )
    except Exception:  # noqa: BLE001
        _LOGGER.error("Gazpar YAML configuration import has failed with exception : %s", traceback.format_exc())
        raise


# --------------------------------------------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Create the sensor of a config entry and schedule its queries."""

    data = {**entry.data, **entry.options}
    version = await Manifest.version()
    account = account_from_entry_data(data, version)
    async_add_entities(account.sensors, True)

    scan_interval = timedelta(seconds=data[CONF_SCAN_INTERVAL])
    account.track(async_call_later(hass, 5, account.async_update_gazpar_data))
    account.track(async_track_time_interval(hass, account.async_update_gazpar_data, scan_interval))
    entry.async_on_unload(account.stop)

    _LOGGER.debug("Gazpar platform initialization has completed successfully")


# --------------------------------------------------------------------------------------------
class GazparAccount:
    """Representation of a Gazpar account."""

    # ----------------------------------
    def __init__(
        self,
        name: str,
        username: str,
        password: str,
        pceIdentifier: str,
        wait_time: int,
        tmpdir: str,
        scan_interval: timedelta,
        lastNDays: int,
        version: str,
        datasource: str,
    ):
        """Initialise the Gazpar account."""
        self._name = name
        self._username = username
        self._password = password
        self._pceIdentifier = pceIdentifier
        self._wait_time = wait_time
        self._tmpdir = tmpdir
        self._scan_interval = scan_interval
        self._lastNDays = lastNDays
        self._version = version
        self._datasource = datasource
        self._dataByFrequency: dict[str, list[dict[str, Any]]] = {}
        self.sensors: list[GazparSensor] = []
        self._errorMessages: list[str] = []
        self._unsubscribers: list[Callable[[], None]] = []

        self.sensors.append(GazparSensor(name, PropertyName.ENERGY.value, UnitOfEnergy.KILO_WATT_HOUR, self))

    # ----------------------------------
    async def async_update_gazpar_data(self, event_time):
        """Fetch new state data for the sensor."""

        _LOGGER.debug("Querying PyGazpar library for new data...")

        # Reset the error message.
        self._errorMessages = []

        try:
            if self._datasource == "test":
                client = Client(TestDataSource())
            elif self._datasource == "json":
                client = Client(JsonWebDataSource(self._username, self._password))
            elif self._datasource == "excel":
                client = Client(ExcelWebDataSource(self._username, self._password, self._tmpdir))
            else:
                raise Exception(
                    f"Invalid datasource value: '{self._datasource}' (valid values are: json | excel | test)"
                )

            loop = asyncio.get_event_loop()
            self._dataByFrequency = await loop.run_in_executor(
                None, client.load_since, self._pceIdentifier, self._lastNDays
            )

            _LOGGER.debug(f"data={json.dumps(self._dataByFrequency, indent=2)}")

            _LOGGER.debug("New data have been retrieved successfully from PyGazpar library")
        except Exception as exception:
            # The data of the previous successful query is kept: a transient GRDF failure must not blank the sensor.
            errorMessage = "Failed to query PyGazpar library. The exception has been raised: {0}"
            self._errorMessages.append(errorMessage.format(str(exception)[:MAX_ERROR_MESSAGE_LENGTH]))
            _LOGGER.error(errorMessage.format(traceback.format_exc()))
            if event_time is None:
                raise

        if event_time is not None:
            for sensor in self.sensors:
                sensor.async_schedule_update_ha_state(True)
            _LOGGER.debug("HA notified that new data are available")

    # ----------------------------------
    def track(self, unsubscribe: Callable[[], None]):
        """Keep the function that cancels a scheduled query, so that stop() can cancel it."""
        self._unsubscribers.append(unsubscribe)

    # ----------------------------------
    def stop(self):
        """Cancel the scheduled queries."""
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()

    # ----------------------------------
    @property
    def pceIdentifier(self):
        """Return the PCE identifier."""
        return self._pceIdentifier

    # ----------------------------------
    @property
    def version(self):
        """Return the version."""
        return self._version

    # ----------------------------------
    @property
    def tmpdir(self):
        """Return the tmpdir."""
        return self._tmpdir

    # ----------------------------------
    @property
    def dataByFrequency(self):
        """Return the data dictionary by frequency."""
        return self._dataByFrequency

    # ----------------------------------
    @property
    def errorMessages(self):
        """Return the error messages."""
        return self._errorMessages


# --------------------------------------------------------------------------------------------
def account_from_entry_data(data: dict[str, Any], version: str) -> GazparAccount:
    """Build the account from the entry data."""

    return GazparAccount(
        data[CONF_NAME],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data[CONF_PCE_IDENTIFIER],
        data[CONF_WAITTIME],
        data[CONF_TMPDIR],
        timedelta(seconds=data[CONF_SCAN_INTERVAL]),
        data[CONF_LAST_N_DAYS],
        version,
        data[CONF_DATASOURCE],
    )


# --------------------------------------------------------------------------------------------
class GazparSensor(SensorEntity):
    """Representation of a sensor entity for Gazpar."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_attribution = HA_ATTRIBUTION
    _attr_icon = ICON_GAS
    # GazparAccount pushes the new data after each query, so Home Assistant must not poll the sensor.
    _attr_should_poll = False

    # ----------------------------------
    def __init__(self, name, identifier, unit, account: GazparAccount):
        """Initialize the sensor."""
        self._attr_name = name
        self._identifier = identifier
        self._attr_native_unit_of_measurement = unit
        self._account = account
        self._attr_unique_id = account.pceIdentifier
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account.pceIdentifier)},
            manufacturer="GrDF",
            model="Gas meter",
            name=name,
        )
        self._dataByFrequency: dict[str, list[dict[str, Any]]] = {}
        self._selectByFrequence = {
            Frequency.HOURLY: GazparSensor.__selectHourly,
            Frequency.DAILY: GazparSensor.__selectDaily,
            Frequency.WEEKLY: GazparSensor.__selectWeekly,
            Frequency.MONTHLY: GazparSensor.__selectMonthly,
            Frequency.YEARLY: GazparSensor.__selectYearly,
        }

    # ----------------------------------
    @property
    def dataByFrequency(self):
        """Return the data dictionary by frequency."""
        return self._dataByFrequency

    # ----------------------------------
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        return Util.toAttributes(
            self._account.pceIdentifier,
            self._account.version,
            self._dataByFrequency,
            self._account.errorMessages,
        )

    # ----------------------------------
    def update(self):
        """Retrieve the new data for the sensor."""

        _LOGGER.debug("HA requests its data to be updated...")
        try:
            # PyGazpar delivers data sorted by ascending dates.
            # Below, we reverse the order. We want most recent at the top.
            # And we select a subset of the readings by frequency.
            for frequency in Frequency:
                data = self._account.dataByFrequency.get(frequency.value)

                if data is not None and len(data) > 0:
                    self._dataByFrequency[frequency.value] = self._selectByFrequence[frequency](data[::-1])
                    _LOGGER.debug(f"HA {frequency} data have been updated successfully")
                else:
                    self._dataByFrequency[frequency.value] = []
                    _LOGGER.debug(f"No {frequency} data available yet for update")

            # When the readings cannot give a state (e.g. a gap in the index data), the last known state is kept.
            state = Util.toState(self._dataByFrequency)
            if state is not None:
                self._attr_native_value = state

        except Exception:  # noqa: BLE001
            _LOGGER.error(f"Failed to update HA data. The exception has been raised: {traceback.format_exc()}")

    MAX_DAILY_READINGS = 14
    MAX_WEEKLY_READINGS = 20
    MAX_MONTHLY_READINGS = 24
    MAX_YEARLY_READINGS = 5
    # The other lists fill about 14.9 KB of the 16 KB attribute limit, and one hourly reading adds about 300 bytes.
    # GRDF does not publish hourly gas readings, so only the most recent one is kept.
    MAX_HOURLY_READINGS = 1

    DATE_FORMAT = "%d/%m/%Y"

    # ----------------------------------
    @staticmethod
    def __selectHourly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[: GazparSensor.MAX_HOURLY_READINGS]

    # ----------------------------------
    @staticmethod
    def __selectDaily(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[: GazparSensor.MAX_DAILY_READINGS]

    # ----------------------------------
    @staticmethod
    def __selectWeekly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:

        res = []

        previousYearWeekDate = []

        index = 0
        for reading in data:
            weekDate = GazparSensor.__getIsoCalendar(reading["time_period"])

            if index < GazparSensor.MAX_WEEKLY_READINGS / 2:
                weekDate = (weekDate.weekday, weekDate.week, weekDate.year - 1)

                previousYearWeekDate.append(weekDate)

                res.append(reading)
            else:
                if previousYearWeekDate.count((weekDate.weekday, weekDate.week, weekDate.year)) > 0:
                    res.append(reading)

            index += 1

        return res

    # ----------------------------------
    @staticmethod
    def __selectMonthly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[: GazparSensor.MAX_MONTHLY_READINGS]

    # ----------------------------------
    @staticmethod
    def __selectYearly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[: GazparSensor.MAX_YEARLY_READINGS]

    # ----------------------------------
    @staticmethod
    def __getIsoCalendar(weekly_time_period):

        date = datetime.strptime(weekly_time_period.split(" ")[1], GazparSensor.DATE_FORMAT)

        return date.isocalendar()
