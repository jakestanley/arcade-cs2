# Roadmap

Forward-looking only. Already shipped: `restart_round`/`pause_match`/
`unpause_match`/`end_warmup`/`set_bot_quota`/`apply_preset`/`change_map`
actions, live `stats` (map/mode/players), and lib-arcade's first-party
`update`/`update_available` (checked automatically, applied only by an
explicit portal click — see `arcade/README.md`).

## Persistent host checkout instead of ephemeral CI clones

Every CI run (`ci.yaml`/`refresh.yaml`) currently clones fresh, builds, and
deploys straight from that throwaway clone — unlike `arcade-palworld`/
`arcade-minecraft`, which run from a real, persistent checkout via
`scripts/up.sh`. Bring this repo in line with that convention:

- Check it out once at the same path the sibling repos use
  (`/home/jake/git/github.com/jakestanley/arcade-cs2` — i.e. wherever it's
  actually cloned on the host).
- Add `scripts/up.sh` doing the same scoped `docker compose build`/
  `up -d arcade-adapter` this repo's CI already does — never touching
  `cs2` automatically, same reasoning as today (an unscoped `up -d`
  restarts a live game for no reason).
- Move `SRCDS_TOKEN`/`CS2_RCONPW` out of Woodpecker's secret store into a
  real `.env`/`.env.example`, matching the other two repos. Acceptable
  trade at this scale — single operator, not a shared secret store
  audited across a team.
- CI's job shrinks to `git fetch && git reset --hard origin/main &&
  ./scripts/up.sh` — reset-to-remote rather than a plain `git pull`,
  since an unattended checkout should never be able to hit a merge
  conflict. The 6-hourly refresh becomes a plain host cron calling the
  same script, sidestepping Woodpecker's cron-registration-by-name quirk
  entirely.

Net effect: full parity with the other two repos (`cd` in, read `.env`,
run `up.sh` by hand) without losing automatic deploy-on-push, and CI
becomes a thin trigger around one script instead of the only place the
deploy logic exists — which also makes a future move off Woodpecker a
non-event for this repo. Not a CI best-practices violation worth worrying
about at this scale: ephemeral/immutable build environments exist to
solve drift-across-many-machines and shared-checkout problems that don't
apply to a single-operator homelab host, and the sibling repos already
prove the pattern works fine here.

## Active-session monitoring + team balance

For long sessions where auto-balance falls short: a live per-player/
per-team roster in the portal's detail view, plus a manual team-balance
action (force scramble/swap) via RCON. CS2-specific — not planned for the
other adapters unless it turns out useful there too.
