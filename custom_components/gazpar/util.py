from typing import Any, Union

from homeassistant.components.sensor.const import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_USERNAME,
    UnitOfEnergy,
)
from pygazpar.enum import Frequency, PropertyName

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

        res = None

        if len(pygazparData) > 0:

            dailyData = pygazparData[Frequency.DAILY.value]

            if dailyData is not None and len(dailyData) > 0:
                currentIndex = 0
                cumulativeEnergy = 0.0

                # For low consumption, we also use the energy column in addition to the volume index columns
                # and compute more accurately the consumed energy.
                startIndex = dailyData[currentIndex][PropertyName.START_INDEX.value]
                endIndex = dailyData[currentIndex][PropertyName.END_INDEX.value]

                while (
                    (startIndex is not None)
                    and (endIndex is not None)
                    and (currentIndex < len(dailyData))
                    and (float(startIndex) == float(endIndex))
                ):
                    energy = dailyData[currentIndex][PropertyName.ENERGY.value]
                    if energy is not None:
                        cumulativeEnergy += float(energy)
                    currentIndex += 1
                    startIndex = dailyData[currentIndex][PropertyName.START_INDEX.value]
                    endIndex = dailyData[currentIndex][PropertyName.END_INDEX.value]

                currentIndex = min(currentIndex, len(dailyData) - 1)

                endIndex = dailyData[currentIndex][PropertyName.END_INDEX.value]
                converterFactorStr = dailyData[currentIndex][PropertyName.CONVERTER_FACTOR.value]

                if endIndex is not None:
                    volumeEndIndex = float(endIndex)
                else:
                    raise ValueError("End index is missing in the daily data.")

                if converterFactorStr is not None:
                    converterFactor = float(converterFactorStr)
                else:
                    raise ValueError("Converter factor is missing in the daily data.")

                res = volumeEndIndex * converterFactor + cumulativeEnergy

        return res

    # ----------------------------------
    @staticmethod
    def toAttributes(
        username: str,
        pceIdentifier: str,
        version: str,
        pygazparData: dict[str, list[dict[str, Any]]],
        errorMessages: list[str],
    ) -> dict[str, Any]:

        res = {
            ATTR_ATTRIBUTION: HA_ATTRIBUTION,
            ATTR_VERSION: version,
            CONF_USERNAME: username,
            ATTR_PCE: pceIdentifier,
            ATTR_UNIT_OF_MEASUREMENT: UnitOfEnergy.KILO_WATT_HOUR,
            ATTR_FRIENDLY_NAME: SENSOR_FRIENDLY_NAME,
            ATTR_ICON: ICON_GAS,
            ATTR_DEVICE_CLASS: SensorDeviceClass.ENERGY,
            ATTR_STATE_CLASS: SensorStateClass.TOTAL_INCREASING,
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
