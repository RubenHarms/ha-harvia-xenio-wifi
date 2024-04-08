from __future__ import annotations
import json
import logging
import asyncio
import signal
import websockets
import asyncio
import json
import uuid
import random


from .switch import HarviaPowerSwitch, HarviaLightSwitch
from .climate import HarviaThermostat
from .api import HarviaSaunaAPI
from .binary_sensor import HarviaDoorSensor
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER, STATE_CODE_SAFETY,STATE_CODE_HEATING, STATE_CODE_RESTING_PERIOD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_ON, STATE_OFF, CONF_USERNAME, CONF_PASSWORD

from pycognito import Cognito
import boto3

_LOGGER = logging.getLogger('custom_component.harvia_sauna')
ENTITY_TYPES = [ 'switch', 'climate',  'binary_sensor']

class HarviaDevice:
    def __init__(self, sauna: HarviaSauna, id: str):
        self.sauna = sauna
        self.data = {}
        self.user  = None
        self.id = id
        self.active = False
        self.lightsOn = False
        self.steamOn = False
        self.targetTemp = None
        self.currentTemp = None
        self.humidity = None
        self.remainingTime = None
        self.heatUpTime = 0
        self.targetRh = 0
        self.onTime = 0
        self.fanOn = False
        self.stateCodes = None
        self.name = None
        self.lightSwitch = None
        self.powerSwitch = None
        self.doorSensor = None
        self.thermostat = None
        self.binarySensors = None
        self.switches = None
        self.thermostats = None
        self.lastestUpdate = None


    async def update_data(self, data: dict):
        self.data = data

        _LOGGER.debug(f"Performing device update: " + json.dumps(data))

        if 'displayName' in data:
            self.name = data['displayName']
        if 'active' in data:
            self.active = bool(data['active'])
        if 'light' in data:
            self.lightsOn = bool(data['light'])
        if 'fanOn' in data:
            self.fanOn = bool(data['fanOn'])
        if 'steamOn' in data:
            self.fanOn = bool(data['steamOn'])
        if 'heatOn' in data:
            self.active = data['heatOn']
        if 'targetTemp' in data:
            self.targetTemp = data['targetTemp']
        if 'targetRh' in data:
            self.targetRh = data['targetRh']
        if 'heatUpTime' in data:
            self.heatUpTime = data['heatUpTime']
        if 'remainingTime' in data:
            self.remainingTime = data['remainingTime']
        if 'temperature' in data:
            self.currentTemp = data['temperature']
        if 'humidity' in data:
            self.humidity = data['humidity']
        if 'timestamp' in data:
            self.lastestUpdate = data['timestamp']
        if 'statusCodes' in data:
            self.statusCodes = data['statusCodes']

        await self.dump_data()
        await self.update_ha_devices()

    async def update_ha_devices(self):

        if self.lightSwitch is not None:
            self.lightSwitch._is_on = self.lightsOn
            await self.lightSwitch.update_state()

        if self.powerSwitch is not None:
            self.powerSwitch._is_on = self.active
            await self.powerSwitch.update_state()

        #_LOGGER.error("Status codes == " +  str(self.statusCodes))
        #_LOGGER.error("STATE_CODE_SAFETY == " +  str(STATE_CODE_SAFETY))

        #BinarySensorDeviceClass.DOOR On means open, Off means closed.

        if self.doorSensor is not None:
            # _LOGGER.error("Door sensor loaded")
            if self.statusCodes == STATE_CODE_SAFETY:
                _LOGGER.error("Door is open")
                self.doorSensor._state = STATE_ON
            else:
                _LOGGER.error("Door is closed")
                self.doorSensor._state = STATE_OFF
            await self.doorSensor.update_state()

        if self.thermostat is not None:
            self.thermostat._target_temperature = self.targetTemp
            self.thermostat._current_temperature = self.currentTemp

            if self.active == True:
                self.thermostat._hvac_mode = HVACMode.HEAT
            else:
                self.thermostat._hvac_mode =  HVACMode.OFF
            await self.thermostat.update_state()

    async def set_target_temperature(self, temp: int):

        payload = {'targetTemp': temp}
        await self.sauna.device_mutation(deviceId=self.id,payload=payload)


    async def set_lights(self, state: bool):
        lightInt = int(state)
        payload = {'light': lightInt}
        await self.sauna.device_mutation(deviceId=self.id,payload=payload)

    async def set_active(self, state: bool):
        activeInt = int(state)
        payload = {'active': activeInt}
        await self.sauna.device_mutation(deviceId=self.id,payload=payload)

    async def dump_data(self):

        data = { 'name': self.name, 'active': self.active, 'lightsOn': self.lightsOn,  'targetTemp': self.targetTemp,  'targetRh': self.targetRh, 'fanOn':  self.fanOn, 'heatUpTime': self.heatUpTime  }

        attributes_as_string = json.dumps(data, indent=4)
        _LOGGER.debug(f"Device attributen: {attributes_as_string}")

    async def get_binary_sensors(self) -> list:

        if self.binarySensors != None:
            return self.binarySensors

        self.binarySensors = []

        binarySensor = HarviaDoorSensor(device=self, name=self.name, sauna=self.sauna)
        self.binarySensors.append(binarySensor)

        return self.binarySensors


    async def get_thermostats(self) -> list:
        if self.thermostats != None:
            return self.thermostats

        self.thermostats = []

        thermostat = HarviaThermostat(device=self, name=self.name, sauna=self.sauna)
        self.thermostats.append(thermostat)

        return self.thermostats

    async def get_switches(self) -> list:
        if self.switches != None:
            return self.switches

        self.switches = []

        powerSwitch = HarviaPowerSwitch(device=self, name=self.name, sauna=self.sauna)
        lightSwitch = HarviaLightSwitch(device=self, name=self.name, sauna=self.sauna)

        self.switches.append(powerSwitch)
        self.switches.append(lightSwitch)

        return self.switches


