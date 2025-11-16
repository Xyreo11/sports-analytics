import math
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from common import auth_guard, inject_dark_theme, sql_df

st.set_page_config(page_title="Matches · Sports Analytics", page_icon="🏟️", layout="wide")
inject_dark_theme()
auth_guard()

if "match_view" not in st.session_state:
    st.session_state.match_view = "search"
if "current_match" not in st.session_state:
    st.session_state.current_match = None

st.title("🏟 Matches")

if st.session_state.match_view == "search":
    st.subheader("Search Matches")
    st.write("Filter by team or opponent, then click **Search Matches**.")

    teams = sql_df("SELECT team_name FROM Teams ORDER BY team_name")
    team_list = ["All"] + teams["team_name"].tolist() if not teams.empty else ["All"]

    c1, c2, c3 = st.columns([2, 2, 1])
    team_filter = c1.selectbox("Team", team_list)
    opponent_filter = c2.selectbox("Opponent", team_list)
    sort_by = c3.selectbox("Sort by", [
        "No Sorting",
        "Newest",
        "Oldest",
        "Most Goals",
        "Fewest Goals",
        "Largest Goal Difference"
    ])

    if st.button("Search Matches"):
        st.session_state.search_triggered = True

    if "search_triggered" not in st.session_state:
        st.session_state.search_triggered = False

    if not st.session_state.search_triggered:
        st.info("Use the filters above and click **Search Matches**.")
        st.stop()

    base = """
        SELECT m.match_id, m.date, m.stadium,
               ht.team_name AS home_team, at.team_name AS away_team,
               COALESCE(h.pts,0) AS home_points, COALESCE(a.pts,0) AS away_points,
               (COALESCE(h.pts,0) + COALESCE(a.pts,0)) AS total_goals,
               ABS(COALESCE(h.pts,0) - COALESCE(a.pts,0)) AS goal_diff
        FROM Matches m
        JOIN Teams ht ON ht.team_id = m.home_team_id
        JOIN Teams at ON at.team_id = m.away_team_id
        LEFT JOIN (SELECT match_id, team_id, SUM(points) AS pts FROM Scores GROUP BY match_id, team_id) h
          ON h.match_id=m.match_id AND h.team_id=m.home_team_id
        LEFT JOIN (SELECT match_id, team_id, SUM(points) AS pts FROM Scores GROUP BY match_id, team_id) a
          ON a.match_id=m.match_id AND a.team_id=m.away_team_id
        WHERE 1=1
    """
    params = {}

    if team_filter != "All":
        base += " AND (ht.team_name=:t OR at.team_name=:t) "
        params["t"] = team_filter
    if opponent_filter != "All":
        base += " AND (ht.team_name=:o OR at.team_name=:o) "
        params["o"] = opponent_filter

    dfm = sql_df(base, params)

    if not dfm.empty:
        if "date" in dfm.columns:
            dfm["date"] = pd.to_datetime(dfm["date"], errors="coerce")

        for col in ["home_points", "away_points", "total_goals", "goal_diff"]:
            if col in dfm.columns:
                dfm[col] = pd.to_numeric(dfm[col], errors="coerce").fillna(0).astype(int)

    if not dfm.empty:
        if sort_by == "Newest":
            dfm = dfm.sort_values(by="date", ascending=False, na_position="last")
        elif sort_by == "Oldest":
            dfm = dfm.sort_values(by="date", ascending=True, na_position="last")
        elif sort_by == "Most Goals":
            dfm = dfm.sort_values(by="total_goals", ascending=False)
        elif sort_by == "Fewest Goals":
            dfm = dfm.sort_values(by="total_goals", ascending=True)
        elif sort_by == "Largest Goal Difference":
            dfm = dfm.sort_values(by="goal_diff", ascending=False)

    if dfm.empty:
        st.warning("No matches found.")
        st.stop()

    st.subheader("Results")
    for _, m in dfm.iterrows():
        home = m["home_team"]
        away = m["away_team"]
        hs = int(m["home_points"] or 0)
        as_ = int(m["away_points"] or 0)

        if "date" in m and pd.notna(m["date"]):
            try:
                date_label = pd.to_datetime(m["date"]).strftime("%Y-%m-%d")
            except:
                date_label = str(m["date"])
        else:
            date_label = str(m.get("date", ""))

        btn_label = f"{home} {hs} - {as_} {away} ({date_label})"
        if st.button(btn_label, key=f"m_{m['match_id']}"):
            st.session_state.current_match = int(m["match_id"])
            st.session_state.match_view = "detail"
            st.rerun()

