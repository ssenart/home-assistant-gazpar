from pygazpar.enum import PropertyName
from pygazpar.enum import Frequency
from homeassistant.const import CONF_USERNAME, ATTR_ATTRIBUTION, ATTR_UNIT_OF_MEASUREMENT, ATTR_FRIENDLY_NAME, ATTR_ICON, ATTR_DEVICE_CLASS, ENERGY_KILO_WATT_HOUR, DEVICE_CLASS_ENERGY
from homeassistant.components.sensor import ATTR_STATE_CLASS, STATE_CLASS_TOTAL_INCREASING


HA_ATTRIBUTION = "Data provided by GrDF"

ICON_GAS = "mdi:fire"

SENSOR_FRIENDLY_NAME = "Gazpar"

LAST_INDEX = -1

ATTR_ERROR_MESSAGE = "errorMessage"

# --------------------------------------------------------------------------------------------
class Util:


    
    # ----------------------------------
    @staticmethod
    def toState(pygazparData: list) -> str:

        if len(pygazparData) > 0:
            volumeIndex = int(pygazparData[Frequency.DAILY][LAST_INDEX].get(PropertyName.END_INDEX.value))
            converterFactor = float(pygazparData[Frequency.DAILY][LAST_INDEX].get(PropertyName. CONVERTER_FACTOR.value))
            return volumeIndex * converterFactor
        else:
            return None

    # ----------------------------------
    @staticmethod
    def toAttributes(username: str, pygazparData: list, errorMessage: str) -> dict:

        friendlyNameByFrequency = {
            Frequency.HOURLY: "hourly",
            Frequency.DAILY: "daily",
            Frequency.WEEKLY: "weekly",
            Frequency.MONTHLY: "monthly"
        }

        res = {
            ATTR_ATTRIBUTION: HA_ATTRIBUTION,
            CONF_USERNAME: username,
            ATTR_UNIT_OF_MEASUREMENT: ENERGY_KILO_WATT_HOUR,
            ATTR_FRIENDLY_NAME: SENSOR_FRIENDLY_NAME,
            ATTR_ICON: ICON_GAS,
            ATTR_DEVICE_CLASS: DEVICE_CLASS_ENERGY,
            ATTR_STATE_CLASS: STATE_CLASS_TOTAL_INCREASING,
            ATTR_ERROR_MESSAGE: errorMessage
        }

        for frequency in Frequency:
            if frequency is not Frequency.HOURLY:  # Hourly not yet implemented.

                if len(pygazparData) > 0:
                    data = pygazparData.get(frequency)

                    if len(data) > 0:
                        reversedData = data[::-1]
                    else:
                        reversedData = []

                    res[friendlyNameByFrequency[frequency]] = reversedData

        return res