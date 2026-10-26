# VinnEdu AI — Enhanced University Portal

A Flask + MySQL prototype for a university portal with role-based login, dashboard, branch/section-aware timetable, attendance summaries and an 11-agent directory.

## 1. Requirements
- Python 3.10–3.13 recommended
- MySQL Server running locally
- MySQL Workbench (optional, for running `schema.sql`)

## 2. Configure MySQL
1. Open MySQL Workbench and connect to your local MySQL Server.
2. Open `schema.sql` and run it (lightning icon). This creates `vinnedu_ai`.
3. Copy `.env.example` to `.env` in this project folder.
4. Set `MYSQL_USER` and `MYSQL_PASSWORD` to a MySQL account that can use the database.
5. If your MySQL host, port, or database name differs, update the matching `MYSQL_*` values.
6. Set `FLASK_SECRET_KEY` to a long random value before deployment.

The application creates its tables and sample courses on startup. It creates the demo accounts only when the `users` table is empty.

## 3. Install and run (VS Code PowerShell)
Open the terminal inside the `VinnEdu-AI-Enhanced` folder, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

If PowerShell blocks activation, use:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 4. Deploy on Render
1. Push this repository to GitHub and create a Render Blueprint using `render.yaml`.
2. Provide `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` in Render's environment settings. Use a hosted MySQL service reachable from Render; do not put credentials in this repository.
3. Render builds with `pip install -r requirements.txt`, starts `gunicorn wsgi:app`, and checks `/health`.

The configured MySQL database must already exist. The WSGI startup initializes or migrates the application tables. Ensure the database provider permits connections from the Render service.

## 5. Demo accounts
The app creates these accounts only when the `users` table is empty:
- Student: `student@vinnedu.local` / `Student@123`
- Teacher: `teacher@vinnedu.local` / `Teacher@123`
- Admin: `admin@vinnedu.local` / `Admin@123`

Change demo passwords before any real deployment. This is a development prototype, not production-ready identity management.

## 6. Features
- Dashboard counts for students, teachers and courses
- Multiple branches and sample course data
- Timetable add/view with room and faculty conflict checks
- Attendance recording and per-student/per-course summaries
- AI agent directory with simple rule-based request routing
- Signup/login with hashed passwords
- Health endpoint: `http://127.0.0.1:5000/health`

## Notes
- Demo data is fictional. Replace it with approved university data.
- The AI agent responses are rule-based demonstrations, not a connected LLM.
- Do not commit `.env` or real credentials to GitHub.
