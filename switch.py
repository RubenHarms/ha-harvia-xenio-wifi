from homeassistant.components.switch import SwitchEntity
import logging


_LOGGER = logging.getLogger('custom_component.harvia_sauna')
DOMAIN = "harvia_sauna"

class HarviaPowerSwitch(SwitchEntity):
    def __init__(self, device, name):
        self._device = device
        self._name = name + ' schakelaar'
        self._is_on = device.active
        self._device_id = device.id + '_power'

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
        await self._device.set_active(True)
        self._is_on = True

    async def async_turn_off(self, **kwargs):
        # Code om de sauna uit te zetten
        await self._device.set_active(False)
        self._is_on = False


class HarviaLightSwitch(SwitchEntity):
    def __init__(self, device, name):
        self._device = device
        self._name = name + ' lichtschakelaar'
        self._is_on = device.lightsOn
        self._device_id = device.id + '_light'


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