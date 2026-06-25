"""Tests for allowlist-enforced fetcher."""

from __future__ import annotations

import httpx
import pytest

from phases.phase1.fetcher import CorpusFetcher, content_hash
from phases.phase1.models import Scheme
from phases.phase1.validator import ValidationError


@pytest.fixture
def mid_cap_scheme() -> Scheme:
    return Scheme(
        id="hdfc-mid-cap",
        scheme_name="HDFC Mid Cap Fund - Direct Growth",
        category="mid-cap",
        plan="Direct",
        option="Growth",
        url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    )


def test_content_hash_prefix() -> None:
    assert content_hash("hello").startswith("sha256:")


def test_fetcher_rejects_disallowed_redirect(mid_cap_scheme: Scheme, tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, text="<html>ok</html>")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)

    fetcher = CorpusFetcher(raw_dir=tmp_path, client=client)
    try:
        bad_scheme = Scheme(
            id="hdfc-mid-cap",
            scheme_name="HDFC Mid Cap Fund - Direct Growth",
            category="mid-cap",
            plan="Direct",
            option="Growth",
            url="https://groww.in/mutual-funds/not-allowed-page",
        )
        with pytest.raises(ValidationError, match="not in ALLOWED_URLS"):
            fetcher.fetch_scheme(bad_scheme)
    finally:
        fetcher.close()


def test_fetcher_stores_snapshot_on_success(mid_cap_scheme: Scheme, tmp_path) -> None:
    html = "<html><body>HDFC Mid Cap Fund</body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, text=html)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)

    with CorpusFetcher(raw_dir=tmp_path, client=client) as fetcher:
        record = fetcher.fetch_scheme(mid_cap_scheme)

    assert record.status == "ok"
    assert record.content_hash == content_hash(html)
    assert record.raw_snapshot == "hdfc-mid-cap.html"
    assert (tmp_path / "hdfc-mid-cap.html").read_text(encoding="utf-8") == html
