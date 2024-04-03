# Harvia Sauna

Home Assistant component for Harva Sauna (working with Xenio Wifi), using the same API as the MyHarvia App.


## In development

Component is in development and currently only publishes:

- Sauna light switch
- Sauna power switch (enables heater)
- Sauna termostat (only target temp)

## Compatibility
Component has been tested with the Harvia Xenio Wifi (CX001WIFI) and Harvia Cilindro PC90XE, but may also work with other sauna's compatible with the MyHarvia app, as it uses the same API.

## Installation

Add a custom repository https://github.com/RubenHarms/ha-harvia-xenio-wifi.git/ to HACS and search for Harvia Sauna to install.

## Configuration

Add the following code to configuration.yaml

```yml
harvia_sauna:
  username: "your@username.com"
  password: !secret harvia_password

switch:
  - platform: harvia_sauna
climate:
  - platform: harvia_sauna
```

Add the following password to secrets.yml:

```yml
harvia_password: yourPassword
```

Your username and password is corresponding with the MyHarvia app.
Restart Homeassistant 

## Contribute

Please do! Open a Pull Request with your improvements.
