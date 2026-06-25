# Phase Edge Cases — Mutual Fund FAQ Assistant

> **Reference:** [PhaseWiseArchitecture.md](./PhaseWiseArchitecture.md)  
> **Scope:** HDFC Mutual Fund — 5 pinned Groww URLs only (§1.4)  
> **Purpose:** Document edge cases, expected behavior, and handling strategy for each implementation phase

---

## How to Read This Document

Each edge case follows this structure:

| Column | Description |
|--------|-------------|
| **ID** | Unique identifier (`P{phase}-E{number}`) |
| **Scenario** | What can go wrong or what unusual input occurs |
| **Expected behavior** | What the system must do |
| **Handling** | Implementation or test guidance |

**Severity legend**

| Severity | Meaning |
|----------|---------|
| **Critical** | Compliance, security, or data-integrity risk — must block or fail safely |
| **High** | Wrong answer or wrong routing — must handle before release |
| **Medium** | Degraded experience but safe fallback acceptable |
| **Low** | Cosmetic or rare; document and monitor |

---

## Phase 1 — Corpus Definition & Source Curation

**Goal:** Establish a bounded knowledge base from exactly 5 pinned Groww URLs.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P1-E01 | Critical | Developer adds a 6th URL to `urls.json` (AMC site, AMFI, SEBI, etc.) | Fetcher and indexer reject it; system never contacts or cites it | Validate `urls.json` against hard-coded `ALLOWED_URLS` at startup; fail build/CI if mismatch |
| P1-E02 | Critical | URL in `urls.json` is typo'd or truncated | Ingestion fails for that scheme; no partial corpus silently shipped | Startup validation: HTTP HEAD/GET check; block index if any of the 5 URLs fail |
| P1-E03 | High | Groww page returns HTTP 403/503 during initial fetch | Scheme marked `fetch_failed` in `source_registry.json`; other 4 schemes still indexed | Per-URL error isolation; log status code; surface missing scheme in README known limitations |
| P1-E04 | High | Groww redirects one scheme URL to a different slug | Redirect target must still be one of the 5 allowed URLs or fetch is rejected | Follow redirects but validate final URL ∈ `ALLOWED_URLS`; reject if destination differs |
| P1-E05 | High | Same scheme listed twice under different slugs in config | Duplicate ingestion; conflicting chunks in index | Enforce unique `scheme_id` and unique `url` in `scheme_registry.json` |
| P1-E06 | Medium | User query references "HDFC Midcap" vs "HDFC Mid Cap Fund" (spacing/casing) | Scheme resolver maps aliases to `hdfc-mid-cap` | Maintain alias map in `scheme_registry.json` (`aliases: ["mid cap", "midcap", "hdfc mid cap"]`) |
| P1-E07 | Medium | User asks about HDFC scheme not in corpus (e.g., HDFC Balanced Advantage Fund) | Out-of-scope refusal — not RAG | Classifier checks scheme name against registry before retrieval (Phase 4) |
| P1-E08 | Medium | User asks about non-HDFC fund (e.g., SBI Bluechip) | Out-of-scope refusal | Same registry check; no retrieval attempted |
| P1-E09 | Medium | `scheme_registry.json` and `urls.json` drift (name/id mismatch) | Inconsistent citations or failed scheme filter | Single source of truth: generate registry from `urls.json` or validate cross-file consistency in CI |
| P1-E10 | Low | Groww page title differs slightly from canonical `scheme_name` | Facts still tied to correct `scheme_id` and `source_url` | Store canonical name from registry; treat page title as display-only |
| P1-E11 | Critical | Attempt to fetch Groww homepage or search results instead of scheme page | Request blocked | Fetcher accepts only exact URLs from `ALLOWED_URLS` — no host-level wildcard |
| P1-E12 | High | Raw HTML snapshot missing for a scheme after failed fetch | Re-index cannot diff; operator unaware | `source_registry.json` records `last_fetched`, `status`, `content_hash`; alert if hash absent |

### Phase 1 Test Checklist

