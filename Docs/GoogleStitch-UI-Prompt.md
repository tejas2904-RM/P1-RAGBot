# Google Stitch Prompt — Groww RAG Mutual Fund FAQ Assistant (Light Theme)

Copy everything inside the block below into Google Stitch.

---

```
Design a light-theme, premium fintech web UI for a single-page “Mutual Fund FAQ Assistant” chatbot. The product answers factual questions about five HDFC mutual fund schemes using data sourced from Groww.in. It is facts-only — never investment advice. Visual tone: clean, trustworthy, modern Indian fintech (Groww-adjacent polish: crisp whitespace, soft shadows, confident blue accents) without copying Groww branding or logos.

## Product context
- Name: Mutual Fund FAQ Assistant
- Tagline / badge: “Facts-only. No investment advice.”
- Data source: Groww.in (cite source URL on every factual answer)
- Scope: 5 HDFC Direct Growth schemes only — Mid Cap, Equity (Flexi Cap), Focused, ELSS Tax Saver, Large Cap
- Supported factual fields: expense ratio, exit load, minimum SIP, lock-in period, riskometer, benchmark, fund manager, AUM, and similar objective scheme metadata
- Refuses: investment advice, comparisons (“which is better?”), performance predictions, PII requests, out-of-scope questions

## Target users
Retail investors researching HDFC schemes on Groww who want quick, cited factual answers — not recommendations.

## Layout (desktop + mobile)
Single-column centered layout, max width ~760px on desktop, full-width on mobile.

### 1. Header
- App title: “Mutual Fund FAQ Assistant”
- Subtle subtitle optional: “HDFC schemes · Groww sources”
- Prominent disclaimer pill/chip: “Facts-only. No investment advice.” (soft blue background, medium weight)
- No hamburger menu — single-purpose app

### 2. Status banner (conditional)
- Warning style when index/API unavailable
- Example: “The knowledge index is not ready. Run indexing before asking questions.”
- Hidden when system is healthy

### 3. Welcome card
- Section label: “Welcome”
- Body copy: “Ask factual questions about five HDFC mutual fund schemes (Direct Growth) sourced from Groww. I can help with expense ratio, exit load, minimum SIP, lock-in period, riskometer, benchmark, and similar objective details. I cannot provide investment advice, comparisons, or performance projections.”
- Friendly but professional — not chatty or salesy

### 4. Example questions card
- Section label: “Try asking”
- Three tappable suggestion chips/buttons (full width, left-aligned text):
  1. “What is the expense ratio of HDFC Mid Cap Fund?”
  2. “What is the lock-in period of HDFC ELSS Tax Saver Fund?”
  3. “What is the benchmark index of HDFC Large Cap Fund?”
- Hover/focus: light blue border + background lift
- Clicking fills the input and submits (show loading state)

### 5. Chat input card
- Label: “Your question”
- Multi-line textarea (3 rows), placeholder: “e.g. What is the expense ratio of HDFC Mid Cap Fund?”
- Character limit hint: 500 characters (subtle, bottom-right)
- Primary CTA button: “Ask” (right-aligned)
- Loading state: button disabled, label “Thinking…” with subtle spinner

### 6. Response card (appears after submit)
- Section label: “Response”
- Answer body: readable 16–17px, comfortable line height
- Metadata block below answer (muted gray):
  - “Source:” + clickable Groww URL (external link icon)
  - “Last updated from sources: YYYY-MM-DD”
- **Factual success state:** white card, calm confidence
- **Refusal state:** warm amber/cream background (not error red) — for advice/comparison/performance refusals
- **Error state:** neutral message — “Something went wrong while processing your question. Please try again.”

### 7. Footer
- Centered, small muted text repeating disclaimer: “Facts-only. No investment advice.”

## Visual design system (light theme, premium)
- Background: soft cool gradient (#EEF3F9 → #F4F7FB)
- Surface/cards: pure white #FFFFFF
- Primary text: #1A2332
- Muted text: #5C6B7A
- Primary accent: deep trust blue #0B5CAB (buttons, links, focus rings)
- Accent hover: #094A8F
- Borders: #D8E0EA
- Card radius: 12px; inner controls 8px
- Shadow: soft elevation `0 8px 24px rgba(26,35,50,0.08)`
- Typography: modern sans (Inter, SF Pro, or Segoe UI) — strong hierarchy, no decorative fonts
- Spacing: generous padding (20px cards), 16px section gaps
- Micro-interactions: 150ms transitions on hover/focus; visible focus rings for accessibility
- Premium touches: subtle glass/blur optional on header only; fine 1px borders; no clutter, no stock photos

## UX behaviors to show in mockups
1. **Default / empty** — welcome + examples visible, no response yet
2. **Loading** — Ask button in “Thinking…” state
3. **Successful factual answer** — answer + Groww source link + last updated date
4. **Refusal** — amber-tinted response card with fixed refusal copy (no source URL)
5. **Mobile (375px)** — stacked cards, full-width buttons, readable tap targets (min 44px)

## Accessibility
- WCAG AA contrast on text and buttons
- Visible keyboard focus states
- `aria-live` region for response updates
- Semantic headings (h1 app title, h2 section labels)
- Disclaimer marked as note/status, not dismissible marketing

## Do NOT include
- Buy/sell CTAs, portfolio widgets, charts, NAV graphs, star ratings, “recommended for you”
- Groww or HDFC official logos (generic fintech aesthetic only)
- Dark mode (light theme only for this prompt)
- Sidebar navigation, login, user accounts, chat history drawer
- Emoji-heavy or playful consumer-app styling

## Deliverables
Generate high-fidelity mockups for:
- Desktop (1440px) — default, loading, success, refusal states
- Mobile (375px) — default + success state

Export as a cohesive design system: colors, type scale, button styles, input styles, card component, example chip, response panel variants, disclaimer badge.
```

---

## Notes for implementation

After Stitch generates the UI, map components to the existing frontend:

| Stitch component | Project file |
|------------------|--------------|
| Page structure | `phases/phase5/frontend/index.html` |
| Styles / tokens | `phases/phase5/frontend/static/css/styles.css` |
| Interactions | `phases/phase5/frontend/static/js/app.js` |
| Copy / examples | `phases/phase5/config.py` |

API endpoints the UI consumes: `GET /api/v1/meta`, `GET /health`, `POST /api/v1/chat`.
