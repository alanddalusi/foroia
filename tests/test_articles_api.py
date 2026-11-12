"""Pruebas de la API de artículos y del panel editorial (SQLite en memoria).

`create_all` se usa solo aquí, como fixture de pruebas; producción usa Alembic.
"""
import asyncio
import os

import pytest

TOKEN = "t" * 40
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ["EDITORIAL_API_TOKEN"] = TOKEN
os.environ["LEGACY_EDITORIAL_ENABLED"] = "true"

httpx = pytest.importorskip("httpx")
pytest.importorskip("aiosqlite")

from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core import db as core_db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

AUTH = {"X-Editorial-Token": TOKEN}
BODY = "Explicación detallada en español. " * 20


def article(**overrides):
    data = {
        "slug": "nuevo-modelo-abierto",
        "title": "Un nuevo modelo abierto explicado",
        "summary": "Resumen del anuncio original con los datos verificados y lo que significa en la práctica.",
        "body": BODY,
        "section": "actualidad",
        "author_name": "Redacción",
        "sources": [{"title": "Anuncio oficial", "url": "https://example.com/post", "language": "en"}],
    }
    data.update(overrides)
    return data


@pytest.fixture
def client():
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
                                 connect_args={"check_same_thread": False})
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override():
        async with maker() as session:
            yield session

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    app.dependency_overrides[core_db.get_db] = override
    transport = httpx.ASGITransport(app=app)

    class Sync:
        def request(self, method, url, **kw):
            async def go():
                async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as c:
                    return await c.request(method, url, **kw)
            return asyncio.run(go())

        def get(self, url, **kw):
            return self.request("GET", url, **kw)

        def post(self, url, **kw):
            return self.request("POST", url, **kw)

        def patch(self, url, **kw):
            return self.request("PATCH", url, **kw)

        def delete(self, url, **kw):
            return self.request("DELETE", url, **kw)

    yield Sync()
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def publish(client, **overrides):
    created = client.post("/editorial/articles", json=article(**overrides), headers=AUTH)
    assert created.status_code == 201, created.text
    aid = created.json()["id"]
    assert client.post(f"/editorial/articles/{aid}/status", json={"status": "review"}, headers=AUTH).status_code == 200
    r = client.post(f"/editorial/articles/{aid}/status", json={"status": "published"}, headers=AUTH)
    assert r.status_code == 200, r.text
    return aid


def test_editorial_requires_token(client):
    assert client.get("/editorial/articles").status_code == 401
    assert client.get("/editorial/articles", headers={"X-Editorial-Token": "x" * 40}).status_code == 401
    assert client.post("/editorial/articles", json=article()).status_code == 401


def test_editorial_disabled_without_token(client, monkeypatch):
    monkeypatch.setenv("EDITORIAL_API_TOKEN", "")
    get_settings.cache_clear()
    try:
        assert client.get("/editorial/articles", headers=AUTH).status_code == 503
    finally:
        monkeypatch.setenv("EDITORIAL_API_TOKEN", TOKEN)
        get_settings.cache_clear()


def test_draft_is_not_public(client):
    r = client.post("/editorial/articles", json=article(), headers=AUTH)
    assert r.status_code == 201 and r.json()["status"] == "draft"
    assert client.get("/articles/nuevo-modelo-abierto").status_code == 404
    assert client.get("/articles").json()["items"] == []
    assert client.get("/articles-sitemap").json() == []


def test_cannot_publish_without_review_or_sources(client):
    aid = client.post("/editorial/articles", json=article(sources=[]), headers=AUTH).json()["id"]
    assert client.post(f"/editorial/articles/{aid}/status", json={"status": "published"}, headers=AUTH).status_code == 409
    client.post(f"/editorial/articles/{aid}/status", json={"status": "review"}, headers=AUTH)
    r = client.post(f"/editorial/articles/{aid}/status", json={"status": "published"}, headers=AUTH)
    assert r.status_code == 422 and "fuente" in r.json()["detail"]


def test_publish_flow_and_related(client):
    publish(client)
    publish(client, slug="otra-noticia-relacionada", title="Otra noticia relacionada de IA")
    publish(client, slug="guia-programacion", section="programacion", title="Guía de programación con APIs")
    detail = client.get("/articles/nuevo-modelo-abierto")
    assert detail.status_code == 200
    data = detail.json()
    assert data["sources"][0]["url"] == "https://example.com/post"
    assert data["published_at"] and data["reviewed_at"]
    assert [r["slug"] for r in data["related"]] == ["otra-noticia-relacionada"]
    assert "status" not in data and "id" not in data
    listing = client.get("/articles?section=programacion").json()
    assert [a["slug"] for a in listing["items"]] == ["guia-programacion"]