- [ ] All 5 URLs resolve (200) and final URL ∈ `ALLOWED_URLS`
- [ ] Adding a 6th URL causes validation failure
- [ ] Each scheme has unique `scheme_id`, category, and pinned `source_url`
- [ ] Alias resolution works for common name variants
- [ ] Unlisted HDFC / non-HDFC scheme names trigger out-of-scope path (with Phase 4)

---

## Phase 2 — Document Ingestion & Vector Indexing

**Goal:** Transform 5 Groww pages into searchable, metadata-rich fact chunks.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P2-E01 | Critical | Groww changes DOM structure; selectors break | Missing fields logged; no silent empty index | Parser reports per-field extraction status; fail CI if required fields missing for any scheme |
| P2-E02 | High | `__NEXT_DATA__` present but field path moved | DOM fallback attempted; field marked missing if both fail | Layered extraction (JSON → DOM); version selectors in `groww_selectors.py` |
| P2-E03 | High | Expense ratio shown as "0.74%" in UI but "0.74" in JSON | Normalized to `0.74` + unit `%`; display string preserved | `normalizer.py` strips `%`, stores typed `value` + `unit` + `display_value` |
| P2-E04 | High | Exit load is "Nil" or "NA" vs "0%" | Stored as zero/none with consistent fact text | Normalizer maps `Nil`, `NA`, `—`, `0%` to canonical `exit_load` representation |
| P2-E05 | High | Minimum SIP shown as "₹100" with comma/space variants | Parsed to numeric 100, currency INR | Regex for ₹ amounts; reject unparseable values with warning |
| P2-E06 | High | ELSS lock-in absent on non-ELSS pages | No lock-in chunk created for schemes where field N/A | Field extraction is scheme-aware; skip N/A fields per category |
| P2-E07 | Medium | NAV/AUM snapshot date missing on page | `last_updated` falls back to fetch date; footer still valid | Priority: page date → `source_registry.last_fetched` |
| P2-E08 | Medium | Same fact appears in JSON and DOM with different values | Prefer structured JSON; log discrepancy | JSON wins; log DOM mismatch for manual review |
| P2-E09 | Medium | Page content unchanged but re-index runs | No re-embed; hash match skips work | `content_hash` diff in `reindex_job.py` |
| P2-E10 | Medium | Page content changed (hash differs) | Re-embed only affected scheme chunks | Delete stale chunks for that `scheme_id` before upsert |
| P2-E11 | High | Embedding API rate limit or timeout | Retry with backoff; partial index not marked complete | Batch embeds; idempotent upsert; job status flag |
| P2-E12 | High | Vector DB empty or corrupted | RAG returns "insufficient context" message — no hallucination | Health check: chunk count ≥ expected minimum before serving |
| P2-E13 | Medium | Duplicate fact statements for same field/scheme | Retriever may return redundant chunks | Dedupe at index time on `(scheme_id, field)` |
| P2-E14 | Critical | Parser extracts performance/CAGR/returns text | Must NOT create answerable chunks for returns | Blocklist fields: `returns`, `cagr`, `1y`, `3y`, `5y`, `rating`; exclude from `fact_builder.py` |
| P2-E15 | High | Unicode/encoding issues in HTML (₹, en-dash) | Clean UTF-8 text in chunks | Force UTF-8 decode; normalize special characters |
| P2-E16 | Low | Very long fund description text on page | Only target factual fields ingested — not full page prose | Field-scoped extraction; avoid indexing marketing copy |
| P2-E17 | Medium | Lock-in queried for non-ELSS fund | No lock-in chunk exists; RAG says insufficient context | Expected; optionally add static "Not applicable" only if present on Groww page |

### Phase 2 Test Checklist

- [ ] All required fields extracted for all 5 schemes (or explicitly N/A)
- [ ] Performance/return fields never appear in vector index
- [ ] Hash-based re-index skips unchanged pages
- [ ] Normalization handles `Nil`, `%`, `₹`, and date formats
- [ ] Duplicate `(scheme_id, field)` chunks deduped
- [ ] Empty/corrupt index blocks RAG startup

