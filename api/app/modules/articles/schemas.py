from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints, field_validator
from app.modules.articles.media import Media

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
Section = Literal["actualidad", "herramientas", "programacion", "tutoriales"]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=180, pattern=SLUG_PATTERN)]


def _no_control_chars(value: str) -> str:
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("Contiene caracteres de control no permitidos")
    return value


class Source(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    url: AnyHttpUrl
    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2}$")] = "en"

    @field_validator("url")
    @classmethod
    def only_http(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme not in ("http", "https") or len(str(value)) > 2000:
            raise ValueError("URL no válida")
        return value


class SectionOut(BaseModel):
    slug: str
    name: str
    description: str


class ArticleSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    summary: str
    section: str
    author_name: str
    published_at: datetime | None
    updated_at: datetime
    media: Media=Field(default_factory=Media)


class ArticleOut(ArticleSummaryOut):
    body: str
    sources: list[Source]
    reviewed_at: datetime | None
    comments_enabled: bool


class ArticleDetailOut(ArticleOut):
    related: list[ArticleSummaryOut]


class ArticlePage(BaseModel):
    items: list[ArticleSummaryOut]
    page: int
    has_next: bool


class SitemapEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    section: str
    updated_at: datetime


class ArticleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: Slug
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=180)]
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=50, max_length=300)]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)]
    section: Section
    author_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
    sources: list[Source] = Field(default_factory=list, max_length=30)

    @field_validator("title", "summary", "body", "author_name")
    @classmethod
    def clean(cls, value: str) -> str:
        return _no_control_chars(value)


class ArticleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: Slug | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=180)] | None = None
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=50, max_length=300)] | None = None
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100_000)] | None = None
    section: Section | None = None
    author_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)] | None = None
    sources: list[Source] | None = Field(default=None, max_length=30)
    comments_enabled: bool | None = None

    @field_validator("title", "summary", "body", "author_name")
    @classmethod
    def clean(cls, value: str | None) -> str | None:
        return None if value is None else _no_control_chars(value)


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["draft", "review", "published", "archived"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class EditorialArticleOut(ArticleOut):
    id: int
    status: str
    created_at: datetime
    reviewed_by: str | None
