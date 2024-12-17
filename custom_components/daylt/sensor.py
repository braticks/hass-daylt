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
        # Selektorių sąrašas skirtingiems elementams
        self._selectors = {
            'vardadieniai': [
                ('p', {'class_': 'vardadieniai'}),
                ('div', {'class_': 'names'}),
            ],
            'savaites_diena': [
                ('span', {'title': 'Savaitės diena'}),
                ('p', {'class_': 'weekday'}),
                ('div', {'class_': 'text-center'}, 'span', {'class_': 'font-bold'}),
            ],
            'patarle': [
                ('p', {'title': 'Patarlė'}),
                ('div', {'class_': 'proverb'}),
                ('div', {'class_': 'text-center text-sm mb-10'}, 'p'),
            ],
            'saule_info': [
                ('div', {'class_': 'sun-data'}),
                ('ul', {'class_': 'sun-info'}),
            ],
            'menulio_info': [
                ('div', {'class_': 'moon-data'}),
                ('ul', {'class_': 'moon-info'}),
            ],
            'sventes': [
                ('div', {'class_': 'text-center text-xl mb-4'}),
                ('div', {'class_': 'holidays'}),
            ]
        }

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def _find_element(self, soup, selector_list):
        """Bando rasti elementą naudojant skirtingus selektorius"""
        for selector in selector_list:
            try:
                if len(selector) == 2:
                    element = soup.find(selector[0], selector[1])
                elif len(selector) == 4:
                    parent = soup.find(selector[0], selector[1])
                    if parent:
                        element = parent.find(selector[2], selector[3])
                    else:
                        continue
                else:
                    continue

                if element:
                    return element
            except Exception as e:
                _LOGGER.debug(f"Klaida ieškant elemento su selektoriumi {selector}: {e}")
        return None

    async def _clean_text(self, text):
        """Išvalo tekstą nuo nereikalingų simbolių"""
        if text:
            return text.strip().encode('utf-8').decode('utf-8')
        return text

    async def async_update(self):
        now = datetime.now()
        current_date = now.date()

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
                        
                        html = await response.text(encoding='utf-8')

                soup = BeautifulSoup(html, 'html.parser')
                
                # Vardadieniai
                vardadieniai_el = await self._find_element(soup, self._selectors['vardadieniai'])
                if vardadieniai_el:
                    vardadieniai = [await self._clean_text(a.text) for a in vardadieniai_el.find_all('a')]
                    self._attributes['vardadieniai'] = ', '.join(vardadieniai)
                else:
                    _LOGGER.debug("Nepavyko rasti vardadienių")
                    self._attributes['vardadieniai'] = "Nerasta"

                # Saulės informacija
                saule_info = await self._find_element(soup, self._selectors['saule_info'])
                if saule_info:
                    saule_items = saule_info.find_all('li')
                    if len(saule_items) >= 3:
                        self._attributes['saule_teka'] = await self._clean_text(saule_items[0].text.replace('teka', ''))
                        self._attributes['saule_leidziasi'] = await self._clean_text(saule_items[1].text.replace('leidžiasi', ''))
                        self._attributes['dienos_ilgumas'] = await self._clean_text(saule_items[2].text.replace('ilgumas', ''))
                else:
                    _LOGGER.debug("Nepavyko rasti saulės informacijos")
                    self._attributes['saule_teka'] = "Nerasta"
                    self._attributes['saule_leidziasi'] = "Nerasta"
                    self._attributes['dienos_ilgumas'] = "Nerasta"

                # Savaitės diena
                savaites_diena_el = await self._find_element(soup, self._selectors['savaites_diena'])
                if savaites_diena_el:
                    diena_text = savaites_diena_el.find('a').text if savaites_diena_el.find('a') else savaites_diena_el.text
                    self._attributes['savaites_diena'] = await self._clean_text(diena_text)
                else:
                    _LOGGER.debug("Nepavyko rasti savaitės dienos")
                    self._attributes['savaites_diena'] = "Nerasta"

                # Patarlė
                patarle_el = await self._find_element(soup, self._selectors['patarle'])
                if patarle_el:
                    self._attributes['patarle'] = await self._clean_text(patarle_el.text)
                else:
                    _LOGGER.debug("Nepavyko rasti patarlės")
                    self._attributes['patarle'] = "Nerasta"

                # Mėnulio informacija
                menulio_info = await self._find_element(soup, self._selectors['menulio_info'])
                if menulio_info:
                    menulio_items = menulio_info.find_all('li')
                    if len(menulio_items) >= 2:
                        self._attributes['menulio_faze'] = await self._clean_text(menulio_items[0].text)
                        self._attributes['menulio_diena'] = await self._clean_text(menulio_items[1].text)
                else:
                    _LOGGER.debug("Nepavyko rasti mėnulio informacijos")
                    self._attributes['menulio_faze'] = "Nerasta"
                    self._attributes['menulio_diena'] = "Nerasta"

                # Šventės
                sventes = []
                sventes_el = await self._find_element(soup, self._selectors['sventes'])
                if sventes_el:
                    for span in sventes_el.find_all('span', title='Šios dienos šventė'):
                        svente = await self._clean_text(span.text.replace('<small></small>', ''))
                        if svente:
                            sventes.append(svente)
                
                if sventes:
                    self._attributes['sventes'] = ', '.join(sventes)
                else:
                    self._attributes['sventes'] = "Nėra švenčių"

                self._state = "OK"
                self._last_update_date = current_date
                
            except Exception as error:
                _LOGGER.error(f"Klaida gaunant duomenis: {error}")
                self._state = "Error"