---

## Phase 3 — RAG Core (Retrieval + Generation)

**Goal:** Answer factual queries with ≤3 sentences, exactly one Groww citation, and footer.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P3-E01 | Critical | LLM invents expense ratio not in retrieved context | Answer rejected; fallback to insufficient-context message | Post-generation validation: answer values must match retrieved chunk `value` or `display_value` |
| P3-E02 | Critical | LLM cites URL not in `ALLOWED_URLS` | Response rejected and regenerated or replaced with safe fallback | `response_formatter.py` validates citation ∈ `ALLOWED_URLS` |
| P3-E03 | Critical | LLM returns 2+ source links | Formatter strips to exactly one — the top retrieved chunk's `source_url` | Enforce single link programmatically; ignore model-added links |
| P3-E04 | High | Query mentions scheme A but retrieval returns scheme B chunks | Scheme filter applied first; low-confidence cross-scheme results discarded | Detect scheme → filter `scheme_id`; re-query without filter only if no scheme detected |
| P3-E05 | High | Query mentions no scheme ("What is the expense ratio?") | Ask implicitly via top match OR list ambiguity in ≤3 sentences | Prefer highest-similarity chunk; if scores tied across schemes, state ambiguity briefly |
| P3-E06 | High | Query uses alias ("midcap fund expense ratio") | Correct scheme filter via alias map | Reuse Phase 1 alias resolution before retrieval |
| P3-E07 | High | Similarity below threshold — no relevant chunks | Fixed insufficient-context message; no fabricated answer | Threshold gate; no LLM call if retrieval empty |
| P3-E08 | High | Retrieved chunks conflict (same field, different values) | Prefer newest `last_updated`; if tie, prefer JSON-sourced chunk | Conflict resolver in retriever; log conflict |
| P3-E09 | Medium | User asks compound question ("expense ratio and exit load of Mid Cap") | Answer both facts in ≤3 sentences with one citation | Allow multi-field retrieval from same scheme; same `source_url` |
| P3-E10 | Medium | LLM produces 4+ sentences | Formatter truncates or regenerates to ≤3 sentences | Sentence-count validator |
| P3-E11 | Medium | Footer date missing in chunk metadata | Use `last_updated` from top chunk; fallback to fetch date | Never omit footer on factual answers |
| P3-E12 | High | Query is factual phrasing but asks for returns ("What was last year's return?") | Routed to Phase 4 performance refusal — not RAG | Classifier runs before RAG (Phase 4 integration) |
| P3-E13 | Medium | Empty or whitespace-only query | UI validation error; no backend call | Min length check in UI and API |
| P3-E14 | Medium | Very long query (prompt injection attempt) | Truncate input; classifier still runs; no instruction override | Max token/char limit; system prompt isolation |
| P3-E15 | High | LLM adds advisory language ("you should consider…") | Strip or reject; regenerate with stricter prompt | Advisory phrase blocklist in formatter |
| P3-E16 | Low | User asks for NAV snapshot | Return NAV + date if in corpus; no return math | Factual snapshot only from indexed field |
| P3-E17 | Medium | Hindi/Hinglish query ("HDFC Mid Cap ka expense ratio kya hai?") | Retrieve on embedding similarity; answer in English | No special-casing required if embeddings capture intent; add test cases |
| P3-E18 | Critical | Context window exceeded with top-k chunks | Reduce k or truncate chunk text; never drop metadata | Cap context size; prioritize highest-scoring chunk |

### Phase 3 Test Checklist

- [ ] Every factual answer has exactly 1 URL from `ALLOWED_URLS`
- [ ] No answer exceeds 3 sentences
- [ ] Footer always present on factual answers
- [ ] Empty retrieval → no hallucinated answer
- [ ] Scheme filter prevents cross-scheme contamination
- [ ] Performance questions never reach generator

---

## Phase 4 — Refusal Handling & Query Classification

