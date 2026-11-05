"""ShiftBoard administrator routes enforce current server-side permissions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app import security

router = APIRouter()


@router.get("/api/admin")
def api_admin(user: Annotated[dict, Depends(security.require_admin)]):
    """Return only the approved administrator identity and access confirmation."""
    return {"username": user["username"], "message": "Administrator access confirmed."}


@router.get("/admin", include_in_schema=False)
def admin_page(request: Request):
    """Apply the same role guard as the API, with helpful browser responses."""
    try:
        user = security.require_admin(request)
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        if error.status_code != 403:
            raise
        return request.app.state.templates.TemplateResponse(
            request=request, name="admin.html", context={}, status_code=403
        )
    return request.app.state.templates.TemplateResponse(
        request=request, name="admin.html", context={"admin_username": user["username"]}
    )
