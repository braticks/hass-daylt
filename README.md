# Day LT Sensor

Home Assistant sensorius rodantis informaciją iš day.lt svetainės.

## Funkcijos

Sensorius rodo:
- Vardadieniai
- Saulės tekėjimas
- Saulės leidimasis
- Dienos ilgumas
- Savaitės diena
- Šios dienos šventės
- Patarlė
- Mėnulio fazė
- Mėnulio diena

## Diegimas

1. Pridėkite šią repozitoriją https://github.com/braticks/hass-daylt į HACS kaip "Custom Repository"
2. Įdiekite "Day LT" integraciją per HACS
3. Pridėkite į `configuration.yaml`: yaml

            sensor:
            platform: daylt
            name: daylt_info # optional

4. Perkraukite Home Assistant
