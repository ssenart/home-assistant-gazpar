"""Support for Gazpar."""
from datetime import timedelta
import json
import logging
import traceback

from pygazpar.client import Client
from pygazpar.enum import PropertyName, Frequency

from .util import Util
from .enum import FrequencyStr

import voluptuous as vol
import pandas as pd

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL, ENERGY_KILO_WATT_HOUR
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval, call_later

_LOGGER = logging.getLogger(__name__)

CONF_PCE_IDENTIFIER = "pce_identifier"
CONF_WAITTIME = "wait_time"
CONF_TMPDIR = "tmpdir"
CONF_TESTMODE = "test_mode"

DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
DEFAULT_WAITTIME = 30
DEFAULT_TESTMODE = False

SENSOR_NAME = "Gazpar"

LAST_INDEX = -1

DAILY_LAST_WEEK_INDEX = -14
WEEKLY_LAST_MONTH_INDEX = -8
MONTHLY_LAST_YEAR_INDEX = -24
YEARLY_LAST_YEAR_INDEX = -5

ICON_GAS = "mdi:fire"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_PCE_IDENTIFIER): cv.string,
    vol.Optional(CONF_WAITTIME, default=DEFAULT_WAITTIME): int,  # type: ignore
    vol.Required(CONF_TMPDIR): cv.string,
    vol.Optional(CONF_TESTMODE, default=DEFAULT_TESTMODE): bool,  # type: ignore
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period  # type: ignore
})


# --------------------------------------------------------------------------------------------
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Configure the platform and add the Gazpar sensor."""

    _LOGGER.debug("Initializing Gazpar platform...")

    try:
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

        testMode = config[CONF_TESTMODE]
        _LOGGER.debug(f"testMode={testMode}")

        scan_interval = config[CONF_SCAN_INTERVAL]
        _LOGGER.debug(f"scan_interval={scan_interval}")

        account = GazparAccount(hass, username, password, pceIdentifier, wait_time, tmpdir, scan_interval, testMode)
        add_entities(account.sensors, True)
        _LOGGER.debug("Gazpar platform initialization has completed successfully")
    except BaseException:
        _LOGGER.error("Gazpar platform initialization has failed with exception : %s", traceback.format_exc())
        raise


# --------------------------------------------------------------------------------------------
class GazparAccount:
    """Representation of a Gazpar account."""

    # ----------------------------------
    def __init__(self, hass, username: str, password: str, pceIdentifier: str, wait_time: int, tmpdir: str, scan_interval: int, testMode: bool):
        """Initialise the Gazpar account."""
        self._username = username
        self._password = password
        self._pceIdentifier = pceIdentifier
        self._wait_time = wait_time
        self._tmpdir = tmpdir
        self._scan_interval = scan_interval
        self._testMode = testMode
        self._dataByFrequency = {}
        self.sensors = []
        self._errorMessages = []
        self._frequencyStrByFrequency = {
            Frequency.HOURLY: FrequencyStr.HOURLY,
            Frequency.DAILY: FrequencyStr.DAILY,
            Frequency.WEEKLY: FrequencyStr.WEEKLY,
            Frequency.MONTHLY: FrequencyStr.MONTHLY,
            # Frequency.YEARLY: FrequencyStr.YEARLY
        }

        self.sensors.append(
            GazparSensor(SENSOR_NAME, PropertyName.ENERGY.value, ENERGY_KILO_WATT_HOUR, self))

        if hass is not None:
            call_later(hass, 5, self.update_gazpar_data)
            track_time_interval(hass, self.update_gazpar_data, self._scan_interval)
        else:
            self.update_gazpar_data(None)

    # ----------------------------------
    def update_gazpar_data(self, event_time):
        """Fetch new state data for the sensor."""

        _LOGGER.debug("Querying PyGazpar library for new data...")

        # Reset the error message.
        self._errorMessages = []

        for frequency in Frequency:

            frequencyStr = self._frequencyStrByFrequency[frequency]

            if frequency is not Frequency.HOURLY:  # Hourly not yet implemented.
                try:
                    client = Client(username=self._username,
                                    password=self._password,
                                    pceIdentifier=self._pceIdentifier,
                                    meterReadingFrequency=frequency,
                                    lastNDays=1095,
                                    tmpDirectory=self._tmpdir,
                                    testMode=self._testMode)
                    client.update()

                    self._dataByFrequency[frequencyStr] = client.data()

                    _LOGGER.debug(f"data[{frequencyStr}]={json.dumps(self._dataByFrequency[frequencyStr], indent=2)}")

                    _LOGGER.debug(f"New {frequencyStr} data have been retrieved successfully from PyGazpar library")
                except BaseException:
                    self._dataByFrequency[frequencyStr] = {}
                    errorMessage = f"Failed to query PyGazpar library for frequency={frequencyStr}. The exception has been raised: {traceback.format_exc()}"
                    self._errorMessages.append(errorMessage)
                    _LOGGER.error(errorMessage)
                    if event_time is None:
                        raise

        self.computeYearlyData()

        if event_time is not None:
            for sensor in self.sensors:
                sensor.async_schedule_update_ha_state(True)
            _LOGGER.debug("HA notified that new data are available")

    # ----------------------------------
    # Compute yearly data from monthly data.
    def computeYearlyData(self):

        monthlyData = self._dataByFrequency.get(FrequencyStr.MONTHLY)

        if monthlyData is not None and len(monthlyData) > 0:
            df = pd.DataFrame(monthlyData)

            # Trimming head and trailing spaces.
            df["time_period"] = df["time_period"].str.strip()

            df[["month", "year"]] = df["time_period"].str.split(" ", expand=True)

            df = df[["year", "energy_kwh", "volume_m3"]].groupby("year").agg(energy_kwh=('energy_kwh', 'sum'), count=('energy_kwh', 'count')).reset_index()

            # Select rows where we have a full year (12 months) except for the current year.
            df = pd.concat([df[(df["count"] == 12)], df.tail(1)])

            df = df.rename(columns={"year": "time_period", "sum": "energy_kwh"})

            self._dataByFrequency[FrequencyStr.YEARLY] = df.to_dict('records')  # df.sort_values(by=['time_period'], ascending=False).to_dict('records')
        else:
            self._dataByFrequency[FrequencyStr.YEARLY] = {}

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

        self._lastIndexByFrequence = {
            FrequencyStr.HOURLY: LAST_INDEX,
            FrequencyStr.DAILY: DAILY_LAST_WEEK_INDEX,
            FrequencyStr.WEEKLY: WEEKLY_LAST_MONTH_INDEX,
            FrequencyStr.MONTHLY: MONTHLY_LAST_YEAR_INDEX,
            FrequencyStr.YEARLY: YEARLY_LAST_YEAR_INDEX,
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

        return Util.toAttributes(self._account.username, self._account.pceIdentifier, self._dataByFrequency, self._account.errorMessages)

    # ----------------------------------
    def update(self):
        """Retrieve the new data for the sensor."""

        _LOGGER.debug("HA requests its data to be updated...")
        try:

            for frequency in FrequencyStr:

                data = self._account.dataByFrequency.get(frequency)

                if data is not None and len(data) > 0:
                    self._dataByFrequency[frequency] = data[self._lastIndexByFrequence[frequency]:]
                    _LOGGER.debug(f"HA {frequency} data have been updated successfully")
                else:
                    _LOGGER.debug(f"No {frequency} data available yet for update")

        except BaseException:
            _LOGGER.error(f"Failed to update HA data. The exception has been raised: {traceback.format_exc()}")
