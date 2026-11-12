#!/usr/bin/env bash
# Ejecutar solo tras autorizar el arranque y sus reglas de red de Docker.
# Versiones disponibles y simuladas en este VPS el 22/10/2026.
set -euo pipefail
test "$(id -u)" -eq 0
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 26.04
if command -v docker >/dev/null; then
    echo 'Docker ya existe: revisar la instalacion antes de modificarla.'
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l
apt-get install -y --no-remove --no-install-recommends \
    docker-ce=5:29.9.2-1~ubuntu.26.04~resolute \
    docker-ce-cli=5:29.9.2-1~ubuntu.26.04~resolute \
    containerd.io=2.4.2-3~ubuntu.26.04~resolute \
    docker-buildx-plugin=0.38.1-1~ubuntu.26.04~resolute \
    docker-compose-plugin=5.6.1-1~ubuntu.26.04~resolute age
systemctl enable --now docker
docker version --format '{{.Server.Version}}'
docker compose version
docker run --rm hello-world
ss -lnt
