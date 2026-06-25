"""Resolve user-facing scheme names and aliases to corpus scheme ids."""

from __future__ import annotations

import re

from phases.phase1.models import Scheme, UrlsConfig


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^\w\s-]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


class SchemeResolver:
    def __init__(self, config: UrlsConfig) -> None:
        self._schemes = config.schemes
        self._by_id = {scheme.id: scheme for scheme in config.schemes}
        self._alias_map: dict[str, str] = {}
        self._build_alias_map()

    def _build_alias_map(self) -> None:
        for scheme in self._schemes:
            candidates = {
                _normalize(scheme.scheme_name),
                _normalize(scheme.id.replace("-", " ")),
                *(_normalize(alias) for alias in scheme.aliases),
            }
            for candidate in candidates:
                if candidate:
                    self._alias_map[candidate] = scheme.id

    def resolve(self, query: str) -> Scheme | None:
        normalized_query = _normalize(query)
        if not normalized_query:
            return None

        for scheme in self._schemes:
            if _normalize(scheme.scheme_name) in normalized_query:
                return scheme
            if scheme.id.replace("-", " ") in normalized_query:
                return scheme

        best_match_id: str | None = None
        best_match_len = 0
        for alias, scheme_id in self._alias_map.items():
            if alias in normalized_query and len(alias) > best_match_len:
                best_match_id = scheme_id
                best_match_len = len(alias)

        if best_match_id:
            return self._by_id[best_match_id]
        return None

    def is_in_corpus(self, query: str) -> bool:
        return self.resolve(query) is not None

    def all_scheme_ids(self) -> list[str]:
        return list(self._by_id.keys())
