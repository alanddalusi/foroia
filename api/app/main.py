from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.modules import forum
from app.modules.articles import editorial, public
from app.modules import accounts, comments
from app.research.routes import router as research_router
from app.modules.analytics import router as analytics_router
from app.modules.seo import router as seo_router

app = FastAPI(title="ForoIA API", version="0.2.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(get_settings().allowed_hosts))


@app.middleware("http")
async def private_and_size_limits(request: Request, call_next):
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 300_000:
                return JSONResponse({"detail": "Contenido demasiado grande"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    if request.url.path.startswith(("/auth", "/editorial", "/moderation")):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(forum.router)
app.include_router(public.router)
app.include_router(editorial.router)
app.include_router(research_router)
app.include_router(accounts.router)
app.include_router(comments.router)
app.include_router(analytics_router)
app.include_router(seo_router)
