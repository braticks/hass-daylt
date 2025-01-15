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
- Zodiakas
- Zodiako ikonėlė
- Kinų zodiakas
- Kinų zodiako ikonėlė
- Nedarbo diena

Home Assistant atributai:

    "Attributes":{
       "zodiakas":"Ožiaragis",
       "zodiakas_icon":"https://day.lt/v2/images/zodiakas/oziaragis.svg",
       "kinu_zodiakas":"Gyvatė",
       "kinu_zodiakas_icon":"https://day.lt/v2/images/zodiakas/kinu/gyvate.svg",
       "vardadieniai":"Mečislovas, Arvaidas, Arvaidė, Eufrozija, Mečys, Eufrozina",
       "sventes":"Naujieji metai, Lietuvos vėliavos diena",
       "is_red_day":true,
       "savaites_diena":"TREČIADIENIS",
       "patarle":"Tyla - gera byla",
       "saule_teka":"08:42",
       "saule_leidziasi":"16:02",
       "dienos_ilgumas":"07.20",
       "menulio_faze":"Jaunatis",
       "menulio_diena":"2 mėnulio diena"
    }

Neradus einamos dienos atributo, numatytoji reikšmė - "Nerasta"

    "Attributes":{
       ...
       "sventes":"Nerasta",
       ...
    }


## Diegimas

1. Pridėkite šią repozitoriją https://github.com/braticks/hass-daylt į HACS kaip "Custom Repository"
2. Įdiekite "Day LT" integraciją per HACS
3. Pridėkite į `configuration.yaml`: yaml

        sensor:
        platform: daylt
        name: daylt_info # optional

4. Perkraukite Home Assistant
