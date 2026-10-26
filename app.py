
import os
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import Error, USE_POSTGRES, get_connection, initialize_database
from agents import AGENTS, answer_query


# =========================================================
# FLASK CONFIGURATION
# =========================================================

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key-before-deployment"
)


# =========================================================
# DATABASE HELPERS
# =========================================================

def query_all(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor() if USE_POSTGRES else connection.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def query_one(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor() if USE_POSTGRES else connection.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def execute_query(sql, params=()):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        if USE_POSTGRES and sql.lstrip().upper().startswith("INSERT"):
            sql = f"{sql.rstrip().rstrip(';')} RETURNING id"
        cursor.execute(sql, params)
        connection.commit()
        if USE_POSTGRES:
            row = cursor.fetchone()
            return row["id"] if row else None
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    try:
        user = query_one(
            """
            SELECT id, full_name, email, role
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )
        if user:
            user["name"] = user["full_name"]
        return user
    except Error:
        return None


@app.context_processor
def inject_template_variables():
    """Make current_user available in every HTML template."""
    return {"current_user": get_current_user()}


# =========================================================
# LOGIN PROTECTION
# =========================================================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = get_current_user()

        if not user:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))

        if user.get("role", "").lower() != "admin":
            flash("Administrator access is required.", "error")
            return redirect(url_for("dashboard"))

        return function(*args, **kwargs)

    return wrapper


# =========================================================
# HOME
# =========================================================

@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    # Uses your existing index.html template.
    return render_template("index.html")


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        requested_role = request.form.get("role", "student").strip().lower()

        if not full_name or not email or not password:
            flash("Please complete all required fields.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("signup.html")

        if requested_role == "faculty":
            requested_role = "teacher"
        if requested_role not in {"student", "teacher"}:
            flash("Choose a valid account role.", "error")
            return render_template("signup.html")

        role = requested_role

        try:
            existing_user = query_one(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            if existing_user:
                flash("An account with this email already exists.", "error")
                return render_template("signup.html")

            password_hash = generate_password_hash(password)

            execute_query(
                """
                INSERT INTO users
                    (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (full_name, email, password_hash, role)
            )

            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for("login"))

        except Error as error:
            app.logger.exception("Signup database error")
            flash(
                "Could not create your account. Check your database "
                "connection and users table.",
                "error"
            )

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Enter your email and password.", "error")
            return render_template("login.html")

        try:
            user = query_one(
                """
                SELECT id, full_name, email, password_hash, role
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            if (
                user
                and user.get("password_hash")
                and check_password_hash(user["password_hash"], password)
            ):
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]
                session["user_role"] = user["role"]

                flash("Welcome back!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid email or password.", "error")

        except Error:
            app.logger.exception("Login database error")
            flash(
                "Unable to access the database. Verify your .env settings.",
                "error"
            )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()

    if not user:
        session.clear()
        flash("Please log in again.", "error")
        return redirect(url_for("login"))

    stats = {
        "students": query_one(
            "SELECT COUNT(*) AS total FROM users WHERE role = 'student'"
        )["total"],
        "teachers": query_one(
            "SELECT COUNT(*) AS total FROM users WHERE role IN ('teacher', 'faculty')"
        )["total"],
        "courses": query_one("SELECT COUNT(*) AS total FROM courses")["total"],
    }
    notifications = query_all(
        """
        SELECT title, message, created_at
        FROM notifications
        ORDER BY created_at DESC
        LIMIT 5
        """
    )

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        notifications=notifications,
    )


# =========================================================
# TIMETABLE
# =========================================================

@app.route("/timetable", methods=["GET", "POST"])
@login_required
def timetable():
    user = get_current_user()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if request.method == "POST":
        if user["role"].lower() not in {"teacher", "faculty", "admin"}:
            flash("Only teachers and administrators can add classes.", "error")
            return redirect(url_for("timetable"))

        entry = {
            key: request.form.get(key, "").strip()
            for key in ("branch", "section", "course", "faculty", "room", "day_name", "start_time", "end_time")
        }
        try:
            start_time = datetime.strptime(entry["start_time"], "%H:%M").time()
            end_time = datetime.strptime(entry["end_time"], "%H:%M").time()
        except ValueError:
            flash("Enter valid class start and end times.", "error")
            return redirect(url_for("timetable"))

        if (
            not all(entry.values())
            or entry["day_name"] not in days
            or start_time >= end_time
        ):
            flash("Complete every field and choose a valid time range.", "error")
            return redirect(url_for("timetable"))

        try:
            course = query_one(
                "SELECT id FROM courses WHERE title = %s",
                (entry["course"],),
            )
            if not course:
                flash("Choose a course from the list.", "error")
                return redirect(url_for("timetable"))

            conflict = query_one(
                """
                SELECT id
                FROM timetable
                WHERE LOWER(day_name) = LOWER(%s)
                  AND start_time < %s
                  AND end_time > %s
                  AND (LOWER(room) = LOWER(%s) OR LOWER(faculty) = LOWER(%s))
                LIMIT 1
                """,
                (entry["day_name"], end_time, start_time, entry["room"], entry["faculty"]),
            )
            if conflict:
                flash("That room or faculty member is already scheduled during this time.", "error")
                return redirect(url_for("timetable"))

            execute_query(
                """
                INSERT INTO timetable
                    (branch, section, course, faculty, room, day_name, start_time, end_time, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    entry["branch"], entry["section"], entry["course"], entry["faculty"],
                    entry["room"], entry["day_name"], start_time, end_time, user["id"],
                ),
            )
            flash("Class added to the timetable.", "success")
            return redirect(url_for("timetable"))
        except Error:
            app.logger.exception("Could not add timetable entry")
            flash("Could not save the timetable entry.", "error")

    branches = query_all("SELECT DISTINCT branch FROM courses ORDER BY branch")
    courses = query_all("SELECT code, title FROM courses ORDER BY code")
    entries = query_all(
        """
        SELECT branch, section, course, faculty, room, day_name, start_time, end_time
        FROM timetable
        ORDER BY CASE LOWER(day_name)
            WHEN 'monday' THEN 1
            WHEN 'tuesday' THEN 2
            WHEN 'wednesday' THEN 3
            WHEN 'thursday' THEN 4
            WHEN 'friday' THEN 5
            WHEN 'saturday' THEN 6
            WHEN 'sunday' THEN 7
            ELSE 8
        END, start_time
        """
    )
    return render_template(
        "timetable.html",
        branches=[row["branch"] for row in branches],
        courses=courses,
        days=days,
        entries=entries,
    )


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    user = get_current_user()
    can_record = user["role"].lower() in {"teacher", "faculty", "admin"}

    if request.method == "POST":
        if not can_record:
            flash("Only teachers and administrators can record attendance.", "error")
            return redirect(url_for("attendance"))

        student_name = request.form.get("student_name", "").strip()
        course_name = request.form.get("course", "").strip()
        status = request.form.get("status", "").strip().title()
        raw_date = request.form.get("attendance_date", "").strip()
        try:
            attendance_date = (
                datetime.strptime(raw_date, "%Y-%m-%d").date()
                if raw_date
                else date.today()
            )
        except ValueError:
            flash("Enter a valid attendance date.", "error")
            return redirect(url_for("attendance"))

        if not student_name or not course_name or status not in {"Present", "Absent", "Late"}:
            flash("Complete every attendance field.", "error")
            return redirect(url_for("attendance"))

        try:
            course = query_one("SELECT id FROM courses WHERE title = %s", (course_name,))
            if not course:
                flash("Choose a course from the list.", "error")
                return redirect(url_for("attendance"))
            execute_query(
                """
                INSERT INTO attendance
                    (student_name, course, status, attendance_date, created_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (student_name, course_name, status, attendance_date, user["id"]),
            )
            flash("Attendance saved.", "success")
            return redirect(url_for("attendance"))
        except Error:
            app.logger.exception("Could not record attendance")
            flash("Could not save the attendance record.", "error")

    filter_sql = "" if can_record else " WHERE student_name = %s"
    params = () if can_record else (user["full_name"],)
    summary = query_all(
        f"""
        SELECT student_name, course,
             SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
             SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late_count,
               COUNT(*) AS total_count,
             ROUND(100.0 * SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) / COUNT(*), 2) AS attendance_pct
        FROM attendance{filter_sql}
        GROUP BY student_name, course
        ORDER BY student_name, course
        """,
        params,
    )
    records = query_all(
        f"""
        SELECT attendance_date, student_name, course, status
        FROM attendance{filter_sql}
        ORDER BY attendance_date DESC, id DESC
        LIMIT 100
        """,
        params,
    )
    courses = query_all("SELECT code, title FROM courses ORDER BY code")
    return render_template(
        "attendance.html", summary=summary, records=records, courses=courses
    )


# =========================================================
# AI AGENTS
# IMPORTANT: Endpoint name is "agents_page".
# Templates should use url_for('agents_page').
# =========================================================

@app.route("/agents", methods=["GET", "POST"], endpoint="agents_page")
@login_required
def agents_page():
    user = get_current_user()
    result = None
    log_id = None

    if request.method == "POST":
        user_query = request.form.get("query", "").strip()

        if not user_query:
            flash("Please enter a question for the AI agent.", "error")
        else:
            try:
                agent_name, match_score, response_text, matched_keywords = answer_query(user_query)
                score = max(0.0, min(1.0, float(match_score)))
                result = (agent_name, score, response_text)
                try:
                    log_id = execute_query(
                        """
                        INSERT INTO agent_logs
                            (
                                user_id,
                                user_query,
                                agent_name,
                                match_score,
                                matched_keywords,
                                routing_method
                            )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user["id"],
                            user_query,
                            agent_name or "General Agent",
                            round(score * 100, 2),
                            ", ".join(matched_keywords or []),
                            "keyword"
                        )
                    )
                except Error:
                    # The agent can still respond if logging has not
                    # been configured successfully.
                    app.logger.exception("Could not save agent query log")

            except Exception:
                app.logger.exception("AI agent error")
                flash(
                    "The AI agent encountered an error. Check agents.py.",
                    "error"
                )
    return render_template(
        "agents.html", agents=AGENTS, result=result, log_id=log_id
    )


