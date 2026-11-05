"""Regressions for role-aware navigation and limited administrator output."""

from app import database
from tests.test_accounts import sign_in


def test_navigation_and_output_follow_current_role(client, settings):
    """The same session gains and loses the link and access with its DB role."""
    assert 'href="/admin"' not in client.get("/").text
    sign_in(client)
    assert 'href="/admin"' not in client.get("/dashboard").text
    denied = client.get("/admin")
    assert denied.status_code == 403
    assert "Admin access required" in denied.text
    for role, status in (("admin", 200), ("member", 403)):
        assert database.set_role(settings, "route_member", role)
        page = client.get("/admin")
        api = client.get("/api/admin")
        assert page.status_code == api.status_code == status
        assert (
            page.headers["cache-control"] == api.headers["cache-control"] == "no-store"
        )
        assert ('href="/admin"' in client.get("/dashboard").text) == (role == "admin")
        if role == "admin":
            assert api.json() == {
                "username": "route_member",
                "message": "Administrator access confirmed.",
            }
            assert "route_member" in page.text
        else:
            assert "Administrator access confirmed." not in page.text
            assert "username" not in api.json()


def test_logout_revokes_administrator_access(client, settings):
    """Copied admin cookies cannot retain access after server-side logout."""
    sign_in(client)
    assert database.set_role(settings, "route_member", "admin")
    cookie = client.cookies.get(settings.cookie_name)
    csrf = client.get("/api/csrf").json()["csrf_token"]
    assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    client.cookies.clear()
    client.cookies.set(settings.cookie_name, cookie)
    assert client.get("/api/admin").status_code == 401
    page = client.get("/admin", follow_redirects=False)
    assert page.status_code == 303
    assert page.headers["location"] == "/login"
