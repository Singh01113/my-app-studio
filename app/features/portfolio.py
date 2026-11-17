"""Public professional portfolio and a separately presented knowledge assistant."""

import httpx

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app import security
from app.knowledge import corpus

router = APIRouter()


class Question(BaseModel):
    """Bound user input; fields cannot set retrieval or fetch configuration."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=1000)


class ImportRequest(BaseModel):
    """Only reviewed document IDs, never arbitrary URLs or local files."""

    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^C0[1-5]$")


@router.get("/portfolio", include_in_schema=False)
def portfolio(request: Request):
    """Public introduction, project evidence, background and contact."""
    return request.app.state.templates.TemplateResponse(
        request=request, name="portfolio.html", context={}
    )


@router.get("/assistant", include_in_schema=False)
def assistant(request: Request):
    """Render the working retrieval interface with an honest answer-mode label."""
    return request.app.state.templates.TemplateResponse(
        request=request, name="assistant.html", context={}
    )


@router.get("/api/knowledge/sources")
def sources(request: Request):
    """Show imported provenance; an empty index is distinguishable from a plan."""
    return {
        "sources": request.app.state.knowledge.store.sources(),
        "mode": "extractive",
    }


@router.post("/api/knowledge/query")
def query(payload: Question, request: Request):
    """Public, bounded retrieval; rate budgets survive a process restart."""
    service = request.app.state.knowledge
    if not service.store.consume_budget(
        request.client.host if request.client else "unknown"
    ):
        raise HTTPException(
            429, "Query limit reached. Try again later.", headers={"Retry-After": "60"}
        )
    if not service.operation.acquire(blocking=False):
        raise HTTPException(503, "The assistant is busy. Please try again shortly.")
    try:
        return service.answer(payload.question)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(
            503, "Retrieval unavailable; the owner must check the model and index."
        ) from error
    finally:
        service.operation.release()


@router.post("/api/knowledge/import")
def import_source(payload: ImportRequest, request: Request):
    """Require current admin role and CSRF for transactional imports."""
    security.require_admin(request)
    security.require_csrf(request, request.headers.get("X-CSRF-Token"))
    service = request.app.state.knowledge
    if not service.operation.acquire(blocking=False):
        raise HTTPException(503, "The assistant is busy. Please try again shortly.")
    try:
        source = corpus.SOURCES[payload.document_id]
        document = corpus.extract(source, corpus.fetch_source(source))
        return service.store.import_document(document, service.embedder)
    except (ValueError, RuntimeError, OSError, httpx.HTTPError) as error:
        raise HTTPException(
            502, "Import failed; the previous active source version remains available."
        ) from error
    finally:
        service.operation.release()