class HarviaWebsock:

    def __init__(self, sauna: HarviaSauna, endpoint: str):
        self.sauna = sauna
        self.websocket = None
        self.timeout = 300
        self.endpoint = endpoint
        self.endpoint_host = None
        self.reconnect_attempts = 0
        self.uuid = None
        self.websocket_task = None

    async def connect(self):
        self.websocket_task = asyncio.create_task(self.start())

    async def start(self):
        """Probeer opnieuw verbinding te maken in geval van verbreking."""
        try:
            endpoint = await self.sauna.api.getWebsocketEndpoint(self.endpoint)
            self.endpoint_host = endpoint['host']
            self.uuid = str(uuid.uuid4())

            url = await self.sauna.api.getWebsockUrlByEndpoint(self.endpoint)
            payload = {'type': 'connection_init'}
            _LOGGER.debug(f"wssUrl: {url}")

            async with websockets.connect(url,  subprotocols=["graphql-ws"],) as self.websocket:
                self.reconnect_attempts = 0
                await self.websocket.send(json.dumps(payload))

                while True:
                    message = await self.receive_message(self.websocket)
                    if message:
                        await self.handle_message(message)
                    else:
                        _LOGGER.error("Geen 'ka' bericht ontvangen binnen 5 minuten.")
                        break  # Trigger de reconnect logica.

        except (websockets.exceptions.ConnectionClosedError, asyncio.TimeoutError) as e:
                _LOGGER.error("Verbindingsfout: %s", e)

        await asyncio.sleep(min(2 ** self.reconnect_attempts, 60) + random.uniform(0, 1))

        self.reconnect_attempts += 1
        self.websocket_task = asyncio.create_task(self.start())

    async def create_subscription(self):

        id_token = await self.sauna.api.getIdToken()
        data = ""
        if self.endpoint == 'data':
            data =  await self.create_data_subscription_message()
        elif self.endpoint == 'device':
            data =  await self.create_device_subscription_message()

        payload = {
                    "id": self.uuid,
                    "payload": {
                        "data": data,
                        "extensions": {
                            "authorization": {
                                "Authorization": id_token,
                                "host": self.endpoint_host,
                                "x-amz-user-agent": "aws-amplify/2.0.5 react-native"
                            }
                        }
                    },
                    "type": "start"
                    }

        message = json.dumps(payload)
        _LOGGER.debug(f"Websock "+self.endpoint+ f" send subscription: {message}")

        await self.websocket.send(message)

    async def create_data_subscription_message(self) -> str:
        userData = await self.sauna.get_user_data()
        organizationId = userData["organizationId"]
        return "{\"query\":\"subscription Subscription($receiver: String!) {\\n  onDataUpdates(receiver: $receiver) {\\n    item {\\n      deviceId\\n      timestamp\\n      sessionId\\n      type\\n      data\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\",\"variables\":{\"receiver\":\""+organizationId+"\"}}"

    async def create_device_subscription_message(self) -> str:
        userData = await self.sauna.get_user_data()
        organizationId = userData["organizationId"]
        return "{\"query\":\"subscription Subscription($receiver: String!) {\\n  onStateUpdated(receiver: $receiver) {\\n    desired\\n    reported\\n    timestamp\\n    receiver\\n    __typename\\n  }\\n}\\n\",\"variables\":{\"receiver\":\""+organizationId+"\"}}"

    async def handle_message(self, message):
        """Verwerk en reageer op het ontvangen bericht."""

        _LOGGER.debug("Websock " + self.endpoint +  " - received message: " + message)
        data = json.loads(message)  # Veronderstelt dat het bericht in JSON-formaat is
        # Voorbeeld: controleer of het bericht een specifiek type of inhoud heeft
        if data.get("type") == "ka":
            _LOGGER.debug("Websock  " + self.endpoint +  " Hartslag ontvangen.")
        elif data.get('type') == 'connection_ack':
            _LOGGER.debug("Websock connection_ack ontvangen")
            if data.get('payload'):
                self.timeout = data['payload']['connectionTimeoutMs']/1000
            await self.create_subscription()
        elif data.get("type") == "data":
            if self.endpoint == 'device':
                await self.sauna.process_device_update(data)
            elif self.endpoint == 'data':
                await self.sauna.process_device_update(data)
            _LOGGER.debug("Websock " + self.endpoint +  " Actie vereist: " + message)
        else:
            _LOGGER.debug("Onbekend berichttype " + self.endpoint +  " ontvangen: " + message)

    async def receive_message(self,websocket):
        """Wacht op een bericht met een maximale duur."""
        try:
            message = await asyncio.wait_for(websocket.recv(), self.timeout)
            return message
        except websockets.exceptions.ConnectionClosedError as e:
            _LOGGER.error("WebSocket verbinding is gesloten: %s", e)
        except asyncio.TimeoutError:
            return None

