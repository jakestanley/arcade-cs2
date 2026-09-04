# Roadmap

Forward-looking only. Already shipped: `restart_round`/`pause_match`/
`unpause_match`/`end_warmup`/`set_bot_quota`/`apply_preset`/`change_map`
actions, live `stats` (map/mode/players), and lib-arcade's first-party
`update`/`update_available` (checked automatically, applied only by an
explicit portal click — see `arcade/README.md`).

Whether this repo should move to a persistent host checkout (matching
`arcade-palworld`/`arcade-minecraft`) instead of its current
ephemeral-CI-clone deploy model — and whether CI belongs in this picture
at all — is an open question, not a committed item: see
`homelab-standards/OPEN_QUESTIONS.md`.

## Active-session monitoring + team balance

For long sessions where auto-balance falls short: a live per-player/
per-team roster in the portal's detail view, plus a manual team-balance
action (force scramble/swap) via RCON. CS2-specific — not planned for the
other adapters unless it turns out useful there too.
