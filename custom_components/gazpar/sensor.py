"""Support for Gazpar."""
from datetime import timedelta
import json
import logging
import traceback

from pygazpar.client import Client
from pygazpar.enum import PropertyName
from pygazpar.enum import Frequency

from .util import Util

import voluptuous as vol

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

ICON_GAS = "mdi:fire"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_PCE_IDENTIFIER): cv.string,
    vol.Optional(CONF_WAITTIME, default=DEFAULT_WAITTIME): int,
    vol.Required(CONF_TMPDIR): cv.string,
    vol.Optional(CONF_TESTMODE, default=DEFAULT_TESTMODE): bool,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period
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

        try:
            for frequency in Frequency:
                if frequency is not Frequency.HOURLY:  # Hourly not yet implemented.
                    client = Client(username=self._username,
                                    password=self._password,
                                    pceIdentifier=self._pceIdentifier,
                                    meterReadingFrequency=frequency,
                                    lastNDays=720,
                                    tmpDirectory=self._tmpdir,
                                    testMode=self._testMode)
                    client.update()
                    self._dataByFrequency[frequency] = client.data()

                    _LOGGER.debug(f"data[{frequency}]={json.dumps(self._dataByFrequency[frequency], indent=2)}")

                    if event_time is not None:
                        for sensor in self.sensors:
                            sensor.async_schedule_update_ha_state(True)
                        _LOGGER.debug(f"HA notified that new {frequency} data are available")
                    _LOGGER.debug(f"New {frequency} data have been retrieved successfully from PyGazpar library")

        except BaseException:
            _LOGGER.error("Failed to query PyGazpar library with exception : %s", traceback.format_exc())
            if event_time is None:
                raise

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
        self._username = account.username
        self._dataByFrequency = {}
        self._errorMessage = ""

        self._lastIndexByFrequence = {
            Frequency.HOURLY: LAST_INDEX,
            Frequency.DAILY: DAILY_LAST_WEEK_INDEX,
            Frequency.WEEKLY: WEEKLY_LAST_MONTH_INDEX,
            Frequency.MONTHLY: MONTHLY_LAST_YEAR_INDEX,
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

        return Util.toAttributes(self._username, self._dataByFrequency, self._errorMessage)

    # ----------------------------------
    def update(self):
        """Retrieve the new data for the sensor."""

        _LOGGER.debug(f"HA requests its data to be updated...")
        try:

            for frequency in Frequency:
                if frequency is not Frequency.HOURLY:  # Hourly not yet implemented.

                    data = self._account.dataByFrequency.get(frequency)

                    if data is not None and len(data) > 0:
                        self._dataByFrequency[frequency] = data[self._lastIndexByFrequence[frequency]:]
                        _LOGGER.debug(f"HA {frequency} data have been updated successfully")
                    else:
                        _LOGGER.debug(f"No {frequency} data available yet for update")
        except BaseException:
            self._errorMessage = f"Failed to update {self._meterReadingFrequency} HA data with exception : {traceback.format_exc()}"
            _LOGGER.error(self._errorMessage)
