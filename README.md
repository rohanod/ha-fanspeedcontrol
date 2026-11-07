# Fan Speed Control

A native Home Assistant custom integration for fans controlled by incremental remote commands. Set up each fan as a device integration with a native remote picker and plain code fields. No YAML or action sequences are needed for setup.

Requires **Home Assistant 2026.11.0+**. Install as an **Integration** in the built-in Marketplace or HACS, not as a Python Script. This repository is a custom repository, not an official Core integration or a default Marketplace listing.

## Install

1. In Marketplace, accept its first-run warning and connect GitHub if prompted.
2. Add `rohanod/ha-fanspeedcontrol` as a custom repository, category **Integration**. Install the integration release containing `custom_components/fan_speed_control/`.
3. Restart Home Assistant, then **Settings → Devices & services → Add integration → Fan Speed Control**.
4. Choose the remote and paste the power-on, power-off, speed-up, speed-down, and optional oscillation codes. Save. The fan appears as its own device with a native fan entity.
5. Later, open **Fan Speed Control → Configure** to edit the saved codes. **Timing and speed behavior** is collapsed by default.

New setup defaults match the existing Bedroom Fan: `remote.bedroom`, ten speeds, the current five Broadlink `b64:` codes, 10% startup speed, one-second command/startup delays, and wrapping disabled. Existing entries show their saved values, including any custom codes; opening or saving the form sends no IR. Clear the optional oscillation field to remove oscillation control.

For a toggle-only power command, paste the same code in both power fields. Paste the full `b64:...` string or a learned command name. Each speed code must move the fan exactly one speed step.

Manual installation: copy `custom_components/fan_speed_control` into your HA configuration's `custom_components` folder, restart, and add it through the UI.

Existing entries created with custom action sequences continue to work. If a sequence cannot be represented by one remote and one command per action, Configure retains its native action editor instead of discarding it. These advanced entries may call scripts or other HA actions; use direct script calls so completion can be awaited, and never call the fan recursively from its own actions.

## Behavior

- Normal `fan.turn_on`, `fan.turn_off`, `fan.set_percentage`, scenes, and oscillation services.
- Requests serialize per fan, including power, speed, oscillation, and synchronization.
- Percentage 0 is off. Nonzero percentages map to the nearest discrete speed, preserving the legacy script's rounding. Example: ten speeds, 10% → 50% sends four increases.
- Startup uses the configured power-on speed and waits before adjusting. Set this to the fan's actual startup behavior; IR cannot detect a remembered physical speed.
- Repeated presses wait `command_delay` seconds between them. Wrapping is disabled by default; enable each direction only if your fan supports it.
- State restores on restart without sending commands. No polling or external speed/power helpers required.
- Edit codes through the entry's **Configure** button without replacing its entity identity.

IR is one-way: state is an estimate. Missed commands, the physical remote, and power loss can cause drift. An action error invalidates the affected estimate instead of claiming the requested target. Inspect the physical fan, then use **Tools → Actions → Fan Speed Control: Synchronize state** with its actual percentage (`0` for off) and oscillation. Synchronization sends no IR. Verify the fan is off and synchronize to 0 before first use with toggle-only power.

Oscillation is likewise estimated. Configure actions that set the desired state using `oscillating`, or a single toggle command if the physical oscillation state is known. Synchronize after using the physical remote.

## Migrate from the Python Script

See [migration guide](docs/migration.md). The old script and [legacy YAML example](examples/configuration.yaml) remain available for rollback; they are not used by the integration. Do not run two controllers for the same physical fan.

## Tests and cloud setup

Home Assistant 2026.11 provides the official [`pytest-homeassistant`](https://github.com/home-assistant/core/tree/2026.11.0/packages/pytest-homeassistant) package. It creates a real test Home Assistant instance and supplies config-entry, service, registry, time, and restore-state fixtures. It replaces `pytest-homeassistant-custom-component`; do not install both.

With `uv` available, run locally or in a Codex Cloud checkout:

```sh
bash scripts/setup-test-env.sh
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
```

The setup script provisions Python 3.14, installs exact Home Assistant and official pytest package version **2026.11.0**, and runs tests. Cloud setup needs package-index/Python-download network access. Tests mock the transmitter at the service boundary; they exercise the real config flow, fan service dispatch, action engine, restoration, concurrency, failure handling, and unloading. They do not transmit IR or prove physical reception.

GitHub Actions runs the same tests on Linux, plus official `hassfest` and HACS integration validation. A custom integration's brand assets/default listing require separate upstream submissions; those are not implied by successful code tests.

## Legacy

The previous installation used `python_script.fan_speed_control`, a template fan, and helpers. Keep their backups until migration is verified. Leave `python_script:` enabled if anything else still uses it.
