import os
import glob
import json
from datetime import date, datetime

import anthropic
import streamlit as st
from dotenv import load_dotenv

from config import (CLASS_PASSWORD, COURSE_NAME, END_DATE,
                    INSTRUCTOR, MAX_TOKENS, MODEL, SEMESTER, START_DATE)
from system_prompt import build_system_prompt

load_dotenv()

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title=f"{COURSE_NAME} Tutor", page_icon="📊")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def load_resources() -> str:
    """Load all .txt files from the resources/ folder into one string."""
    files = sorted(glob.glob(os.path.join("resources", "*.txt")))
    if not files:
        return ""
    parts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            name = os.path.basename(path)
            parts.append(f"### {name}\n{content}")
    return "\n\n".join(parts)


def is_within_semester() -> bool:
    today = date.today()
    return START_DATE <= today <= END_DATE


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY is not set. Please check your .env file.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def get_sheet():
    """Return the Google Sheet worksheet, or None if not configured."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

        # Support both local credentials file and Streamlit Cloud secrets
        if os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        elif "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        else:
            return None

        sheet_id = os.getenv("GOOGLE_SHEET_ID") or st.secrets.get("GOOGLE_SHEET_ID")
        if not sheet_id:
            return None

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.sheet1

        # Add header row if sheet is empty
        if worksheet.row_count == 0 or not worksheet.get_all_values():
            worksheet.append_row(["Timestamp", "Semester", "Question", "Answer"])

        return worksheet
    except Exception:
        return None


def log_exchange(question: str, answer: str):
    """Log a question/answer pair to Google Sheets silently."""
    sheet = get_sheet()
    if sheet is None:
        return
    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            SEMESTER,
            question,
            answer,
        ])
    except Exception:
        pass  # Never let logging failures break the app


# ─── Session State Init ────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []


# ─── Date Gate ─────────────────────────────────────────────────────────────────
if not is_within_semester():
    st.title(f"📊 {COURSE_NAME}")
    st.info(
        f"This tutor is available from **{START_DATE.strftime('%B %d, %Y')}** "
        f"to **{END_DATE.strftime('%B %d, %Y')}** ({SEMESTER}).\n\n"
        "Please check back when the semester begins."
    )
    st.stop()


# ─── Password Gate ─────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.title(f"📊 {COURSE_NAME} — AI Tutor")
    st.caption(f"{SEMESTER} · {INSTRUCTOR}")
    st.write("Enter the class password to access the tutor.")
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if pw == CLASS_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()


# ─── Main Chat UI ──────────────────────────────────────────────────────────────
st.title(f"📊 {COURSE_NAME} — AI Tutor")
st.caption(f"{SEMESTER} · {INSTRUCTOR}")
st.markdown(
    "Ask me anything about the course material. I won't give away answers, "
    "but I'll help you understand the concepts."
)

with st.expander("ℹ️ How this tutor works", expanded=False):
    st.markdown(
        "- I only know what your instructor has shared with me — no outside sources.\n"
        "- I won't solve homework or discuss exam questions.\n"
        "- For course policy questions, contact Dr. Dastan at sdastan@utep.edu.\n"
        "- **Conversations may be logged anonymously for course improvement purposes.**"
    )

# Show chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if user_input := st.chat_input("Ask a question about the course…"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            client = get_client()
            resources_text = load_resources()
            system = build_system_prompt(resources_text)

            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=st.session_state.messages,
            )
            reply = response.content[0].text

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    log_exchange(user_input, reply)

# Sidebar
with st.sidebar:
    st.header("Session")
    st.caption(f"Messages this session: {len(st.session_state.messages)}")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption(f"Instructor: {INSTRUCTOR}")
    st.caption("sdastan@utep.edu")