**Goal:** Route queries correctly; refuse advisory, comparative, performance, PII, and out-of-scope inputs with fixed text — no external links.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P4-E01 | Critical | "Should I invest in HDFC Mid Cap Fund?" | Advisory refusal template; no RAG; no URL | Keyword + intent classifier → `refusal_handler.py` |
| P4-E02 | Critical | "Which is better — Mid Cap or Large Cap?" | Advisory/comparative refusal; no URL | Comparative patterns: `better`, `best`, `vs`, `compare` |
| P4-E03 | Critical | "What will the return be in 5 years?" | Performance refusal template; no URL | Performance patterns: `return`, `cagr`, `outperform`, `profit`, `gain` |
| P4-E04 | Critical | "Show me NAV history and calculate my gains" | Performance refusal; no calculations | Block even if NAV fact exists — calculation intent triggers refusal |
| P4-E05 | Critical | User submits PAN, Aadhaar, account number, OTP, email, or phone | PII refusal; input not logged | PII regex detection; redact from logs |
| P4-E06 | High | Factual + advisory combo ("Expense ratio of Mid Cap and should I buy it?") | Refusal wins — do not partial-answer | Classify whole query; prefer safe refusal on mixed intent |
| P4-E07 | High | "Is HDFC Mid Cap a good fund?" | Advisory refusal (opinion-seeking) | Opinion patterns: `good fund`, `worth it`, `safe`, `risky` in subjective sense |
| P4-E08 | High | "HDFC Flexi Cap expense ratio" — scheme not in corpus | Out-of-scope refusal (Flexi Cap not listed; Equity Fund is flexi-cap category) | Fuzzy match against registry; if no match → out-of-scope template |
| P4-E09 | Medium | "Tell me about mutual funds" (generic, no scheme) | Out-of-scope refusal | No matching scheme + broad topic → out-of-scope |
| P4-E10 | Medium | Factual query about listed scheme but field excluded (returns) | Performance refusal even if returns visible on Groww page | Intent on field type, not corpus presence |
| P4-E11 | Medium | Sarcasm or negation ("I definitely shouldn't invest, right?") | Advisory refusal | LLM classifier or expanded rules for rhetorical advice |
| P4-E12 | Medium | Direct Growth vs Regular plan question for unlisted Regular plan | Out-of-scope — corpus is Direct Growth only | Plan mismatch → out-of-scope with note in message scope |
| P4-E13 | Low | "Hi" / "Hello" / "Thanks" | Short polite reply or prompt to ask a factual question; no RAG | Greeting handler in UI or classifier |
| P4-E14 | Critical | Refusal template accidentally includes a URL | Must never ship — CI test scans refusal strings | Unit test: refusal outputs contain zero `http` substrings |
| P4-E15 | High | Classifier false negative — advice query reaches RAG | Generator may still refuse if prompt guardrails hold; formatter validates | Defense in depth: Phase 3 prompt + Phase 4 classifier |
| P4-E16 | High | Classifier false positive — factual query refused | User gets refusal incorrectly | Maintain labeled test set; tune hybrid classifier; log misroutes |
| P4-E17 | Medium | "Benchmark of Mid Cap vs Large Cap" | Comparative refusal even though benchmarks are factual | Comparison intent overrides factual sub-questions |

### Refusal Template Selection Matrix

| Detected intent | Template | External link |
|-----------------|----------|---------------|
| Advisory / comparative | Advisory / Comparative | **None** |
| Performance / returns | Performance / Returns | **None** |
| Unlisted scheme / topic | Out-of-scope | **None** |
| PII / account-specific | Advisory / Comparative (or dedicated PII-safe variant) | **None** |

### Phase 4 Test Checklist

- [ ] All refusal responses contain zero URLs
- [ ] Mixed intent queries refuse safely
- [ ] All 5 in-corpus schemes resolve correctly
- [ ] Unlisted schemes and non-HDFC funds → out-of-scope
- [ ] PII patterns never persisted in logs
- [ ] Performance queries never reach RAG

---

## Phase 5 — Minimal User Interface

