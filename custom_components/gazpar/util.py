import logging
from typing import Any

from pygazpar.enum import Frequency, PropertyName  # type: ignore

_LOGGER = logging.getLogger(__name__)

LAST_INDEX = -1

ATTR_PCE = "pce"
ATTR_VERSION = "version"
ATTR_ERROR_MESSAGES = "errorMessages"


# --------------------------------------------------------------------------------------------
class Util:
    # Tolerance (kWh) between the index-implied energy of the most recent daily reading
    # (end_index_m3 - start_index_m3) * converter_factor and its independently-reported
    # energy_kwh. GRDF's own metering noise stays under ~10 kWh/day (observed max 9.75 kWh
    # over a 26-day real export); the 2024-10-14 incident's corrupted reading produced a gap
    # of ~52837 kWh. 50 kWh keeps a wide margin on both sides without needing to scale with
    # installation size, since it compares two figures for the *same* day rather than
    # capping absolute daily volume.
    LAST_READING_ENERGY_EPSILON_KWH = 50.0

    # ----------------------------------
    @staticmethod
    def toState(pygazparData: dict[str, list[dict[str, Any]]]) -> float | None:
        """Compute the cumulative energy state from the daily readings.

        Walks backward from the most recent day while start_index_m3 == end_index_m3
        (no index movement yet), accumulating energy_kwh for those "flat" days -- GRDF
        also reports a small independently-metered energy_kwh on low-consumption days
        even when the 1 m3-resolution index hasn't moved, so this is not dropped. It
        then uses the index of the day where it stops (index * converter_factor) as the
        base, clamping to the last day of the window if every day was flat.

        Before running that walk, the single most recent daily reading is checked for
        internal consistency: GRDF may not have finalized it yet, and a corrupted
        end_index_m3 on just this one record was the root cause of the 2024-10-14
        incident (a single bad reading inflated the state by ~52840 kWh, although the
        official GRDF export shows a normal, continuous index for that day). If the
        index-implied energy for that record disagrees with its own reported energy_kwh
        by more than LAST_READING_ENERGY_EPSILON_KWH, or if its index or converter factor is missing,
        it is dropped and the walk proceeds from the previous (already-published) day
        instead -- older records are never second-guessed this way.
        """

        res = None

        if len(pygazparData) > 0:
            dailyData = pygazparData.get(Frequency.DAILY.value)

            if dailyData is not None and len(dailyData) > 0:
                dailyData = Util._dropImplausibleMostRecentReading(dailyData)

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
                    if currentIndex < len(dailyData):
                        startIndex = dailyData[currentIndex][PropertyName.START_INDEX.value]
                        endIndex = dailyData[currentIndex][PropertyName.END_INDEX.value]

                currentIndex = min(currentIndex, len(dailyData) - 1)

                endIndex = dailyData[currentIndex][PropertyName.END_INDEX.value]
                converterFactorStr = dailyData[currentIndex][PropertyName.CONVERTER_FACTOR.value]

                # The walk stops on a reading with a missing index, or the anchor itself may lack its
                # converter factor. Without them the state cannot be computed: report it as unknown
                # rather than publishing a wrong value or raising from the state property.
                if endIndex is None or converterFactorStr is None:
                    _LOGGER.warning(
                        "Cumulative energy state is unknown, index or converter factor missing in reading: %s",
                        dailyData[currentIndex],
                    )
                    return None

                res = float(endIndex) * float(converterFactorStr) + cumulativeEnergy

        return res

    # ----------------------------------
    @staticmethod
    def _dropImplausibleMostRecentReading(dailyData: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop the most recent (index 0) daily reading if it looks corrupted or unfinalized.

        Older, already-published readings are never touched here -- they keep going
        through the existing backward-walk logic unchanged, including its handling of
        genuine low-consumption flat days.
        """

        mostRecent = dailyData[0]

        startIndexRaw = mostRecent[PropertyName.START_INDEX.value]
        endIndexRaw = mostRecent[PropertyName.END_INDEX.value]

        if startIndexRaw is None or endIndexRaw is None:
            _LOGGER.debug("Ignoring most recent daily reading, missing index: %s", mostRecent)
            return dailyData[1:]

        converterFactorStr = mostRecent[PropertyName.CONVERTER_FACTOR.value]
        energyRaw = mostRecent[PropertyName.ENERGY.value]

        if converterFactorStr is None:
            # The converter factor turns the index into kWh, so this record cannot be used.
            _LOGGER.debug("Ignoring most recent daily reading, missing converter factor: %s", mostRecent)
            return dailyData[1:]

        if energyRaw is None:
            # Can't cross-check consistency without the reported energy -- keep the record as before.
            return dailyData

        impliedEnergy = (float(endIndexRaw) - float(startIndexRaw)) * float(converterFactorStr)
        gap = abs(impliedEnergy - float(energyRaw))

        if gap >= Util.LAST_READING_ENERGY_EPSILON_KWH:
            _LOGGER.warning(
                "Ignoring most recent daily reading: index-implied energy %.2f kWh does not "
                "match reported energy_kwh %.2f kWh (gap %.2f kWh >= threshold %.2f kWh), "
                "falling back to the previous day: %s",
                impliedEnergy,
                energyRaw,
                gap,
                Util.LAST_READING_ENERGY_EPSILON_KWH,
                mostRecent,
            )
            return dailyData[1:]

        return dailyData

    # ----------------------------------
    @staticmethod
    def toAttributes(
        pceIdentifier: str,
        version: str,
        pygazparData: dict[str, list[dict[str, Any]]],
        errorMessages: list[str],
    ) -> dict[str, Any]:

        # Unit, device class, state class, icon and attribution come from the SensorEntity itself.
        res = {
            ATTR_VERSION: version,
            ATTR_PCE: pceIdentifier,
            ATTR_ERROR_MESSAGES: errorMessages,
            str(Frequency.HOURLY): list[dict[str, Any]](),
            str(Frequency.DAILY): list[dict[str, Any]](),
            str(Frequency.WEEKLY): list[dict[str, Any]](),
            str(Frequency.MONTHLY): list[dict[str, Any]](),
            str(Frequency.YEARLY): list[dict[str, Any]](),
        }

        if len(pygazparData) > 0:
            for frequency in Frequency:
                data = pygazparData.get(frequency.value)

                if data is not None and len(data) > 0:
                    res[str(frequency)] = data
                else:
                    res[str(frequency)] = []

        return res  # type: ignore
