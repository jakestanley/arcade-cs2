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

_MAP_RE = re.compile(r"^\s*map\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_PLAYERS_RE = re.compile(
    r"players\s*:\s*(\d+)\s+humans?,\s*(\d+)\s+bots?\s*\((\d+)(?:\s*/\s*\d+)?\s*max\)",
    re.IGNORECASE,
)


def restart_round() -> tuple[bool, str]:
    # RCON listens on the same port as the game itself (confirmed live) --
    # the adapter can reach it directly since it also runs network_mode:
    # host, same as cs2's published port.
    try:
        rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, "mp_restartgame 1")
    except (rcon.RconError, OSError) as exc:
        return False, str(exc)
    return True, "restarting"


def _query_cvar(name: str) -> str | None:
    """Read a cvar's current value by sending its bare name as an RCON
    command -- the Source engine console prints `"name" = "value" ...` for
    any cvar queried this way, same as typing it at the server console."""
    try:
        response = rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, name)
    except (rcon.RconError, OSError):
        return None
    match = re.search(rf'"{re.escape(name)}"\s*=\s*"(-?\d+)"', response)
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


if __name__ == "__main__":
    run_adapter(
        config,
        extra_actions={
            "restart_round": restart_round,
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
        },
        stats_fn=stats,
    )
