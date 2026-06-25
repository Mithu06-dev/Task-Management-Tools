TaskFlow — Project Description

TaskFlow is a small web-based task management app built with Flask (Python) + SQLite. It lets users register, log in, manage a personal task list, and update task progress through a simple workflow.

Key Features
✅ Create, update, and delete tasks
📌 Set task priorities (High, Medium, Low)
📅 Assign due dates and deadlines
🔄 Track task status (To Do, In Progress, Completed)
👥 User authentication and secure login system
📊 Interactive dashboard with task statistics
🔍 Search, sort, and filter tasks
📱 Fully responsive design for all devices
💾 Secure data storage and management

Tech Stack
Backend: Flask
Database: SQLite (task_manager.db)
Frontend: Jinja templates + CSS (in static/styles.css)
Security included: hashed passwords + per-user data isolation in SQL queries
Main Files
app.py — Flask application, routes, DB initialization, CRUD logic
templates/ — HTML pages (landing, login, register, dashboard, profile, base layout)
static/styles.css — UI styling
requirements.txt — Python dependencies
task_manager.db — SQLite database file
