"""Normalisation for outbound links stored on documents (source_url, profile
links, and anything else that ends up in an href).

The bug this exists to prevent: a value stored as "cam.ac.uk/research/news/..."
has no scheme, so a browser resolves it as a *relative path*. The link then
silently becomes supasift.com/app/post/cam.ac.uk/... and 404s. Every stored
link must therefore be fully protocol-qualified before it is written.
"""

from urllib.parse import urlsplit, urlunsplit

# Only these can be put in an href. `source_url` is reader-supplied through
# compose, so allowing javascript:/data: would make it a stored-XSS vector.
SAFE_SCHEMES = ("http", "https")

_MAX_URL_LENGTH = 500


class InvalidExternalURL(ValueError):
    """Raised when a value cannot be made into a safe absolute http(s) URL."""


def normalize_external_url(raw: str | None) -> str | None:
    """Return a fully-qualified http(s) URL, or None for empty input.

    Prepends https:// when the scheme is missing. Raises InvalidExternalURL if
    the value carries an unsafe scheme or has no host.
    """
    if raw is None:
        return None

    candidate = raw.strip()
    if not candidate:
        return None

    if candidate.startswith("//"):
        # Protocol-relative. Valid, but pin it rather than inheriting.
        candidate = f"https:{candidate}"
    elif "://" not in candidate:
        scheme_prefix = candidate.split(":", 1)[0].lower()
        # "javascript:alert(1)" has a scheme but no "://" — reject it here
        # rather than silently turning it into https://javascript:alert(1).
        if ":" in candidate and scheme_prefix.isalpha():
            raise InvalidExternalURL(
                f"Links must start with http:// or https:// (got {scheme_prefix}:)."
            )
        candidate = f"https://{candidate}"

    parts = urlsplit(candidate)

    if parts.scheme.lower() not in SAFE_SCHEMES:
        raise InvalidExternalURL("Links must start with http:// or https://.")
    if not parts.hostname or "." not in parts.hostname:
        raise InvalidExternalURL("That link doesn't include a valid domain.")

    normalized = urlunsplit(
        (parts.scheme.lower(), parts.netloc, parts.path, parts.query, parts.fragment)
    )

    if len(normalized) > _MAX_URL_LENGTH:
        raise InvalidExternalURL(
            f"Links are capped at {_MAX_URL_LENGTH} characters."
        )

    return normalized


def needs_migration(raw: object) -> bool:
    """Whether a stored value is a non-empty string lacking an http(s) scheme."""
    if not isinstance(raw, str) or not raw.strip():
        return False
    return not raw.strip().lower().startswith(("http://", "https://"))
