#!/usr/bin/env bash
# Ejecutar como root desde cron/systemd. La clave privada age vive fuera del VPS.
set -euo pipefail
umask 077
cd /opt/foroia
command -v age >/dev/null
recipient=/etc/foroia/backup-recipients.txt
test -s "$recipient"
install -d -m 700 /var/backups/foroia
target="/var/backups/foroia/postgres-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump.age"
trap 'rm -f -- "$target.partial"' EXIT
docker compose --env-file production.env -f compose.production.yml exec -T db \
    pg_dump -U foroia -d foroia --format=custom --no-owner --no-privileges \
    | age -R "$recipient" -o "$target.partial"
test -s "$target.partial"
mv -- "$target.partial" "$target"
echo "Backup cifrado terminado. Copiar fuera del VPS y probar restauracion."
