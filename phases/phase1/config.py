"""Pinned URL allowlist and corpus constants for Phase 1."""

from __future__ import annotations

# Only these exact 5 URLs are permitted anywhere in the system.
# No other domain — including amfiindia.com or sebi.gov.in — is fetched or cited.
ALLOWED_URLS: tuple[str, ...] = (
    "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
    "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
)

AMC_NAME = "HDFC Mutual Fund"
SOURCE_NAME = "groww.in"

# Maps scheme_id -> raw HTML filename under corpus/raw/
RAW_SNAPSHOT_FILES: dict[str, str] = {
    "hdfc-mid-cap": "hdfc-mid-cap.html",
    "hdfc-equity": "hdfc-equity.html",
    "hdfc-focused": "hdfc-focused.html",
    "hdfc-elss": "hdfc-elss.html",
    "hdfc-large-cap": "hdfc-large-cap.html",
}

# Aliases for scheme name resolution (Phase 1 + Phase 4 integration).
SCHEME_ALIASES: dict[str, list[str]] = {
    "hdfc-mid-cap": [
        "hdfc mid cap",
        "hdfc mid cap fund",
        "hdfc midcap",
        "mid cap",
        "midcap",
        "mid cap fund",
    ],
    "hdfc-equity": [
        "hdfc equity",
        "hdfc equity fund",
        "equity fund",
        "flexi cap",
        "flexi-cap",
        "flexicap",
    ],
    "hdfc-focused": [
        "hdfc focused",
        "hdfc focused fund",
        "focused fund",
        "focused",
    ],
    "hdfc-elss": [
        "hdfc elss",
        "hdfc elss tax saver",
        "elss tax saver",
        "elss",
        "tax saver",
        "tax saver fund",
    ],
    "hdfc-large-cap": [
        "hdfc large cap",
        "hdfc large cap fund",
        "large cap",
        "large-cap",
        "largecap",
        "large cap fund",
    ],
}

REQUIRED_CATEGORIES = frozenset({"mid-cap", "flexi-cap", "focused", "elss", "large-cap"})
