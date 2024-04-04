from homeassistant.components.climate import ClimateEntity, HVAC_MODE_HEAT
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE, HVAC_MODE_OFF
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

class HarviaThermostat(ClimateEntity):
    def __init__(self, device, name, sauna):
        self._device = device
        self._name = name + ' Thermostat'
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVAC_MODE_OFF
        self._device_id = device.id + '_termostat'
        self._sauna = sauna
        self._attr_unique_id = device.id + '_termostat'

    @property
    def min_temp(self):
        return 40

    @property
    def max_temp(self):
        return 110

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE


    async def async_turn_on(self, **kwargs):
        # Code om de sauna aan te zetten
        await self.async_set_hvac_mode(HVAC_MODE_HEAT)

    async def async_turn_off(self, **kwargs):
        # Code om de sauna uit te zetten
        await self.async_set_hvac_mode(HVAC_MODE_OFF)

    async def async_added_to_hass(self):
        """Acties die uitgevoerd moeten worden als entiteit aan HA is toegevoegd."""
        self._device.thermostat = self
        await self._device.update_ha_devices()

    async def async_set_temperature(self, **kwargs):
        """Stel de doeltemperatuur in."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._target_temperature = temperature
            # Hier de logica om de doeltemperatuur in je apparaat te wijzigen
            await self._device.set_target_temperature(temperature)
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Stel de HVAC-modus in."""
        self._hvac_mode = hvac_mode
        if hvac_mode == HVAC_MODE_HEAT:
            await self._device.set_active(True)
        elif hvac_mode == HVAC_MODE_OFF:
            await self._device.set_active(False)

        # Hier logica om de modus op je apparaat in te stellen, indien nodig
        self.async_write_ha_state()

    async def update_state(self):
        self.async_write_ha_state()

    async def async_update(self):
        """Update de huidige staat van de thermostaat."""
        # Hier de logica om de huidige temperatuur en doeltemperatuur van je apparaat op te halen
        #self._current_temperature = await self._device.fetch_current_temperature()
        #self._target_temperature = await self._device.fetch_target_temperature()

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up de Harvia theromostats."""
    # Hier zou je de logica toevoegen om je apparaten op te halen.
    # Voor nu voegen we handmatig een schakelaar toe als voorbeeld.
    devices = await hass.data[DOMAIN]['api'].get_devices()
    theromostats = []

    for device in devices:
        _LOGGER.debug(f"Loading theromostats for device: {device.name}")
        device_theromostats = await device.get_thermostats()
        for device_theromostat in device_theromostats:
            theromostats.append(device_theromostat)

    async_add_entities(theromostats, True)
