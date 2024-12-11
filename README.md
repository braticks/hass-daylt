# Day.lt sensor for Home Assistant

Sensorius, kuris rodo informaciją iš Day.lt svetainės.

## Įdiegimas per HACS

1. Eikite į HACS
2. Spauskite ant "Integrations"
3. Spauskite "..." viršutiniame dešiniajame kampe
4. Pasirinkite "Custom repositories"
5. Pridėkite šią repozitoriją:
   - URL: https://github.com/JUSERNAMEHERE/hass-daylt
   - Kategorija: Integration

## Konfigūracija

Pridėkite į configuration.yaml:

sensor:
platform: daylt
name: daylt_info
