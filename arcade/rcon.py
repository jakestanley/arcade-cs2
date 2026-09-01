"""Minimal Source RCON client for the CS2 dedicated server.

Genuinely game-specific control logic (Source's packet framing, the
auth handshake) -- stays in this repo rather than lib-arcade, per the
arcade contract's separation-of-concerns rule (lib-arcade only owns
generic HTTP/Docker/UPnP plumbing shared across every adapter).

Protocol verified live against a real running cs2 server this session
while diagnosing the Wingman map issue -- this is that same client,
cleaned up into a reusable module.
"""

from __future__ import annotations

import socket
import struct
import time

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2


class RconError(Exception):
    """Raised on auth failure or a connection/protocol problem."""


def _send_packet(sock: socket.socket, pkt_id: int, pkt_type: int, body: str) -> None:
    payload = struct.pack("<ii", pkt_id, pkt_type) + body.encode() + b"\x00\x00"
    sock.sendall(struct.pack("<i", len(payload)) + payload)


def _read_packet(sock: socket.socket) -> tuple[int, int, str]:
    size_data = sock.recv(4)
    if len(size_data) < 4:
        raise RconError("connection closed while reading packet size")
    size = struct.unpack("<i", size_data)[0]
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise RconError("connection closed mid-packet")
        data += chunk
    pkt_id, pkt_type = struct.unpack("<ii", data[:8])
    body = data[8:-2].decode(errors="replace")
    return pkt_id, pkt_type, body


def exec_command(host: str, port: int, password: str, command: str, timeout: float = 5) -> str:
    """Authenticate and run one RCON command, returning its response body.

    Opens and closes a fresh connection per call -- this backs
    occasional, user-triggered actions, not frequent enough to justify
    keeping a persistent connection around.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((host, port))

        _send_packet(sock, 1, SERVERDATA_AUTH, password)
        auth_id, _auth_type, _auth_body = _read_packet(sock)
        if auth_id == -1:
            raise RconError("RCON authentication failed")

        _send_packet(sock, 1, SERVERDATA_EXECCOMMAND, command)
        # The server can take a moment to process before its response is
        # ready -- matches the timing already proven reliable live.
        time.sleep(0.15)
        _resp_id, _resp_type, body = _read_packet(sock)
        return body