if st.session_state.match_view == "detail":
    mid = st.session_state.current_match
    if not mid:
        st.session_state.match_view = "search"
        st.rerun()

    info_q = """
        SELECT m.date, m.stadium, m.status,
               ht.team_name AS home_team, at.team_name AS away_team,
               m.home_team_id, m.away_team_id
        FROM Matches m
        JOIN Teams ht ON ht.team_id = m.home_team_id
        JOIN Teams at ON at.team_id = m.away_team_id
        WHERE m.match_id = :m
    """
    info_df = sql_df(info_q, {"m": mid})
    if info_df.empty:
        st.error("Match not found.")
        st.session_state.match_view = "search"
        st.rerun()
    info = info_df.iloc[0]

    score = sql_df("""
        SELECT 
          (SELECT COALESCE(SUM(points),0) FROM Scores WHERE match_id=:m AND team_id=m.home_team_id) AS home_score,
          (SELECT COALESCE(SUM(points),0) FROM Scores WHERE match_id=:m AND team_id=m.away_team_id) AS away_score
        FROM Matches m WHERE match_id=:m
    """, {"m": mid}).iloc[0]

    hs, as_ = int(score["home_score"] or 0), int(score["away_score"] or 0)

    st.markdown(f"""
    <div class="score-card">
        <h3>{info['home_team']} vs {info['away_team']}</h3>
        <h1>{hs} - {as_}</h1>
        <div class="muted">{info['date']} • {info['stadium']} • {info['status']}</div>
    </div>
    """, unsafe_allow_html=True)

    timeline = sql_df("""
        SELECT minute_scored, player_name, team_name, points
        FROM v_match_play_by_play
        WHERE match_id=:m
        ORDER BY minute_scored
    """, {"m": mid})

    st.subheader("Scoring Timeline")
    if timeline.empty:
        st.info("No scoring events recorded.")
    else:
        for _, ev in timeline.iterrows():
            st.markdown(f"**{int(ev['minute_scored'])}'** — {ev['player_name']} ({ev['team_name']}) scored {int(ev['points'])}")

    st.markdown("---")
    st.subheader("Advanced Match Analytics")

    sf = sql_df("""
        SELECT match_id, minute_scored, home_cum, away_cum
        FROM v_match_score_flow
        WHERE match_id = :m
        ORDER BY minute_scored
    """, {"m": mid})

    if sf.empty:
        st.info("No score-flow data available for this match.")
        minute_df = pd.DataFrame()
    else:
        max_min = int(max(90, int(sf["minute_scored"].max())))
        minutes = pd.DataFrame({"minute": list(range(0, max_min + 1))})
        evt = sf[["minute_scored", "home_cum", "away_cum"]].rename(columns={"minute_scored": "minute"})
        evt = evt.groupby("minute").agg({"home_cum": "max", "away_cum": "max"}).reset_index()
        minute_df = minutes.merge(evt, on="minute", how="left").sort_values("minute")
        minute_df[["home_cum", "away_cum"]] = minute_df[["home_cum", "away_cum"]].ffill().fillna(0).astype(int)

        fig_flow = go.Figure()
        fig_flow.add_trace(go.Scatter(x=minute_df["minute"], y=minute_df["home_cum"], mode="lines+markers", name=info["home_team"]))
        fig_flow.add_trace(go.Scatter(x=minute_df["minute"], y=minute_df["away_cum"], mode="lines+markers", name=info["away_team"]))
        for _, r in sf.iterrows():
            fig_flow.add_vline(x=int(r["minute_scored"]), line_width=1, line_dash="dot", line_color="rgba(200,200,200,0.12)")
        fig_flow.update_layout(title="Score Flow (Cumulative Goals)", xaxis_title="Minute", yaxis_title="Cumulative Goals",
                               template="plotly_dark", legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_flow, use_container_width=True)

    st.markdown("**Turning point detection**")
    if sf.empty or minute_df.empty:
        st.info("Not enough data to compute turning point.")
    else:
        minute_df["lead"] = minute_df["home_cum"] - minute_df["away_cum"]
        minute_df["lead_diff"] = minute_df["lead"].diff().fillna(0)
        minute_df["lead_diff2"] = minute_df["lead_diff"].diff().fillna(0).abs()
        tp_row = minute_df.loc[minute_df["lead_diff2"].idxmax()]
        tp_minute = int(tp_row["minute"])
        tp_change = float(tp_row["lead_diff2"])

        tp_desc = "No clear turning point detected."
        if tp_change > 0:
            evs = timeline[timeline["minute_scored"] <= tp_minute]
            if not evs.empty:
                last_ev = evs.iloc[-1]
                tp_desc = f"Turning point at {tp_minute}' — {last_ev['player_name']} ({last_ev['team_name']}) scored {int(last_ev['points'])}."
            else:
                tp_desc = f"Turning point detected at {tp_minute}' (momentum change: {tp_change:.2f})."

        st.info(tp_desc)

    st.markdown("### Expected Goals (xG) per Player")
    xg_df = sql_df("""
        SELECT match_id, player_id, player_name, team_name, shots, goals, xg
        FROM v_match_player_xg
        WHERE match_id = :m
        ORDER BY xg DESC
    """, {"m": mid})

    if xg_df.empty:
        st.info("No xG/player data available for this match.")
    else:
        fig_xg = px.bar(
            xg_df,
            x="player_name",
            y="goals",
            color="team_name",
            text="goals",
            title="Goals by Player (xG in hover)",
            template="plotly_dark",
            labels={"goals": "Goals", "player_name": "Player"}
        )
        fig_xg.update_traces(
            hovertemplate='<b>%{x}</b><br>Team: %{marker.color}<br>Goals: %{y}<br>xG: %{customdata[0]}',
            customdata=np.stack([xg_df["xg"].astype(str)], axis=-1)
        )
        st.plotly_chart(fig_xg, use_container_width=True)

    st.markdown("### Heatmap — Scoring Minutes (players vs minute bins)")
    if timeline.empty:
        st.info("No scoring minutes to display.")
    else:
        bins = list(range(0, 91, 10))
        labels = [f"{i}-{i+9}" for i in bins[:-1]]
        labels[-1] = "80-89"
        timeline["minute_bin"] = pd.cut(
            timeline["minute_scored"].astype(int),
            bins=bins + [1000],
            right=False,
            labels=labels + ["90+"]
        )
        heat = timeline.groupby(["player_name", "minute_bin"])["points"].sum().unstack(fill_value=0)
        cols_order = labels + ["90+"]
        heat = heat.reindex(columns=cols_order, fill_value=0)

        fig_heat = go.Figure(data=go.Heatmap(
            z=heat.values,
            x=heat.columns.astype(str),
            y=heat.index.astype(str),
            colorscale="YlOrRd",
            hoverongaps=False,
            colorbar=dict(title="Points")
        ))
        fig_heat.update_layout(title="Scoring Minutes Heatmap", template="plotly_dark",
                               xaxis_title="Minute bins", yaxis_title="Player")
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("### Team Comparison Radar")
    stats = sql_df("""
        SELECT match_id, team_id, team_name, shots, goals, shots_on_target, possession, passes, pass_accuracy
        FROM v_match_team_stats
        WHERE match_id = :m
    """, {"m": mid})

    if stats.empty or stats.shape[0] < 2:
        st.info("Not enough team stats to build radar chart.")
    else:
        home_id = int(info["home_team_id"])
        away_id = int(info["away_team_id"])
        s_home = stats[stats["team_id"] == home_id]
        s_away = stats[stats["team_id"] == away_id]

        if s_home.empty or s_away.empty:
            s_home = stats.iloc[[0]]
            s_away = stats.iloc[[1]]
        else:
            s_home = s_home.iloc[[0]]
            s_away = s_away.iloc[[0]]

        categories = ["shots", "shots_on_target", "goals", "possession", "passes", "pass_accuracy"]
        home_vals = [float(s_home[c].iloc[0]) for c in categories]
        away_vals = [float(s_away[c].iloc[0]) for c in categories]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=home_vals + [home_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=s_home["team_name"].iloc[0]
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=away_vals + [away_vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=s_away["team_name"].iloc[0]
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True,
                                template="plotly_dark", title="Team Comparison Radar")
        st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("### MVP Prediction")
    mvp = sql_df("""
        SELECT match_id, player_id, player_name, team_name, goals, xg, key_moments, mvp_score
        FROM v_match_mvp
        WHERE match_id = :m
        ORDER BY mvp_score DESC
        LIMIT 3
    """, {"m": mid})

    if mvp.empty:
        st.info("No MVP data available.")
    else:
        top = mvp.iloc[0]
        c1, c2, c3 = st.columns([2, 5, 3])
        with c1:
            st.metric("Predicted MVP", f"{top['player_name']}")
            st.write(f"Team: {top['team_name']}")
        with c2:
            st.write("#### MVP Score Breakdown")
            st.write(f"- Goals: {int(top['goals'])}")
            st.write(f"- xG: {float(top['xg'])}")
            st.write(f"- Key moments: {int(top['key_moments'])}")
            st.write(f"- MVP Score: {float(top['mvp_score'])}")
        with c3:
            st.write("#### Top 3 Candidates")
            st.table(
                mvp[["player_name", "team_name", "mvp_score"]]
                .rename(columns={"player_name": "Player", "team_name": "Team", "mvp_score": "Score"})
            )

    st.markdown("### Key Moments & Events")
    km = sql_df("""
        SELECT match_id, minute_scored, player_name, team_name, points, moment_type
        FROM v_match_key_moments
        WHERE match_id = :m
        ORDER BY minute_scored
    """, {"m": mid})

    if km.empty:
        st.info("No key moments recorded.")
    else:
        for _, r in km.iterrows():
            st.markdown(
                f"**{int(r['minute_scored'])}'** — {r['player_name']} ({r['team_name']}) — *{r['moment_type']}* — {int(r['points'])} pts"
            )

    st.markdown("---")
    if st.button("← Back to search"):
        st.session_state.match_view = "search"
        st.session_state.current_match = None
        st.rerun()
