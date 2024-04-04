from __future__ import annotations
import json
import logging
import re
import base64
import asyncio
import signal
import websockets
import asyncio
import json
import uuid


from urllib.parse import quote
from .switch import HarviaPowerSwitch, HarviaLightSwitch
from .climate import HarviaThermostat
from .constants import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REGION,_LOGGER

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.components.climate import ClimateEntity, HVAC_MODE_HEAT
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE, HVAC_MODE_OFF


from pycognito import Cognito
import boto3

_LOGGER = logging.getLogger('custom_component.harvia_sauna')


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
        self.name = None
        self.lightSwitch = None
        self.powerSwitch = None
        self.thermostat = None
        self.switches = None
        self.thermostats = None
        self.lastestUpdate = None
        self.websockDevice = None
        self.websockData = None

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
            self.actvie = data['heatOn']
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


        await self.dump_data()
        await self.update_ha_devices()

    async def update_ha_devices(self):
        if self.lightSwitch is not None:
            self.lightSwitch._is_on = self.lightsOn
            await self.lightSwitch.update_state()

        if self.powerSwitch is not None:
            self.powerSwitch._is_on = self.active
            await self.powerSwitch.update_state()

        if self.thermostat is not None:
            self.thermostat._target_temperature = self.targetTemp
            self.thermostat._current_temperature = self.currentTemp

            if self.active == True:
                self.thermostat._hvac_mode = HVAC_MODE_HEAT
            else:
                self.thermostat._hvac_mode = HVAC_MODE_OFF
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


    async def get_thermostats(self) -> list:
        if self.switches != None:
            return self.switches

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
        self.uuid = None

    async def connect(self):
        asyncio.create_task(self.start())

    async def start(self):

        endpoint = await self.sauna.get_websock_endpoint(self.endpoint)
        self.endpoint_host = endpoint['host']
        self.uuid = str(uuid.uuid4())

        url = await self.sauna.websock_get_url(self.endpoint)
        payload = {'type': 'connection_init'}
        _LOGGER.debug(f"wssUrl: {url}")

        async with websockets.connect(url,  subprotocols=["graphql-ws"],) as self.websocket:
            await self.websocket.send(json.dumps(payload))

            while True:
                message = await self.receive_message(self.websocket)
                if message:
                    await self.handle_message(message)
                else:
                    print("Geen 'ka' bericht ontvangen binnen 5 minuten.")
                    break

    async def create_subscription(self):

        id_token = await self.sauna.get_id_token()

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

    async def async_setup(self, config: dict) -> bool:
        """Stel de Harvia Sauna component in op basis van configuration.yaml."""
        _LOGGER.info("Starting setup of Harvia Sauna component.")

        self.data = await self.storage.async_load() or {}

        harvia_config = self.config.get(DOMAIN)
        if harvia_config is None:
            _LOGGER.error("Harvia Sauna configuration not found.")
            return False

        self.hass.data[DOMAIN] = harvia_config

        await self.update_devices()
        await self.websocket_init()

        self.hass.data[DOMAIN]['api'] = self

        _LOGGER.info("Harvia Sauna component setup completed.")
        return True

    async def get_device(self, deviceId: str) -> dict:
        headers = await self.get_headers()

        data_string = json.dumps(headers, indent=4)
        device_query = { "operationName": "Query", "variables": {  "deviceId": deviceId  },      "query": "query Query($deviceId: ID!) {\n  getDeviceState(deviceId: $deviceId) {\n    desired\n    reported\n    timestamp\n    __typename\n  }\n}\n"}
        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        url = self.data['endpoints']['device']['endpoint']
        async with session.post(url, json=device_query, headers=headers) as response:
            deviceResp = await response.json()
            data_string = json.dumps(deviceResp, indent=4)
            _LOGGER.debug(f"Ontvangen data: {data_string}")
            deviceData = json.loads(deviceResp['data']['getDeviceState']['reported'])

        return deviceData

    async def get_latest_device_data(self, deviceId: str) -> dict:
        headers = await self.get_headers()
        data_string = json.dumps(headers, indent=4)
        data_query ={
                        "operationName": "Query",
                        "variables": {
                            "deviceId": deviceId
                        },
                        "query": "query Query($deviceId: String!) {\n  getLatestData(deviceId: $deviceId) {\n    deviceId\n    timestamp\n    sessionId\n    type\n    data\n    __typename\n  }\n}\n"
                    }
        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        url = self.data['endpoints']['data']['endpoint']
        async with session.post(url, json=data_query, headers=headers) as response:
            deviceResp = await response.json()
            data_string = json.dumps(deviceResp, indent=4)
            _LOGGER.debug(f"Ontvangen data: {data_string}")
            deviceData = json.loads(deviceResp['data']['getLatestData']['data'])

            deviceData['timestamp'] = deviceResp['data']['getLatestData']['timestamp']
            deviceData['type'] = deviceResp['data']['getLatestData']['type']

        return deviceData

    async def get_headers(self) -> dict:
        id_token = await self.get_id_token()
        headers = {
            'authorization': id_token
        }
        return headers

    async def get_devices(self) -> list:
        if self.devices is None:
            await self.update_devices()
        return self.devices


    async def update_devices(self):

        self.devices = []

        headers = await self.get_headers()
        device_data= {
        "operationName": "Query",
        "variables": {},
        "query": 'query Query {\n  getDeviceTree\n}\n'
        }

        session = self.hass.helpers.aiohttp_client.async_get_clientsession()

        url = self.data['endpoints']['device']['endpoint']
        async with session.post(url, json=device_data, headers=headers) as response:
            self.devices = []
            deviceTree = await response.json()
            data_string = json.dumps(deviceTree, indent=4)
            _LOGGER.debug(f"Ontvangen data: {data_string}")

            # Zorg ervoor dat je eerst controleert of 'data' en 'getDeviceTree' in de response aanwezig zijn
            if 'data' in deviceTree and 'getDeviceTree' in deviceTree['data']:
                # Als 'getDeviceTree' gevonden is, kun je de data eruit halen
                devicesTreeData =  json.loads(deviceTree['data']['getDeviceTree'])
                # Hieronder ga ik ervan uit dat devicesTreeData een lijst van dictionaries is en we geïnteresseerd zijn in de 'c' sleutel van het eerste element.
                # Pas dit aan op basis van de werkelijke structuur van je data.
                if devicesTreeData:  # Check of de lijst niet leeg is
                    data_string = json.dumps(devicesTreeData, indent=4)
                    _LOGGER.debug(f"Devices: {data_string}")
                    devices = devicesTreeData[0]['c']
                    for device in devices:
                        deviceId = device['i']['name']

                        deviceData = await self.get_device(deviceId)
                        latestDeviceData = await self.get_latest_device_data(deviceId)
                        deviceObject  = HarviaDevice(sauna=self, id=deviceId)

                        await deviceObject.update_data(deviceData)
                        await deviceObject.update_data(latestDeviceData)
                        self.devices.append(deviceObject)


                    # Doe iets met 'devices'
                else:
                    _LOGGER.error("Geen devices gevonden in de response.")
            else:
                _LOGGER.error("Onverwachte structuur van de response: 'data' of 'getDeviceTree' niet gevonden.")

    async def check_and_renew_token(self):
        client = await self.get_client()

        current_id_token = self.data['token_data']['id_token']
        await self.hass.async_add_executor_job(
            lambda: client.check_token(renew=True)
        )
        self.data["token_data"] = {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
            "id_token": client.id_token,
        }

        if current_id_token != client.id_token:
            _LOGGER.debug(f"Token renewed! {current_id_token} != {client.id_token}")


    async def get_id_token(self) -> str:
        await self.check_and_renew_token()
        return self.data['token_data']['id_token']

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

        headers = await self.get_headers()
        query = {   "operationName": "Mutation",
                    "variables": {
                    "deviceId": deviceId,
                    "state": payloadString,
                    "getFullState": False
                    },
                    "query": "mutation Mutation($deviceId: ID!, $state: AWSJSON!, $getFullState: Boolean) {\n  requestStateChange(deviceId: $deviceId, state: $state, getFullState: $getFullState)\n}\n"
                }

        session = self.hass.helpers.aiohttp_client.async_get_clientsession()

        url = self.data['endpoints']['device']['endpoint']
        async with session.post(url, json=query, headers=headers) as response:
            response = await response.json()
            responseString = json.dumps(response, indent=4)
            _LOGGER.debug(f"Device mutation: {responseString}")

    async def get_client(self) -> Cognito:
        if self.cognito == None:
            await self.authenticate_and_save_tokens()


        return self.cognito

    async def fetch_and_save_endpoints(self):
        """Haalt endpoints op en slaat deze op als ze nog niet bestaan."""
        _LOGGER.debug("Fetching and saving endpoints.")

        if "endpoints" not in self.data:
            self.data['endpoints'] = {}
            session = self.hass.helpers.aiohttp_client.async_get_clientsession()
            endpoints = ["users", "device", "events", "data"]
            for endpoint in endpoints:
                url = f'https://prod.myharvia-cloud.net/{endpoint}/endpoint'
                _LOGGER.debug(f"Fetching endpoint: {url}")
                async with session.get(url) as response:
                    self.data['endpoints'][endpoint] = await response.json()
                    data_string = json.dumps(self.data['endpoints'][endpoint], indent=4)
                    _LOGGER.debug(f"Ontvangen data: {data_string}")

            await self.storage.async_save(self.data)
            _LOGGER.info("Endpoints successfully fetched and saved.")
        else:
            _LOGGER.info("Endpoints already exist and were not fetched.")
            data_string = json.dumps(self.data['endpoints'], indent=4)
            _LOGGER.debug(f"Endpoint data: {data_string}")

    async def get_websock_endpoint(self, endpoint: str) -> dict:
        user_endpoint = self.data['endpoints'][endpoint]['endpoint']
        regex = r"^https:\/\/(.+)\.appsync-api\.(.+)\/graphql$"
        regexReplace = r"wss://\1.appsync-realtime-api.\2/graphql"
        regexReplaceHost = r"\1.appsync-api.\2"

        wssUrl = re.sub(regex, regexReplace, user_endpoint)
        host = re.sub(regex, regexReplaceHost, user_endpoint)

        return { 'wssUrl': wssUrl, 'host': host}

    async def websock_get_url(self, endpoint) -> str:
        websockEndpoint = await self.get_websock_endpoint(endpoint)
        data_string = json.dumps(websockEndpoint, indent=4)
        _LOGGER.debug(f"Websock endpoint: {data_string}")

        id_token = await self.get_id_token()
        headerPayload = {"Authorization":id_token,"host":websockEndpoint['host']}

        data_string = str(json.dumps(headerPayload, indent=4))
        _LOGGER.debug(f"Websock data: {data_string}")

        encoded_header = base64.b64encode(data_string.encode())
        _LOGGER.debug(f"Encoded data: {encoded_header}")

        wssUrl = websockEndpoint['wssUrl']+ '?header='+ quote(encoded_header)+'&payload=e30='
        return wssUrl


    async def websocket_init(self):
        self.websockDevice = HarviaWebsock(self, 'device')
        await self.websockDevice.connect()

        self.websockData = HarviaWebsock(self, 'data')
        await self.websockData.connect()

    async def get_user_data(self):
        if self.user_data is not None:
            return self.user_data
        headers = await self.get_headers()

        user_query= {
        "operationName": "Query",
        "variables": {},
        "query": "query Query {\n  getCurrentUserDetails {\n    email\n    organizationId\n    admin\n    given_name\n    family_name\n    superAdmin\n    rdUser\n    appSettings\n    __typename\n  }\n}\n"
        }

        session = self.hass.helpers.aiohttp_client.async_get_clientsession()
        url = self.data['endpoints']['users']['endpoint']
        async with session.post(url, json=user_query, headers=headers) as response:
            user_data = await response.json()
            data_string = json.dumps(user_data, indent=4)
            _LOGGER.debug(f"User data: {data_string}")

            self.user_data = user_data['data']['getCurrentUserDetails']
            return  self.user_data


    async def authenticate_and_save_tokens(self):
        """Authenticateert met de service en slaat de tokens op."""
        _LOGGER.debug("Authenticating and saving tokens.")

        await self.fetch_and_save_endpoints()
        user_pool_id = self.data["endpoints"]["users"]["userPoolId"]
        client_id = self.data["endpoints"]["users"]["clientId"]
        id_token = self.data["endpoints"]["users"]["identityPoolId"]
        username = self.hass.data[DOMAIN]["username"]
        password = self.hass.data[DOMAIN]["password"]

        _LOGGER.debug("Using Cognito for authentication.")

        u = await self.hass.async_add_executor_job(
            lambda: Cognito(user_pool_id, client_id, username=username, user_pool_region=REGION, id_token=id_token)
        )
        self.cognito = u

        _LOGGER.debug("Using username: " + username + ' - with password:"'+password+ "'")

        await self.hass.async_add_executor_job(

            lambda: u.authenticate(password=password)
        )

        self.data["token_data"] = {
            "access_token": u.access_token,
            "refresh_token": u.refresh_token,
            "id_token": u.id_token,
        }

        data_string = json.dumps( self.data["token_data"], indent=4)
        await self.check_and_renew_token()
        await self.storage.async_save(self.data)
        _LOGGER.info("Authentication successful, tokens saved.")

        data_string = json.dumps( self.data["token_data"], indent=4)
        _LOGGER.debug(f"Token data: {data_string}")

        self.hass.data[DOMAIN]["token_data"] = self.data["token_data"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup de Harvia Sauna integratie."""
    boto3.set_stream_logger('custom_component.harvia_sauna')
    storage = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    harvia_sauna = HarviaSauna(hass, storage, config)
    return await harvia_sauna.async_setup(config)
