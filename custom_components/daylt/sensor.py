import logging
from datetime import timedelta, datetime
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import async_timeout
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_NAME = "Day LT Info"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    async_add_entities([DayLtSensor(hass, name)], True)

class DayLtSensor(Entity):
    def __init__(self, hass, name):
        self._name = name
        self._state = None
        self._attributes = {}
        self._last_update_date = None
        self._hass = hass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        now = datetime.now()
        current_date = now.date()

        # Tikriname ar reikia atnaujinti - tik kartą per dieną
        if self._last_update_date != current_date:
            try:
                session = async_get_clientsession(self._hass)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                async with async_timeout.timeout(10):
                    async with session.get('https://day.lt', headers=headers) as response:
                        if response.status != 200:
                            _LOGGER.error(f"Svetainė neatsakė: {response.status}")
                            self._state = "Error"
                            return
                        
                        html = await response.text(encoding='ISO-8859-13')

                soup = BeautifulSoup(html, 'html.parser')
                
                # Vardadieniai
                vardadieniai_div = soup.find('p', class_='vardadieniai')
                if vardadieniai_div:
                    vardadieniai = [a.text for a in vardadieniai_div.find_all('a')]
                    self._attributes['vardadieniai'] = ', '.join(vardadieniai)
                else:
                    self._attributes['vardadieniai'] = "Nerasta"

                # Saulės informacija
                saule_info = soup.find('div', class_='sun-data')
                if saule_info:
                    saule_items = saule_info.find_all('li')
                    if len(saule_items) >= 3:
                        teka = saule_items[0].text.replace('teka', '').strip()
                        leidziasi = saule_items[1].text.replace('leidžiasi', '').strip()
                        ilgumas = saule_items[2].text.replace('ilgumas', '').strip()
                        
                        self._attributes['saule_teka'] = teka
                        self._attributes['saule_leidziasi'] = leidziasi
                        self._attributes['dienos_ilgumas'] = ilgumas
                else:
                    self._attributes['saule_teka'] = "Nerasta"
                    self._attributes['saule_leidziasi'] = "Nerasta"
                    self._attributes['dienos_ilgumas'] = "Nerasta"

                # Savaitės diena
                savaites_diena = soup.find('span', title='Savaitės diena')
                if savaites_diena and savaites_diena.find('a'):
                    self._attributes['savaites_diena'] = savaites_diena.find('a').text.strip()
                else:
                    self._attributes['savaites_diena'] = "Nerasta"

                # Šventės
                sventes = []
                # Ieškome švenčių div'o
                sventes_div = soup.find('div', class_='text-center text-xl mb-4')
                if sventes_div:
                    # Ieškome visų span elementų su title="Šios dienos šventė"
                    for span in sventes_div.find_all('span', title='Šios dienos šventė'):
                        svente = span.text.replace('<small></small>', '').strip()
                        if svente:
                            sventes.append(svente)

                # Pašaliname dublikatus ir tuščias reikšmes
                sventes = list(set([s for s in sventes if s]))

                if sventes:
                    self._attributes['sventes'] = ', '.join(sventes)
                else:
                    self._attributes['sventes'] = "Nėra švenčių"

                # Patarlė
                patarle = soup.find('p', title='Patarlė')
                if patarle:
                    self._attributes['patarle'] = patarle.text.strip()
                else:
                    self._attributes['patarle'] = "Nerasta"

                # Mėnulio informacija
                menulio_info = soup.find('div', class_='moon-data')
                if menulio_info:
                    menulio_items = menulio_info.find_all('li')
                    if len(menulio_items) >= 2:
                        self._attributes['menulio_faze'] = menulio_items[0].text.strip()
                        self._attributes['menulio_diena'] = menulio_items[1].text.strip()
                else:
                    self._attributes['menulio_faze'] = "Nerasta"
                    self._attributes['menulio_diena'] = "Nerasta"

                self._state = "OK"
                self._last_update_date = current_date
                
            except Exception as error:
                _LOGGER.error(f"Klaida gaunant duomenis: {error}")
                self._state = "Error"
