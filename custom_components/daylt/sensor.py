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
    """Set up the DayLt sensor platform."""
    name = config.get(CONF_NAME)
    async_add_entities([DayLtSensor(hass, name)], True)

class DayLtSensor(Entity):
    """Representation of the DayLt sensor."""

    def __init__(self, hass, name):
        """Initialize the sensor."""
        self._name = name
        self._state = None
        self._attributes = {}
        self._last_update_date = None
        self._hass = hass

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return self._attributes

    async def async_update(self):
        """Fetch new data for the sensor."""
        try:
            if self._last_update_date == datetime.now().date():
                return  # No need to update

            session = async_get_clientsession(self._hass)
            async with async_timeout.timeout(10):
                response = await session.get('https://day.lt', headers={
                    'User-Agent': 'Mozilla/5.0 (HomeAssistant Integration)'
                })
                response.raise_for_status()
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')
            self._parse_data(soup)
            self._state = "OK"
            self._last_update_date = datetime.now().date()

        except Exception as e:
            _LOGGER.error("Error fetching data: %s", e, exc_info=True)
            self._state = "Error"

    def _parse_data(self, soup):
        """Parse the HTML data and update attributes."""
        # Extract zodiac data
        zodiac, zodiac_icon = self._extract_zodiac(soup)
        self._attributes['zodiakas'] = zodiac
        self._attributes['zodiakas_icon'] = zodiac_icon
        
        # Extract chinese zodiac data
        chinese_zodiac, chinese_zodiac_icon = self._extract_chinese_zodiac(soup)
        self._attributes['kinu_zodiakas'] = chinese_zodiac
        self._attributes['kinu_zodiakas_icon'] = chinese_zodiac_icon
        
        # Extract vardadieniai and sventes
        special_days = self._extract_special_days(soup)
        self._attributes['vardadieniai'] = special_days['vardadieniai']
        self._attributes['sventes'] = special_days['sventes']

        self._attributes['is_red_day'] = self._extract_is_red_day(soup)
        self._attributes['savaites_diena'] = self._extract_weekday(soup)
        self._attributes['patarle'] = self._extract_proverb(soup)
        # Extract Solar and Moon data
        self._attributes.update(self._extract_solar_data(soup))
        self._attributes.update(self._extract_moon_data(soup))

    def _extract_is_red_day(self, soup):
        """Determine if today is a red day."""
        try:
            day_number = soup.find('p', class_='text-9xl font-bold')
            weekday = soup.find('span', title='Savaitės diena')
            holidays = soup.find('div', class_='text-center text-xl mb-4')

            if day_number and 'style' in day_number.attrs and 'color: red' in day_number['style']:
                return True
            if weekday and weekday.find('a') and 'style' in weekday.find('a').attrs and 'color: red' in weekday.find('a')['style']:
                return True
            if holidays and holidays.find_all('a', style=lambda value: value and 'color: red' in value):
                return True
        except Exception:
            pass
        return False

    def _extract_solar_data(self, soup):
        """Extract solar data (sunrise, sunset, day length)."""
        solar_data = soup.find('div', class_='sun-data')
        if solar_data:
            items = solar_data.find_all('li')
            if len(items) >= 3:
                return {
                    'saule_teka': self._clean_text(items[0].text.replace('teka', '')),
                    'saule_leidziasi': self._clean_text(items[1].text.replace('leidžiasi', '')),
                    'dienos_ilgumas': self._clean_text(items[2].text.replace('ilgumas', ''))
                }
        return {'saule_teka': "Nerasta", 'saule_leidziasi': "Nerasta", 'dienos_ilgumas': "Nerasta"}

    def _extract_moon_data(self, soup):
        """Extract moon phase and day."""
        moon_data = soup.find('div', class_='moon-data')
        if moon_data:
            items = moon_data.find_all('li')
            if len(items) >= 2:
                return {
                    'menulio_faze': self._clean_text(items[0].text),
                    'menulio_diena': self._clean_text(items[1].text)
                }
        return {'menulio_faze': "Nerasta", 'menulio_diena': "Nerasta"}

    def _extract_special_days(self, soup):
        """Extract vardadieniai (name days) and sventes (holidays)."""
        vardadieniai = "Nerasta"
        sventes = "Nerasta"

        try:
            # Extract vardadieniai (name days)
            vardadieniai_div = soup.find('p', class_='vardadieniai')
            if vardadieniai_div:
                vardadieniai_list = [self._clean_text(a.text) for a in vardadieniai_div.find_all('a')]
                vardadieniai = ', '.join(vardadieniai_list) if vardadieniai_list else "Nerasta"

            # Extract sventes (holidays)
            sventes = []
            sventes_div = soup.find('div', class_='text-center text-xl mb-4')
            if sventes_div:
                sventes_links = sventes_div.find_all('a')
                for link in sventes_links:
                    svente_name = link.get_text(strip=True)  # Extract holiday name
                    sventes.append(svente_name)
            # Convert list of holidays to string or set as 'Nerasta'
            sventes = ', '.join(sventes) if sventes else ""

        except Exception as e:
            _LOGGER.warning("Error parsing special days: %s", e)

        return {'vardadieniai': vardadieniai, 'sventes': sventes}

    def _extract_weekday(self, soup):
        """Extract the day of the week."""
        try:
            weekday = soup.find('p', class_='text-3xl font-semibold mt-2')
            if not weekday:
                weekday = soup.find('span', title='Savaitės diena')
            if weekday and weekday.find('a'):
                return self._clean_text(weekday.find('a').text)
        except Exception as e:
            _LOGGER.warning("Error parsing weekday: %s", e)
        return "Nerasta"

    def _extract_proverb(self, soup):
        """Extract the proverb."""
        try:
            proverb = soup.find('p', title='Patarlė')
            if not proverb:
                proverb = soup.find('div', class_='text-center text-sm mb-10').find('p')
            if proverb:
                return self._clean_text(proverb.text)
        except Exception as e:
            _LOGGER.warning("Error parsing proverb: %s", e)
        return "Nerasta"

    def _extract_zodiac(self, soup):
        """Extract Western zodiac sign and icon."""
        try:
            zodiac = soup.find('div', class_='flex-1 flex items-center')
            if zodiac:
                zodiac_text = zodiac.find('span').text if zodiac.find('span') else "Nerasta"
                zodiac_img = zodiac.find('img')['src'] if zodiac.find('img') and 'src' in zodiac.find('img').attrs else None
                zodiac_icon = f"https://day.lt/{zodiac_img}" if zodiac_img else "Nerasta"
                return zodiac_text, zodiac_icon
        except Exception as e:
            _LOGGER.warning("Error parsing zodiac: %s", e)
        return "Nerasta", "Nerasta"

    def _extract_chinese_zodiac(self, soup):
        """Extract Chinese zodiac sign and icon."""
        try:
            chinese_zodiac = soup.find('div', class_='flex-1 flex items-center justify-center')
            if chinese_zodiac:
                chinese_zodiac_text = chinese_zodiac.find('span').text if chinese_zodiac.find('span') else "Nerasta"
                chinese_zodiac_img = chinese_zodiac.find('img')['src'] if chinese_zodiac.find('img') and 'src' in chinese_zodiac.find('img').attrs else None
                chinese_zodiac_icon = f"https://day.lt/{chinese_zodiac_img}" if chinese_zodiac_img else "Nerasta"
                return chinese_zodiac_text, chinese_zodiac_icon
        except Exception as e:
            _LOGGER.warning("Error parsing Chinese zodiac: %s", e)
        return "Nerasta", "Nerasta"

    def _clean_text(self, text):
        """Clean and normalize text."""
        return text.strip() if text else "Nerasta"
