"""Five reviewed public sources; no user-controlled fetch targets."""

import hashlib
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.cisa.gov/secure-our-world/"
SOURCES = {
    "C01": {
        "title": "Use Strong Passwords",
        "url": BASE + "use-strong-passwords",
        "sections": [
            "An Easy Way to Protect Your Accounts",
            "Strengthen Your Passwords with Three Simple Tips",
            "Use a Password Manager",
        ],
    },
    "C02": {
        "title": "Turn On MFA",
        "url": BASE + "turn-mfa",
        "sections": ["Follow these Easy Steps"],
    },
    "C03": {
        "title": "Recognize and Report Phishing",
        "url": BASE + "recognize-and-report-phishing",
        "sections": [
            "Don’t Take the Bait",
            "Stay Safe with Three Simple Tips",
            "If a message looks suspicious, it's probably phishing.",
        ],
    },
    "C04": {
        "title": "Update Software",
        "url": BASE + "update-software",
        "sections": [
            "Think Twice Before Putting Off Updates!",
            "Keep Software Up to Date with Three Simple Steps",
            "Why It’s So Important to Update Promptly",
        ],
    },
    "C05": {
        "title": "Multi-Factor Authentication",
        "url": (
            "https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/"
            "multi-factor-authentication"
        ),
        "sections": [],
    },
}
for source_id, source_record in SOURCES.items():
    source_record.update(
        id=source_id,
        agency="NIST" if source_id == "C05" else "CISA",
        archived=source_id != "C05",
        source_date="2026-01-05" if source_id == "C05" else None,
        permission=(
            "Agency-authored educational text; 17 USC 105; NIST "
            "reuse policy for C05. Images, stories and third-party "
            "material excluded."
        ),
    )


def fetch_source(source):
    """Bound response time/size; do not follow redirects to unreviewed targets."""
    started = time.monotonic()
    with httpx.stream(
        "GET",
        source["url"],
        timeout=15,
        follow_redirects=False,
        headers={"User-Agent": "IS373-Educational-Importer/1.0"},
    ) as response:
        response.raise_for_status()
        if response.status_code != 200 or "text/html" not in response.headers.get(
            "content-type", ""
        ):
            raise ValueError("Expected an HTML source without redirects.")
        body = bytearray()
        for part in response.iter_bytes():
            body.extend(part)
            if len(body) > 1_000_000 or time.monotonic() - started > 30:
                raise ValueError("Source exceeds the import size/time limit.")
    return body.decode("utf-8")


def extract(source, html):
    """Keep reviewed article sections and their actual headings, excluding stories."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script,style,nav,footer,header"):
        tag.decompose()
    elements = (soup.find("main") or soup).find_all(["h2", "h3", "p", "li"])
    sections, heading, parts, active = [], "", [], False
    for element in elements:
        text = " ".join(element.get_text(" ", strip=True).split())
        is_heading = element.name in {"h2", "h3"}
        if source["id"] == "C05":
            is_heading = is_heading or text in {
                "Protecting Your Business from a Common Cyber Threat: Phishing",
                "How does MFA Protect My Business From this Threat?",
                "Taking MFA to the Next Level: Phishing-Resistant Authentication",
                "Questions to Consider",
                "Technical Deep Dive",
                "Related Resources",
            }
            wanted = text.startswith("What is Multi-Factor") or text in {
                "Protecting Your Business from a Common Cyber Threat: Phishing",
                "How does MFA Protect My Business From this Threat?",
                "Taking MFA to the Next Level: Phishing-Resistant Authentication",
            }
        else:
            wanted = text in source["sections"] or (
                active and element.name == "h3" and not element.get("class")
            )
        if is_heading:
            if active and parts:
                sections.append({"heading": heading, "text": " ".join(parts)})
            heading, parts, active = text, [], wanted
        elif active and text and not element.find(["p", "li"]):
            if (
                not text.startswith(
                    ("Example:", "Learn more here:", "Download", "PRO TIP")
                )
                and "Audio Description" not in text
            ):
                parts.append(text)
    if active and parts:
        sections.append({"heading": heading, "text": " ".join(parts)})
    if len(" ".join(s["text"] for s in sections)) < 200:
        raise ValueError(
            "Reviewed article sections missing; inspect the changed source."
        )
    content_hash = hashlib.sha256(
        ("offsets-v3-title-context:" + str(sections)).encode()
    ).hexdigest()
    return {
        **source,
        "sections": sections,
        "content_hash": content_hash,
        "accessed_at": datetime.now(timezone.utc).isoformat(),
    }
