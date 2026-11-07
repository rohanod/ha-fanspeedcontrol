# Migration and rollback

## Map before changing

Old readers: dashboards, scenes, automations, and scripts use the template fan's entity ID. Some configurations also read or write its power, speed, and oscillation helpers. Old writers: template fan actions and `python_script.fan_speed_control`; direct IR/calibration scripts can independently move the physical fan.

New owner: one UI config entry owns a native fan's estimated power, discrete speed, and oscillation. State uses HA's restore-state mechanism; commands are native action sequences. External helpers are not automatically synchronized. No raw `.storage` migration or editing is needed.

Before cutover, search every consumer of the old fan ID and helper IDs, including all dashboards and config-entry helper options. Keep the original entity ID to minimize changes. Scripts directly editing helpers need conversion to fan services or `fan_speed_control.sync_state`. Stop in-flight ventilation/timer scripts before the cutover so they cannot command a half-migrated entity.

## Expand, then migrate

1. Save the original fan YAML and referenced script/dashboard configs. Keep the legacy Python script. If a package contains other settings, preserve those settings.
2. Install the native integration files using Marketplace/HACS as category **Integration**, or copy its component folder manually. Leave the old template fan active until installation has succeeded. Restart HA if required.
3. Prepare configuration using the existing transmitter actions. Copy only the power transmission commands into power actions, not their old helper conditions/updates. Copy `service_data_increase` and `service_data_decrease` into corresponding service actions. Copy oscillation transmission actions without the old helper update. Copy speed count, delays, startup assumption, and wrap flags.
4. Create the new integration entry but do not operate it while the old controller remains active. HA may assign it `fan.bedroom_fan_2` because the old ID is occupied.
5. Remove only the old template fan definition from its YAML package (keep a recoverable copy), validate configuration, then reload template entities. Preserve other templates and helpers. Do not delete the original entity registry entry: rename it to `fan.bedroom_fan_legacy`, then rename the native entity to `fan.bedroom_fan`. This leaves a reversible registry path without rewriting consumers.
6. Physically verify the fan's state. Call `fan_speed_control.sync_state` on the new fan with the actual percentage (0 when off) and oscillation. This sends no IR and seeds the estimate before control begins.
7. Verify identity, expected supported features, power, 10% → 50% → 20%, oscillation, and a scene that turns an off fan on at a requested percentage. Check physical response; software success cannot prove IR reception. Reload/restart and check restoration without unexpected commands.
8. Re-search consumers. Every existing fan consumer should still target the native fan. Review direct helper writers and direct remote/calibration scripts separately; they bypass state tracking. Prefer `sync_state` after any physical calibration.

Do not remove old helpers, the legacy registry entry, or the Python script during this transition. Remove them later only after confirming no remaining consumers. Never enable both controllers against the same physical fan.

## Rollback

Disable the new config entry. Rename the native entity away from the original ID, rename the legacy registry entry back, restore the original template fan YAML, validate, and reload templates. Restore any explicitly changed consumers from their saved configs. Set the original helpers to the physically verified state before using the template fan again. No full HA backup restore is needed for this scoped rollback.

## Bedroom fan inspection — 7 November 2026

The connected instance runs Core and Marketplace **2026.11.0**. The old fan is `fan.bedroom_fan`, template unique ID `bedroom_fan`, defined in `packages/ir_fan.yaml`. It has ten speeds, `remote.bedroom`, a shared power toggle, and an oscillation toggle. Its legacy helpers are `input_boolean.status_fan_power`, `input_number.status_fan_speed`, and `input_select.fan_osc`.

The same package contains `input_select.transport_lcd_mode`; retain it. Search found fan references in four scripts and one card on `dashboard-devices`. The calibration script sends IR directly after setting speed, so it bypasses estimates; review it before reuse. Search coverage is limited to accessible HA configuration, not external systems such as Node-RED.

Local, ignored `.migration/` contains the original fan package, proposed replacement package retaining all helpers and the transport selector, and native entry configuration using the existing IR codes. These are preparation artifacts; their presence does not mean anything has been deployed.

Marketplace reported its first-run warning unaccepted during inspection. Installation must wait for the user to accept it. The new integration source also needs publishing to an installable repository revision before Marketplace can download it.