def test_archived_disappears(client):
    aid = publish(client)
    assert client.post(f"/editorial/articles/{aid}/status", json={"status": "archived"}, headers=AUTH).status_code == 200
    assert client.get("/articles/nuevo-modelo-abierto").status_code == 404


def test_pagination_limits(client):
    for i in range(3):
        publish(client, slug=f"articulo-{i}", title=f"Artículo de prueba número {i}")
    first = client.get("/articles?limit=2").json()
    second = client.get("/articles?limit=2&page=2").json()
    assert first["has_next"] and not second["has_next"]
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert client.get("/articles?limit=51").status_code == 422
    assert client.get("/articles?page=0").status_code == 422
    assert client.get("/articles?section=inventada").status_code == 422


@pytest.mark.parametrize("bad", [
    {"slug": "Mayúsculas no"},
    {"slug": "x' OR 1=1 --"},
    {"title": "corto"},
    {"sources": [{"title": "malo", "url": "javascript:alert(1)"}]},
    {"section": "otra"},
    {"extra": "campo"},
    {"body": "a" * 100_001},
])
def test_validation(client, bad):
    assert client.post("/editorial/articles", json=article(**bad), headers=AUTH).status_code == 422


def test_duplicate_slug_and_published_slug_locked(client):
    aid = publish(client)
    assert client.post("/editorial/articles", json=article(), headers=AUTH).status_code == 409
    r = client.patch(f"/editorial/articles/{aid}", json={"slug": "cambiado"}, headers=AUTH)
    assert r.status_code == 409
    r = client.patch(f"/editorial/articles/{aid}", json={"title": "Título corregido tras revisión"}, headers=AUTH)
    assert r.status_code == 200
    assert client.get("/articles/nuevo-modelo-abierto").json()["title"] == "Título corregido tras revisión"


def test_html_is_stored_as_text(client):
    payload = "<script>alert(1)</script>" + BODY
    publish(client, body=payload)
    assert client.get("/articles/nuevo-modelo-abierto").json()["body"].startswith("<script>")


def test_invalid_slug_is_404(client):
    assert client.get("/articles/..%2Fetc").status_code == 404
    assert client.get("/articles/" + "a" * 200).status_code == 404


def test_sections(client):
    slugs = [s["slug"] for s in client.get("/sections").json()]
    assert slugs == ["actualidad", "herramientas", "programacion", "tutoriales"]


def test_forum_category_counts_only_public_topics(client):
    from app.models import Category, Topic
    async def seed():
        async for db in app.dependency_overrides[core_db.get_db]():
            category = Category(slug='visible', name='Visible', description='Con temas')
            empty = Category(slug='empty', name='Vacía', description='Sin temas')
            db.add_all([category, empty]); await db.flush()
            db.add_all([Topic(category_id=category.id, slug='shown', title='Visible', body='Texto', author_name='Prueba', published=True),
                        Topic(category_id=category.id, slug='hidden', title='Oculto', body='Texto', author_name='Prueba', published=False)])
            await db.commit()
    asyncio.run(seed())
    result = {c['slug']: c['published_topics'] for c in client.get('/categories').json()}
    assert result == {'visible': 1, 'empty': 0}


def test_search_only_published_with_escaped_wildcards(client):
    publish(client, slug="embeddings-busqueda", title="Qué son los embeddings para buscar texto",
            summary="Cómo usar embeddings para encontrar textos parecidos en una base de documentos propia.")
    publish(client, slug="tokens-coste", title="Contar tokens antes de enviar texto",
            summary="Estimar los tokens de una petición para controlar el coste y el contexto disponible.")
    client.post("/editorial/articles", json=article(slug="borrador-embeddings", title="Borrador sobre embeddings"), headers=AUTH)
    r = client.get("/search", params={"q": "embeddings buscar"})
    assert r.status_code == 200
    assert [a["slug"] for a in r.json()["items"]] == ["embeddings-busqueda"]
    assert client.get("/search", params={"q": "%"}).status_code == 422  # demasiado corta
    assert client.get("/search", params={"q": "%%"}).json()["items"] == []  # sin términos válidos: no devuelve «todo»
    assert client.get("/search", params={"q": "to_ens"}).json()["items"] == []  # «_» es literal, no comodín
    assert client.get("/search", params={"q": "x" * 81}).status_code == 422
    assert client.get("/search", params={"q": "tokens", "page": 21}).status_code == 422