**Goal:** Clean chat UI with persistent disclaimer and no PII collection.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P5-E01 | Critical | Disclaimer not visible on load or scroll | "Facts-only. No investment advice." always visible | Sticky `disclaimer_banner`; never hidden by chat overflow |
| P5-E02 | High | Example question click sends query but shows no loading state | Loading indicator while pipeline runs | Disable input + spinner during request |
| P5-E03 | High | Backend timeout or 500 error | User-friendly error message; no stack trace | Generic error copy; log details server-side only |
| P5-E04 | High | Response contains markdown link `[text](url)` | Render as single clickable Groww link | Sanitize renderer; validate URL host/path |
| P5-E05 | Medium | User submits empty query via Enter | Inline validation — no API call | Disable submit when input blank |
| P5-E06 | Medium | User pastes very long text | Truncate before send; show char limit | Max length on input field |
| P5-E07 | Critical | UI includes PAN/Aadhaar/account/OTP/email/phone fields | Must not exist — only free-text query box | UI audit; no optional identity fields |
| P5-E08 | Medium | Mobile viewport — disclaimer pushed off-screen | Disclaimer remains visible (sticky top or bottom) | Responsive CSS test |
| P5-E09 | Medium | Multiple rapid clicks on example questions | Debounce; queue or ignore duplicate in-flight requests | Disable buttons while loading |
| P5-E10 | Medium | Refusal response displayed — no source link section shown | UI hides citation block for refusals | Response type flag from backend (`factual` vs `refusal`) |
| P5-E11 | Low | User copies response including footer | Plain-text copy includes footer and single source URL | Copy-friendly formatting |
| P5-E12 | Medium | Groww URL in response is broken (typo from backend) | Link validation before render; show URL as text if invalid | Client-side check against `ALLOWED_URLS` |
| P5-E13 | Low | Session refresh clears chat history | Acceptable — stateless MVP | Document in README; no persistence required |
| P5-E14 | Medium | Accessibility: screen reader on disclaimer | Disclaimer announced; query input labeled | ARIA labels on banner and input |

### Phase 5 Test Checklist

- [ ] Disclaimer visible on desktop and mobile
- [ ] Exactly 3 example questions, all wired to backend
- [ ] No PII input fields
- [ ] Factual vs refusal responses render differently
- [ ] Errors show safe message only
- [ ] Only `ALLOWED_URLS` links are clickable

---

## Phase 6 — Integration, Testing & Documentation

**Goal:** End-to-end validation and shippable deliverables.

### Edge Cases

| ID | Severity | Scenario | Expected behavior | Handling |
|----|----------|----------|-------------------|----------|
| P6-E01 | Critical | E2E factual test expects URL not in `ALLOWED_URLS` | Test fails — catches citation drift | Golden-file tests with exact 5 URLs |
| P6-E02 | Critical | Re-index changes expense ratio; stale tests fail | Update golden answers or use live validation against index | Separate structural tests from value snapshots |
| P6-E03 | High | One of 5 Groww pages down during CI | CI warns but passes if 4/5 indexed and documented | `--min-schemes 4` flag with explicit waiver in README |
| P6-E04 | High | Classifier accuracy below 95% on test set | Block release until tuned | `tests/test_classifier.py` with ≥95% threshold |
| P6-E05 | High | Response occasionally exceeds 3 sentences in E2E | Formatter regression test fails | Automated sentence count assertion |
| P6-E06 | High | Refusal response contains URL in E2E scan | Build fails | Regex test: refusals must not match `https?://` |
| P6-E07 | Medium | README lists wrong scheme count or URLs | Docs drift from `urls.json` | Generate README scheme table from `urls.json` |
| P6-E08 | Medium | New developer runs app without indexing | Clear setup error: "index not found" | Preflight script checks vector store + chunk count |
| P6-E09 | Medium | LLM API key missing | Startup fails with actionable message | Env var validation on boot |
| P6-E10 | Low | Duplicate question in manual QA | Same answer and citation — deterministic at temp≈0 | Document non-determinism if temp > 0 |
| P6-E11 | High | Cross-phase regression: Phase 4 bypass added for "speed" | CI must include advisory queries in E2E suite | Mandatory refusal test suite in CI |
| P6-E12 | Medium | Groww markup change breaks parser silently | Nightly re-index + field coverage alert | Monitor required field count per scheme |

