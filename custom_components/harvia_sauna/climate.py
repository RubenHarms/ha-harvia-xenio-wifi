from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

class HarviaThermostat(ClimateEntity):
    def __init__(self, device, name, sauna):
        self._device = device
        self._name = name + ' Thermostat'
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
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
        return UnitOfTemperature.CELSIUS

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
        return [HVACMode.OFF, HVACMode.HEAT]

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
        active = False
        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

        if hvac_mode == HVACMode.HEAT:
            await self._device.set_active(True)
            active = True
        elif hvac_mode == HVACMode.OFF:
            await self._device.set_active(False)
            active = False

        if self._device.powerSwitch is not None:
            self._device.powerSwitch._is_on = active
            await self._device.powerSwitch.update_state()

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    async def update_state(self):
        self.async_write_ha_state()

    async def async_update(self):
        """Update de huidige staat van de thermostaat."""
        # Hier de logica om de huidige temperatuur en doeltemperatuur van je apparaat op te halen
        #self._current_temperature = await self._device.fetch_current_temperature()
        #self._target_temperature = await self._device.fetch_target_temperature()

async def async_setup_entry(hass, entry, async_add_entities):
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
