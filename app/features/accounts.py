"""ShiftBoard account pages and API share the prepared security services."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import security
from app.schemas import LoginInput, PublicUser, SignupInput

router = APIRouter()


def api_csrf(request: Request):
    """Require a session-bound token on every state-changing API request."""
    security.require_csrf(request, request.headers.get("X-CSRF-Token"))


@router.get("/api/csrf")
def get_csrf(request: Request, response: Response):
    """Start or reuse a pre-session without exposing an authentication token."""
    return {"csrf_token": security.csrf_token(request, response)}


@router.post(
    "/api/signup",
    status_code=201,
    response_model=PublicUser,
    dependencies=[Depends(api_csrf)],
)
def api_signup(request: Request, credentials: SignupInput):
    """Only validated username/password inputs can create a member."""
    security.limit_signup(request)
    return security.signup(request.app.state.settings, **credentials.model_dump())


@router.post("/api/login", response_model=PublicUser, dependencies=[Depends(api_csrf)])
def api_login(request: Request, response: Response, credentials: LoginInput):
    """Set the HttpOnly session cookie; JSON contains only public account fields."""
    return security.login(request, response, **credentials.model_dump())


@router.get("/api/me", response_model=PublicUser)
def api_me(user: Annotated[dict, Depends(security.require_user)]):
    """Filter the helper's private session ID out of the response."""
    return user


@router.post("/api/logout", dependencies=[Depends(api_csrf)])
def api_logout(request: Request, response: Response):
    """Revoke server state and clear the browser cookie."""
    security.logout(request, response)
    return {"message": "You are logged out."}


def render_page(request, template, context=None, status_code=200, headers=None):
    """Render a fresh CSRF token while preserving any pre-session cookie."""
    cookies = Response()
    token = security.csrf_token(request, cookies)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name=template,
        context={**(context or {}), "csrf_token": token},
        status_code=status_code,
        headers=headers,
    )
    for cookie in cookies.headers.getlist("set-cookie"):
        response.headers.append("set-cookie", cookie)
    return response


@router.get("/signup", include_in_schema=False)
def signup_page(request: Request):
    """Show an accessible signup form or the existing member space."""
    if security.authenticate(request):
        return RedirectResponse("/dashboard", status_code=303)
    return render_page(request, "account.html", {"signup": True})


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    """Show login without accepting an arbitrary redirect destination."""
    if security.authenticate(request):
        return RedirectResponse("/dashboard", status_code=303)
    return render_page(request, "account.html", {"signup": False})


async def read_form(request: Request, allowed):
    """Reject uploads, extra fields, and duplicate fields instead of ignoring them."""
    try:
        form = await request.form(max_files=0, max_fields=3, max_part_size=2048)
    except StarletteHTTPException as error:
        raise HTTPException(
            422, "Please use only the fields shown on this form."
        ) from error
    pairs = list(form.multi_items())
    if (
        len(pairs) != len(form)
        or not set(form).issubset(allowed)
        or any(not isinstance(value, str) for _, value in pairs)
    ):
        raise HTTPException(422, "Please use only the fields shown on this form.")
    return dict(form)


def submit_account(request, values, signup):
    """Validate CSRF and credentials before invoking shared account services."""
    username = ""
    try:
        security.require_csrf(request, values.pop("csrf_token", None))
        model = SignupInput if signup else LoginInput
        credentials = model.model_validate(values)
        username = credentials.username
        if signup:
            security.limit_signup(request)
            security.signup(request.app.state.settings, **credentials.model_dump())
            return RedirectResponse("/login?created=1", status_code=303)
        response = RedirectResponse("/dashboard", status_code=303)
        security.login(request, response, **credentials.model_dump())
        return response
    except ValidationError:
        error = HTTPException(
            422, "Check the username and password requirements below."
        )
    except HTTPException as caught:
        error = caught
    return render_page(
        request,
        "account.html",
        {
            "signup": signup,
            "username": username,
            "error": error.detail,
        },
        error.status_code,
        error.headers,
    )


async def account_form(request, signup):
    """Parse form input and keep password hashing off the async event loop."""
    try:
        values = await read_form(request, {"username", "password", "csrf_token"})
    except HTTPException as error:
        return render_page(
            request,
            "account.html",
            {
                "signup": signup,
                "error": error.detail,
            },
            error.status_code,
            error.headers,
        )
    return await run_in_threadpool(submit_account, request, values, signup)


@router.post("/signup", include_in_schema=False)
async def signup_form(request: Request):
    """Create an account through the same service as POST /api/signup."""
    return await account_form(request, True)


@router.post("/login", include_in_schema=False)
async def login_form(request: Request):
    """Sign in through the same service as POST /api/login."""
    return await account_form(request, False)


@router.get("/dashboard", include_in_schema=False)
def dashboard(request: Request):
    """Require a live authenticated session before rendering private information."""
    user = security.authenticate(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render_page(request, "dashboard.html", {"user": user})


@router.post("/logout", include_in_schema=False)
async def logout_form(request: Request):
    """Only a valid POST revokes the session; a GET never signs someone out."""
    try:
        values = await read_form(request, {"csrf_token"})
        security.require_csrf(request, values.get("csrf_token"))
    except HTTPException as error:
        return render_page(
            request,
            "account_error.html",
            {"error": error.detail},
            error.status_code,
            error.headers,
        )
    response = RedirectResponse("/login?logged_out=1", status_code=303)
    await run_in_threadpool(security.logout, request, response)
    return response
