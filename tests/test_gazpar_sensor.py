import json
import logging
import os

import pytest
from pygazpar.enum import Frequency

from custom_components.gazpar.sensor import (
    CONF_DATASOURCE,
    CONF_LAST_N_DAYS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PCE_IDENTIFIER,
    CONF_SCAN_INTERVAL,
    CONF_TMPDIR,
    CONF_USERNAME,
    CONF_WAITTIME,
    GazparSensor,
    async_setup_platform,
)
from custom_components.gazpar.util import Util

# --------------------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

global_entities: list[GazparSensor] = []


# ----------------------------------
def add_entities(entities: list, flag: bool):  # pylint: disable=unused-argument
    global_entities.extend(entities)


# ----------------------------------
@pytest.mark.asyncio
async def test_live():

    config = {
        CONF_NAME: "gazpar",
        CONF_USERNAME: os.environ["GRDF_USERNAME"],
        CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
        CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
        CONF_WAITTIME: 30,
        CONF_TMPDIR: "./tmp",
        CONF_SCAN_INTERVAL: 600,
        CONF_LAST_N_DAYS: 30,
        CONF_DATASOURCE: "json",
    }

    await async_setup_platform(None, config, add_entities)

    for entity in global_entities:
        entity.update()
        state = entity.state
        attributes = entity.extra_state_attributes

        logger.debug(f"state={state}")
        logger.debug(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
@pytest.mark.asyncio
async def test_sample():

    config = {
        CONF_NAME: "gazpar",
        CONF_USERNAME: os.environ["GRDF_USERNAME"],
        CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
        CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
        CONF_WAITTIME: 30,
        CONF_TMPDIR: "./tmp",
        CONF_SCAN_INTERVAL: 600,
        CONF_LAST_N_DAYS: 30,
        CONF_DATASOURCE: "test",
    }

    await async_setup_platform(None, config, add_entities)

    for entity in global_entities:
        entity.update()
        state = entity.state
        attributes = entity.extra_state_attributes

        logger.debug(f"state={state}")
        logger.debug(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
@pytest.mark.asyncio
async def test_toAttribute():

    config = {
        CONF_NAME: "gazpar",
        CONF_USERNAME: os.environ["GRDF_USERNAME"],
        CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
        CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
        CONF_WAITTIME: 30,
        CONF_TMPDIR: "./tmp",
        CONF_SCAN_INTERVAL: 600,
        CONF_LAST_N_DAYS: 30,
        CONF_DATASOURCE: "test",
    }

    await async_setup_platform(None, config, add_entities)

    for entity in global_entities:
        entity.update()

        attributes = Util.toAttributes(
            config[CONF_USERNAME], config[CONF_PCE_IDENTIFIER], "1.0.0", entity.dataByFrequency, []
        )

        logger.info(f"attributes={json.dumps(attributes, indent=2)}")


# ----------------------------------
def test_toState_low():

    with open("tests/resources/low_daily_data.json", "r", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    assert state == 154397.136

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_high():

    with open("tests/resources/high_daily_data.json", "r", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    assert state == 154405.404

    logger.info(f"state={state}")


# ----------------------------------
def test_toState_zero():

    with open("tests/resources/zero_daily_data.json", "r", encoding="utf-8") as f:
        data = {Frequency.DAILY.value: json.load(f)}

    state = Util.toState(data)

    assert state == 154397.136

    logger.info(f"state={state}")
