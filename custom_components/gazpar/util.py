from pygazpar.enum import PropertyName
from homeassistant.const import CONF_USERNAME, ATTR_ATTRIBUTION, ATTR_UNIT_OF_MEASUREMENT, ATTR_FRIENDLY_NAME, ATTR_ICON, ATTR_DEVICE_CLASS, ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY
from homeassistant.components.sensor import ATTR_STATE_CLASS, STATE_CLASS_TOTAL_INCREASING
from typing import Any, Union
from .enum import FrequencyStr
from .manifest import Manifest

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
    def toState(pygazparData: dict[FrequencyStr, list[Any]]) -> Union[float, None]:

        if len(pygazparData) > 0:
            volumeStartIndex = float(pygazparData[FrequencyStr.DAILY][LAST_INDEX].get(PropertyName.START_INDEX.value))
            converterFactor = float(pygazparData[FrequencyStr.DAILY][LAST_INDEX].get(PropertyName. CONVERTER_FACTOR.value))
            energy = float(pygazparData[FrequencyStr.DAILY][LAST_INDEX].get(PropertyName.ENERGY.value))
            return volumeStartIndex * converterFactor + energy
        else:
            return None

    # ----------------------------------
    @staticmethod
    def toAttributes(username: str, pceIdentifier: str, pygazparData: dict[FrequencyStr, list[Any]], errorMessages: list[str]) -> dict[str, Any]:

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
            str(FrequencyStr.HOURLY): {},
            str(FrequencyStr.DAILY): {},
            str(FrequencyStr.WEEKLY): {},
            str(FrequencyStr.MONTHLY): {},
            str(FrequencyStr.YEARLY): {},
        }

        for frequency in FrequencyStr:
            if len(pygazparData) > 0:
                data = pygazparData.get(frequency)

                if data is not None and len(data) > 0:
                    reversedData = data[::-1]
                else:
                    reversedData = []

                res[str(frequency)] = reversedData
            else:
                res[str(frequency)] = []

        return res  # type: ignore
