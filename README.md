# HA-FanSpeedControl

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/dodoro)

A python script for Home Assistant that control fan speed with [Fan Template](https://www.home-assistant.io/integrations/fan.template/) and [Broadlink](https://www.home-assistant.io/integrations/broadlink/).

# Document

- [Documentation](https://github.com/rohanod/ha-fanspeedcontrol/blob/main/README.md)

# How it work

The script automatically call broadlink service when you set fan speed.

## Example

If your fan exposes 10 discrete speed steps, store the requested speed as a
percentage helper with values `0, 10, 20 ... 100`.

example1: call `increase` 4 times when you set fan speed from `10` to `50`.

example2: call `decrease` 3 times when you set fan speed from `50` to `20`.

example3: call `decrease` 2 times when you set fan speed from `20` to `100`.

# Installation

enable [python_script](https://www.home-assistant.io/integrations/python_script/) for your HomeAssistant.

- Add to `configuration.yaml`: `python_script:`
- Create folder `<config>/python_scripts`
- restart HomeAssistant

Find `Fan Speed Control` on HACS automation category.

Or you can copy the Python script in to your `<config>/python_scripts` directory.

# Script arguments

|key|required|type|description|
|-|-|-|-|
|fan_speed|true|string|target percentage from the fan entity (`0` turns off)|
|fan_speed_entity_id|true|string||
|fan_entity_id|true|string||
|fan_speed_count|true|integer||
|command_delay|false|float|seconds to wait between repeated commands, default `1.0`|
|startup_delay|false|float|seconds to wait after turning the fan on before adjusting speed, default `1.0`|
|power_on_percentage|false|integer|assumed startup speed after power on, default is the minimum speed step|
|wrap_increase|false|boolean|allow wraparound when increasing past the maximum speed, default `false`|
|wrap_decrease|false|boolean|allow wraparound when decreasing past the minimum speed, default `false`|
|service_domain|true|string||
|service|true|string||
|service_data_increase|true|object||
|service_data_decrease|true|object||

# Config Example

`set_percentage` on template fan

```yaml
set_percentage:
  - service: python_script.fan_speed_control
    data:
      fan_speed: "{{ percentage }}"
      fan_speed_entity_id: 'input_number.status_fan_speed'
      fan_entity_id: 'fan.bedroom_fan'
      fan_speed_count: 10
      command_delay: 1.0
      startup_delay: 1.0
      power_on_percentage: 10
      service_domain: 'remote'
      service: 'send_command'
      service_data_increase:
        entity_id: remote.broadlink
        device: fan
        command: increase
      service_data_decrease:
        entity_id: remote.broadlink
        device: fan
        command: decrease
```

## Template Fan config

Use the complete modern template fan example in [examples/configuration.yaml](/Users/rohan/HA-FanSpeedControl/examples/configuration.yaml).

# Debug

add logger to your `configuration.yaml`

```yaml
logger:
  default: warn
  logs:
    homeassistant.components.python_script.fan_speed_control.py: debug
```

## Sample configuration

See [examples/configuration.yaml](/Users/rohan/HA-FanSpeedControl/examples/configuration.yaml) for a complete modern template fan example using:

- `input_number.status_fan_speed` with `10..100` and `step: 10`
- `percentage: 0` only when the fan is actually off
- `speed_count: 10`
- `command_delay: 1.0` for slower repeated presses
- `startup_delay: 1.0` and `power_on_percentage: 10` for scene-safe power-on-to-target changes
- no wraparound by default, so `30 -> 100` increases seven steps instead of incorrectly decreasing to `10`
- Broadlink `b64:` commands

# Screenshot

![image](https://github.com/rohanod/ha-fanspeedcontrol/blob/main/Screenshot/fan.png?raw=true)

## Custom ui

![image](https://github.com/rohanod/ha-fanspeedcontrol/blob/main/Screenshot/fanui.png?raw=true)

# Todos

- [ ] Refactor arguments, like: remove not used argument `service`
- [ ] Find some way to get `entity.state` and `fan speed` not by arguments

<br><br>
<p align="center">
<br>
<a href="https://www.buymeacoffee.com/dodoro" target="_blank">
  <img src="https://github.com/appcraftstudio/buymeacoffee/raw/master/Images/snapshot-bmc-button.png" width="300">
</a>
</p>
