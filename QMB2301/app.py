import os
import glob
import base64
from datetime import date, datetime

import anthropic
import requests
import streamlit as st
from dotenv import load_dotenv
import extra_streamlit_components as stx
from PIL import Image

from config import (CLASS_PASSWORD, COURSE_NAME, END_DATE, INSTRUCTOR,
                    MAX_TOKENS, MODEL, REQUIRE_PASSWORD, RESOURCES_PATH,
                    SEMESTER, START_DATE)
from system_prompt import build_system_prompt

load_dotenv()

# ─── Paths (work both locally and on Streamlit Cloud) ──────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Maya — QMB 2301 Tutor", page_icon="🌟")

MAYA_AVATAR = Image.open(os.path.join(BASE_DIR, "assets", "maya_clean.png"))
COOKIE_NAME = "maya_auth"


# ─── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_resources() -> str:
    token = os.getenv("GITHUB_RESOURCES_TOKEN") or st.secrets.get("GITHUB_RESOURCES_TOKEN", "")
    repo  = os.getenv("RESOURCES_REPO") or st.secrets.get("RESOURCES_REPO", "MasoodDastan/Dastan-Course-Tutor-Resources")

    if token:
        headers  = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        api_url  = f"https://api.github.com/repos/{repo}/contents/{RESOURCES_PATH}"
        resp     = requests.get(api_url, headers=headers)
        if resp.ok:
            files = sorted([f for f in resp.json() if f["name"].endswith(".txt")],
                           key=lambda x: x["name"])
            parts = []
            for f in files:
                file_resp = requests.get(f["url"], headers=headers)
                if file_resp.ok:
                    content = base64.b64decode(file_resp.json()["content"]).decode("utf-8").strip()
                    if content:
                        parts.append(f"### {f['name']}\n{content}")
            return "\n\n".join(parts)

    # fallback: local files (for development)
    files = sorted(glob.glob(os.path.join(BASE_DIR, "resources", "*.txt")))
    parts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
        if content:
            parts.append(f"### {os.path.basename(path)}\n{content}")
    return "\n\n".join(parts)


def is_within_semester() -> bool:
    return START_DATE <= date.today() <= END_DATE


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("ANTHROPIC_API_KEY is not set.")
        st.stop()
    return anthropic.Anthropic(api_key=api_key)


def get_sheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_path = os.path.join(BASE_DIR, "credentials.json")
        if os.path.exists(creds_path):
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        elif "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        else:
            return None
        sheet_id = os.getenv("GOOGLE_SHEET_ID") or st.secrets.get("GOOGLE_SHEET_ID")
        if not sheet_id:
            return None
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(sheet_id).sheet1
        if not ws.get_all_values():
            ws.append_row(["Timestamp", "Semester", "Question", "Answer"])
        return ws
    except Exception:
        return None


def log_exchange(question: str, answer: str):
    sheet = get_sheet()
    if sheet is None:
        return
    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            SEMESTER, question, answer,
        ])
    except Exception:
        pass


# ─── Cookie-based Auth ─────────────────────────────────────────────────────────
cookie_manager = stx.CookieManager()
auth_cookie = cookie_manager.get(COOKIE_NAME)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = (not REQUIRE_PASSWORD) or (auth_cookie == CLASS_PASSWORD)
if "messages" not in st.session_state:
    st.session_state.messages = []


# ─── Date Gate ─────────────────────────────────────────────────────────────────
if not is_within_semester():
    st.title("🌟 Maya")
    st.caption(f"{COURSE_NAME} · {INSTRUCTOR}")
    st.info(
        f"Maya is available from **{START_DATE.strftime('%B %d, %Y')}** "
        f"to **{END_DATE.strftime('%B %d, %Y')}** ({SEMESTER}).\n\n"
        "Please check back when the semester begins."
    )
    st.stop()


# ─── Password Gate ─────────────────────────────────────────────────────────────
if REQUIRE_PASSWORD and not st.session_state.authenticated:
    st.title("Hi, I'm Maya! 👋")
    st.caption(f"{COURSE_NAME}")
    st.write("Enter the class password to get started.")
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if pw == CLASS_PASSWORD:
            cookie_manager.set(
                COOKIE_NAME, CLASS_PASSWORD,
                expires_at=datetime(END_DATE.year, END_DATE.month, END_DATE.day)
            )
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()


# ─── Main Chat UI ──────────────────────────────────────────────────────────────
st.title("🌟 Maya")
st.caption(f"{COURSE_NAME} · {INSTRUCTOR}")

with st.expander("ℹ️ How Maya works", expanded=False):
    st.markdown(
        "- I only know what Dr. Dastan has shared with me — no outside sources.\n"
        "- I won't solve graded homework or discuss exam questions.\n"
        "- I *will* generate practice questions and guide you through problems step by step.\n"
        "- For course policy questions, contact Dr. Dastan at sdastan@utep.edu.\n"
        "- **Conversations may be logged anonymously for course improvement purposes.**"
    )

# Greeting on fresh session
if not st.session_state.messages:
    with st.chat_message("assistant", avatar=MAYA_AVATAR):
        st.markdown(
            "¡Hola! I'm here to help you *understand* the material — not just get the right answer. "
            "Ask me to explain a concept, quiz you on a chapter, or walk through a problem together. "
            "What would you like to work on? 😊"
        )

# Chat history
for msg in st.session_state.messages:
    avatar = MAYA_AVATAR if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Chat input
if user_input := st.chat_input("Ask Maya a question…"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=MAYA_AVATAR):
        with st.spinner("Maya is thinking…"):
            client = get_client()
            system = build_system_prompt(load_resources())
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=st.session_state.messages,
            )
            reply = response.content[0].text
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    log_exchange(user_input, reply)

# Sidebar
with st.sidebar:
    st.markdown("### 🌟 Maya")
    st.caption(f"Messages this session: {len(st.session_state.messages)}")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption(f"Instructor: {INSTRUCTOR}")
    st.caption("sdastan@utep.edu")
