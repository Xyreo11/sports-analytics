import math
from datetime import date
import pandas as pd
import streamlit as st
from common import auth_guard, inject_dark_theme, sql_df, call_proc, null_or

st.set_page_config(page_title="Players · Sports Analytics", page_icon="👟", layout="wide")
inject_dark_theme()
auth_guard()

st.title("👟 Players")

c1, c2, c3, c4, c5 = st.columns(5)
teams = sql_df("SELECT team_id, team_name FROM Teams ORDER BY team_name")
team_map = {r.team_name: r.team_id for _, r in teams.iterrows()}
team_choice = c1.selectbox("Team", ["All"] + list(team_map.keys()))
team_id = None if team_choice == "All" else team_map[team_choice]

pos_list = sql_df("SELECT DISTINCT position FROM Players WHERE position IS NOT NULL ORDER BY position")
pos_choice = c2.selectbox("Position", ["All"] + pos_list["position"].dropna().tolist())

nat_list = sql_df("SELECT DISTINCT nationality FROM Players WHERE nationality IS NOT NULL ORDER BY nationality")
nat_choice = c3.selectbox("Nationality", ["All"] + nat_list["nationality"].dropna().tolist())

q = c4.text_input("Search (name/position/nationality)")
min_points = c5.number_input("Min points", min_value=0, value=0, step=1)

df = sql_df("CALL search_players(:q, :minpts, :team)", {
    "q": q,
    "minpts": int(min_points),
    "team": team_id
})

if pos_choice != "All":
    df = df[df["position"] == pos_choice]
if nat_choice != "All":
    df = df[df["nationality"] == nat_choice]

if st.session_state.user.get("role") == "admin":
    with st.expander("➕ Add player (Admin only)"):
        with st.form("add_player_form"):
            a1, a2, a3 = st.columns(3)
            name = a1.text_input("Name*")
            dob = a2.date_input("DOB", value=None)
            pos = a3.text_input("Position")

            b1, b2 = st.columns(2)
            nat = b1.text_input("Nationality")
            tsel = b2.selectbox("Team", list(team_map.keys()) if team_map else [])

            submit = st.form_submit_button("Add")
            if submit:
                if not name:
                    st.error("Name is required.")
                else:
                    ok = call_proc(
                        "add_player",
                        p_name=name,
                        p_dob=str(dob) if dob else None,
                        p_position=null_or(pos),
                        p_nationality=null_or(nat),
                        p_team_id=team_map.get(tsel),
                    )
                    if ok:
                        st.success("Player added.")
                        st.rerun()
else:
    st.caption("Only admins can add new players. Go to **Admin > Players**.")

if df.empty:
    st.info("No players found.")
else:
    n_cols = 3
    n_rows = math.ceil(len(df) / n_cols)

    for r in range(n_rows):
        cols = st.columns(n_cols)
        for i, col in enumerate(cols):
            idx = r * n_cols + i
            if idx >= len(df):
                break

            row = df.iloc[idx]
            status = "Injured" if row["injured"] else "Fit"
            status_class = "bad" if row["injured"] else "ok"

            with col:
                st.markdown(
                    f"""
                    <div class="app-card">
                        <div class="title-20">{row['name']}</div>
                        <span class="app-badge">{row['team_name'] or 'No Team'}</span>
                        <span class="app-badge">{row['position'] or '-'}</span>
                        <span class="app-badge">{row['nationality'] or '-'}</span>
                        <div class="muted" style="margin-top:8px;">Points: <b>{int(row['total_points'])}</b></div>
                        <div class="{status_class}" style="margin-top:6px;">{status}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
