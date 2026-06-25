"""Phase 6 — Streamlit Community Cloud backend / ops UI."""

from __future__ import annotations

import streamlit as st

from phases.phase5.config import APP_TITLE, DISCLAIMER, EXAMPLE_QUESTIONS, WELCOME_MESSAGE
from phases.phase5.service import ask_question, get_health
from phases.phase6.bootstrap import init_backend

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

_DARK_CSS = """
<style>
    .stApp { background-color: #0a0e17; color: #f1f5f9; }
    .block-container { padding-top: 2rem; max-width: 720px; }
    .disclaimer-pill {
        display: inline-block;
        padding: 0.35rem 0.875rem;
        border-radius: 999px;
        background: rgba(0, 208, 156, 0.12);
        border: 1px solid rgba(0, 208, 156, 0.2);
        color: #00d09c;
        font-size: 0.8125rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .welcome-text { color: #94a3b8; font-size: 0.9375rem; line-height: 1.55; }
    div[data-testid="stAlert"] { border-radius: 12px; }
    .stTextInput > label, .stTextArea > label { color: #cbd5e1 !important; font-weight: 600; }
    .stButton > button {
        border-radius: 10px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        background: #141b2d;
        color: #cbd5e1;
    }
    .stButton > button:hover {
        border-color: #00d09c;
        color: #f1f5f9;
    }
    div[data-testid="stFormSubmitButton"] > button {
        background: #00d09c !important;
        color: #0a0e17 !important;
        font-weight: 600;
        border: none !important;
    }
</style>
"""


@st.cache_resource(show_spinner="Starting backend…")
def _bootstrap() -> bool:
    init_backend()
    return True


def _render_health_panel() -> None:
    health = get_health()
    with st.expander("Backend status", expanded=not health.index_ready):
        cols = st.columns(2)
        cols[0].metric("Index chunks", health.index_chunk_count)
        cols[1].metric("LLM enabled", "Yes" if health.llm_enabled else "No")
        st.caption(
            f"Status: **{health.status}** · Generator: `{health.generator}` · "
            f"Index ready: **{health.index_ready}**"
        )


def _render_response(payload) -> None:
    body = payload.answer_body or payload.answer
    if payload.refused:
        st.warning(body)
    else:
        st.success(body)

    if payload.source_url:
        st.markdown(f"**Source:** [{payload.source_url}]({payload.source_url})")
    if payload.last_updated:
        st.caption(f"Last updated from sources: {payload.last_updated}")


def main() -> None:
    st.markdown(_DARK_CSS, unsafe_allow_html=True)

    try:
        _bootstrap()
    except Exception as exc:
        st.error(f"Backend failed to start: {exc}")
        st.stop()

    health = get_health()
    st.markdown(f'<p class="disclaimer-pill">{DISCLAIMER}</p>', unsafe_allow_html=True)
    st.title(APP_TITLE)

    if not health.index_ready:
        st.error(
            "The knowledge index is not ready. Ensure `corpus/processed/embedded_chunks.json` "
            "is in the repo or rebuild the index locally before deploying."
        )

    st.markdown(f'<p class="welcome-text">{WELCOME_MESSAGE}</p>', unsafe_allow_html=True)
    _render_health_panel()

    st.subheader("Try asking")
    example_cols = st.columns(len(EXAMPLE_QUESTIONS))
    pending_example: str | None = st.session_state.pop("pending_example", None)

    for col, question in zip(example_cols, EXAMPLE_QUESTIONS, strict=True):
        if col.button(question, use_container_width=True, key=f"ex-{question[:24]}"):
            pending_example = question

    with st.form("chat-form", clear_on_submit=False):
        query = st.text_area(
            "Your question",
            value=pending_example or "",
            placeholder="e.g. What is the expense ratio of HDFC Mid Cap Fund?",
            max_chars=500,
            height=100,
        )
        submitted = st.form_submit_button("Ask", disabled=not health.index_ready)

    if submitted and query.strip():
        with st.spinner("Thinking…"):
            try:
                response = ask_question(query.strip())
            except Exception:
                st.error("Something went wrong while processing your question. Please try again.")
            else:
                st.subheader("Response")
                _render_response(response)

    st.caption(DISCLAIMER)


main()
