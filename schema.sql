CREATE DATABASE IF NOT EXISTS vinnedu_ai
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vinnedu_ai;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'student',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(30) NOT NULL UNIQUE,
  title VARCHAR(150) NOT NULL,
  branch VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS timetable (
  id INT AUTO_INCREMENT PRIMARY KEY,
  branch VARCHAR(100) NOT NULL,
  section VARCHAR(10) NOT NULL,
  course VARCHAR(150) NOT NULL,
  faculty VARCHAR(150) NOT NULL,
  room VARCHAR(80) NOT NULL,
  day_name VARCHAR(15) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_timetable_day_time (day_name, start_time),
  INDEX idx_timetable_room (room)
);

CREATE TABLE IF NOT EXISTS attendance (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  student_name VARCHAR(150) NOT NULL,
  course VARCHAR(150) NOT NULL,
  status ENUM('Present', 'Absent', 'Late') NOT NULL,
  attendance_date DATE NOT NULL,
  created_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_attendance_student_course (student_name, course),
  INDEX idx_attendance_date (attendance_date)
);

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(150) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  user_query TEXT NOT NULL,
  agent_name VARCHAR(100) NOT NULL,
  match_score DECIMAL(5,2) NULL,
  matched_keywords TEXT NULL,
  routing_method VARCHAR(50) NOT NULL DEFAULT 'keyword',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_agent_name (agent_name),
  INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS agent_feedback (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  log_id BIGINT NOT NULL,
  user_id INT NOT NULL,
  rating TINYINT NOT NULL,
  feedback_text TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_agent_feedback_log
    FOREIGN KEY (log_id) REFERENCES agent_logs(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user_log_feedback (log_id, user_id)
);

INSERT INTO courses (code, title, branch) VALUES
  ('CS101', 'Introduction to Computing', 'Computer Science'),
  ('CS201', 'Data Structures', 'Computer Science'),
  ('EE101', 'Circuit Fundamentals', 'Electrical Engineering'),
  ('ME101', 'Engineering Mechanics', 'Mechanical Engineering')
ON DUPLICATE KEY UPDATE title = VALUES(title), branch = VALUES(branch);
