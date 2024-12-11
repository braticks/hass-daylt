import logging
import requests
from bs4 import BeautifulSoup
from datetime import timedelta, datetime
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(days=1)
DEFAULT_NAME = "Day LT Info"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    add_entities([DayLtSensor(name)], True)

class DayLtSensor(Entity):
    def __init__(self, name):
        self._name = name
        self._state = None
        self._attributes = {}
        self._last_update = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    def should_update(self):
        """Patikrina ar reikia atnaujinti duomenis"""
        now = datetime.now()
        if (self._last_update is None or 
            self._last_update.date() < now.date()):
            return True
        return False

    def update(self):
        if not self.should_update():
            return

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get('https://day.lt', headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            self._state = "OK"
            self._attributes['vardadieniai'] = soup.find('div', {'class': 'vardadieniai'}).text.strip() if soup.find('div', {'class': 'vardadieniai'}) else "Nerasta"
            self._attributes['saule_teka'] = soup.find('div', {'class': 'saule-teka'}).text.strip() if soup.find('div', {'class': 'saule-teka'}) else "Nerasta"
            self._attributes['saule_leidziasi'] = soup.find('div', {'class': 'saule-leidziasi'}).text.strip() if soup.find('div', {'class': 'saule-leidziasi'}) else "Nerasta"
            
            self._last_update = datetime.now()
            
        except Exception as error:
            _LOGGER.error(f"Nepavyko gauti duomenų: {error}")
            self._state = "Error"
