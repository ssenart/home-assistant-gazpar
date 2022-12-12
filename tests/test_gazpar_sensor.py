from custom_components.gazpar.sensor import CONF_PCE_IDENTIFIER, CONF_DATASOURCE, setup_platform
from custom_components.gazpar.sensor import CONF_USERNAME, CONF_PASSWORD, CONF_WAITTIME, CONF_TMPDIR, CONF_SCAN_INTERVAL
from custom_components.gazpar.util import Util
from pygazpar.enum import Frequency
import os
import logging
import json


# --------------------------------------------------------------------------------------------
class TestGazparSensor:

    logger = logging.getLogger(__name__)

    _entities = []

    # ----------------------------------
    def add_entities(self, entities: list, flag: bool):
        self._entities.extend(entities)

    # ----------------------------------
    def test_live(self):

        config = {
            CONF_USERNAME: os.environ["GRDF_USERNAME"],
            CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
            CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
            CONF_WAITTIME: 30,
            CONF_TMPDIR: "./tmp",
            CONF_SCAN_INTERVAL: 600,
            CONF_DATASOURCE: "json"
        }

        setup_platform(None, config, self.add_entities)

        for entity in self._entities:
            entity.update()
            state = entity.state
            attributes = entity.extra_state_attributes

            TestGazparSensor.logger.debug(f"state={state}")
            TestGazparSensor.logger.debug(f"attributes={json.dumps(attributes, indent=2)}")

    # ----------------------------------
    def test_sample(self):

        config = {
            CONF_USERNAME: os.environ["GRDF_USERNAME"],
            CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
            CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
            CONF_WAITTIME: 30,
            CONF_TMPDIR: "./tmp",
            CONF_SCAN_INTERVAL: 600,
            CONF_DATASOURCE: "test"
        }

        setup_platform(None, config, self.add_entities)

        for entity in self._entities:
            entity.update()
            state = entity.state
            attributes = entity.extra_state_attributes

            TestGazparSensor.logger.debug(f"state={state}")
            TestGazparSensor.logger.debug(f"attributes={json.dumps(attributes, indent=2)}")

    # ----------------------------------
    def test_toAttribute(self):

        config = {
            CONF_USERNAME: os.environ["GRDF_USERNAME"],
            CONF_PASSWORD: os.environ["GRDF_PASSWORD"],
            CONF_PCE_IDENTIFIER: os.environ["PCE_IDENTIFIER"],
            CONF_WAITTIME: 30,
            CONF_TMPDIR: "./tmp",
            CONF_SCAN_INTERVAL: 600,
            CONF_DATASOURCE: "test"
        }

        setup_platform(None, config, self.add_entities)

        for entity in self._entities:
            entity.update()

            attributes = Util.toAttributes(config[CONF_USERNAME], config[CONF_PCE_IDENTIFIER], entity._dataByFrequency, [])

            TestGazparSensor.logger.info(f"attributes={json.dumps(attributes, indent=2)}")

    # ----------------------------------
    def test_toState_low(self):

        with open('tests/resources/low_daily_data.json') as f:
            data = {
                Frequency.DAILY.value: json.load(f)
            }

        state = Util.toState(data)

        assert (state == 154397.136)

        TestGazparSensor.logger.info(f"state={state}")

    # ----------------------------------
    def test_toState_high(self):

        with open('tests/resources/high_daily_data.json') as f:
            data = {
                Frequency.DAILY.value: json.load(f)
            }

        state = Util.toState(data)

        assert (state == 154405.404)

        TestGazparSensor.logger.info(f"state={state}")
