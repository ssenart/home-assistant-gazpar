"""Support for Gazpar."""
from datetime import timedelta
import json
import logging
import traceback
import asyncio
from datetime import datetime

from pygazpar.client import Client
from pygazpar.datasource import JsonWebDataSource, ExcelWebDataSource, TestDataSource
from pygazpar.enum import PropertyName, Frequency
from typing import Any

from custom_components.gazpar.util import Util
from custom_components.gazpar.manifest import Manifest

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL, UnitOfEnergy
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later, async_track_time_interval

_LOGGER = logging.getLogger(__name__)

CONF_PCE_IDENTIFIER = "pce_identifier"
CONF_WAITTIME = "wait_time"
CONF_TMPDIR = "tmpdir"
CONF_DATASOURCE = "datasource"

DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
DEFAULT_WAITTIME = 30
DEFAULT_DATASOURCE = "json"

DEFAULT_NAME = "gazpar"

LAST_INDEX = -1

ICON_GAS = "mdi:fire"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,  # type: ignore
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_PCE_IDENTIFIER): cv.string,
    vol.Optional(CONF_WAITTIME, default=DEFAULT_WAITTIME): int,  # type: ignore
    vol.Required(CONF_TMPDIR): cv.string,
    vol.Optional(CONF_DATASOURCE, default=DEFAULT_DATASOURCE): cv.string,  # type: ignore
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period  # type: ignore
})


