#!/usr/bin/env bash
# Comprobacion local; los fallos quedan en systemd/journal, no hay alertas externas aun.
set -euo pipefail
cd /opt/foroia
for service in db redis api web; do
    state=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "foroia-production-$service-1")
    if [[ "$state" != healthy ]]; then
        echo "Servicio no saludable: $service" >&2
        exit 1
    fi
done
expected=200
if grep -Eq '^SITE_MAINTENANCE=true[[:space:]]*$' production.env; then expected=503; fi
actual=$(curl --silent --show-error --connect-timeout 3 --max-time 10 --output /dev/null --write-out '%{http_code}' https://foroiaaldia.com/)
if [[ "$actual" != "$expected" ]]; then
    echo 'Respuesta HTTPS inesperada' >&2
    exit 1
fi
recent=$(find /var/backups/foroia -maxdepth 1 -type f -name 'postgres-*.dump.age' -mmin -2880 -size +0c -print -quit)
if [[ -z "$recent" ]]; then
    echo 'No hay backup PostgreSQL cifrado reciente' >&2
    exit 1
fi
docker exec foroia-production-api-1 python -m app.research.monitor
echo 'Servicios, HTTPS, backup y comprobacion editorial ejecutados. Resultados en journal y panel privado.'
