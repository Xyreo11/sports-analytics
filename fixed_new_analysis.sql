USE sports_analytics;

CREATE OR REPLACE VIEW v_match_score_flow AS
WITH ordered AS (
    SELECT 
        s.match_id,
        m.date,
        m.home_team_id,
        m.away_team_id,
        s.minute_scored,
        s.team_id,
        s.points
    FROM Scores s
    JOIN Matches m ON m.match_id = s.match_id
),
expanded AS (
    SELECT 
        o.match_id,
        o.date,
        o.minute_scored,
        o.team_id,
        o.points,
        SUM(CASE WHEN o.team_id = o.home_team_id THEN o.points END)
            OVER (PARTITION BY o.match_id ORDER BY o.minute_scored) AS home_cum,
        SUM(CASE WHEN o.team_id = o.away_team_id THEN o.points END)
            OVER (PARTITION BY o.match_id ORDER BY o.minute_scored) AS away_cum
    FROM ordered o
)
SELECT * FROM expanded;

CREATE OR REPLACE VIEW v_match_player_xg AS
SELECT 
    s.match_id,
    p.player_id,
    p.name AS player_name,
    t.team_name,
    COUNT(*) AS shots,
    SUM(points) AS goals,
    ROUND(
        SUM(
            CASE 
                WHEN minute_scored <= 20 THEN 0.25
                WHEN minute_scored <= 45 THEN 0.18
                WHEN minute_scored <= 70 THEN 0.12
                ELSE 0.08
            END
        ), 3
    ) AS xg
FROM Scores s
JOIN Players p ON p.player_id = s.player_id
JOIN Teams t ON t.team_id = s.team_id
GROUP BY s.match_id, p.player_id;

CREATE OR REPLACE VIEW v_match_team_stats AS
WITH team_sc AS (
    SELECT 
        m.match_id,
        t.team_id,
        t.team_name,
        COUNT(*) AS shots,
        SUM(points) AS goals,
        SUM(CASE WHEN points > 0 THEN 1 ELSE 0 END) AS shots_on_target
    FROM Matches m
    JOIN Scores s ON s.match_id = m.match_id
    JOIN Teams t ON t.team_id = s.team_id
    GROUP BY m.match_id, t.team_id
),
both AS (
    SELECT 
        a.*,
        b.shots AS opp_shots
    FROM team_sc a
    JOIN team_sc b 
      ON a.match_id = b.match_id 
     AND a.team_id <> b.team_id
)
SELECT 
    *,
    ROUND(shots / (shots + opp_shots) * 100, 1) AS possession,
    (shots * 32) AS passes,
    ROUND((0.75 + (shots_on_target * 0.04)) * 100, 1) AS pass_accuracy
FROM both;

CREATE OR REPLACE VIEW v_match_key_moments AS
WITH base AS (
    SELECT 
        s.match_id,
        s.minute_scored,
        t.team_name,
        p.name AS player_name,
        s.points,
        LAG(points) OVER (PARTITION BY s.match_id ORDER BY minute_scored) AS prev_points
    FROM Scores s
    JOIN Players p ON p.player_id = s.player_id
    JOIN Teams t ON t.team_id = s.team_id
)
SELECT 
    *,
    CASE
        WHEN minute_scored >= 90 THEN 'Decisive (Injury-Time)'
        WHEN prev_points IS NULL THEN 'Opening Goal'
        WHEN points > prev_points THEN 'Momentum Shift'
        WHEN points = prev_points THEN 'Equalizer'
        ELSE 'Key Moment'
    END AS moment_type
FROM base;

CREATE OR REPLACE VIEW v_match_mvp AS
WITH x AS (
    SELECT * FROM v_match_player_xg
),
km AS (
    SELECT 
        match_id, player_name,
        COUNT(*) AS key_moments
    FROM v_match_key_moments
    GROUP BY match_id, player_name
)
SELECT 
    x.match_id,
    x.player_id,
    x.player_name,
    x.team_name,
    x.goals,
    x.xg,
    COALESCE(km.key_moments, 0) AS key_moments,
    ROUND(
        (x.goals * 5) + 
        (x.xg * 3) + 
        (COALESCE(km.key_moments, 0) * 2), 2
    ) AS mvp_score
FROM x
LEFT JOIN km
  ON x.match_id = km.match_id
 AND x.player_name = km.player_name
ORDER BY match_id, mvp_score DESC;
