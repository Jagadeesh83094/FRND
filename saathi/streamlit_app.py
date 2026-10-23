import os
import requests
import streamlit as st

st.set_page_config(page_title="Saathi", page_icon="💛", layout="centered")

API_BASE = os.getenv("SAATHI_API_BASE", "https://saathi-api-icii.onrender.com").rstrip("/")
TIMEOUT = 90

st.markdown("""
<style>
    .stApp { max-width: 900px; margin: 0 auto; }
    .hero { padding: 1.3rem 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#fff2df,#f5e9ff); margin-bottom: 1rem; }
    .hero h1 { margin: 0; color: #382650; }
    .hero p { margin: .4rem 0 0; color: #604c70; }
</style>
<div class="hero">
  <h1>💛 Saathi</h1>
  <p>A little space to talk, reflect, and feel heard.</p>
</div>
""", unsafe_allow_html=True)

def api_request(method, path, *, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method, f"{API_BASE}{path}", headers=headers, timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            "Couldn't reach Saathi's API. The Render service may be waking up; wait a minute and retry."
        ) from exc
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        if isinstance(detail, (dict, list)):
            detail = str(detail)
        raise RuntimeError(f"API returned {response.status_code}: {detail}")
    if response.status_code == 204 or not response.content:
        return None
    return response.json()

def clear_login():
    for key in ("token", "user", "characters", "selected_character"):
        st.session_state.pop(key, None)

if "token" not in st.session_state:
    login_tab, register_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        st.subheader("Welcome back")
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_submit = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if login_submit:
            try:
                result = api_request("POST", "/api/auth/login", json={
                    "email": login_email.strip(), "password": login_password
                })
                st.session_state.token = result["access_token"]
                st.session_state.user = result
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
    with register_tab:
        st.subheader("Create your Saathi account")
        st.caption("Use a strong password with at least 12 characters.")
        with st.form("register_form"):
            display_name = st.text_input("What should Saathi call you?")
            register_email = st.text_input("Email", key="register_email")
            register_password = st.text_input("Password (12+ characters)", type="password", key="register_password")
            register_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if register_submit:
            try:
                result = api_request("POST", "/api/auth/register", json={
                    "email": register_email.strip(),
                    "password": register_password,
                    "display_name": display_name.strip() or None,
                })
                st.session_state.token = result["access_token"]
                st.session_state.user = result
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
    st.info("Your account is handled by the Saathi API. Never share your password or access token.")
    st.stop()

token = st.session_state.token
user = st.session_state.get("user", {})
with st.sidebar:
    st.markdown("### Your Saathi")
    st.write(f"Signed in as **{user.get('display_name') or user.get('email', 'friend')}**")
    st.caption("Your conversations may contain personal information. Avoid sharing details you don't want stored.")
    if st.button("Log out", use_container_width=True):
        clear_login()
        st.rerun()
    st.divider()
    st.caption("API status")
    if st.button("Check connection", use_container_width=True):
        try:
            health = api_request("GET", "/api/health")
            st.success(f"API is {health.get('status', 'reachable')}; provider: {health.get('provider', 'unknown')}")
        except RuntimeError as exc:
            st.error(str(exc))

if "characters" not in st.session_state:
    try:
        st.session_state.characters = api_request("GET", "/api/characters", token=token)
    except RuntimeError as exc:
        st.error(f"Couldn't load your characters: {exc}")
        if st.button("Retry"):
            st.session_state.pop("characters", None)
            st.rerun()
        st.stop()

characters = st.session_state.characters or []
if not characters:
    st.warning("No characters are available for this account yet.")
    st.stop()

character_by_id = {str(c.get("id")): c for c in characters}
options = list(character_by_id.keys())
def format_character(cid):
    c = character_by_id[cid]
    nickname = c.get("nickname")
    return f"{c.get('display_name', cid)}" + (f" ({nickname})" if nickname else "")

default_id = st.session_state.get("selected_character")
if default_id not in options:
    default_id = options[0]
selected_id = st.selectbox(
    "Choose your companion", options, index=options.index(default_id),
    format_func=format_character, key="character_picker"
)
if selected_id != st.session_state.get("active_character"):
    st.session_state.active_character = selected_id
    st.session_state.messages = []
    try:
        session = api_request("GET", f"/api/characters/{selected_id}/session", token=token)
        for message in session.get("messages", []):
            role = "assistant" if message.get("role") in ("assistant", "character") else "user"
            st.session_state.messages.append({"role": role, "content": message.get("content", "")})
    except RuntimeError:
        pass

character = character_by_id[selected_id]
st.markdown(f"### Chat with {character.get('display_name', 'your companion')}")
if character.get("short_description"):
    st.caption(character["short_description"])
st.caption("Saathi is an AI companion, not a human or a substitute for professional help.")

if st.button("Start with a greeting", use_container_width=True):
    try:
        result = api_request("POST", f"/api/characters/{selected_id}/greeting", token=token, params={"speak": "false"})
        st.session_state.messages.append({"role": "assistant", "content": result.get("reply", "Hello! I'm glad you're here.")})
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))

for message in st.session_state.get("messages", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("What's on your mind?")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Saathi is thinking…"):
            try:
                result = api_request(
                    "POST", f"/api/characters/{selected_id}/chat", token=token,
                    json={"text": prompt, "mode": "text", "speak": False}
                )
                reply = result.get("reply", "I'm here with you.")
                st.markdown(reply)
                if result.get("crisis", {}).get("flagged"):
                    st.info("If you may be in immediate danger, contact local emergency services or someone you trust.")
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except RuntimeError as exc:
                st.error(str(exc))
                st.session_state.messages.pop()
