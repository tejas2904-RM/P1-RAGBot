"""Validate corpus configuration and URL allowlist."""

from __future__ import annotations

from urllib.parse import urlparse

from phases.phase1.config import ALLOWED_URLS, REQUIRED_CATEGORIES
from phases.phase1.models import UrlsConfig


class ValidationError(Exception):
    """Raised when corpus configuration fails validation."""


def is_allowed_url(url: str) -> bool:
    return url in ALLOWED_URLS


def validate_url_allowlist(url: str, *, context: str = "URL") -> None:
    if not is_allowed_url(url):
        raise ValidationError(f"{context} is not in ALLOWED_URLS: {url}")


def validate_urls_config(config: UrlsConfig) -> None:
    if not config.schemes:
        raise ValidationError("urls.json must contain at least one scheme")

    if len(config.schemes) != len(ALLOWED_URLS):
        raise ValidationError(
            f"Expected exactly {len(ALLOWED_URLS)} schemes, found {len(config.schemes)}"
        )

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    categories: set[str] = set()

    for scheme in config.schemes:
        if scheme.id in seen_ids:
            raise ValidationError(f"Duplicate scheme_id: {scheme.id}")
        seen_ids.add(scheme.id)

        if scheme.url in seen_urls:
            raise ValidationError(f"Duplicate URL for scheme {scheme.id}")
        seen_urls.add(scheme.url)

        validate_url_allowlist(scheme.url, context=f"scheme {scheme.id}")

        parsed = urlparse(scheme.url)
        if parsed.scheme != "https" or parsed.netloc != "groww.in":
            raise ValidationError(f"scheme {scheme.id} URL must be https://groww.in/...")

        categories.add(scheme.category)

    if seen_urls != set(ALLOWED_URLS):
        missing = set(ALLOWED_URLS) - seen_urls
        extra = seen_urls - set(ALLOWED_URLS)
        if missing:
            raise ValidationError(f"urls.json missing pinned URLs: {sorted(missing)}")
        if extra:
            raise ValidationError(f"urls.json contains non-allowlisted URLs: {sorted(extra)}")

    if not REQUIRED_CATEGORIES.issubset(categories):
        missing_categories = REQUIRED_CATEGORIES - categories
        raise ValidationError(f"Missing required categories: {sorted(missing_categories)}")


def validate_scheme_registry_matches_urls(config: UrlsConfig, registry: UrlsConfig) -> None:
    config_by_id = {scheme.id: scheme for scheme in config.schemes}
    registry_by_id = {scheme.id: scheme for scheme in registry.schemes}

    if config_by_id.keys() != registry_by_id.keys():
        raise ValidationError("scheme_registry.json scheme ids do not match urls.json")

    for scheme_id, scheme in config_by_id.items():
        registry_scheme = registry_by_id[scheme_id]
        if scheme.url != registry_scheme.url:
            raise ValidationError(f"URL mismatch for scheme {scheme_id} between urls.json and scheme_registry.json")
        if scheme.category != registry_scheme.category:
            raise ValidationError(
                f"Category mismatch for scheme {scheme_id} between urls.json and scheme_registry.json"
            )
