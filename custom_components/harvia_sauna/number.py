from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

class HarviaHumiditySetPoint(NumberEntity):
    """Representatie van een nummer entiteit om de gewenste vochtigheid in te stellen."""

    def __init__(self, device, name, sauna):
        """Initialiseer de humidity number set point."""
        self._name = name + ' Steamer Humidity'
        self._state = None
        self._device = device
        self._device_id = device.id + '_humidity_set_point'
        self._sauna = sauna
        self._attr_unique_id = device.id + '_humidity_set_point'
        self._attr_icon = 'mdi:cloud-percent'

    @property
    def name(self):
        """Return de naam van de entiteit."""
        return self._name


    @property
    def min_value(self):
        """Return het minimum waarde van de vochtigheid die kan worden ingesteld."""
        return 0  # Stel in op je minimum grenswaarde

    @property
    def max_value(self):
        """Return het maximum waarde van de vochtigheid die kan worden ingesteld."""
        return 140  # Stel in op je maximum grenswaarde

    @property
    def step(self):
        """Return de stapgrootte van de vochtigheidsinstelling."""
        return 1.0

    @property
    def unit_of_measurement(self):
        """Return de eenheid van deze entiteit."""
        return PERCENTAGE

    @property
    def value(self):
        """Return de huidige ingestelde waarde."""
        return self._state

    async def async_added_to_hass(self):
        """Acties die uitgevoerd moeten worden als entiteit aan HA is toegevoegd."""
        self._device.humidityNumber = self
        await self._device.update_ha_devices()

    async def update_state(self):
        self.async_write_ha_state()

    async def async_set_value(self, value):
        """Update de ingestelde waarde."""
        self._state = value
        await self._device.set_target_relative_humidity(value)
        self.async_write_ha_state()

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up de Harvia numbers."""
    devices = await hass.data[DOMAIN]['api'].get_devices()
    all_numbers = []  # Gebruik een andere variabele om verwarring te voorkomen

    for device in devices:
        _LOGGER.debug(f"Loading sensors for device: {device.name}")
        device_numbers = await device.get_numbers()  # Verkrijg  sensors voor het huidige apparaat
        all_numbers.extend(device_numbers)  # Voeg de verkregen sensors toe aan de lijst

    async_add_entities(all_numbers, True)