class HarviaSauna:

    def __init__(self, hass: HomeAssistant, storage: Store, config: dict):
        self.hass = hass
        self.storage = storage
        self.config = config
        self.data = {}
        self.devices = None
        self.user_data = None
        self.cognito = None
        self.websockDevice = None
        self.websockData = None
        self.api = None

    async def async_setup(self, config: dict) -> bool:
        """Stel de Harvia Sauna component in op basis van configuration.yaml."""
        _LOGGER.info("Starting setup of Harvia Sauna component.")

        self.data = await self.storage.async_load() or {}

        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}

        username = self.config.data.get(CONF_USERNAME)
        password = self.config.data.get(CONF_PASSWORD)

        self.api =  HarviaSaunaAPI(username, password, self.hass)
        if await self.api.authenticate():
            _LOGGER.info("Harvia Sauna component setup completed.")
        else:
            _LOGGER.info("Error! Could'nt authenticate!")
            return False

        await self.update_devices()
        self.hass.loop.create_task(self.check_connections())
        self.hass.data[DOMAIN]['api'] = self

        return True

    async def get_device(self, deviceId: str) -> dict:
        query = { "operationName": "Query", "variables": {  "deviceId": deviceId  },      "query": "query Query($deviceId: ID!) {\n  getDeviceState(deviceId: $deviceId) {\n    desired\n    reported\n    timestamp\n    __typename\n  }\n}\n"}
        data = await self.api.endpoint('device', query )
        return json.loads(data['data']['getDeviceState']['reported'])

    async def get_latest_device_data(self, deviceId: str) -> dict:
        query ={
            "operationName": "Query",
            "variables": {
                "deviceId": deviceId
            },
            "query": "query Query($deviceId: String!) {\n  getLatestData(deviceId: $deviceId) {\n    deviceId\n    timestamp\n    sessionId\n    type\n    data\n    __typename\n  }\n}\n"
        }
        data = await self.api.endpoint('data', query)
        deviceData = json.loads(data['data']['getLatestData']['data'])
        deviceData['timestamp'] = data['data']['getLatestData']['timestamp']
        deviceData['type'] = data['data']['getLatestData']['type']
        return deviceData

    async def get_headers(self) -> dict:
        _LOGGER.warning("get_headers is DEPRICATED use HarviaSaunaApi.getHeaders() instead.")
        return await self.api.getHeaders()

    async def get_devices(self) -> list:
        if self.devices is None:
            await self.update_devices()
        return self.devices


    async def update_devices(self):
        self.devices = []

        query = {
        "operationName": "Query",
        "variables": {},
        "query": 'query Query {\n  getDeviceTree\n}\n'
        }

        deviceTree = await self.api.endpoint('device', query)
        if 'data' in deviceTree and 'getDeviceTree' in deviceTree['data']:
            devicesTreeData =  json.loads(deviceTree['data']['getDeviceTree'])
            if devicesTreeData:  # Check of de lijst niet leeg is
                data_string = json.dumps(devicesTreeData, indent=4)
                devices = devicesTreeData[0]['c']
                for device in devices:
                    deviceId = device['i']['name']
                    _LOGGER.info("Found device: " + deviceId)
                    deviceData = await self.get_device(deviceId)
                    latestDeviceData = await self.get_latest_device_data(deviceId)
                    deviceObject  = HarviaDevice(sauna=self, id=deviceId)
                    await deviceObject.update_data(deviceData)
                    await deviceObject.update_data(latestDeviceData)
                    self.devices.append(deviceObject)
            else:
                _LOGGER.error("Geen devices gevonden in de response.")
        else:
            _LOGGER.error("Onverwachte structuur van de response: 'data' of 'getDeviceTree' niet gevonden.")


    async def process_device_update(self, message: dict):

        _LOGGER.debug("Device update process: " + json.dumps(message))


        if message.get('type') != 'data':
            return
        if 'onStateUpdated' in message['payload']['data']:
            #{"id":"5ae58e56-d03a-4a7a-ab7d-9e8b308810a1","type":"data","payload":{"data":{"onStateUpdated":{"desired":null,"reported":"{\"active\":1,\"light\":0,\"fan\":0,\"steamEn\":0,\"targetTemp\":90,\"targetRh\":50,\"heatUpTime\":37,\"tz\":\"UTC+1 dst\",\"onTime\":360,\"dehumEn\":0,\"autoLight\":0,\"tempUnit\":0,\"timedStart\":\"ARhaABxEDGY=\",\"displayName\":\"Sauna boven\",\"cmd\":\"\",\"autoFan\":0,\"aromaEn\":0,\"aromaLevel\":0,\"wClkEn\":0,\"wClk\":\"\",\"deviceId\":\"e0b84f32-9eb0-4add-aad5-8d50886b3a66\",\"otaId\":\"\",\"__typename\":\"SAUNA\"}","timestamp":1712078650,"receiver":"5b53af61-8f6a-4fc5-ba12-d33af78dbac3","__typename":"StateResponse"}}}}
            data = json.loads(message['payload']['data']['onStateUpdated']['reported'])
            deviceId = data['deviceId']
        elif 'onDataUpdates' in message['payload']['data']:
            #{ "id": "898df439-408e-4d35-b7c6-9a5bc6d69e81", "type": "data", "payload": { "data": { "onDataUpdates": { "item": { "deviceId": "e0b84f32-9eb0-4add-aad5-8d50886b3a66", "timestamp": "1712161222726", "sessionId": "1", "type": "sauna", "data": "{\"targetTemp\":90,\"ph2RelayCounterLT\":0,\"remainingTime\":357,\"steamOn\":false,\"temperature\":27,\"humidity\":0,\"heatOn\":true,\"steamOnCounterLT\":0,\"steamOnCounter\":0,\"heatOnCounterLT\":0,\"heatOnCounter\":0,\"ph1RelayCounterLT\":1,\"ph3RelayCounterLT\":0,\"ph1RelayCounter\":1,\"ph3RelayCounter\":0,\"wifiRSSI\":-68,\"testVar1\":0,\"testVar2\":0,\"ph2RelayCounter\":0}", "__typename": "DataItem" }, "__typename": "UpdatedData" } } } }
            data = json.loads(message['payload']['data']['onDataUpdates']['item']['data'])
            data['timestamp'] = message['payload']['data']['onDataUpdates']['item']['timestamp']
            data['type'] = message['payload']['data']['onDataUpdates']['item']
            deviceId =  message['payload']['data']['onDataUpdates']['item']['deviceId']
        else:
            return

        for device in self.devices:
            if device.id != deviceId:
                continue
            await device.update_data(data)

    async def device_mutation(self, deviceId: str, payload: str):
        payloadString =  json.dumps(payload, indent=4)
        query = {   "operationName": "Mutation",
                    "variables": {
                    "deviceId": deviceId,
                    "state": payloadString,
                    "getFullState": False
                    },
                    "query": "mutation Mutation($deviceId: ID!, $state: AWSJSON!, $getFullState: Boolean) {\n  requestStateChange(deviceId: $deviceId, state: $state, getFullState: $getFullState)\n}\n"
                }
        response = await self.api.endpoint('device', query)
        return response

    async def get_client(self) -> Cognito:
        if self.cognito == None:
            await self.authenticate_and_save_tokens()
        return self.cognito

    async def websock_get_url(self, endpoint) -> str:
        return await self.api.getWebsockUrlByEndpoint(endpoint)

    async def get_user_data(self):
        if self.user_data is not None:
            return self.user_data
        query= {
            "operationName": "Query",
            "variables": {},
            "query": "query Query {\n  getCurrentUserDetails {\n    email\n    organizationId\n    admin\n    given_name\n    family_name\n    superAdmin\n    rdUser\n    appSettings\n    __typename\n  }\n}\n"
        }
        data = await self.api.endpoint('users',query )
        self.user_data = data['data']['getCurrentUserDetails']
        return  self.user_data

    async def check_connections(self):
        while True:
            _LOGGER.debug("Checking websocket connections: ")
            if self.websockDevice is None:
                self.websockDevice = HarviaWebsock(self, 'device')
                await self.websockDevice.connect()

            if self.websockData is None:
                self.websockData = HarviaWebsock(self, 'data')
                await self.websockData.connect()

            if self.websockDevice and self.websockDevice.websocket_task.done():
                _LOGGER.debug("WebSocket Device: NOT RUNNING. Reconnecting!")
                await self.websockDevice.connect()
            else:
                _LOGGER.debug("\tWebsocket Device: RUNNING")

            if self.websockData and self.websockData.websocket_task.done():
                _LOGGER.debug("\tWebSocket Data: NOT RUNNING. Reconnecting!")
                await self.websockData.connect()
            else:
                _LOGGER.debug("\tWebsocket Data: RUNNING")
            await asyncio.sleep(60)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup de Harvia Sauna integratie."""
    boto3.set_stream_logger('custom_component.harvia_sauna')

    return True

async def async_setup_entry(hass, entry):
    """Set up Harvia Sauna from a config entry."""
    _LOGGER.debug(f"Setup entry...")

    """Setup een Harvia Sauna configuratie entry."""
    # Haal de configuratiegegevens op die zijn opgeslagen door de config flow
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    if not username or not password:
        _LOGGER.error("Username or password not configured.")
        return False

    storage = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    harvia_sauna = HarviaSauna(hass, storage, entry)
    await harvia_sauna.async_setup(entry)

    for entity_type in ENTITY_TYPES:
        hass.async_create_task(  hass.config_entries.async_forward_entry_setup(entry, entity_type) )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handel het ontladen van een configuratie-entry."""
    # Ontlaad platformen die deel uitmaken van de integratie
    for entity_type in ENTITY_TYPES:
        await hass.config_entries.async_forward_entry_unload(entry, entity_type)

    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handel het herladen van een configuratie-entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

    return True
