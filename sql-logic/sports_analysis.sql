DROP DATABASE IF EXISTS sports_analytics;
CREATE DATABASE sports_analytics;
USE sports_analytics;

SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE';

CREATE TABLE Users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Teams (
    team_id INT PRIMARY KEY AUTO_INCREMENT,
    team_name VARCHAR(50) NOT NULL,
    coach_name VARCHAR(50),
    founded_year INT,
    home_city VARCHAR(50)
);

CREATE TABLE Players (
    player_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    dob DATE,
    position VARCHAR(30),
    nationality VARCHAR(40),
    team_id INT,
    FOREIGN KEY (team_id) REFERENCES Teams(team_id)
);

CREATE TABLE Matches (
    match_id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE,
    home_team_id INT,
    away_team_id INT,
    stadium VARCHAR(50),
    status VARCHAR(30),
    FOREIGN KEY (home_team_id) REFERENCES Teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES Teams(team_id)
);

CREATE TABLE Scores (
    score_id INT PRIMARY KEY AUTO_INCREMENT,
    match_id INT,
    team_id INT,
    player_id INT,
    points INT,
    minute_scored INT,
    FOREIGN KEY (match_id) REFERENCES Matches(match_id),
    FOREIGN KEY (team_id) REFERENCES Teams(team_id),
    FOREIGN KEY (player_id) REFERENCES Players(player_id)
);

CREATE TABLE Injuries (
    injury_id INT PRIMARY KEY AUTO_INCREMENT,
    player_id INT,
    injury_type VARCHAR(50),
    injury_date DATE,
    expected_return DATE,
    status VARCHAR(20),
    FOREIGN KEY (player_id) REFERENCES Players(player_id)
);

CREATE TABLE Team_Match (
    team_id INT,
    match_id INT,
    PRIMARY KEY (team_id, match_id),
    FOREIGN KEY (team_id) REFERENCES Teams(team_id),
    FOREIGN KEY (match_id) REFERENCES Matches(match_id)
);

CREATE TABLE Audit_Log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(64),
    record_id INT,
    action VARCHAR(32),
    actor VARCHAR(64) DEFAULT 'app-user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_players_team ON Players(team_id);
CREATE INDEX idx_scores_match ON Scores(match_id);
CREATE INDEX idx_scores_player ON Scores(player_id);
CREATE INDEX idx_injuries_player ON Injuries(player_id);

ALTER TABLE Players ADD FULLTEXT ft_players (name, position, nationality);

DELIMITER $$

DROP FUNCTION IF EXISTS age_from_dob;
CREATE FUNCTION age_from_dob(p_dob DATE)
RETURNS INT DETERMINISTIC
BEGIN
  IF p_dob IS NULL THEN RETURN NULL; END IF;
  RETURN TIMESTAMPDIFF(YEAR, p_dob, CURDATE());
END$$

DROP FUNCTION IF EXISTS is_injured;
CREATE FUNCTION is_injured(p_player_id INT)
RETURNS TINYINT DETERMINISTIC
BEGIN
  DECLARE cnt INT DEFAULT 0;
  SELECT COUNT(*) INTO cnt FROM Injuries
  WHERE player_id=p_player_id AND (status IS NULL OR status <> 'Fit');
  RETURN (cnt > 0);
END$$

DELIMITER ;

CREATE OR REPLACE VIEW v_player_summary AS
SELECT 
  p.player_id,
  p.name,
  p.dob,
  age_from_dob(p.dob) AS age,
  p.position,
  p.nationality,
  t.team_name,
  COALESCE(SUM(s.points),0) AS total_points,
  MAX(m.date) AS last_match_date,
  is_injured(p.player_id) AS injured
FROM Players p
LEFT JOIN Scores s ON s.player_id=p.player_id
LEFT JOIN Matches m ON m.match_id=s.match_id
LEFT JOIN Teams t ON t.team_id=p.team_id
GROUP BY p.player_id;

CREATE OR REPLACE VIEW v_team_totals AS
WITH tpts AS (
  SELECT t.team_id, t.team_name, COALESCE(SUM(s.points),0) AS total_points
  FROM Teams t
  LEFT JOIN Scores s ON s.team_id=t.team_id
  GROUP BY t.team_id
)
SELECT team_id, team_name, total_points,
       RANK() OVER (ORDER BY total_points DESC) AS points_rank
FROM tpts;

CREATE OR REPLACE VIEW v_match_play_by_play AS
SELECT 
  m.match_id, m.date, m.stadium, m.status,
  s.minute_scored, s.points,
  t.team_name,
  p.name AS player_name
FROM Scores s
JOIN Matches m ON m.match_id=s.match_id
JOIN Teams t ON t.team_id=s.team_id
JOIN Players p ON p.player_id=s.player_id
ORDER BY m.match_id, s.minute_scored;

CREATE OR REPLACE VIEW v_injury_summary AS
SELECT 
  i.injury_id, i.player_id,
  p.name AS player_name, t.team_name,
  i.injury_type, i.injury_date,
  i.expected_return, i.status,
  (i.status IS NULL OR i.status<>'Fit') AS is_active
FROM Injuries i
JOIN Players p ON p.player_id=i.player_id
LEFT JOIN Teams t ON t.team_id=p.team_id
ORDER BY i.injury_date DESC;

DELIMITER $$

DROP PROCEDURE IF EXISTS signup_user;
CREATE PROCEDURE signup_user(IN p_username VARCHAR(50),
                             IN p_email VARCHAR(100),
                             IN p_password_hash VARCHAR(255),
                             IN p_role ENUM('admin','viewer'))
