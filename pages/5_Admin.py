from datetime import date
import streamlit as st
from common import auth_guard, inject_dark_theme, sql_df, call_proc, null_or

st.set_page_config(page_title="Admin · Sports Analytics", page_icon="🛠️", layout="wide")
inject_dark_theme()
auth_guard()

if st.session_state.user.get("role") != "admin":
    st.error("Admin access only.")
    st.stop()

st.title("🛠️ Admin Panel")
tabs = st.tabs(["Players", "Teams", "Matches", "Scores", "Injuries", "Audit Log"])


# ----------------------------- PLAYERS TAB -----------------------------
with tabs[0]:
    st.subheader("Players (Add / Update / Delete)")

    with st.expander("➕ Add Player"):
        with st.form("form_add_player"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name*", key="add_p_name")
            dob = c2.date_input("DOB", value=date(2000, 1, 1))
            position = c3.text_input("Position", key="add_p_pos")

            c4, c5 = st.columns(2)
            nationality = c4.text_input("Nationality", key="add_p_nat")

            teams = sql_df("SELECT team_id, team_name FROM Teams ORDER BY team_name")
            team_map = {r.team_name: r.team_id for _, r in teams.iterrows()}
            team_sel = c5.selectbox("Team", list(team_map.keys()), key="add_p_team")

            if st.form_submit_button("Add Player"):
                if name:
                    call_proc(
                        "add_player",
                        p_name=name,
                        p_dob=str(dob),
                        p_position=null_or(position),
                        p_nationality=null_or(nationality),
                        p_team_id=team_map[team_sel]
                    )
                    st.success("Added player ✔️")
                    st.rerun()

    with st.expander("✏️ Update / 🗑 Delete Player", expanded=True):
        players = sql_df("SELECT player_id, name FROM Players ORDER BY name")

        if not players.empty:
            player_map = {str(r.name): int(r.player_id) for _, r in players.iterrows()}
            selected_name = st.selectbox("Select Player", list(player_map.keys()), key="upd_player_select")
            selected_pid = player_map[selected_name]

            mode = st.radio("Action", ["Update", "Delete"], horizontal=True, key="upd_player_mode")

            if mode == "Update":
                full = sql_df("SELECT * FROM Players WHERE player_id=:pid", {"pid": selected_pid}).iloc[0]

                with st.form("form_update_player"):
                    c1, c2, c3 = st.columns(3)
                    new_name = c1.text_input("Name", full["name"])
                    new_dob = c2.date_input("DOB", value=full["dob"])
                    new_pos = c3.text_input("Position", full["position"] or "")

                    c4, c5 = st.columns(2)
                    new_nat = c4.text_input("Nationality", full["nationality"] or "")

                    teams = sql_df("SELECT team_id, team_name FROM Teams ORDER BY team_name")
                    tmap = {r.team_name: r.team_id for _, r in teams.iterrows()}
                    tnames = list(tmap.keys())

                    if full["team_id"] in tmap.values():
                        curr_team = sql_df("SELECT team_name FROM Teams WHERE team_id=:t", {"t": full["team_id"]}).iloc[0][0]
                        t_index = tnames.index(curr_team)
                    else:
                        t_index = 0

                    new_team = c5.selectbox("Team", tnames, index=t_index)

                    if st.form_submit_button("Save Changes"):
                        call_proc(
                            "update_player",
                            p_player_id=selected_pid,
                            p_name=null_or(new_name),
                            p_dob=str(new_dob),
                            p_position=null_or(new_pos),
                            p_nationality=null_or(new_nat),
                            p_team_id=tmap[new_team]
                        )
                        st.success("Player updated ✔️")
                        st.rerun()

            else:
                if st.button(f"Confirm Delete {selected_name}", key="del_player_btn"):
                    call_proc("delete_player", p_player_id=selected_pid)
                    st.success("Player deleted ✔️")
                    st.rerun()
        else:
            st.info("No players in database.")


# ----------------------------- TEAMS TAB -----------------------------
with tabs[1]:
    st.subheader("Teams (Add / Update / Delete)")

    with st.expander("➕ Add Team"):
        with st.form("form_add_team"):
            c1, c2, c3, c4 = st.columns(4)
            tn = c1.text_input("Team Name*")
            coach = c2.text_input("Coach")
            fy = c3.number_input("Founded Year", min_value=0, step=1)
            city = c4.text_input("Home City")

            if st.form_submit_button("Add"):
                if tn:
                    call_proc(
                        "add_team",
                        p_team_name=tn,
                        p_coach_name=null_or(coach),
                        p_founded_year=int(fy),
                        p_home_city=null_or(city)
                    )
                    st.success("Team added ✔️")
                    st.rerun()

    with st.expander("✏️ Update / 🗑 Delete Team", expanded=True):
        teams = sql_df("SELECT team_id, team_name FROM Teams ORDER BY team_name")
        tmap = {r.team_name: r.team_id for _, r in teams.iterrows()}
        selected_team = st.selectbox("Select Team", list(tmap.keys()), key="team_sel")
        tid = tmap[selected_team]

        mode = st.radio("Action", ["Update", "Delete"], horizontal=True, key="team_mode")

        if mode == "Update":
            t = sql_df("SELECT * FROM Teams WHERE team_id=:tid", {"tid": tid}).iloc[0]

            with st.form("form_upd_team"):
                c1, c2, c3, c4 = st.columns(4)
                new_tn = c1.text_input("Team Name", t["team_name"])
                new_coach = c2.text_input("Coach", t["coach_name"] or "")
                new_fy = c3.number_input("Founded", value=t["founded_year"] or 0)
                new_city = c4.text_input("City", t["home_city"] or "")

                if st.form_submit_button("Save"):
                    call_proc(
                        "update_team",
                        p_team_id=tid,
                        p_team_name=null_or(new_tn),
                        p_coach_name=null_or(new_coach),
                        p_founded_year=int(new_fy),
                        p_home_city=null_or(new_city),
                    )
                    st.success("Updated ✔️")
                    st.rerun()
        else:
            if st.button("Confirm Delete Team"):
                call_proc("delete_team", p_team_id=tid)
                st.success("Team deleted ✔️")
                st.rerun()


# ----------------------------- MATCHES TAB -----------------------------
with tabs[2]:
    st.subheader("Matches (Add / Update / Delete)")

    teams = sql_df("SELECT team_id, team_name FROM Teams ORDER BY team_name")
    tmap = {r.team_name: r.team_id for _, r in teams.iterrows()}

    with st.expander("➕ Add Match"):
        with st.form("form_add_match"):
            c1, c2, c3 = st.columns(3)
            md = c1.date_input("Date", value=date.today())
            home = c2.selectbox("Home Team", list(tmap.keys()))
            away = c3.selectbox("Away Team", [t for t in tmap.keys() if t != home])

            c4, c5 = st.columns(2)
            stadium = c4.text_input("Stadium")
            status = c5.text_input("Status", value="Completed")

            if st.form_submit_button("Add"):
                call_proc(
                    "add_match",
                    p_date=str(md),
                    p_home_team_id=tmap[home],
                    p_away_team_id=tmap[away],
                    p_stadium=null_or(stadium),
                    p_status=null_or(status),
                )
                st.success("Match added ✔️")
                st.rerun()

    with st.expander("✏️ Update / 🗑 Delete Match", expanded=True):
        matches = sql_df("""
            SELECT m.match_id,
                   CONCAT(ht.team_name,' vs ',at.team_name,' — ',m.date) AS label
            FROM Matches m
            JOIN Teams ht ON ht.team_id = m.home_team_id
            JOIN Teams at ON at.team_id = m.away_team_id
            ORDER BY m.match_id DESC
        """)

        match_map = {r.label: r.match_id for _, r in matches.iterrows()}
        selected_label = st.selectbox("Select Match", list(match_map.keys()), key="match_sel")
        mid = match_map[selected_label]

        mode = st.radio("Action", ["Update", "Delete"], horizontal=True, key="match_mode")

        if mode == "Update":
            m = sql_df("SELECT * FROM Matches WHERE match_id=:mid", {"mid": mid}).iloc[0]

            with st.form("form_upd_match"):
                c1, c2, c3 = st.columns(3)
                md = c1.date_input("Date", value=m["date"])
                home = c2.selectbox("Home Team", list(tmap.keys()))
                away = c3.selectbox("Away Team", [t for t in tmap.keys() if t != home])

                c4, c5 = st.columns(2)
                stadium = c4.text_input("Stadium", m["stadium"] or "")
                status = c5.text_input("Status", m["status"] or "")

                if st.form_submit_button("Save"):
                    call_proc(
                        "update_match",
                        p_match_id=mid,
                        p_date=str(md),
                        p_home_team_id=tmap[home],
                        p_away_team_id=tmap[away],
                        p_stadium=null_or(stadium),
                        p_status=null_or(status)
                    )
                    st.success("Match updated ✔️")
                    st.rerun()
        else:
            if st.button("Confirm Delete Match"):
                call_proc("delete_match", p_match_id=mid)
                st.success("Match deleted ✔️")
                st.rerun()


# ----------------------------- SCORES TAB -----------------------------
with tabs[3]:
    st.subheader("Scores (Add / Update / Delete)")

    matches = sql_df("SELECT match_id FROM Matches ORDER BY match_id DESC")
    teams = sql_df("SELECT * FROM Teams ORDER BY team_name")
    players = sql_df("SELECT * FROM Players ORDER BY name")

    tmap = {r.team_name: r.team_id for _, r in teams.iterrows()}
    pmap = {r.name: r.player_id for _, r in players.iterrows()}

    with st.expander("➕ Add Score"):
        with st.form("form_add_score"):
            c1, c2, c3, c4, c5 = st.columns(5)
            mid = c1.selectbox("Match", matches["match_id"].tolist())
            team = c2.selectbox("Team", list(tmap.keys()))
            player = c3.selectbox("Player", list(pmap.keys()))
            pts = c4.number_input("Points", min_value=0)
            minute = c5.number_input("Minute", min_value=0)

            if st.form_submit_button("Add"):
                call_proc(
                    "add_score",
                    p_match_id=mid,
                    p_team_id=tmap[team],
                    p_player_id=pmap[player],
                    p_points=int(pts),
                    p_minute_scored=int(minute)
                )
                st.success("Score added ✔️")
                st.rerun()

    with st.expander("✏️ Update / 🗑 Delete Score", expanded=True):
        scores = sql_df("""
            SELECT s.score_id,
                   CONCAT(p.name,' scored for ',t.team_name,' in match #',s.match_id,' (',s.points,' pts)')
                   AS label
            FROM Scores s
            JOIN Players p ON p.player_id=s.player_id
            JOIN Teams t ON t.team_id=s.team_id
            ORDER BY s.score_id DESC
        """)

        sc_map = {r.label: r.score_id for _, r in scores.iterrows()}
        selected_score = st.selectbox("Select Score", list(sc_map.keys()), key="score_sel")
        sid = sc_map[selected_score]

        mode = st.radio("Action", ["Update", "Delete"], horizontal=True, key="score_mode")

        if mode == "Update":
            with st.form("form_upd_score"):
                c1, c2, c3, c4, c5 = st.columns(5)
                mid = c1.selectbox("Match", matches["match_id"].tolist())
                team = c2.selectbox("Team", list(tmap.keys()))
                player = c3.selectbox("Player", list(pmap.keys()))
                pts = c4.number_input("Points", min_value=0)
                minute = c5.number_input("Minute", min_value=0)

                if st.form_submit_button("Save"):
                    call_proc(
                        "update_score",
                        p_score_id=sid,
                        p_match_id=mid,
                        p_team_id=tmap[team],
                        p_player_id=pmap[player],
                        p_points=int(pts),
                        p_minute_scored=int(minute)
                    )
                    st.success("Score updated ✔️")
                    st.rerun()

        else:
            if st.button("Confirm Delete Score"):
                call_proc("delete_score", p_score_id=sid)
                st.success("Score deleted ✔️")
                st.rerun()


# ----------------------------- INJURIES TAB -----------------------------
with tabs[4]:
    st.subheader("Injuries (Add / Update / Delete)")

    players = sql_df("SELECT player_id, name FROM Players ORDER BY name")
    pmap = {r.name: r.player_id for _, r in players.iterrows()}

    with st.expander("➕ Add Injury"):
        with st.form("form_add_injury"):
            c1, c2, c3, c4 = st.columns(4)
            player = c1.selectbox("Player", list(pmap.keys()))
            itype = c2.text_input("Injury Type*")
            idate = c3.date_input("Injury Date", value=date.today())
            ereturn = c4.date_input("Expected Return", value=None)
            status = st.selectbox("Status", ["Injured", "Recovering", "Fit"])

            if st.form_submit_button("Add"):
                call_proc(
                    "add_injury",
                    p_player_id=pmap[player],
                    p_injury_type=itype,
                    p_injury_date=str(idate),
                    p_expected_return=str(ereturn) if ereturn else None,
                    p_status=status
                )
                st.success("Injury added ✔️")
                st.rerun()

    with st.expander("✏️ Update / 🗑 Delete Injury", expanded=True):
        injuries = sql_df("""
            SELECT i.injury_id,
                   CONCAT(p.name,' — ',i.injury_type,' (',i.status,')') AS label
            FROM Injuries i
            JOIN Players p ON p.player_id=i.player_id
            ORDER BY i.injury_id DESC
        """)

        if not injuries.empty:
            inj_map = {r.label: r.injury_id for _, r in injuries.iterrows()}
            selected_injury = st.selectbox("Select Injury", list(inj_map.keys()), key="inj_sel")
            iid = inj_map[selected_injury]

            mode = st.radio("Action", ["Update", "Delete"], horizontal=True, key="inj_mode")

            if mode == "Update":
                with st.form("form_upd_injury"):
                    c1, c2, c3, c4 = st.columns(4)
                    player = c1.selectbox("Player", list(pmap.keys()))
                    new_type = c2.text_input("Type")
                    new_date = c3.date_input("Date", value=date.today())
                    new_ereturn = c4.date_input("Expected Return", value=None)
                    status = st.selectbox("Status", ["Injured", "Recovering", "Fit"])

                    if st.form_submit_button("Save"):
                        call_proc(
                            "update_injury",
                            p_injury_id=iid,
                            p_player_id=pmap[player],
                            p_injury_type=null_or(new_type),
                            p_injury_date=str(new_date),
                            p_expected_return=str(new_ereturn) if new_ereturn else None,
                            p_status=status
                        )
                        st.success("Injury updated ✔️")
                        st.rerun()
            else:
                if st.button("Confirm Delete Injury"):
                    call_proc("delete_injury", p_injury_id=iid)
                    st.success("Injury deleted ✔️")
                    st.rerun()
        else:
            st.info("No injury records.")


# ----------------------------- AUDIT LOG TAB -----------------------------
with tabs[5]:
    st.subheader("Audit Log")

    f1, f2, f3 = st.columns(3)
    table_filter = f1.selectbox("Table", ["All", "Players", "Teams", "Matches", "Scores", "Injuries"])
    action_filter = f2.selectbox("Action", ["All", "INSERT", "UPDATE", "DELETE"])
    limit = f3.number_input("Limit", min_value=10, max_value=5000, value=200, step=10)

    logs = sql_df("""
        SELECT id, table_name, record_id, action, actor, created_at
        FROM Audit_Log
        ORDER BY id DESC
        LIMIT :l
    """, {"l": int(limit)})

    if table_filter != "All":
        logs = logs[logs["table_name"] == table_filter]
    if action_filter != "All":
        logs = logs[logs["action"] == action_filter]

    st.dataframe(logs, use_container_width=True, height=420)
