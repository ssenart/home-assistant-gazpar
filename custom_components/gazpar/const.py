"""Constants of the GrDF Gazpar integration."""

from datetime import timedelta

DOMAIN = "gazpar"

CONF_PCE_IDENTIFIER = "pce_identifier"
CONF_WAITTIME = "wait_time"
CONF_TMPDIR = "tmpdir"
CONF_LAST_N_DAYS = "lastNDays"
CONF_DATASOURCE = "datasource"

DEFAULT_NAME = "gazpar"
DEFAULT_SCAN_INTERVAL = timedelta(hours=4)
DEFAULT_WAITTIME = 30
DEFAULT_LAST_N_DAYS = 1095
DEFAULT_DATASOURCE = "json"
DEFAULT_TMPDIR = "/tmp"
