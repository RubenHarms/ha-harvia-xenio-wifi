from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_ON, STATE_OFF
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

class HarviaDoorSensor(BinarySensorEntity):
    """Een sensor die aangeeft of de Harvia sauna deur open of gesloten is."""

    def __init__(self, device, name, sauna):
        """Initialiseer de sensor."""
        self._name = name + ' Door'
        self._state = STATE_OFF
        self._device = device
        self._device_id = device.id + '_door_sensor'
        self._sauna = sauna
        self._attr_unique_id = device.id + '_door_sensor'
        self._attr_icon = 'mdi:door'

    @property
    def name(self):
        """Return de naam van de sensor."""
        return self._name

    @property
    def device_class(self):
        return  BinarySensorDeviceClass.DOOR

    @property
    def is_on(self):
        """Return True als de sensor aan is/detecteert dat de deur open is."""
        if self._state == STATE_OFF:
            return False
        else:
            return True
        #return self._state

    async def async_added_to_hass(self):
        """Acties die uitgevoerd moeten worden als entiteit aan HA is toegevoegd."""
        self._device.doorSensor = self
        await self._device.update_ha_devices()

    async def update_state(self):
        self.async_write_ha_state()

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up de Harvia binary sensors."""
    devices = await hass.data[DOMAIN]['api'].get_devices()
    all_binary_sensors = []  # Gebruik een andere variabele om verwarring te voorkomen

    for device in devices:
        _LOGGER.debug(f"Loading binary sensors for device: {device.name}")
        device_binary_sensors = await device.get_binary_sensors()  # Verkrijg binary sensors voor het huidige apparaat
        all_binary_sensors.extend(device_binary_sensors)  # Voeg de verkregen binary sensors toe aan de lijst

    async_add_entities(all_binary_sensors, True)
