#!/usr/bin/env python3
"""arcade.stanley.arpa control adapter for arcade-cs2.

Thin wrapper around lib_arcade -- see that repo for the actual HTTP
server, Docker control, heartbeat loop, and UPnP port-forwarding logic.
This file only supplies this repo's own defaults.
"""

from __future__ import annotations

import os
import re

import rcon
from lib_arcade import AdapterConfig, run_adapter

config = AdapterConfig.from_env(
    default_server_id="arcade-cs2",
    default_server_name="CS2",
    default_server_description="CS2 dedicated server (arcade-cs2)",
    default_adapter_port=8302,
    default_compose_project="arcade-cs2",
    default_compose_service="cs2",
    default_stop_timeout_seconds=30,
    default_forward_protocols=("udp", "tcp"),
)

RCON_PASSWORD = os.environ.get("CS2_RCONPW", "")

# (game_type, game_mode) -> human label. This repo's docker-compose.yml
# sets CS2_GAMETYPE=0/CS2_GAMEMODE=2 for Wingman -- the full table is the
# documented set of official combos, not just the one this server uses.
GAME_MODE_LABELS = {
    (0, 0): "Casual",
    (0, 1): "Competitive",
    (0, 2): "Wingman",
    (1, 0): "Arms Race",
    (1, 1): "Demolition",
    (1, 2): "Deathmatch",
    (2, 0): "Custom",
    (3, 0): "Co-op Strike",
    (4, 0): "Danger Zone",
}

# Economy cvars per preset. "Casual" here means effectively-infinite money
# (start/after-round money pinned to the max) rather than CS2's own
# "Casual" game mode -- this is the ROADMAP's "casual/competitive economy
# preset", applied on top of whatever game mode is already running.
ECONOMY_PRESETS = {
    "casual": {
        "mp_startmoney": "16000",
        "mp_maxmoney": "16000",
        "mp_afterroundmoney": "16000",
    },
    "competitive": {
        "mp_startmoney": "800",
        "mp_maxmoney": "16000",
        "mp_afterroundmoney": "0",
    },
}

# Installed maps confirmed live via `maps *`, split by which mode family
# they're built for -- excludes vanity/night reskins, prefabs, and UI
# scenes. A defusal map has no arms-race weapon-progression spawns and
# vice versa; mixing them isn't a crash (learned live: an unsupported
# map/mode pairing just gives wrong spawns/rules), but it's still wrong,
# so change_map validates map against whichever mode applies.
_DEFUSAL_MAPS = [
    "de_ancient",
    "de_anubis",
    "de_boulder",
    "de_cache",
    "de_dust2",
    "de_eldorado",
    "de_fachwerk",
    "de_inferno",
    "de_mirage",
    "de_nuke",
    "de_overpass",
    "de_poseidon",
    "de_train",
    "de_vertigo",
]
_ARMS_RACE_MAPS = ["ar_baggage", "ar_pool_day", "ar_shoots"]
# Hostage-rescue maps. Valid alongside defusal maps in Casual/Competitive
# (Classic is a single game_type covering both objective types), but not
# in Wingman -- official Wingman map pools have always been defusal-only.
# Not live-verified via an actual changelevel (unlike the defusal/arms-race
# pools) -- worth confirming next time the server's up.
_HOSTAGE_MAPS = ["cs_italy", "cs_office", "cs_shelter"]

# name -> (game_type, game_mode, compatible maps). "arms_race" is CS2's
# official name for what's colloquially "Gun Game" (game_type 1, game_mode
# 0). Demolition/Deathmatch (game_type 1, game_mode 1/2) share arms_race's
# map pool convention-wise but aren't wired up as switchable modes yet.
MODES = {
    "casual": (0, 0, _DEFUSAL_MAPS + _HOSTAGE_MAPS),
    "competitive": (0, 1, _DEFUSAL_MAPS + _HOSTAGE_MAPS),
    "wingman": (0, 2, _DEFUSAL_MAPS),
    "arms_race": (1, 0, _ARMS_RACE_MAPS),
}
ALL_MAPS = sorted({map_name for *_, maps in MODES.values() for map_name in maps})

# CS2's `status` output has no `map:` line at all (unlike CS:GO/CS:S) --
# confirmed live. The only place the current map name shows up is the
# first spawngroup entry, e.g.
# "loaded spawngroup(  1)  : SV:  [1: de_nuke | main lump | mapload]".
_MAP_RE = re.compile(r"spawngroup\(\s*1\)\s*:\s*SV:\s*\[1:\s*([^|]+?)\s*\|", re.IGNORECASE)
_PLAYERS_RE = re.compile(
    r"players\s*:\s*(\d+)\s+humans?,\s*(\d+)\s+bots?\s*\((\d+)(?:\s*/\s*\d+)?\s*max\)",
    re.IGNORECASE,
)


def _rcon(command: str, ok_message: str) -> tuple[bool, str]:
    # RCON listens on the same port as the game itself (confirmed live) --
    # the adapter can reach it directly since it also runs network_mode:
    # host, same as cs2's published port.
    try:
        rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, command)
    except (rcon.RconError, OSError) as exc:
        return False, str(exc)
    return True, ok_message


def restart_round() -> tuple[bool, str]:
    return _rcon("mp_restartgame 1", "restarting")


def pause_match() -> tuple[bool, str]:
    # Confirmed live: queues cleanly even mid-warmup and takes effect once
    # the match actually goes live.
    return _rcon("mp_pause_match", "paused")


def unpause_match() -> tuple[bool, str]:
    return _rcon("mp_unpause_match", "unpaused")


