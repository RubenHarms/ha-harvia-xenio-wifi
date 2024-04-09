# Harvia Sauna integration for Home Assistant

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

Unofficial Home Assistant component for Harvia Sauna (working with Xenio Wifi), using the same API as the MyHarvia App.


## WARNING: Pre-alpha development release

*This component is still in 'pre-alpha' and can exhibit unpredictable behavior. I have tested the component for a few days now and it seems to be quite stable. I have now managed to run the component for a day without it breaking. I would appreciate it if you install the component so that I can gather information and feedback to improve the component. After all, I only have one sauna and without extensive testing it won't get better. Keep an eye on this page..* 

(updated at April 9, 2024)

Component is in development and currently only publishes:

- Sauna light switch
- Sauna power switch (enables heater)
- Sauna termostat (current and target temp)
- Sauna door sensor (safety circuit)


## Compatibility
Component has been tested with the Harvia Xenio Wifi (CX001WIFI) and Harvia Cilindro PC90XE, but may also work with other sauna's compatible with the MyHarvia app, as it uses the same API.

## Installation

Add a custom repository https://github.com/RubenHarms/ha-harvia-xenio-wifi.git/ to HACS and search for Harvia Sauna to install.
Restart Homeassistant 

## Configuration

Go to settings, integrations and add 'Harvia Sauna'
Your username and password is corresponding with the MyHarvia app.

<!-- ## Limitations

- You dont't get any message when the door of your sauna is open and you can't start the heater.  -->

<!--
## Known issues

- Connection interruption ensures that no new sauna updates are received as no 'reconnect' mechanism has yet been created for web sockets. You need to restart HA in order to reset the component. -->


## Road map (short term)

- Creating support for Fan
- Creating support for Steamer

Please do! Open a Pull Request with your improvements. -->


## Credits

This integration was developed by Ruben Harms. It uses the unofficial API of Harvia Xenio WiFi controllers and is not directly associated with Harvia.

[home-assistant-harvia-sauna]: https://github.com/RubenHarms/ha-harvia-xenio-wifi
[buymecoffee]: https://www.buymeacoffee.com/rubenharms
[buymecoffeebadge]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
