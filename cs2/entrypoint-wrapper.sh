#!/bin/bash
# Rebuild the ldconfig cache so libv8.so resolves via the trusted system
# cache instead of LD_LIBRARY_PATH (see Dockerfile for why). Runs as root
# since regenerating /etc/ld.so.cache needs write access there; the actual
# game process still runs as the normal `steam` user via su below.
#
# On a genuinely fresh volume (no game files downloaded yet), this first
# ldconfig pass has nothing to find yet -- SteamCMD downloads afterward,
# inside entry.sh. If that happens, the first real launch attempt fails
# the same way it did before this fix, but `restart: unless-stopped`
# brings the container back, and this wrapper's ldconfig then finds the
# now-present files -- self-heals after one restart, not worth chasing
# further for a one-time case.
ldconfig || true

exec su -s /bin/bash steam -c "cd /home/steam && exec bash entry.sh"
