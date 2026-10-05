import json
import logging
import os
from datetime import timedelta

import pytest
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from pygazpar.api_client import ServerError  # type: ignore
from pygazpar.enum import Frequency  # type: ignore

import custom_components.gazpar.sensor as sensor_module
from custom_components.gazpar.config_flow import (
    CannotConnect,
    InvalidAuth,
    UnknownPce,
    check_account,
    entry_data_from_user,
)
from custom_components.gazpar.const import (
    CONF_DATASOURCE,
    CONF_LAST_N_DAYS,
    CONF_PCE_IDENTIFIER,
    CONF_TMPDIR,
    CONF_WAITTIME,
)
from custom_components.gazpar.sensor import (
    GazparAccount,
    GazparSensor,
    account_from_entry_data,
    entry_data_from_yaml,
)
from custom_components.gazpar.util import Util

# --------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# The live test needs real GrDF credentials. They are empty on fork PRs, where the test is skipped.
requires_grdf = pytest.mark.skipif(not os.environ.get("GRDF_USERNAME"), reason="GrDF credentials are not set")


# ----------------------------------
def make_config(datasource: str, username: str = "user", password: str = "password", pce: str = "0") -> dict:
    """A YAML configuration, as Home Assistant validates it."""

    return {
        CONF_NAME: "gazpar",
        CONF_USERNAME: username,
        CONF_PASSWORD: password,
        CONF_PCE_IDENTIFIER: pce,
        CONF_WAITTIME: 30,
        CONF_TMPDIR: "./tmp",
        CONF_SCAN_INTERVAL: 600,
        CONF_LAST_N_DAYS: 30,
        CONF_DATASOURCE: datasource,
    }


# ----------------------------------
def make_account(config: dict) -> GazparAccount:
    """The account a config entry creates from the same configuration."""

    return account_from_entry_data(entry_data_from_yaml(config), "1.0.0")


