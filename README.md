# Harvia Sauna

Home Assistant component for Harvia Sauna (working with Xenio Wifi), using the same API as the MyHarvia App.


## WARNING: Pre-alpha development release

*This component is still in 'pre-alpha' and can exhibit unpredictable behavior. I am happy that I have already achieved this result. Still, I would appreciate you installing the component so that I can gather information and feedback to improve the component. After all, I only have one sauna and without extensive testing it won't get better.  Keep an eye on this page.* 

(updated at April 4, 2024)

Component is in development and currently only publishes:

- Sauna light switch
- Sauna power switch (enables heater)
- Sauna termostat (current and target temp)


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

## Limitations

- You dont't get any message when the door of your sauna is open and you can't start the heater. 

## Known issues

- Connection interruption ensures that no new sauna updates are received as no 'reconnect' mechanism has yet been created for web sockets. You need to restart HA in order to reset the component.

## Road map (short term)

For version 0.0.6: 

- Creating reconnection machanism
- Door sensor detection and feedback
- Expanding sensors

<!-- ## Contribute

Please do! Open a Pull Request with your improvements. -->
