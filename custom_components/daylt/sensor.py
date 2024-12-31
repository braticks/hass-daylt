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
                
                # Check for red day
                is_red_day = False

                # Check for red styling in day number
                day_number = soup.find('p', class_='text-9xl font-bold')
                if day_number and 'style' in day_number.attrs and 'color: red' in day_number['style']:
                    is_red_day = True

                # Check for red styling in weekday
                weekday = soup.find('span', title='Savaitės diena')
                if weekday and weekday.find('a') and 'style' in weekday.find('a').attrs and 'color: red' in weekday.find('a')['style']:
                    is_red_day = True

                # Check for red holidays
                sventes_div = soup.find('div', class_='text-center text-xl mb-4')
                if sventes_div:
                    red_holidays = sventes_div.find_all('a', style=lambda value: value and 'color: red' in value)
                    if red_holidays:
                        is_red_day = True

                self._attributes['is_red_day'] = is_red_day

                # Vardadieniai
                vardadieniai_div = soup.find('p', class_='vardadieniai')
                if vardadieniai_div:
                    vardadieniai = [await self._clean_text(a.text) for a in vardadieniai_div.find_all('a')]
                    self._attributes['vardadieniai'] = ', '.join(vardadieniai)
                else:
                    self._attributes['vardadieniai'] = "Nerasta"

                # Saulės informacija
                saule_info = soup.find('div', class_='sun-data')
                if saule_info:
                    saule_items = saule_info.find_all('li')
                    if len(saule_items) >= 3:
                        teka = await self._clean_text(saule_items[0].text.replace('teka', ''))
                        leidziasi = await self._clean_text(saule_items[1].text.replace('leidžiasi', ''))
                        ilgumas = await self._clean_text(saule_items[2].text.replace('ilgumas', ''))
                        
                        self._attributes['saule_teka'] = teka
                        self._attributes['saule_leidziasi'] = leidziasi
                        self._attributes['dienos_ilgumas'] = ilgumas
                else:
                    self._attributes['saule_teka'] = "Nerasta"
                    self._attributes['saule_leidziasi'] = "Nerasta"
                    self._attributes['dienos_ilgumas'] = "Nerasta"

                # Savaitės diena
                savaites_diena = soup.find('p', class_='text-3xl font-semibold mt-2')
                if not savaites_diena:
                    savaites_diena = soup.find('span', title='Savaitės diena')
                if savaites_diena and savaites_diena.find('a'):
                    self._attributes['savaites_diena'] = await self._clean_text(savaites_diena.find('a').text)
                else:
                    self._attributes['savaites_diena'] = "Nerasta"

                # Patarlė
                patarle = soup.find('p', title='Patarlė')
                if not patarle:
                    patarle = soup.find('div', class_='text-center text-sm mb-10').find('p')
                if patarle:
                    self._attributes['patarle'] = await self._clean_text(patarle.text)
                else:
                    self._attributes['patarle'] = "Nerasta"

                # Mėnulio informacija
                menulio_info = soup.find('div', class_='moon-data')
                if menulio_info:
                    menulio_items = menulio_info.find_all('li')
                    if len(menulio_items) >= 2:
                        self._attributes['menulio_faze'] = await self._clean_text(menulio_items[0].text)
                        self._attributes['menulio_diena'] = await self._clean_text(menulio_items[1].text)
                else:
                    self._attributes['menulio_faze'] = "Nerasta"
                    self._attributes['menulio_diena'] = "Nerasta"

                # Šventės
                sventes = []
                sventes_div = soup.find('div', class_='text-center text-xl mb-4')
                if sventes_div:
                    for span in sventes_div.find_all('span', title='Šios dienos šventė'):
                        svente = await self._clean_text(span.text.replace('<small></small>', ''))
                        if svente:
                            sventes.append(svente)

                if sventes:
                    self._attributes['sventes'] = ', '.join(sventes)
                else:
                    self._attributes['sventes'] = "Nėra švenčių"

                self._state = "OK"
                self._last_update_date = current_date
                
                # Zodiako ženklas ir ikona
                zodiakas = soup.find('div', class_='flex-1 flex items-center')
                if zodiakas and zodiakas.find('a'):
                    zodiakas_text = zodiakas.find('span').text
                    zodiakas_img = zodiakas.find('img')
                    self._attributes['zodiakas'] = await self._clean_text(zodiakas_text)
                    if zodiakas_img and 'src' in zodiakas_img.attrs:
                        self._attributes['zodiakas_icon'] = 'https://day.lt/' + zodiakas_img['src']
                else:
                    self._attributes['zodiakas'] = "Nerasta"
                    self._attributes['zodiakas_icon'] = "Nerasta"

                # Kinų zodiakas ir ikona
                kinu_zodiakas = soup.find('div', class_='flex-1 flex items-center justify-center')
                if kinu_zodiakas and kinu_zodiakas.find('a'):
                    kinu_zodiakas_text = kinu_zodiakas.find('span').text
                    kinu_zodiakas_img = kinu_zodiakas.find('img')
                    self._attributes['kinu_zodiakas'] = await self._clean_text(kinu_zodiakas_text)
                    if kinu_zodiakas_img and 'src' in kinu_zodiakas_img.attrs:
                        self._attributes['kinu_zodiakas_icon'] = 'https://day.lt/' + kinu_zodiakas_img['src']
                else:
                    self._attributes['kinu_zodiakas'] = "Nerasta"
                    self._attributes['kinu_zodiakas_icon'] = "Nerasta"

                self._state = "OK"
                self._last_update_date = current_date
                
            except Exception as error:
                _LOGGER.error(f"Klaida gaunant duomenis: {error}")
                self._state = "Error"
