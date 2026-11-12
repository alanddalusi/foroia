FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache font-dejavu
COPY requirements.txt constraints.txt ./
RUN python -m pip install --no-cache-dir --progress-bar off pip==26.2.2 \
    && python -m pip install --no-cache-dir --progress-bar off -r requirements.txt \
    && python -m pip uninstall --yes pip \
    && adduser -D appuser
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
USER appuser
EXPOSE 8000
# Migraciones al arrancar: válido con una sola réplica. Con varias, ejecutar `alembic upgrade head` como paso previo del despliegue.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --http h11 --proxy-headers"]