### End-to-End Scenario Matrix

| # | User input | Expected route | Citation |
|---|------------|----------------|----------|
| 1 | "What is the expense ratio of HDFC Mid Cap Fund?" | RAG factual | Mid Cap Groww URL |
| 2 | "Exit load on HDFC Focused Fund?" | RAG factual | Focused Groww URL |
| 3 | "Minimum SIP for HDFC Large Cap Fund?" | RAG factual | Large Cap Groww URL |
| 4 | "ELSS lock-in for HDFC ELSS Tax Saver?" | RAG factual | ELSS Groww URL |
| 5 | "Benchmark of HDFC Equity Fund?" | RAG factual | Equity Groww URL |
| 6 | "Should I invest in HDFC Mid Cap?" | Advisory refusal | None |
| 7 | "Mid Cap vs Large Cap — which is better?" | Comparative refusal | None |
| 8 | "What was the 1-year return of HDFC Mid Cap?" | Performance refusal | None |
| 9 | "Tell me about SBI Bluechip Fund" | Out-of-scope | None |
| 10 | "My PAN is ABCDE1234F, check my balance" | PII refusal | None |
| 11 | "" (empty) | UI validation | None |
| 12 | "Expense ratio and should I buy Mid Cap?" | Advisory refusal (mixed) | None |

### Phase 6 Test Checklist

- [ ] All 12 E2E scenarios pass
- [ ] README matches `urls.json` (5 schemes, 5 URLs)
- [ ] Disclaimer snippet present in README and UI
- [ ] Known limitations documented (5 schemes only, no external links, re-index dependency)
- [ ] CI enforces: single citation, ≤3 sentences, zero URLs in refusals
- [ ] Preflight catches missing index and missing API keys

---

## Cross-Phase Edge Cases

These scenarios span multiple phases and should be handled consistently.

| ID | Phases | Scenario | Expected behavior |
|----|--------|----------|-------------------|
| XP-E01 | 1, 2, 3 | Groww page updated overnight | Re-index updates chunks; answers reflect new values; `last_updated` footer changes |
| XP-E02 | 2, 3 | Field missing after Groww redesign | RAG returns insufficient-context for that field; no hallucination |
| XP-E03 | 3, 4 | Factual question about returns phrased neutrally ("1-year return of Mid Cap") | Phase 4 blocks before Phase 3 |
| XP-E04 | 1, 4 | User says "HDFC Equity" meaning Equity Fund | Alias resolves to `hdfc-equity` |
| XP-E05 | 3, 5 | Backend returns malformed JSON | UI shows safe error; no partial citation rendered |
| XP-E06 | 1–6 | Operator attempts to add AMFI link to refusal "for helpfulness" | Rejected by architecture and CI URL scan |
| XP-E07 | 2, 3, 6 | Same query before and after re-index | Citation URL unchanged (same pinned URL); fact value may change |
| XP-E08 | 4, 5 | Refusal displayed in UI | No source link block; disclaimer footer still shown |

---

## Summary by Severity

| Phase | Critical | High | Medium | Low |
|-------|----------|------|--------|-----|
| Phase 1 | 3 | 4 | 4 | 1 |
| Phase 2 | 2 | 7 | 7 | 1 |
| Phase 3 | 4 | 7 | 6 | 1 |
| Phase 4 | 6 | 6 | 5 | 1 |
| Phase 5 | 2 | 3 | 7 | 2 |
| Phase 6 | 2 | 5 | 4 | 1 |
| Cross-phase | — | — | 8 | — |

---

*Derived from [PhaseWiseArchitecture.md](./PhaseWiseArchitecture.md) — Mutual Fund FAQ Assistant (Facts-Only Q&A)*