# =========================================================
# AI AGENT FEEDBACK
# =========================================================

@app.route("/agents/feedback", methods=["POST"])
@login_required
def agent_feedback():
    user = get_current_user()

    try:
        log_id = int(request.form.get("log_id", "0"))
        rating = int(request.form.get("rating", "0"))
        feedback_text = request.form.get("feedback_text", "").strip()

        if log_id <= 0 or rating < 1 or rating > 5:
            flash("Choose a rating between 1 and 5.", "error")
            return redirect(url_for("agents_page"))

        # Ensure users can only rate their own query logs.
        log = query_one(
            """
            SELECT id
            FROM agent_logs
            WHERE id = %s AND user_id = %s
            """,
            (log_id, user["id"])
        )

        if not log:
            flash("That AI agent query was not found.", "error")
            return redirect(url_for("agents_page"))

        if USE_POSTGRES:
            feedback_sql = """
                INSERT INTO agent_feedback
                    (log_id, user_id, rating, feedback_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (log_id, user_id) DO UPDATE
                SET rating = EXCLUDED.rating,
                    feedback_text = EXCLUDED.feedback_text
            """
        else:
            feedback_sql = """
                INSERT INTO agent_feedback
                    (log_id, user_id, rating, feedback_text)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rating = VALUES(rating),
                    feedback_text = VALUES(feedback_text)
            """
        execute_query(feedback_sql, (log_id, user["id"], rating, feedback_text))

        flash("Thank you! Your feedback has been saved.", "success")

    except (ValueError, Error):
        app.logger.exception("Could not save agent feedback")
        flash("Could not save feedback. Check the agent tables.", "error")

    return redirect(url_for("agents_page"))


