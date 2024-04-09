import logging
_LOGGER = logging.getLogger('custom_component.harvia_sauna')
DOMAIN = "harvia_sauna"
STORAGE_KEY = "harvia_sauna"
STORAGE_VERSION = 1
REGION = "eu-west-1"

STATE_CODE_STANDBY_SAFETY = 397326
STATE_CODE_SAFETY = 397322
STATE_CODE_HEATING = 135432
STATE_CODE_RESTING_PERIOD = 331784