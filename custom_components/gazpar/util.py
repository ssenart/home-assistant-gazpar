from pygazpar.enum import PropertyName
from pygazpar.enum import Frequency
from homeassistant.const import CONF_USERNAME, ATTR_ATTRIBUTION, ATTR_UNIT_OF_MEASUREMENT, ATTR_FRIENDLY_NAME, ATTR_ICON, ENERGY_KILO_WATT_HOUR


# --------------------------------------------------------------------------------------------
class Util:

    __HA_ATTRIBUTION = "Data provided by GrDF"

    __LAST_INDEX = -1
    __BEFORE_LAST_INDEX = -2

    # ----------------------------------
    @staticmethod
    def toState(pygazparData: list) -> str:

        if len(pygazparData) > 0:
            return pygazparData[Util.__LAST_INDEX].get(PropertyName.ENERGY.value)
        else:
            return None

    # ----------------------------------
    @staticmethod
    def toAttributes(username: str, frequency: Frequency, pygazparData: list) -> dict:

        friendlyNameByFrequency = {
            Frequency.HOURLY: "Gazpar hourly energy",
            Frequency.DAILY: "Gazpar daily energy",
            Frequency.WEEKLY: "Gazpar weekly energy",
            Frequency.MONTHLY: "Gazpar monthly energy"
        }

        res = {
            ATTR_ATTRIBUTION: Util.__HA_ATTRIBUTION,
            CONF_USERNAME: username,
            ATTR_UNIT_OF_MEASUREMENT: ENERGY_KILO_WATT_HOUR,
            ATTR_FRIENDLY_NAME: friendlyNameByFrequency[frequency],
            ATTR_ICON: "mdi:fire"
        }

        if frequency == Frequency.WEEKLY or frequency == Frequency.MONTHLY:  # Cases WEEKLY and MONTHLY.
            if len(pygazparData) > 1:
                res["previous"] = pygazparData[Util.__BEFORE_LAST_INDEX]
            if len(pygazparData) > 0:
                res["current"] = pygazparData[Util.__LAST_INDEX]
        elif frequency == Frequency.DAILY and len(pygazparData) > 0:  # Cases DAILY.
            for propertyName in PropertyName:
                value = pygazparData[Util.__LAST_INDEX].get(propertyName.value)
                if value is not None:
                    res[propertyName.value] = value

        return res