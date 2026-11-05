"""Route-level regressions for rejected HTML input and private session boundaries."""

import re

import jwt
import pytest

from app import database, security

PASSWORD = "disposable account test passphrase"


def form_token(client, path):
    """Read a form token without logging or publishing it."""
    response = client.get(path)
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)


def sign_in(client):
    """Create a throwaway account in the fixture's isolated database."""
    credentials = {"username": "route_member", "password": PASSWORD}
    headers = {"X-CSRF-Token": client.get("/api/csrf").json()["csrf_token"]}
    assert (
        client.post("/api/signup", json=credentials, headers=headers).status_code == 201
    )
    assert (
        client.post("/api/login", json=credentials, headers=headers).status_code == 200
    )


@pytest.mark.parametrize("path", ["/signup", "/login"])
def test_html_rejects_role_and_duplicate_credentials(client, settings, path):
    """Extra or ambiguous fields must not be silently accepted by HTML routes."""
    token = form_token(client, path)
    response = client.post(
        path,
        data={
            "username": "route_member",
            "password": PASSWORD,
            "csrf_token": token,
            "role": "admin",
        },
    )
    assert response.status_code == 422
    response = client.post(
        path,
        content=(f"username=one&username=two&password={PASSWORD}&csrf_token={token}"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 422
    assert PASSWORD not in response.text
    with database.connect(settings) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


@pytest.mark.parametrize("path", ["/logout", "/api/logout"])
def test_logout_requires_post_and_csrf_without_ending_session(client, path):
    """Neither a navigation nor a forged POST signs a user out."""
    sign_in(client)
    assert client.get(path).status_code == 405
    assert client.post(path).status_code == 403
    assert client.get("/api/me").status_code == 200


@pytest.mark.parametrize("kind", ["expired_jwt", "wrong_signature", "expired_session"])
def test_actual_private_routes_reject_invalid_sessions(client, settings, kind):
    """Both HTML and API enforce token validation and live database state."""
    sign_in(client)
    token = client.cookies.get(settings.cookie_name)
    claims = jwt.decode(
        token,
        settings.secret,
        algorithms=["HS256"],
        audience=security.AUDIENCE,
        issuer=settings.origin,
    )
    if kind == "expired_session":
        with database.connect(settings) as connection:
            connection.execute("UPDATE sessions SET expires_at = 0")
    else:
        if kind == "expired_jwt":
            claims["exp"] = 1
        key = settings.secret if kind == "expired_jwt" else "wrong-test-key-" * 4
        token = jwt.encode(
            claims, key, algorithm="HS256", headers={"typ": security.TOKEN_TYPE}
        )
        client.cookies.clear()
        client.cookies.set(settings.cookie_name, token)
    assert client.get("/api/me").status_code == 401
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert "route_member" not in response.text


def test_private_pages_and_identity_do_not_expose_session_id(client):
    """Account output is limited to public identity and is not browser-cacheable."""
    sign_in(client)
    me = client.get("/api/me")
    assert set(me.json()) == {"id", "username", "role"}
    assert me.headers["cache-control"] == "no-store"
    dashboard = client.get("/dashboard")
    assert dashboard.headers["cache-control"] == "no-store"
    assert PASSWORD not in dashboard.text
    assert client.get("/admin").status_code == 403
    assert client.get("/api/admin").status_code == 403
