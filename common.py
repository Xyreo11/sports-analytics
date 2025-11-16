import os
from datetime import date
import bcrypt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text


# Secret
DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}",
    pool_pre_ping=True
)


def inject_dark_theme():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], html, body {
      background: #0f1117 !important; color: #e5e7eb !important;
    }
    [data-testid="stSidebar"] {
      background: #151823 !important; border-right: 1px solid rgba(255,255,255,0.08);
    }
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1f2230 !important;
        color: #e5e7eb !important;
        border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);
    }
    .stButton button {
        background: #4f46e5 !important; color: white !important;
        border-radius: 8px; border: none !important;
    }
    .app-card {
      background: #151823; border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px; padding: 16px 18px;
      box-shadow: 0 10px 30px rgba(0,0,0,.18); color: #e5e7eb;
    }
    .title-20 { font-size:20px; font-weight:700; margin: 0 0 6px 0; }
    .muted { color: #a3a3a3; font-size: 13px; }
    .app-badge {
      display:inline-block; padding: 4px 10px; border-radius:999px;
      border:1px solid rgba(255,255,255,0.08); font-size:12px; color:#a3a3a3; margin-right:6px;
    }
    .ok { color:#22c55e; font-weight:700; }
    .bad { color:#ef4444; font-weight:700; }
    .modalBg { position:fixed; inset:0; background:rgba(0,0,0,.55); backdrop-filter:blur(4px); z-index:9998; }
    .modalBox {
      position:fixed; top:50%; left:50%; transform:translate(-50%,-50%);
      width:min(520px,92vw); background:#151823; color:#e5e7eb;
      border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:20px;
      z-index:9999; box-shadow:0 20px 60px rgba(0,0,0,.35);
    }
    .score-card { background:#151823; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:14px 18px; margin-bottom:12px; }
    .scoreline { display:flex; align-items:center; justify-content:space-between; font-size:22px; font-weight:800; margin:6px 0 10px; }
    .timeline-item { display:flex; gap:10px; align-items:center; margin:6px 0; font-size:14px; color:#a3a3a3; }
    .dot { width:8px; height:8px; border-radius:50%; background:#4f46e5; display:inline-block; }
    </style>
    """, unsafe_allow_html=True)


def sql_df(q: str, params=None) -> pd.DataFrame:
    try:
        with engine.begin() as conn:
            return pd.read_sql(text(q), conn, params=params or {})
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


def call_proc(proc_name: str, **kwargs) -> bool:
    placeholders = ", ".join([f":{k}" for k in kwargs])
    try:
        with engine.begin() as conn:
            conn.execute(text(f"CALL {proc_name}({placeholders})"), kwargs)
        return True
    except Exception as e:
        st.error(f"Procedure `{proc_name}` failed: {e}")
        return False


def null_or(val):
    return val if val not in (None, "", "-", "None") else None


def password_hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def password_check(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def login_form():
    st.markdown("### 🔐 Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            df = sql_df("CALL login_user(:email)", {"email": email})
            if df.empty:
                st.error("No user with that email.")
            else:
                u = df.iloc[0].to_dict()
                if password_check(pw, u["password_hash"]):
                    st.session_state.user = {
                        "id": u["user_id"],
                        "name": u["username"],
                        "role": u["role"],
                        "email": u["email"]
                    }
                    st.success(f"Welcome, {u['username']}!")
                    st.rerun()
                else:
                    st.error("Incorrect password.")


def signup_form():
    st.markdown("### 🆕 Create an account")
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        pw1 = st.text_input("Password", type="password")
        pw2 = st.text_input("Confirm password", type="password")
        role = st.selectbox("Role", ["viewer", "admin"])
        submit = st.form_submit_button("Sign up")

        if submit:
            if not username or not email or not pw1:
                st.error("Please fill all required fields.")
            elif pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                if call_proc(
                    "signup_user",
                    p_username=username,
                    p_email=email,
                    p_password_hash=password_hash(pw1),
                    p_role=role
                ):
                    st.success("Account created. You can login now.")


def auth_guard():
    inject_dark_theme()
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        st.sidebar.info("Please log in to continue.")
        c1, c2 = st.columns(2)
        with c1:
            login_form()
        with c2:
            signup_form()
        st.stop()

    user = st.session_state.user
    with st.sidebar:
        st.markdown("")
        st.markdown(
            f"""
            <div style="
                background-color:#1e1e2f;
                padding:12px 14px;
                border-radius:8px;
                margin-bottom:10px;
                border:1px solid #2d2d40;
            ">
                <p style="margin:0;font-size:13px;color:#c8c8d6;">👤 <strong>{user['name']}</strong></p>
                <p style="margin:0;font-size:12px;color:#8a8a99;">📧 {user['email']}</p>
                <p style="margin:0;font-size:12px;color:#8a8a99;">🛡 Role: {user['role'].capitalize()}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sign Out"):
        st.session_state.user = None
        st.rerun()


def open_modal(key: str, item_id: int):
    st.session_state.modal_open = True
    st.session_state[key] = item_id


def close_modal():
    st.session_state.modal_open = False
    st.session_state.current_player = None
    st.session_state.current_injury = None
    st.session_state.current_match = None
    st.rerun()


def render_modal_box(html_header: str):
    st.markdown('<div class="modalBg"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="modalBox">{html_header}', unsafe_allow_html=True)
