# arcade.stanley.arpa adapter

Registers this CS2 server with the [homelab-arcade](https://github.com/jakestanley/homelab-arcade)
control portal so it can be started/stopped from `arcade.stanley.arpa` alongside other game
servers.

Runs as its own `docker-compose` service (`arcade-adapter`, see `../docker-compose.yml`), built
and deployed entirely by CI (see the top-level `README.md` — there is no `./scripts/up.sh` here).
The adapter talks to the Docker Engine API directly over the mounted Docker socket (`docker`
Python SDK, no CLI needed) to control the sibling `cs2` container — it does not shell out to
`docker compose` and doesn't need the compose plugin installed.

`adapter.py` here is just this repo's own config (server id, adapter port, compose project/
service) — the actual HTTP server, Docker control, heartbeat loop, and UPnP logic live in
[`lib-arcade`](https://github.com/jakestanley/lib-arcade), installed as a git dependency
tracking its `main` branch (see `requirements.txt`).

## Contract

Implements the standard arcade adapter contract — see homelab-arcade's
`docs/ARCADE_CONTRACT.md` for the full spec. Summary:

- `GET /arcade/info` → `{id, name, description, actions, status, update_available}`
- `POST /arcade/actions/start` / `POST /arcade/actions/stop` → starts/stops the sibling
  `cs2` container directly (identified by its `com.docker.compose.project`/`.service`
  labels, not a hardcoded container name)
- `POST /arcade/actions/update` → recreates the `cs2` container onto whatever
  `joedwards32/cs2` image is currently pulled locally (see Gotchas below)
- Registers itself with `POST {ARCADE_BASE_URL}/api/register` every
  `ARCADE_HEARTBEAT_SECONDS` (default 30s)

## Config

Unlike `arcade-palworld`/`arcade-minecraft`, there's no `.env` file — nothing on this
host is meant to hold config for this repo. Non-secret adapter settings (server id/name,
`ARCADE_ADAPTER_PORT=8302`, compose project/service, `ARCADE_FORWARD_PROTOCOL=udp,tcp`) are
literal values directly in `../docker-compose.yml`; change them the normal way, by editing
and pushing. The two real secrets (`SRCDS_TOKEN`, `CS2_RCONPW`) come from Woodpecker's own
secret store, not from here — see the top-level `README.md`.

## Gotchas

- Uses `container.stop()`, not removing it — the container and its named volume are left in
  place. `start()` on an already-running container is a no-op.
- The adapter container has the host Docker socket mounted in — this is root-equivalent host
  access, scoped to this one container only. Standard pattern for control agents (Portainer,
  Watchtower use the same approach), but worth knowing.
- This adapter is **unauthenticated** — it trusts the homelab LAN/VPN, same trust model as
  RCON. Do not expose `ARCADE_ADAPTER_PORT` outside the LAN.
- Runs with `network_mode: host` — required for UPnP router discovery (SSDP multicast), which
  doesn't reliably work across Docker's default bridge network.
- CS2 needs both UDP and TCP forwarded on the same port, unlike the other two arcade adapters
  which only need one — `ARCADE_FORWARD_PROTOCOL=udp,tcp` opens/closes mappings for both. A
  UPnP failure on either protocol is logged as a warning and never blocks the start/stop action
  itself. The mapping is re-asserted once per heartbeat while running, so a router-side lease
  expiry or reboot self-heals within one heartbeat interval, and once on adapter boot so a
  redeploy while the game server is already running converges to the correct forwarding state
  immediately.
- **Image updates are CS2-mandatory, not optional**: the actual dedicated-server files live
  inside `joedwards32/cs2:latest` itself (unlike e.g. Palworld, which fetches its game files
  separately at container boot regardless of image vintage) -- there's no way to run a current
  CS2 version without a current image, and Valve's own client updates aren't opt-out. CI no
  longer touches this at all (see `.woodpecker/refresh.yaml`'s history) -- `update_available`
  is checked automatically by lib-arcade every `ARCADE_UPDATE_CHECK_SECONDS` (default 1800s),
  but applying it is only ever triggered by an explicit `update` action from the portal, never
  automatically, so a bad update is caught immediately by whoever clicked it. Since this
  process has no `docker-compose.yml` of its own (see above), `update` recreates the container
  via the Docker SDK by copying its own existing resolved config (env/labels/host_config)
  rather than shelling out to `docker compose up -d` -- the same technique Watchtower uses.
  Preserves whatever run state `cs2` was already in, same rule as `stop`: an already-stopped
  server stays stopped after updating rather than being started as a side effect.
