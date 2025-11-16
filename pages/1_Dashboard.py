import streamlit as st
import plotly.express as px
from common import auth_guard, inject_dark_theme, sql_df

st.set_page_config(page_title="Dashboard · Sports Analytics", page_icon="📊", layout="wide")
inject_dark_theme()
auth_guard()

st.title("📊 Dashboard")

df_team = sql_df("SELECT team_name, total_points, points_rank FROM v_team_totals")
c1, c2 = st.columns(2)

with c1:
    st.subheader("Total Points by Team")
    if df_team.empty:
        st.info("No teams yet.")
    else:
        fig = px.bar(
            df_team,
            x="team_name",
            y="total_points",
            text_auto=True,
            title="Total Points by Team",
            template="plotly_dark",
            color="total_points",
            color_continuous_scale="Blues",
        )
        fig.update_layout(xaxis_title="Team", yaxis_title="Points")
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Rank by Points (Lower is Better)")
    if df_team.empty:
        st.info("No teams yet.")
    else:
        fig2 = px.bar(
            df_team,
            x="team_name",
            y="points_rank",
            text_auto=True,
            title="Team Ranking",
            template="plotly_dark",
            color="points_rank",
            color_continuous_scale="Plasma",
        )
        fig2.update_layout(
            xaxis_title="Team",
            yaxis_title="Rank",
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig2, use_container_width=True)

st.subheader("Top Players by Points")

df_top = sql_df("""
    SELECT name, team_name, total_points
    FROM v_player_summary
    ORDER BY total_points DESC, name
    LIMIT 10
""")

if df_top.empty:
    st.info("No players yet.")
else:
    fig3 = px.bar(
        df_top,
        x="name",
        y="total_points",
        color="team_name",
        text_auto=True,
        title="Top 10 Players by Points",
        template="plotly_dark",
    )
    fig3.update_layout(xaxis_title="Player", yaxis_title="Points")
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("Injury Snapshot")

df_inj = sql_df("SELECT status, COUNT(*) AS cnt FROM Injuries GROUP BY status")

if df_inj.empty:
    st.info("No injuries recorded.")
else:
    fig4 = px.pie(
        df_inj,
        values="cnt",
        names="status",
        title="Injuries by Status",
        template="plotly_dark",
        hole=0.4,
    )
    fig4.update_traces(textinfo="percent+label")
    st.plotly_chart(fig4, use_container_width=True)
