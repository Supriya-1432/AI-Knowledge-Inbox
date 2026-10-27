"""URL validation and page-text extraction (Phase 5)."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}
MAX_CONTENT_CHARS = 200_000
MIN_CONTENT_CHARS = 40
DEFAULT_TIMEOUT = 20.0
USER_AGENT = "KnowledgeInboxBot/0.1 (+local RAG assignment)"


class UrlValidationError(ValueError):
    """Raised when a URL is syntactically or policy-invalid before fetching."""


class UrlFetchError(RuntimeError):
    """Raised when a URL looks valid but content cannot be retrieved/parsed."""


def validate_url(url: str) -> str:
    """Normalize and validate a URL. Returns the cleaned URL string.

    Rejects empty values, non-http(s) schemes, missing host, and obvious junk.
    """
    if url is None:
        raise UrlValidationError("URL is required")

    cleaned = url.strip()
    if not cleaned:
        raise UrlValidationError("URL is empty")

    # Reject dangerous / non-web schemes even when written as "javascript:..."
    bare_scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", cleaned)
    if bare_scheme:
        scheme_name = bare_scheme.group(1).lower()
        if scheme_name not in ALLOWED_SCHEMES and not cleaned.lower().startswith(
            ("http://", "https://")
        ):
            raise UrlValidationError(
                f"Unsupported URL scheme '{scheme_name}'. Only http/https are allowed."
            )

    # Allow users to paste without scheme (example.com/path)
    if not re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
        cleaned = "https://" + cleaned

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlValidationError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only http/https are allowed."
        )

    host = (parsed.hostname or "").strip()
    if not host:
        raise UrlValidationError("URL is missing a hostname")

    if " " in cleaned:
        raise UrlValidationError("URL must not contain spaces")

    # Block clearly local/dangerous hosts for a safer demo default
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if host.lower() in blocked_hosts:
        raise UrlValidationError("Localhost URLs are not allowed")

    logger.info("url validated host=%s scheme=%s", host, scheme)
    return cleaned


def _normalize_text(node) -> str:
    text = node.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _extract_readable_text(html: str) -> str:
    """Extract the main readable body from HTML.

    Many blog themes put tiny related-post cards in <article> tags while the
    real post lives in a content widget. Prefer the longest plausible content
    block instead of blindly taking the first <article>.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    candidates: list[tuple[int, str]] = []

    # Common CMS / builder content containers first
    css_selectors = [
        ".elementor-widget-theme-post-content",
        ".entry-content",
        ".post-content",
        ".blog-content",
        ".article-content",
        "[itemprop='articleBody']",
        "main",
        "article",
    ]
    for selector in css_selectors:
        for node in soup.select(selector):
            text = _normalize_text(node)
            if text:
                candidates.append((len(text), text))

    # Also consider large sections/divs as a fallback signal
    for node in soup.find_all(["section", "div"]):
        text = _normalize_text(node)
        # Ignore tiny chrome and huge whole-page wrappers for ranking
        if 300 <= len(text) <= 80_000:
            candidates.append((len(text), text))

    if candidates:
        # Longest text wins — usually the real article body
        candidates.sort(key=lambda item: item[0], reverse=True)
        best_len, best_text = candidates[0]
        logger.info("html extract chose candidate chars=%s", best_len)
        return best_text

    root = soup.body or soup
    text = _normalize_text(root)
    logger.info("html extract fallback body chars=%s", len(text))
    return text


def fetch_url_text(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Validate URL, download page, return cleaned visible text."""
    cleaned_url = validate_url(url)
    logger.info("fetching url=%s", cleaned_url)

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(cleaned_url)
    except httpx.TimeoutException as exc:
        logger.warning("url timeout url=%s", cleaned_url)
        raise UrlFetchError(f"Timed out fetching URL: {cleaned_url}") from exc
    except httpx.RequestError as exc:
        logger.warning("url request error url=%s err=%s", cleaned_url, exc)
        raise UrlFetchError(f"Could not reach URL: {cleaned_url}") from exc

    if response.status_code >= 400:
        logger.warning(
            "url bad status url=%s status=%s",
            cleaned_url,
            response.status_code,
        )
        raise UrlFetchError(
            f"URL returned HTTP {response.status_code}: {cleaned_url}"
        )

    content_type = (response.headers.get("content-type") or "").lower()
    if content_type and "html" not in content_type and "text" not in content_type:
        raise UrlFetchError(
            f"URL does not look like an HTML/text page (content-type={content_type})"
        )

    text = _extract_readable_text(response.text)
    if len(text) < MIN_CONTENT_CHARS:
        logger.warning("url empty/short content url=%s chars=%s", cleaned_url, len(text))
        raise UrlFetchError(
            "Fetched page has almost no readable text. Try a different URL."
        )

    if len(text) > MAX_CONTENT_CHARS:
        logger.info(
            "url content truncated url=%s from=%s to=%s",
            cleaned_url,
            len(text),
            MAX_CONTENT_CHARS,
        )
        text = text[:MAX_CONTENT_CHARS]

    logger.info("url fetch ok url=%s chars=%s", cleaned_url, len(text))
    return text
