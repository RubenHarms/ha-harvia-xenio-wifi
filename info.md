# Harvia Sauna Integration for Home Assistant

The Harvia Sauna integration, using the MyHarvia App, allows you to control and monitor Harvia Xenio WIFI sauna controllers through Home Assistant. This integration supports switching the sauna, the lights, and the fan on/off, setting the target temperature, monitoring the current state, and detecting if the sauna door is open or closed directly from the Home Assistant interface.

## Installation via HACS

1. **Add HACS**: Ensure [HACS](https://hacs.xyz/) is correctly installed in your Home Assistant setup.
2. **Add Repository**:
    - Navigate to HACS in the Home Assistant sidebar.
    - Select 'Integrations'.
    - Click the three dots in the top right corner and choose 'Custom repositories'.
    - Add this GitHub repository URL (`https://github.com/RubenHarms/ha-harvia-xenio-wifi`) and select 'Integration' as the category.
    - Click 'Add'.
3. **Install Integration**:
    - Search for 'Harvia Sauna' under the 'Integrations' tab in HACS.
    - Click 'Install' to add the integration to Home Assistant.

## Configuration

After installation via HACS, you need to add the integration to Home Assistant:

1. Go to 'Settings' > 'Devices & Services' > 'Integrations'.
2. Click 'Add Integration' and search for 'Harvia Sauna'.
3. Follow the on-screen instructions to add your Harvia Sauna device.
4. Enter your MyHarvia App credentials to authenticate the integration.

## Supported Features

The Harvia Sauna integration supports the following features:

- **Switch On/Off**: Turn your sauna on or off.
- **Light switch**: Turn your sauna lights on or off.
- **Fan switch**: Turn your sauna fan on or off.
- **Target Temperature**: Set your desired sauna temperature.
- **Monitoring**: View the current state, including whether the sauna is on or off, and the current temperature.
- **Door Sensor**: Detect if the sauna door is open or closed, enhancing safety and energy efficiency.

## Issues and Support

For issues, questions, or suggestions, please open an [issue](https://github.com/RubenHarms/ha-harvia-xenio-wifi/issues) on the GitHub repository. Contributions to the code or documentation are welcome through pull requests.

## Credits

This integration was developed by Ruben Harms. It uses the unofficial API of Harvia Xenio WiFi controllers and is not directly associated with Harvia.