# =========================================================
# ADMIN AGENT ANALYTICS
# =========================================================

@app.route("/agents/analytics")
@login_required
@admin_required
def agent_analytics():
    try:
        totals = query_one(
            """
            SELECT
                COUNT(*) AS total_queries,
                COUNT(DISTINCT user_id) AS unique_users,
                AVG(match_score) AS average_score
            FROM agent_logs
            """
        )

        agent_stats = query_all(
            """
            SELECT
                agent_name,
                COUNT(*) AS total_queries,
                AVG(match_score) AS average_score
            FROM agent_logs
            GROUP BY agent_name
            ORDER BY total_queries DESC
            """
        )

        feedback_stats = query_all(
            """
            SELECT
                agent_logs.agent_name,
                COUNT(agent_feedback.id) AS feedback_count,
                AVG(agent_feedback.rating) AS average_rating
            FROM agent_logs
            LEFT JOIN agent_feedback
                ON agent_logs.id = agent_feedback.log_id
            GROUP BY agent_logs.agent_name
            ORDER BY feedback_count DESC
            """
        )

        return render_template(
            "agent_analytics.html",
            totals=totals,
            agent_stats=agent_stats,
            feedback_stats=feedback_stats,
        )

    except Error:
        app.logger.exception("Agent analytics error")
        flash("Unable to load agent analytics.", "error")
        return redirect(url_for("dashboard"))


# =========================================================
# COMPATIBILITY ROUTE
# Allows older templates using url_for('agents') to keep working.
# =========================================================

app.add_url_rule(
    "/agents",
    endpoint="agents",
    view_func=agents_page,
    methods=["GET", "POST"],
    defaults={},
)


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):
    try:
        return render_template("404.html"), 404
    except Exception:
        return "Page not found (404).", 404


@app.errorhandler(500)
def internal_server_error(error):
    app.logger.exception("Internal server error")
    return (
        "An internal server error occurred. Check the VS Code terminal "
        "for the traceback.",
        500,
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    try:
        initialize_database()
        print("Database initialization completed.")
    except Exception:
        app.logger.exception("Database initialization failed")
        print(
            "WARNING: Database initialization failed. "
            "Check .env and MySQL before using the app."
        )

    app.run(
        debug=os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"},
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
    )

