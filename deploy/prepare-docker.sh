#!/usr/bin/env bash
# Solo prepara/verifica el repositorio. No instala ni arranca Docker.
set -euo pipefail
test "$(id -u)" -eq 0
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 26.04
test "$(dpkg --print-architecture)" = amd64
test -s /etc/apt/keyrings/docker.asc
work=$(mktemp -d)
trap 'rm -f -- "$work/docker.asc" "$work/docker.sources"; rmdir -- "$work"' EXIT
curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
    https://download.docker.com/linux/ubuntu/gpg -o "$work/docker.asc"
cmp /etc/apt/keyrings/docker.asc "$work/docker.asc"
if ! grep -R -q 'download.docker.com' /etc/apt/sources.list.d/ /etc/apt/sources.list 2>/dev/null; then
    test ! -e /etc/apt/sources.list.d/docker.sources
    printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/ubuntu' \
        "Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}" 'Components: stable' \
        'Architectures: amd64' 'Signed-By: /etc/apt/keyrings/docker.asc' > "$work/docker.sources"
    install -m 644 "$work/docker.sources" /etc/apt/sources.list.d/docker.sources
fi
apt-get update
apt-cache policy docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
apt-get --simulate install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin age
