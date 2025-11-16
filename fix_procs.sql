USE sports_analytics;

DROP PROCEDURE IF EXISTS add_team;
DELIMITER $$
CREATE PROCEDURE add_team(
    IN p_team_name VARCHAR(50),
    IN p_coach_name VARCHAR(50),
    IN p_founded_year INT,
    IN p_home_city VARCHAR(50)
)
BEGIN
    INSERT INTO Teams(team_name, coach_name, founded_year, home_city)
    VALUES(p_team_name, p_coach_name, p_founded_year, p_home_city);

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Teams', LAST_INSERT_ID(), 'INSERT');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS update_team;
DELIMITER $$
CREATE PROCEDURE update_team(
    IN p_team_id INT,
    IN p_team_name VARCHAR(50),
    IN p_coach_name VARCHAR(50),
    IN p_founded_year INT,
    IN p_home_city VARCHAR(50)
)
BEGIN
    UPDATE Teams
    SET team_name = p_team_name,
        coach_name = p_coach_name,
        founded_year = p_founded_year,
        home_city = p_home_city
    WHERE team_id = p_team_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Teams', p_team_id, 'UPDATE');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS delete_team;
DELIMITER $$
CREATE PROCEDURE delete_team(IN p_team_id INT)
BEGIN
    DELETE FROM Teams WHERE team_id = p_team_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Teams', p_team_id, 'DELETE');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS update_score;
DELIMITER $$
CREATE PROCEDURE update_score(
    IN p_score_id INT,
    IN p_match_id INT,
    IN p_team_id INT,
    IN p_player_id INT,
    IN p_points INT,
    IN p_minute_scored INT
)
BEGIN
    UPDATE Scores
    SET match_id = p_match_id,
        team_id = p_team_id,
        player_id = p_player_id,
        points = p_points,
        minute_scored = p_minute_scored
    WHERE score_id = p_score_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Scores', p_score_id, 'UPDATE');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS delete_score;
DELIMITER $$
CREATE PROCEDURE delete_score(IN p_score_id INT)
BEGIN
    DELETE FROM Scores WHERE score_id = p_score_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Scores', p_score_id, 'DELETE');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS update_injury;
DELIMITER $$
CREATE PROCEDURE update_injury(
    IN p_injury_id INT,
    IN p_player_id INT,
    IN p_injury_type VARCHAR(50),
    IN p_injury_date DATE,
    IN p_expected_return DATE,
    IN p_status VARCHAR(20)
)
BEGIN
    UPDATE Injuries
    SET player_id = p_player_id,
        injury_type = p_injury_type,
        injury_date = p_injury_date,
        expected_return = p_expected_return,
        status = p_status
    WHERE injury_id = p_injury_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Injuries', p_injury_id, 'UPDATE');
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS delete_injury;
DELIMITER $$
CREATE PROCEDURE delete_injury(IN p_injury_id INT)
BEGIN
    DELETE FROM Injuries WHERE injury_id = p_injury_id;

    INSERT INTO Audit_Log(table_name, record_id, action)
    VALUES('Injuries', p_injury_id, 'DELETE');
END$$
DELIMITER ;

CREATE OR REPLACE VIEW v_injury_active AS
SELECT *
FROM v_injury_summary
WHERE is_active = 1;

CREATE TRIGGER trg_injuries_au
AFTER UPDATE ON Injuries
FOR EACH ROW
INSERT INTO Audit_Log(table_name, record_id, action)
VALUES('Injuries', NEW.injury_id, 'UPDATE');

CREATE TRIGGER trg_injuries_ad
AFTER DELETE ON Injuries
FOR EACH ROW
INSERT INTO Audit_Log(table_name, record_id, action)
VALUES('Injuries', OLD.injury_id, 'DELETE');
