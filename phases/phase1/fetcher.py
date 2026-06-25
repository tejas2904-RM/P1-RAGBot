"""Allowlist-enforced fetcher for pinned Groww scheme pages."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import httpx

from phases import paths
from phases.phase1.config import RAW_SNAPSHOT_FILES
from phases.phase1.models import Scheme, SourceRecord
from phases.phase1.validator import ValidationError, validate_url_allowlist

DEFAULT_TIMEOUT = 60.0
DEFAULT_USER_AGENT = "RAG-Chatbot-Phase1/1.0 (facts-only corpus fetcher)"


def content_hash(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def raw_snapshot_path(scheme_id: str, raw_dir: Path | None = None) -> Path:
    filename = RAW_SNAPSHOT_FILES.get(scheme_id)
    if not filename:
        raise ValidationError(f"No raw snapshot mapping for scheme_id: {scheme_id}")
    return (raw_dir or paths.RAW_DIR) / filename


class CorpusFetcher:
    """Fetches only URLs present in the hard-coded allowlist."""

    def __init__(
        self,
        *,
        raw_dir: Path | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        self.raw_dir = raw_dir or paths.RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> CorpusFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_scheme(self, scheme: Scheme) -> SourceRecord:
        validate_url_allowlist(scheme.url, context=f"fetch for scheme {scheme.id}")

        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            response = self.client.get(scheme.url)
            final_url = str(response.url)
            validate_url_allowlist(final_url, context=f"redirect target for scheme {scheme.id}")

            if response.status_code != 200:
                return SourceRecord(
                    scheme_id=scheme.id,
                    url=scheme.url,
                    status="fetch_failed",
                    last_fetched=timestamp,
                    http_status=response.status_code,
                    error=f"HTTP {response.status_code}",
                )

            body = response.text
            digest = content_hash(body)
            snapshot_path = raw_snapshot_path(scheme.id, self.raw_dir)
            snapshot_path.write_text(body, encoding="utf-8")

            return SourceRecord(
                scheme_id=scheme.id,
                url=scheme.url,
                status="ok",
                last_fetched=timestamp,
                content_hash=digest,
                http_status=response.status_code,
                raw_snapshot=snapshot_path.name,
            )
        except ValidationError:
            raise
        except httpx.HTTPError as exc:
            return SourceRecord(
                scheme_id=scheme.id,
                url=scheme.url,
                status="fetch_failed",
                last_fetched=timestamp,
                error=str(exc),
            )

    def fetch_all(self, schemes: list[Scheme]) -> list[SourceRecord]:
        return [self.fetch_scheme(scheme) for scheme in schemes]
