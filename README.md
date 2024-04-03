# Harvia Sauna

Home Assistant component for Harva Sauna (working with Xenio Wifi), using the same API as the MyHarvia App.


## WARNING: Pre-alpha development release

*This component is still in 'pre-alpha' and can exhibit unpredictable behavior.  I am happy that I have already achieved this result.  The biggest bug fixes will be fixed in the coming days so it's mostly stable.  Keep an eye on this page.* 

(updated at April 3, 2024)

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

## Known issues

- Switches and climate entities stops working after one hour, due token expiry. Token renewal will be implementeren soon. Workaround: Restart HA.

## Contribute

Please do! Open a Pull Request with your improvements.