def end_warmup() -> tuple[bool, str]:
    return _rcon("mp_warmup_end", "warmup ended")


def set_bot_quota(body: dict) -> tuple[bool, str]:
    try:
        count = int(body.get("count"))
    except (TypeError, ValueError):
        return False, f"invalid bot count: {body.get('count')!r}"
    if not 0 <= count <= 10:
        return False, f"bot count out of range (0-10): {count}"
    return _rcon(f"bot_quota {count}", f"bot_quota set to {count}")


def _query_cvar(name: str) -> str | None:
    """Read a cvar's current value by sending its bare name as an RCON
    command. CS2 prints `name = value ...` (no quotes around either side,
    confirmed live -- unlike classic Source engine's `"name" = "value"`)."""
    try:
        response = rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, name)
    except (rcon.RconError, OSError):
        return None
    match = re.search(rf'{re.escape(name)}\s*=\s*"?(-?\d+)"?', response)
    return match.group(1) if match else None


def stats() -> list[dict[str, str]]:
    try:
        status_text = rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, "status")
    except (rcon.RconError, OSError):
        return []

    result: list[dict[str, str]] = []

    map_match = _MAP_RE.search(status_text)
    if map_match:
        result.append({"label": "Map", "value": map_match.group(1)})

    game_type, game_mode = _query_cvar("game_type"), _query_cvar("game_mode")
    if game_type is not None and game_mode is not None:
        label = GAME_MODE_LABELS.get(
            (int(game_type), int(game_mode)), f"type {game_type}/mode {game_mode}"
        )
        result.append({"label": "Mode", "value": label})

    players_match = _PLAYERS_RE.search(status_text)
    if players_match:
        humans, bots, max_players = players_match.groups()
        result.append({"label": "Players", "value": f"{int(humans) + int(bots)}/{max_players}"})

    return result


def apply_preset(body: dict) -> tuple[bool, str]:
    preset = body.get("preset")
    cvars = ECONOMY_PRESETS.get(preset)
    if cvars is None:
        return False, f"unknown preset: {preset}"
    try:
        for name, value in cvars.items():
            rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, f"{name} {value}")
    except (rcon.RconError, OSError) as exc:
        return False, str(exc)
    return True, f"applied {preset}"


def _current_mode() -> str | None:
    """Best-effort reverse lookup of the running mode's name in MODES,
    from the live game_type/game_mode cvars. None if unreadable or if the
    server's current mode isn't one change_map knows how to switch to
    (e.g. Deathmatch)."""
    game_type, game_mode = _query_cvar("game_type"), _query_cvar("game_mode")
    if game_type is None or game_mode is None:
        return None
    current = (int(game_type), int(game_mode))
    for name, (gt, gm, _maps) in MODES.items():
        if (gt, gm) == current:
            return name
    return None


def change_map(body: dict) -> tuple[bool, str]:
    target_map = body.get("map")
    if target_map not in ALL_MAPS:
        return False, f"unknown map: {target_map}"

    mode = body.get("mode") or None
    if mode is not None and mode not in MODES:
        return False, f"unknown mode: {mode}"

    # Validate target_map against whichever mode will actually be running:
    # the one being switched to, or (if unspecified) whatever's live now.
    # Skips validation if the current mode can't be determined -- permissive
    # on failure, since a wrong pairing gives wrong spawns, not a crash.
    effective_mode = mode if mode is not None else _current_mode()
    if effective_mode is not None and target_map not in MODES[effective_mode][2]:
        return False, f"{target_map} isn't a {effective_mode} map"

    try:
        if mode is not None:
            # Set before changelevel, not after -- confirmed live that CS2
            # applies the matching gamemode_*.cfg at map-load time, not
            # immediately on a bare cvar change with the map already
            # running.
            game_type, game_mode, _maps = MODES[mode]
            rcon.exec_command(
                "127.0.0.1", config.forward_port, RCON_PASSWORD, f"game_type {game_type}"
            )
            rcon.exec_command(
                "127.0.0.1", config.forward_port, RCON_PASSWORD, f"game_mode {game_mode}"
            )
        rcon.exec_command(
            "127.0.0.1", config.forward_port, RCON_PASSWORD, f"changelevel {target_map}"
        )
    except (rcon.RconError, OSError) as exc:
        return False, str(exc)
    return True, f"changing to {target_map}" + (f" ({mode})" if mode else "")


if __name__ == "__main__":
    run_adapter(
        config,
        extra_actions={
            "restart_round": restart_round,
            "pause_match": pause_match,
            "unpause_match": unpause_match,
            "end_warmup": end_warmup,
            "apply_preset": {
                "handler": apply_preset,
                "label": "Apply economy preset",
                "params": [
                    {
                        "name": "preset",
                        "type": "enum",
                        "label": "Preset",
                        "options": ["casual", "competitive"],
                        "default": "casual",
                    }
                ],
            },
            "change_map": {
                "handler": change_map,
                "label": "Change map",
                "params": [
                    {
                        "name": "map",
                        "type": "enum",
                        "label": "Map",
                        "options": ALL_MAPS,
                        "default": "de_nuke",
                    },
                    {
                        "name": "mode",
                        "type": "enum",
                        "label": "Mode (leave unset to keep current)",
                        "options": list(MODES),
                    },
                ],
            },
            "set_bot_quota": {
                "handler": set_bot_quota,
                "label": "Set bot quota",
                "params": [
                    {
                        "name": "count",
                        "type": "number",
                        "label": "Bot count",
                        "min": 0,
                        "max": 10,
                        "default": 4,
                    }
                ],
            },
        },
        stats_fn=stats,
    )