# --------------------------------------------------------------------------------------------
async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Configure the platform and add the Gazpar sensor."""

    _LOGGER.debug("Initializing Gazpar platform...")

    try:
        name = config[CONF_NAME]
        _LOGGER.debug(f"name={name}")

        username = config[CONF_USERNAME]
        _LOGGER.debug(f"username={username}")

        password = config[CONF_PASSWORD]
        _LOGGER.debug("password=*********")

        pceIdentifier = config[CONF_PCE_IDENTIFIER]
        _LOGGER.debug(f"pce_identifier={pceIdentifier}")

        wait_time = config[CONF_WAITTIME]
        _LOGGER.debug(f"wait_time={wait_time}")

        tmpdir = config[CONF_TMPDIR]
        _LOGGER.debug(f"tmpdir={tmpdir}")

        datasource = config[CONF_DATASOURCE]
        _LOGGER.debug(f"datasource={datasource}")

        scan_interval = config[CONF_SCAN_INTERVAL]
        _LOGGER.debug(f"scan_interval={scan_interval}")

        version = await Manifest.version()
        _LOGGER.debug(f"version={version}")

        account = GazparAccount(hass, name, username, password, pceIdentifier, version, wait_time, tmpdir, scan_interval, datasource)
        add_entities(account.sensors, True)

        if hass is not None:
            async_call_later(hass, 5, account.async_update_gazpar_data)
            async_track_time_interval(hass, account.async_update_gazpar_data, account._scan_interval)
        else:
            await account.async_update_gazpar_data(None)

        _LOGGER.debug("Gazpar platform initialization has completed successfully")
    except BaseException:
        _LOGGER.error("Gazpar platform initialization has failed with exception : %s", traceback.format_exc())
        raise


# --------------------------------------------------------------------------------------------
class GazparAccount:
    """Representation of a Gazpar account."""

    # ----------------------------------
    def __init__(self, hass, name: str, username: str, password: str, pceIdentifier: str, version: str, wait_time: int, tmpdir: str, scan_interval: timedelta, datasource: str):
        """Initialise the Gazpar account."""
        self._name = name
        self._username = username
        self._password = password
        self._pceIdentifier = pceIdentifier
        self._version = version
        self._wait_time = wait_time
        self._tmpdir = tmpdir
        self._scan_interval = scan_interval
        self._datasource = datasource
        self._dataByFrequency = {}
        self.sensors = []
        self._errorMessages = []

        self.sensors.append(
            GazparSensor(name, PropertyName.ENERGY.value, UnitOfEnergy.KILO_WATT_HOUR, self))

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
                raise Exception(f"Invalid datasource value: '{self._datasource}' (valid values are: json | excel | test)")

            loop = asyncio.get_event_loop()
            self._dataByFrequency = await loop.run_in_executor(None, client.loadSince, self._pceIdentifier, 1095)

            _LOGGER.debug(f"data={json.dumps(self._dataByFrequency, indent=2)}")

            _LOGGER.debug("New data have been retrieved successfully from PyGazpar library")
        except BaseException as exception:
            self._dataByFrequency = {}
            errorMessage = "Failed to query PyGazpar library. The exception has been raised: {0}"
            self._errorMessages.append(errorMessage.format(str(exception)))
            _LOGGER.error(errorMessage.format(traceback.format_exc()))
            if event_time is None:
                raise

        if event_time is not None:
            for sensor in self.sensors:
                sensor.schedule_update_ha_state(True)
            _LOGGER.debug("HA notified that new data are available")

    # ----------------------------------
    @property
    def username(self):
        """Return the username."""
        return self._username

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
class GazparSensor(Entity):
    """Representation of a sensor entity for Linky."""

    # ----------------------------------
    def __init__(self, name, identifier, unit, account: GazparAccount):
        """Initialize the sensor."""
        self._name = name
        self._identifier = identifier
        self._unit = unit
        self._account = account
        self._dataByFrequency = {}
        self._selectByFrequence = {
            Frequency.HOURLY: GazparSensor.__selectHourly,
            Frequency.DAILY: GazparSensor.__selectDaily,
            Frequency.WEEKLY: GazparSensor.__selectWeekly,
            Frequency.MONTHLY: GazparSensor.__selectMonthly,
            Frequency.YEARLY: GazparSensor.__selectYearly,
        }

    # ----------------------------------
    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    # ----------------------------------
    @property
    def state(self):
        """Return the state of the sensor."""

        return Util.toState(self._dataByFrequency)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    # ----------------------------------
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON_GAS

    # ----------------------------------
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""

        return Util.toAttributes(self._account.username, self._account.pceIdentifier, self._account.version, self._dataByFrequency, self._account.errorMessages)

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

        except BaseException:
            _LOGGER.error(f"Failed to update HA data. The exception has been raised: {traceback.format_exc()}")

    MAX_DAILY_READINGS = 14
    MAX_WEEKLY_READINGS = 20
    MAX_MONTHLY_READINGS = 24
    MAX_YEARLY_READINGS = 5

    DATE_FORMAT = "%d/%m/%Y"

    # ----------------------------------
    @staticmethod
    def __selectHourly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data

    # ----------------------------------
    @staticmethod
    def __selectDaily(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[:GazparSensor.MAX_DAILY_READINGS]

    # ----------------------------------
    @staticmethod
    def __selectWeekly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:

        res = []

        previousYearWeekDate = []

        index = 0
        for reading in data:

            weekDate = GazparSensor.__getIsoCalendar(reading["time_period"])

            if (index < GazparSensor.MAX_WEEKLY_READINGS / 2):

                weekDate = (weekDate.weekday, weekDate.week, weekDate.year - 1)

                previousYearWeekDate.append(weekDate)

                res.append(reading)
            else:
                if (previousYearWeekDate.count((weekDate.weekday, weekDate.week, weekDate.year)) > 0):
                    res.append(reading)

            index += 1

        return res

    # ----------------------------------
    @staticmethod
    def __selectMonthly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[:GazparSensor.MAX_MONTHLY_READINGS]

    # ----------------------------------
    @staticmethod
    def __selectYearly(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data[:GazparSensor.MAX_YEARLY_READINGS]

    # ----------------------------------
    @staticmethod
    def __getIsoCalendar(weekly_time_period):

        date = datetime.strptime(weekly_time_period.split(" ")[1], GazparSensor.DATE_FORMAT)

        return date.isocalendar()
