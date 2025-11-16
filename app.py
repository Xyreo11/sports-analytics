# app.py
import streamlit as st
from common import auth_guard, inject_dark_theme

st.set_page_config(page_title="Sports Analytics", page_icon="⚽", layout="wide")
inject_dark_theme()
auth_guard()

st.title("⚽ Sports Analytics")
st.markdown("""
Use the sidebar Pages to navigate:

- **Dashboard**
- **Players**
- **Matches**
- **Injuries**
- **Admin**
""")
