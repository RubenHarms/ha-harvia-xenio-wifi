from pycognito import Cognito
import boto3
import logging
import json
import re
import base64
import botocore.exceptions
from urllib.parse import quote
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .constants import DOMAIN, REGION

_LOGGER = logging.getLogger('custom_component.harvia_sauna')

class HarviaSaunaAPI:
    def __init__(self, username, password, hass):
        self.username  = username
        self.password  = password
        self.hass = hass
        self.endpoints = None
        self.client = None
        self.token_data = None

    async def getEndpoints(self):
        """Haalt endpoints op en slaat deze op als ze nog niet bestaan."""
        _LOGGER.debug("Fetching endpoints.")

        if self.endpoints is None:
            self.endpoints = {}
            session = async_get_clientsession(self.hass)
            endpoints = ["users", "device", "events", "data"]
            for endpoint in endpoints:
                url = f'https://prod.myharvia-cloud.net/{endpoint}/endpoint'
                _LOGGER.debug(f"Fetching endpoint: {url}")
                async with session.get(url) as response:
                    self.endpoints[endpoint] = await response.json()
                    data_string = json.dumps(self.endpoints[endpoint], indent=4)
                    _LOGGER.debug(f"Received data: {data_string}")

            _LOGGER.info("Endpoints successfully fetched and saved.")
        else:
            _LOGGER.info("Endpoints already exist and were not fetched.")
            data_string = json.dumps(self.endpoints, indent=4)
            _LOGGER.debug(f"Endpoint data: {data_string}")

        return self.endpoints

    async def authenticate(self):
        if self.token_data is not None:
            return True

        u = await self.getClient()
        """Authenticateert met de service en slaat de tokens op."""
        _LOGGER.debug("Authenticating")
        _LOGGER.debug("Using username: " + self.username + ' - with password:"'+self.password+ "'")

        try:
            await self.hass.async_add_executor_job(

                lambda: u.authenticate(password=self.password)
            )
        except botocore.exceptions.ClientError as e:
            _LOGGER.info("Authentication failed: " + str(e))
            return False

        self.token_data = {
            "access_token": u.access_token,
            "refresh_token": u.refresh_token,
            "id_token": u.id_token,
        }

        _LOGGER.info("Authentication successful, tokens saved.")
        data_string = json.dumps( self.token_data, indent=4)
        _LOGGER.debug(f"Token data: {data_string}")

        return True

    async def getClient(self) -> Cognito:
        if self.client is None:

            endpoints = await self.getEndpoints()
            user_pool_id = endpoints["users"]["userPoolId"]
            client_id = endpoints["users"]["clientId"]
            id_token = endpoints["users"]["identityPoolId"]

            username =self.username
            u = await self.hass.async_add_executor_job(
                lambda: Cognito(user_pool_id, client_id, username=username, user_pool_region=REGION, id_token=id_token)
            )
            self.client = u

        return self.client

    async def getAuthenticatedClient(self) -> Cognito:
        client = await self.getClient()
        await self.authenticate()
        return client

    async def checkAndRenewTokens(self):
        client = await self.getAuthenticatedClient()
        current_id_token = self.token_data['id_token']
        await self.hass.async_add_executor_job(
            lambda: client.check_token(renew=True)
        )
        self.token_data = {
            "access_token": client.access_token,
            "refresh_token": client.refresh_token,
            "id_token": client.id_token,
        }

        if current_id_token != client.id_token:
            _LOGGER.debug(f"Token renewed! {current_id_token} != {client.id_token}")

    async def getIdToken(self) -> str:
        await self.checkAndRenewTokens()
        return self.token_data['id_token']

    async def getHeaders(self) -> dict:
        idToken = await self.getIdToken()
        headers = {
            'authorization': idToken
        }
        return headers

    async def endpoint(self, endpoint: str, query: dict) -> dict:
        headers = await self.getHeaders()
        session = async_get_clientsession(self.hass)
        url = self.endpoints[endpoint]['endpoint']
        queryDump = json.dumps(query, indent=4)
        _LOGGER.debug("Endpoint request on '" + url + "':")
        _LOGGER.debug("\tQuery:" + queryDump)
        async with session.post(url, json=query, headers=headers) as response:
            data = await response.json()
            dataString = json.dumps(data, indent=4)
            _LOGGER.debug(f"\tReturned data: {dataString}")
            return data

    async def getWebsocketEndpoint(self, endpoint: str) -> dict:
        endpoint = self.endpoints[endpoint]['endpoint']
        regex = r"^https:\/\/(.+)\.appsync-api\.(.+)\/graphql$"
        regexReplace = r"wss://\1.appsync-realtime-api.\2/graphql"
        regexReplaceHost = r"\1.appsync-api.\2"
        wssUrl = re.sub(regex, regexReplace, endpoint)
        host = re.sub(regex, regexReplaceHost, endpoint)
        return { 'wssUrl': wssUrl, 'host': host}

    async def getWebsockUrlByEndpoint(self, endpoint) -> str:
        websockEndpoint = await self.getWebsocketEndpoint(endpoint)
        id_token = await self.getIdToken()
        headerPayload = {"Authorization":id_token,"host":websockEndpoint['host']}
        data_string = str(json.dumps(headerPayload, indent=4))
        encoded_header = base64.b64encode(data_string.encode())
        wssUrl = websockEndpoint['wssUrl']+ '?header='+ quote(encoded_header)+'&payload=e30='
        return wssUrl
