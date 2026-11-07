# Fan Speed Control

A native Home Assistant custom integration for fans controlled by incremental remote commands. Configure one fan per entry using the UI action editor; Broadlink `remote.send_command`, scripts, and other Home Assistant actions work without extra runtime dependencies.

Requires **Home Assistant 2026.11.0+**. Install as an **Integration** in the built-in Marketplace or HACS, not as a Python Script. This repository is a custom repository, not an official Core integration or a default Marketplace listing.

## Install

1. In Marketplace, accept its first-run warning and connect GitHub if prompted.
2. Add `rohanod/ha-fanspeedcontrol` as a custom repository, category **Integration**. Install the integration release containing `custom_components/fan_speed_control/`.
3. Restart Home Assistant, then **Settings → Devices & services → Add integration → Fan Speed Control**.
4. Enter the fan's name, speed count, startup speed, delays, and four action sequences: power on, power off, increase one step, decrease one step. Optional oscillation actions receive the boolean template variable `oscillating`.

Manual installation: copy `custom_components/fan_speed_control` into your HA configuration's `custom_components` folder, restart, and add it through the UI.

Each speed action must send exactly **one** press. Use unconditional transmitter actions, with errors propagated. Do not call this fan entity from its own actions; that would recurse. If using an existing script, call `script.<script_name>` directly so HA waits for completion; `script.turn_on` is fire-and-forget and cannot confirm completion.

For Broadlink, choose `remote.send_command`, target your remote, and enter the learned command (or `b64:...`). The power-on and power-off sequences may use the same IR toggle command: this integration sends it only on a tracked power transition.

## Behavior

- Normal `fan.turn_on`, `fan.turn_off`, `fan.set_percentage`, scenes, and oscillation services.
- Requests serialize per fan, including power, speed, oscillation, and synchronization.
- Percentage 0 is off. Nonzero percentages map to the nearest discrete speed, preserving the legacy script's rounding. Example: ten speeds, 10% → 50% sends four increases.
- Startup uses the configured power-on speed and waits before adjusting. Set this to the fan's actual startup behavior; IR cannot detect a remembered physical speed.
- Repeated presses wait `command_delay` seconds between them. Wrapping is disabled by default; enable each direction only if your fan supports it.
- State restores on restart without sending commands. No polling or external speed/power helpers required.
- Reconfigure commands through the entry's **Reconfigure** menu without replacing its entity identity.

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