BEGIN
    INSERT INTO Users(username,email,password_hash,role)
    VALUES(p_username,p_email,p_password_hash,COALESCE(p_role,'viewer'));
END$$

DROP PROCEDURE IF EXISTS login_user;
CREATE PROCEDURE login_user(IN p_email VARCHAR(100))
BEGIN
    SELECT user_id, username, email, password_hash, role
    FROM Users
    WHERE email = p_email;
END$$

DROP PROCEDURE IF EXISTS add_player;
CREATE PROCEDURE add_player(IN p_name VARCHAR(50), IN p_dob DATE, IN p_position VARCHAR(30),
                            IN p_nationality VARCHAR(40), IN p_team_id INT)
BEGIN
  INSERT INTO Players(name,dob,position,nationality,team_id)
  VALUES(p_name,p_dob,p_position,p_nationality,p_team_id);
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', LAST_INSERT_ID(), 'INSERT');
END$$

DROP PROCEDURE IF EXISTS update_player;
CREATE PROCEDURE update_player(IN pid INT, IN p_name VARCHAR(50), IN p_dob DATE,
                               IN p_position VARCHAR(30), IN p_nationality VARCHAR(40), IN p_team_id INT)
BEGIN
  UPDATE Players
  SET name=p_name,dob=p_dob,position=p_position,nationality=p_nationality,team_id=p_team_id
  WHERE player_id=pid;
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', pid, 'UPDATE');
END$$

DROP PROCEDURE IF EXISTS delete_player;
CREATE PROCEDURE delete_player(IN pid INT)
BEGIN
  DELETE FROM Players WHERE player_id=pid;
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', pid, 'DELETE');
END$$

DROP PROCEDURE IF EXISTS search_players;
CREATE PROCEDURE search_players(
    IN q VARCHAR(255),
    IN minpts INT,
    IN team INT
)
BEGIN
  SELECT v.*
  FROM v_player_summary v
  JOIN Players p ON p.player_id = v.player_id
  WHERE v.total_points >= COALESCE(minpts,0)
    AND (team IS NULL OR v.team_name = (SELECT team_name FROM Teams WHERE team_id=team))
    AND (
        q IS NULL OR q='' OR 
        MATCH(p.name, p.position, p.nationality) AGAINST(q IN NATURAL LANGUAGE MODE)
        OR p.name LIKE CONCAT('%', q, '%')
    )
  ORDER BY v.total_points DESC, v.name;
END$$

DROP PROCEDURE IF EXISTS add_match;
CREATE PROCEDURE add_match(IN p_date DATE, IN p_home INT, IN p_away INT, IN p_stadium VARCHAR(50), IN p_status VARCHAR(30))
BEGIN
  INSERT INTO Matches(date,home_team_id,away_team_id,stadium,status)
  VALUES(p_date,p_home,p_away,p_stadium,p_status);
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Matches', LAST_INSERT_ID(), 'INSERT');
END$$

DROP PROCEDURE IF EXISTS update_match;
CREATE PROCEDURE update_match(IN mid INT, IN p_date DATE, IN p_home INT, IN p_away INT, IN p_stadium VARCHAR(50), IN p_status VARCHAR(30))
BEGIN
  UPDATE Matches
  SET date=p_date, home_team_id=p_home, away_team_id=p_away, stadium=p_stadium, status=p_status
  WHERE match_id=mid;
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Matches', mid, 'UPDATE');
END$$

DROP PROCEDURE IF EXISTS delete_match;
CREATE PROCEDURE delete_match(IN mid INT)
BEGIN
  DELETE FROM Matches WHERE match_id=mid;
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Matches', mid, 'DELETE');
END$$

DROP PROCEDURE IF EXISTS add_score;
CREATE PROCEDURE add_score(IN mid INT, IN tid INT, IN pid INT, IN pts INT, IN minsc INT)
BEGIN
  INSERT INTO Scores(match_id,team_id,player_id,points,minute_scored)
  VALUES(mid,tid,pid,pts,minsc);
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Scores', LAST_INSERT_ID(),'INSERT');
END$$

DROP PROCEDURE IF EXISTS add_injury;
CREATE PROCEDURE add_injury(IN pid INT, IN itype VARCHAR(50), IN idate DATE, IN er DATE, IN stat VARCHAR(20))
BEGIN
  INSERT INTO Injuries(player_id,injury_type,injury_date,expected_return,status)
  VALUES(pid,itype,idate,er,stat);
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Injuries', LAST_INSERT_ID(),'INSERT');
END$$

DELIMITER ;

DROP TRIGGER IF EXISTS trg_scores_check;
DELIMITER $$
CREATE TRIGGER trg_scores_check BEFORE INSERT ON Scores
FOR EACH ROW
BEGIN
  IF NEW.minute_scored < 0 THEN
    SIGNAL SQLSTATE '45000'
       SET MESSAGE_TEXT='minute_scored cannot be negative';
  END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_players_ai;
DELIMITER $$
CREATE TRIGGER trg_players_ai AFTER INSERT ON Players
FOR EACH ROW BEGIN
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', NEW.player_id,'INSERT');
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_players_au;
DELIMITER $$
CREATE TRIGGER trg_players_au AFTER UPDATE ON Players
FOR EACH ROW BEGIN
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', NEW.player_id,'UPDATE');
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_players_ad;
DELIMITER $$
CREATE TRIGGER trg_players_ad AFTER DELETE ON Players
FOR EACH ROW BEGIN
  INSERT INTO Audit_Log(table_name,record_id,action)
  VALUES('Players', OLD.player_id,'DELETE');
END$$
DELIMITER ;

SET SQL_MODE=@OLD_SQL_MODE;
