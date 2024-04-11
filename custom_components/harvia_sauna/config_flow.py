import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from .api import HarviaSaunaAPI
from .constants import DOMAIN  # Zorg ervoor dat je een const.py hebt met je DOMAIN

class HarviaSaunaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for your_component."""

    VERSION = 1  # De versie van je config flow
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        # Controleer of we al een configuratie hebben
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # Verwerk ingevulde gegevens
        if user_input is not None:
            # Hier zou je de inloggegevens valideren
            api =  HarviaSaunaAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD],self.hass)
            valid = await api.authenticate()
            if valid:
                return self.async_create_entry(title="Harvia Sauna", data=user_input)
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return HarviaSaunaOptionsFlowHandler(config_entry)

class HarviaSaunaOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Beheer de opties."""
        errors = {}

        if user_input is not None:
            # Hier zou je de inloggegevens valideren
            api =  HarviaSaunaAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD],self.hass)
            valid = await api.authenticate(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            if valid:
                return self.async_create_entry(title="Harvia Sauna", data=user_input)
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=self.config_entry.data.get(CONF_USERNAME)): str,
                vol.Required(CONF_PASSWORD, default=self.config_entry.data.get(CONF_PASSWORD)): str,
            }),
            errors=errors
        )