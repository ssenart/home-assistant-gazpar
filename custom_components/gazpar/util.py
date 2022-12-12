from pygazpar.enum import PropertyName, Frequency
from homeassistant.const import CONF_USERNAME, ATTR_ATTRIBUTION, ATTR_UNIT_OF_MEASUREMENT, ATTR_FRIENDLY_NAME, ATTR_ICON, ATTR_DEVICE_CLASS, ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY
from homeassistant.components.sensor import ATTR_STATE_CLASS, STATE_CLASS_TOTAL_INCREASING
from typing import Any, Union

from custom_components.gazpar.manifest import Manifest  

HA_ATTRIBUTION = "Data provided by GrDF"

ICON_GAS = "mdi:fire"

SENSOR_FRIENDLY_NAME = "Gazpar"

LAST_INDEX = -1

ATTR_PCE = "pce"
ATTR_VERSION = "version"
ATTR_ERROR_MESSAGES = "errorMessages"


# --------------------------------------------------------------------------------------------
class Util:

    # ----------------------------------
    @staticmethod
    def toState(pygazparData: dict[str, list[dict[str, Any]]]) -> Union[float, None]:

        if len(pygazparData) > 0:

            dailyData = pygazparData[Frequency.DAILY.value]

            currentIndex = len(dailyData) - 1
            cumulativeEnergy = 0.0

            # For low consumption, we also use the energy column in addition to the volume index columns
            # and compute more accurately the consumed energy.
            while (currentIndex >= 0) and (float(dailyData[currentIndex][PropertyName.START_INDEX.value]) == float(dailyData[currentIndex][PropertyName.END_INDEX.value])):
                cumulativeEnergy += float(dailyData[currentIndex][PropertyName.ENERGY.value])
                currentIndex -= 1

            volumeEndIndex = float(dailyData[currentIndex][PropertyName.END_INDEX.value])
            converterFactor = float(dailyData[currentIndex][PropertyName.CONVERTER_FACTOR.value])

            return volumeEndIndex * converterFactor + cumulativeEnergy
        else:
            return None

    # ----------------------------------
    @staticmethod
    def toAttributes(username: str, pceIdentifier: str, pygazparData: dict[str, list[dict[str, Any]]], errorMessages: list[str]) -> dict[str, Any]:

        res = {
            ATTR_ATTRIBUTION: HA_ATTRIBUTION,
            ATTR_VERSION: Manifest.version(),
            CONF_USERNAME: username,
            ATTR_PCE: pceIdentifier,
            ATTR_UNIT_OF_MEASUREMENT: ENERGY_KILO_WATT_HOUR,
            ATTR_FRIENDLY_NAME: SENSOR_FRIENDLY_NAME,
            ATTR_ICON: ICON_GAS,
            ATTR_DEVICE_CLASS: DEVICE_CLASS_ENERGY,
            ATTR_STATE_CLASS: STATE_CLASS_TOTAL_INCREASING,
            ATTR_ERROR_MESSAGES: errorMessages,
            str(Frequency.HOURLY): {},
            str(Frequency.DAILY): {},
            str(Frequency.WEEKLY): {},
            str(Frequency.MONTHLY): {},
            str(Frequency.YEARLY): {},
        }

        if len(pygazparData) > 0:
            for frequency in Frequency:
                data = pygazparData.get(frequency.value)

                if data is not None and len(data) > 0:
                    res[str(frequency)] = data
                else:
                    res[str(frequency)] = []

        return res  # type: ignore
