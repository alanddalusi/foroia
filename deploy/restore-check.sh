#!/usr/bin/env bash
# Restaura SOLO en un contenedor desechable, sin red ni puertos publicados.
# Uso: sudo bash deploy/restore-check.sh BACKUP.dump.age IDENTIDAD.age
set -euo pipefail
umask 077
test "$#" -eq 2
test -s "$1"
test -s "$2"
command -v age >/dev/null
verify="foroia-restore-check-$$"
created=false
cleanup() {
    if "$created"; then docker rm -fv "$verify" >/dev/null; fi
}
trap cleanup EXIT
docker run -d --name "$verify" --network none \
    -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=restore_check \
    postgres:17-alpine >/dev/null
created=true
ready=false
for _ in {1..60}; do
    if docker exec "$verify" pg_isready -U postgres -d restore_check >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
"$ready"
age -d -i "$2" "$1" | docker exec -i "$verify" \
    pg_restore --exit-on-error --no-owner --no-privileges -U postgres -d restore_check
docker exec "$verify" psql -U postgres -d restore_check -v ON_ERROR_STOP=1 \
    -c 'SELECT version_num FROM alembic_version;' \
    -c 'SELECT count(*) AS articles_restored FROM articles;'
echo 'Restauracion aislada terminada; produccion no se ha modificado.'
