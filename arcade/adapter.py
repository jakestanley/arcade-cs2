#!/usr/bin/env python3
"""arcade.stanley.arpa control adapter for arcade-cs2.

Thin wrapper around lib_arcade -- see that repo for the actual HTTP
server, Docker control, heartbeat loop, and UPnP port-forwarding logic.
This file only supplies this repo's own defaults.
"""

from __future__ import annotations

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

if __name__ == "__main__":
    run_adapter(config)
