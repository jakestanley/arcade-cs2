# Thin layer over the upstream image, solely to fix V8's dynamic library
# resolution once cap_sys_ptrace=eip is set on the cs2 binary (needed for
# V8's ptrace-based JIT sandboxing -- see docker-compose.yml).
#
# A file capability puts the binary into glibc's secure-execution mode,
# which makes the dynamic linker ignore LD_LIBRARY_PATH -- and this
# image's own launcher relies on LD_LIBRARY_PATH (not a baked-in path)
# to find its bundled libv8.so. ld.so.conf/ldconfig-registered paths ARE
# still honored in secure-execution mode (they come from a trusted root
# cache, not an untrusted env var), so we register the game's own lib
# directory that way instead.
FROM joedwards32/cs2:latest

USER root

RUN echo "/home/steam/cs2-dedicated/game/bin/linuxsteamrt64" > /etc/ld.so.conf.d/cs2-v8.conf

COPY entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/entrypoint-wrapper.sh

WORKDIR /home/steam
CMD ["/usr/local/bin/entrypoint-wrapper.sh"]