# ----------------------------------
@pytest.mark.asyncio
@requires_grdf
@pytest.mark.usefixtures("grdf_network")
async def test_live():

    account = make_account(
        make_config("json", os.environ["GRDF_USERNAME"], os.environ["GRDF_PASSWORD"], os.environ["PCE_IDENTIFIER"])
    )
    await account.async_update_gazpar_data(None)

    entity = account.sensors[0]
    entity.update()
    attributes = entity.extra_state_attributes

    assert entity.native_value is not None
    assert Frequency.DAILY.value in attributes

    logger.debug(f"state={entity.native_value}")
    logger.debug(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
@pytest.mark.asyncio
async def test_sample():

    account = make_account(make_config("test"))
    await account.async_update_gazpar_data(None)

    entity = account.sensors[0]
    entity.update()
    attributes = entity.extra_state_attributes

    assert isinstance(entity.native_value, float)
    assert len(attributes[Frequency.DAILY.value]) <= GazparSensor.MAX_DAILY_READINGS

    logger.debug(f"state={entity.native_value}")
    logger.debug(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
@pytest.mark.asyncio
async def test_toAttribute():

    config = make_config("test")
    account = make_account(config)
    await account.async_update_gazpar_data(None)

    entity = account.sensors[0]
    entity.update()

    attributes = Util.toAttributes(config[CONF_PCE_IDENTIFIER], "1.0.0", entity.dataByFrequency, [])

    assert attributes["pce"] == config[CONF_PCE_IDENTIFIER]
    assert attributes["version"] == "1.0.0"
    assert attributes["errorMessages"] == []
    assert "username" not in attributes
    for frequency in Frequency:
        assert frequency.value in attributes

    logger.info(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
def test_toState_low():

    with open("tests/resources/low_daily_data.json", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    # 13702.0 * 11.268 + (1.1 + 1.2 + 0.7) -- the 3 preceding "flat" days are genuine
    # low-consumption days (GRDF reports a real energy_kwh even though the 1 m3-resolution
    # index hasn't moved), so their energy is still counted on top of the anchor index.
    assert state == 154397.136

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_high():

    with open("tests/resources/high_daily_data.json", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    assert state == 154405.404

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_zero():

    with open("tests/resources/zero_daily_data.json", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    # 13702.0 * 11.268 + (1.1 + 1.2 + 0.7) -- same reasoning as test_toState_low.
    assert state == 154397.136

    logger.info(f"state={state}")


# ----------------------------------
# Regression tests for the spurious-jump bug: a corrupted or not-yet-finalized most
# recent daily reading being used as-is inflated the cumulative state by anywhere from
# hundreds to tens of thousands of kWh, unrelated to real GRDF consumption. The fix only
# ever second-guesses that single most recent record; every older, already-published
# record keeps going through the original backward-walk logic unchanged, including its
# accumulation of energy_kwh on genuine low-consumption "flat" days (see test_toState_low
# / test_toState_zero above).
# See: https://github.com/ssenart/home-assistant-gazpar
# ----------------------------------


def test_toState_frozen_index_does_not_drift():
    """Boiler switched off for an extended period: the meter index never moves.

    Real-world case that triggered this investigation: 60 consecutive days with
    start_index_m3 == end_index_m3 == 9080 (confirmed by the official GRDF export, all
    readings qualified "Mesure" / real, not estimated), the first 3 of which also carry
    a small genuine energy_kwh (metered independently of the 1 m3-resolution index).
    The state must keep counting that low-consumption energy on top of the unchanged
    index, and must do so identically regardless of how many additional frozen days
    with zero energy_kwh precede it in the window -- those contribute nothing either
    way, so truncating the window must not change the result.
    """

    with open("tests/resources/frozen_index_60days.json", encoding="utf-8") as f:
        fullData = json.load(f)

    expected = 9080 * 11.19 + sum(r["energy_kwh"] for r in fullData)

    # Full 60-day window.
    state_full = Util.toState({Frequency.DAILY.value: fullData})
    assert state_full == pytest.approx(expected)

    # A shorter window covering only the most recent 5 days (which still contains all 3
    # energy-bearing days) must give the same state.
    state_short = Util.toState({Frequency.DAILY.value: fullData[:5]})
    assert state_short == pytest.approx(expected)

    logger.info(f"state_full={state_full} state_short={state_short}")


# ----------------------------------
def test_toState_rejects_implausible_most_recent_reading():
    """A corrupted most recent reading (e.g. a bad API response) must not inflate the state.

    Modeled on the production incident of 2024-10-14, where the reported state jumped
    by +52842.82 kWh in a single update although GRDF's own official export shows a
    normal, continuous index progression for that entire period (6010 -> 6012 -> 6013
    m3, i.e. ~13 kWh that day) -- proving the bad value came from a single corrupted
    reading, not a real meter event. The most recent reading here implies +4551 m3
    (~52837 kWh) while GRDF itself reports energy_kwh=0.0 for that same day -- a gap far
    beyond normal metering noise (observed up to ~10 kWh/day on 26 real, clean days) --
    so it is rejected and the state falls back to the previous, internally-consistent
    reading.
    """

    with open("tests/resources/corrupted_reading.json", encoding="utf-8") as f:
        data = json.load(f)

    state = Util.toState({Frequency.DAILY.value: data})

    # Falls back to the second (plausible) reading: 6012 * 11.61
    assert state == 6012 * 11.61

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_ignores_most_recent_reading_with_missing_start_index():
    """A most recent reading with no start_index_m3 yet must not be trusted blindly.

    GRDF may publish a day's end_index_m3 before its start_index_m3 is finalized. Since
    the consistency check needs both to compare against energy_kwh, a missing index on
    the most recent record is rejected outright (rather than silently accepted, which
    would reproduce the original bug for exactly this case) and the state falls back to
    the previous, complete reading.
    """

    with open("tests/resources/missing_start_index.json", encoding="utf-8") as f:
        data = json.load(f)

    state = Util.toState({Frequency.DAILY.value: data})

    # Falls back to the second reading: 6013 * 11.61
    assert state == 6013 * 11.61

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_real_grdf_window_matches_ground_truth():
    """Cross-check against the official GRDF export for the same period as the
    2024-10-14 incident (25/09/2024 - 20/10/2024, all readings qualified "Mesure").

    Confirms that on real, unmodified GRDF data the fixed implementation always
    reproduces index * converter_factor for the most recent day, and that the
    day-over-day delta around the incident date matches GRDF's real reported
    consumption instead of a multi-thousand kWh spurious jump.
    """

    with open("tests/resources/real_grdf_window_2024_10.json", encoding="utf-8") as f:
        fullData = json.load(f)

    # Most recent day in the fixture is 20/10/2024: end_index_m3=6018, coef=11.61
    expected_full = 6018 * 11.61
    state_full = Util.toState({Frequency.DAILY.value: fullData})
    assert state_full == expected_full

    # Isolate the incident date (14/10/2024) and the day before it (13/10/2024).
    window = [r for r in fullData if r["time_period"] in ("14/10/2024", "13/10/2024", "12/10/2024")]
    state_1014 = Util.toState({Frequency.DAILY.value: window})
    state_1013 = Util.toState({Frequency.DAILY.value: window[1:]})

    delta = state_1014 - state_1013

    assert state_1014 == 6013 * 11.61
    # Real GRDF delta for 14/10/2024 is 1 m3 (6013 - 6012), i.e. ~11.61 kWh -- not the
    # +52842.82 kWh that was actually reported in production that day.
    assert abs(delta - (6013 - 6012) * 11.61) < 1e-6
    assert delta < 20.0

    logger.info(f"state_full={state_full} state_1014={state_1014} state_1013={state_1013} delta={delta}")


# ----------------------------------
def record(start, end, energy=0.0, converter=11.0):
    return {
        "time_period": "01/01/2024",
        "start_index_m3": start,
        "end_index_m3": end,
        "energy_kwh": energy,
        "converter_factor_kwh/m3": converter,
    }


# ----------------------------------
def test_toState_index_gap_in_flat_run_is_unknown():
    """A flat most recent day followed by a day with no index: the anchor day cannot be found."""

    data = [record(10, 10, 0.5), record(None, None, 1.0), record(9, 10, 11.0)]

    assert Util.toState({Frequency.DAILY.value: data}) is None


# ----------------------------------
def test_toState_all_days_missing_index_is_unknown():

    data = [record(None, None), record(None, None)]

    assert Util.toState({Frequency.DAILY.value: data}) is None


# ----------------------------------
def test_toState_anchor_missing_converter_factor_is_unknown():
    """The anchor day (first non-flat day) has no converter factor."""

    data = [record(10, 10, 0.5), record(9, 10, 11.0, converter=None)]

    assert Util.toState({Frequency.DAILY.value: data}) is None


# ----------------------------------
def test_toState_most_recent_missing_converter_factor_falls_back_to_previous_day():
    """Like a missing index, a most recent reading without its converter factor is not finalized."""

    data = [record(10, 11, 11.0, converter=None), record(9, 10, 11.0)]

    assert Util.toState({Frequency.DAILY.value: data}) == 10 * 11.0


# ----------------------------------
def test_toState_no_daily_data_is_unknown():

    assert Util.toState({}) is None
    assert Util.toState({Frequency.DAILY.value: []}) is None


# ----------------------------------
def make_failing_client(message: str):
    """Build a stand-in for pygazpar's Client whose query always fails with the given message."""

    class FailingClient:
        def __init__(self, _dataSource):
            pass

        def load_since(self, _pceIdentifier, _lastNDays):
            raise RuntimeError(message)

    return FailingClient


# ----------------------------------
@pytest.mark.asyncio
async def test_failed_query_keeps_last_good_data(monkeypatch):
    """A transient GRDF failure keeps the data of the last successful query and reports the error.

    The error message is also cut short so a large response body cannot grow the attributes.
    """

    account = make_account(make_config("test"))
    await account.async_update_gazpar_data(None)
    sensor = account.sensors[0]
    sensor.update()
    stateBefore = sensor.state
    assert stateBefore is not None

    monkeypatch.setattr(sensor_module, "Client", make_failing_client("x" * 10000))
    with pytest.raises(RuntimeError):
        await account.async_update_gazpar_data(None)

    sensor.update()
    assert sensor.state == stateBefore
    assert len(account.errorMessages) == 1
    assert len(account.errorMessages[0]) < 600


# ----------------------------------
@pytest.mark.asyncio
async def test_attributes_stay_under_recorder_limit():
    """Home Assistant stores no attributes at all once they exceed 16384 bytes, so the budget must hold."""

    account = make_account(make_config("test"))
    await account.async_update_gazpar_data(None)
    # Hourly readings shaped like the daily ones, so their size is realistic. Far more than the cap are supplied.
    dailyReading = account.dataByFrequency[Frequency.DAILY.value][0]
    account.dataByFrequency[Frequency.HOURLY.value] = [
        {**dailyReading, "frequency": Frequency.HOURLY.value, "time_period": f"{i:02d}/05/2019 13:00"}
        for i in range(500)
    ]
    sensor = account.sensors[0]
    sensor.update()

    attributes = sensor.extra_state_attributes

    assert len(attributes[Frequency.HOURLY.value]) == GazparSensor.MAX_HOURLY_READINGS
    assert "username" not in attributes
    # Home Assistant adds these from the entity itself, so they count towards the limit too.
    entityAttributes = {
        "unit_of_measurement": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "friendly_name": "gazpar",
        "icon": "mdi:fire",
        "attribution": "Data provided by GrDF",
    }
    encoded = json.dumps({**attributes, **entityAttributes}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    assert len(encoded) < 16384


# ----------------------------------
def test_sensor_entity_declares_energy_metadata():
    sensor = make_account(make_config("test")).sensors[0]

    assert isinstance(sensor, SensorEntity)
    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.should_poll is False


# ----------------------------------
@pytest.mark.asyncio
async def test_native_value_keeps_last_known_state_when_readings_have_a_gap():
    """A gap in the index data leaves the sensor on its last known state instead of unknown."""

    account = make_account(make_config("test"))
    await account.async_update_gazpar_data(None)
    sensor = account.sensors[0]
    sensor.update()
    lastKnownState = sensor.native_value
    assert lastKnownState is not None

    # A flat run of days followed by a day without an index: no state can be computed from these readings.
    # The account stores readings oldest first, the sensor reverses them.
    gapReadings = [record(9, 10, 11.0), record(None, None, 1.0), record(10, 10, 0.5)]
    account.dataByFrequency[Frequency.DAILY.value] = gapReadings
    sensor.update()

    assert Util.toState({Frequency.DAILY.value: gapReadings[::-1]}) is None
    assert sensor.native_value == lastKnownState


# ----------------------------------
def test_stop_cancels_the_scheduled_queries():
    """Unloading an account must cancel its scheduled queries, otherwise each reload adds another timer."""

    account = make_account(make_config("test"))
    cancelled = []
    account.track(lambda: cancelled.append("call_later"))
    account.track(lambda: cancelled.append("track_time_interval"))

    account.stop()
    account.stop()

    assert cancelled == ["call_later", "track_time_interval"]


# ----------------------------------
def test_entry_data_from_yaml_keeps_the_scan_interval_in_seconds():

    config = make_config("test")
    config[CONF_SCAN_INTERVAL] = timedelta(hours=8)

    data = entry_data_from_yaml(config)

    assert data[CONF_SCAN_INTERVAL] == 28800
    assert data[CONF_PCE_IDENTIFIER] == "0"
    assert data[CONF_LAST_N_DAYS] == 30


# ----------------------------------
def test_entry_data_from_user_adds_the_defaults_of_the_yaml_configuration():
    data = entry_data_from_user({CONF_NAME: "gazpar", CONF_USERNAME: "u", CONF_PASSWORD: "p", CONF_PCE_IDENTIFIER: "1"})

    assert data[CONF_SCAN_INTERVAL] == 14400
    assert data[CONF_LAST_N_DAYS] == 1095
    assert data[CONF_DATASOURCE] == "json"
    assert data[CONF_PCE_IDENTIFIER] == "1"


# ----------------------------------
class FakeClient:
    """Stands in for the pygazpar client used by the config flow."""

    def __init__(self, pce_identifiers=None, error=None):
        self._pce_identifiers = pce_identifiers
        self._error = error

    def __call__(self, _datasource):
        return self

    def get_pce_identifiers(self):
        if self._error is not None:
            raise self._error
        return self._pce_identifiers


def test_check_account_accepts_a_pce_of_the_account(monkeypatch):
    monkeypatch.setattr("custom_components.gazpar.config_flow.Client", FakeClient(["1", "2"]))

    check_account("u", "p", "2")


def test_check_account_rejects_a_pce_outside_the_account(monkeypatch):
    monkeypatch.setattr("custom_components.gazpar.config_flow.Client", FakeClient(["1"]))

    with pytest.raises(UnknownPce):
        check_account("u", "p", "2")


def test_check_account_reports_refused_credentials(monkeypatch):
    monkeypatch.setattr("custom_components.gazpar.config_flow.Client", FakeClient(error=ServerError("refused", 400)))

    with pytest.raises(InvalidAuth):
        check_account("u", "wrong", "1")


def test_check_account_reports_an_unreachable_grdf(monkeypatch):
    monkeypatch.setattr("custom_components.gazpar.config_flow.Client", FakeClient(error=ConnectionError("down")))

    with pytest.raises(CannotConnect):
        check_account("u", "p", "1")


def test_sensor_is_identified_by_its_pce_and_grouped_in_a_device():
    sensor = make_account(make_config("test", pce="22423299474865")).sensors[0]

    assert sensor.unique_id == "22423299474865"
    assert sensor.device_info["identifiers"] == {("gazpar", "22423299474865")}
    assert sensor.name == "gazpar"
