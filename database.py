
import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "vinnedu_ai"),
}


def get_connection():
    """Create a MySQL database connection."""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """Create the users table if it does not exist."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(30) NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing tables are not modified by CREATE TABLE IF NOT EXISTS.
        cursor.execute("SHOW COLUMNS FROM users")
        user_columns = {row[0]: row for row in cursor.fetchall()}
        existing_columns = set(user_columns)

        if "password_hash" not in existing_columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN password_hash VARCHAR(255) NULL
            """)

        if "created_at" not in existing_columns:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
        if "full_name" in existing_columns:
            nullability = "NULL" if user_columns["full_name"][2] == "YES" else "NOT NULL"
            cursor.execute(
                f"ALTER TABLE users MODIFY full_name VARCHAR(150) {nullability}"
            )
        if "email" in existing_columns:
            nullability = "NULL" if user_columns["email"][2] == "YES" else "NOT NULL"
            cursor.execute(
                f"ALTER TABLE users MODIFY email VARCHAR(255) {nullability}"
            )

        connection.commit()
        print("Users table initialized successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def init_agent_tables():
    """Create tables for AI agent query logs and feedback."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
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
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_feedback (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                log_id BIGINT NOT NULL,
                user_id INT NOT NULL,
                rating TINYINT NOT NULL,
                feedback_text TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_agent_feedback_log
                    FOREIGN KEY (log_id)
                    REFERENCES agent_logs(id)
                    ON DELETE CASCADE,
                UNIQUE KEY unique_user_log_feedback (log_id, user_id)
            )
        """)

        connection.commit()
        print("AI agent tables initialized successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def init_portal_tables():
    """Create the course, timetable, attendance, and notification tables."""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(30) NOT NULL UNIQUE,
                title VARCHAR(150) NOT NULL,
                branch VARCHAR(100) NOT NULL
            )
        """)
        cursor.execute("""
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
            )
        """)
        cursor.execute("""
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
            )
        """)
        cursor.execute("SHOW COLUMNS FROM timetable")
        timetable_columns = {row[0] for row in cursor.fetchall()}
        for column, definition in {
            "branch": "VARCHAR(100) NOT NULL DEFAULT 'Computer Science'",
            "section": "VARCHAR(10) NOT NULL DEFAULT 'A'",
            "created_by": "INT NULL",
            "created_at": "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP",
        }.items():
            if column not in timetable_columns:
                cursor.execute(
                    f"ALTER TABLE timetable ADD COLUMN {column} {definition}"
                )

        cursor.execute("SHOW COLUMNS FROM attendance")
        attendance_columns = {row[0] for row in cursor.fetchall()}
        if "attendance_date" not in attendance_columns:
            cursor.execute(
                "ALTER TABLE attendance ADD COLUMN attendance_date DATE NULL"
            )
        if "created_by" not in attendance_columns:
            cursor.execute(
                "ALTER TABLE attendance ADD COLUMN created_by INT NULL"
            )
        if "created_at" not in attendance_columns:
            cursor.execute(
                "ALTER TABLE attendance "
                "ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP"
            )

        if "recorded_at" in attendance_columns:
            cursor.execute(
                """
                UPDATE attendance
                SET attendance_date = COALESCE(DATE(recorded_at), CURRENT_DATE())
                WHERE attendance_date IS NULL
                """
            )
        else:
            cursor.execute(
                "UPDATE attendance SET attendance_date = CURRENT_DATE() "
                "WHERE attendance_date IS NULL"
            )
        cursor.execute(
            "ALTER TABLE attendance MODIFY attendance_date DATE NOT NULL"
        )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(150) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.executemany(
            """
            INSERT INTO courses (code, title, branch)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE title = VALUES(title), branch = VALUES(branch)
            """,
            [
                ("CS101", "Introduction to Computing", "Computer Science"),
                ("CS201", "Data Structures", "Computer Science"),
                ("EE101", "Circuit Fundamentals", "Electrical Engineering"),
                ("ME101", "Engineering Mechanics", "Mechanical Engineering"),
            ],
        )

        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            demo_users = [
                ("Demo Student", "student@vinnedu.local", "Student@123", "student"),
                ("Demo Teacher", "teacher@vinnedu.local", "Teacher@123", "teacher"),
                ("Demo Admin", "admin@vinnedu.local", "Admin@123", "admin"),
            ]
            cursor.executemany(
                """
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    (name, email, generate_password_hash(password), role)
                    for name, email, password, role in demo_users
                ],
            )

        cursor.execute("SELECT COUNT(*) FROM notifications")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO notifications (title, message) VALUES (%s, %s)",
                ("Welcome", "The VinnEdu university portal is ready to use."),
            )

        connection.commit()
        print("Portal tables initialized successfully.")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def initialize_database():
    """Initialize all application tables."""
    init_db()
    init_portal_tables()
    init_agent_tables()


if __name__ == "__main__":
    initialize_database()
    print("Database initialization completed.")
