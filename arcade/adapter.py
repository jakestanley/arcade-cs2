#!/usr/bin/env python3
"""arcade.stanley.arpa control adapter for arcade-cs2.

Thin wrapper around lib_arcade -- see that repo for the actual HTTP
server, Docker control, heartbeat loop, and UPnP port-forwarding logic.
This file only supplies this repo's own defaults.
"""

from __future__ import annotations

import os

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


def restart_round() -> tuple[bool, str]:
    # RCON listens on the same port as the game itself (confirmed live) --
    # the adapter can reach it directly since it also runs network_mode:
    # host, same as cs2's published port.
    try:
        rcon.exec_command("127.0.0.1", config.forward_port, RCON_PASSWORD, "mp_restartgame 1")
    except (rcon.RconError, OSError) as exc:
        return False, str(exc)
    return True, "restarting"


if __name__ == "__main__":
    run_adapter(config, extra_actions={"restart_round": restart_round})
