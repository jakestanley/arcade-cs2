# Roadmap

Forward-looking only. Already shipped: the `restart_round` action (RCON,
via `lib-arcade`'s pluggable `extra_actions`), Wingman on `de_nuke`.

## Casual/competitive economy preset

The first real parameterized action for this server, once the underlying
portal/contract support lands (see `homelab-arcade/ROADMAP.md`) — apply via
RCON, the same live-`changelevel`-style path already proven for map
switching this repo already uses for `restart_round`.

## Active-session monitoring + team balance

For long sessions where auto-balance falls short: a live per-player/
per-team roster in the portal's detail view, plus a manual team-balance
action (force scramble/swap) via RCON. CS2-specific — not planned for the
other adapters unless it turns out useful there too.
