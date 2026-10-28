import os
import time

import mysql.connector
from flask import Flask, request, redirect, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "flaskdb"),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def initialize_db():
    for attempt in range(30):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
            print("MySQL connected; users table ready.")
            return
        except mysql.connector.Error as exc:
            print(f"MySQL not ready ({attempt + 1}/30): {exc}")
            time.sleep(2)
    raise RuntimeError("Could not connect to MySQL")

PAGE = """
<!doctype html>
<html>
<head>
  <title>Flask MySQL App</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial; max-width: 420px; margin: 50px auto;
           padding: 20px; background: #f4f7fb; }
    form { background: white; padding: 24px; border-radius: 12px; }
    input, button { box-sizing: border-box; width: 100%;
                    padding: 12px; margin: 8px 0; }
    button { background: #1769aa; color: white; border: 0; }
  </style>
</head>
<body>
  <h2>Flask + MySQL Registration</h2>
  <form method="post">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password"
           placeholder="Password (minimum 8 characters)" required>
    <button type="submit">Register</button>
  </form>
  <p>{{ message }}</p>
  <p><a href="/users">View registered usernames</a></p>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or len(password) < 8:
            message = "Enter a username and password of at least 8 characters."
        else:
            conn = None
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, generate_password_hash(password))
                )
                conn.commit()
                message = "Registration successful!"
                cursor.close()
            except mysql.connector.IntegrityError:
                message = "Username already exists."
            except mysql.connector.Error:
                message = "Database operation failed."
            finally:
                if conn and conn.is_connected():
                    conn.close()

    return render_template_string(PAGE, message=message)

@app.route("/users")
def users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users ORDER BY id")
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    return "<h2>Registered Users</h2>" + "".join(
        f"<p>{user_id}: {username}</p>" for user_id, username in records
    ) + '<a href="/">Back</a>'

@app.route("/health")
def health():
    conn = get_db()
    conn.close()
    return {"status": "ok", "database": "connected"}

if __name__ == "__main__":
    initialize_db()
    app.run(host="0.0.0.0", port=5000)