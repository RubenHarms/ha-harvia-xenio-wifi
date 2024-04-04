from homeassistant.components.switch import SwitchEntity
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

class HarviaPowerSwitch(SwitchEntity):
    def __init__(self, device, name, sauna):
        self._device = device
        self._name = name + ' Power switch'
        self._is_on = device.active
        self._device_id = device.id + '_power'
        self._sauna = sauna
        self._attr_unique_id = device.id + '_power'
        self._attr_icon = 'mdi:heating-coil'


    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    @property
    def icon(self) -> str | None:
        """Icon of the entity."""
        return "mdi:heater"

    @property
    def unique_id(self):
        """Return een unieke ID."""
        return self._device_id

    async def async_added_to_hass(self):
        """Acties die uitgevoerd moeten worden als entiteit aan HA is toegevoegd."""
        self._sauna.powerSwitch = self
        await self._device.update_ha_devices()

    async def update_state(self):
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        # Code om de sauna aan te zetten
        await self._device.set_active(True)
        self._is_on = True

    async def async_turn_off(self, **kwargs):
        # Code om de sauna uit te zetten
        await self._device.set_active(False)
        self._is_on = False



class HarviaLightSwitch(SwitchEntity):
    def __init__(self, device, name, sauna):
        self._device = device
        self._name = name + ' Light Switch'
        self._is_on = device.lightsOn
        self._device_id = device.id + '_light'
        self._sauna = sauna
        self._attr_unique_id = device.id + '_light'
        self._attr_icon = 'mdi:lightbulb-multiple'


    async def async_added_to_hass(self):
        """Acties die uitgevoerd moeten worden als entiteit aan HA is toegevoegd."""
        self._device.lightSwitch = self
        await self._device.update_ha_devices()
        #self._device.

    async def update_state(self):
        self.async_write_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on


    @property
    def unique_id(self):
        """Return een unieke ID."""
        return self._device_id

    async def async_turn_on(self, **kwargs):
        # Code om de sauna aan te zetten
        await self._device.set_lights(True)
        self._is_on = True

    async def async_turn_off(self, **kwargs):
        # Code om de sauna uit te zetten
        await self._device.set_lights(False)
        self._is_on = False

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up de Harvia switches."""
    # Hier zou je de logica toevoegen om je apparaten op te halen.
    # Voor nu voegen we handmatig een schakelaar toe als voorbeeld.
    devices = await hass.data[DOMAIN]['api'].get_devices()
    switches = []

    for device in devices:
        _LOGGER.debug(f"Loading switches for device: {device.name}")
        device_switches = await device.get_switches()
        for device_switch in device_switches:
            switches.append(device_switch)

    async_add_entities(switches, True)
