from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import sqlite3
import os
import re
import json
import random
import openai
from openai import OpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

init_db()

# User Model
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

# Load user
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(id=row[0], username=row[1], email=row[2], password=row[3])
    return None

# ---------------- Routes ----------------

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    reply = None
    if request.method == "POST":
        question = request.form.get("message")
        if question:
            reply = get_gpt_response(question)
    return render_template("chat.html", reply=reply)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                           (username, email, hashed_password))
            conn.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or Email already exists!", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            user_obj = User(id=user[0], username=user[1], email=user[2], password=user[3])
            login_user(user_obj, remember="remember" in request.form)
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------- GPT Functions ----------------

def get_gpt_response(question):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful C++ tutor. Only answer C++ questions. If the user asks anything else, respond: 'Sorry, I can only help with C++ programming questions.'"},
            {"role": "user", "content": question}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

# ✅ Route for selecting difficulty and generating quiz
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        difficulty = request.form.get('difficulty')

        # Prompt for GPT
        prompt = f"""
        Generate 20 unique multiple-choice C++ questions for {difficulty} level.
        Each question should be in the following JSON format:
        [
          {{
            "question": "What is the output of ...?",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "answer": "A"
          }},
          ...
        ]
        Return only the JSON array, nothing else.
        """

        # ✅ Call GPT with structured output
        response = client.chat.completions.create(
            model="gpt-4o",  # Faster and newer model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # ✅ Parse JSON safely
        try:
            data = json.loads(response.choices[0].message.content)

            # Ensure it's a list
            if isinstance(data, list):
                questions = data
            elif "questions" in data and isinstance(data["questions"], list):
                questions = data["questions"]
            else:
                raise ValueError("Invalid response format from GPT.")

            random.shuffle(questions)
            session['quiz'] = questions
            session['difficulty'] = difficulty

        except (json.JSONDecodeError, ValueError) as e:
            return f"Error parsing GPT response: {e}"

        return redirect(url_for('take_quiz'))

    return render_template('quiz_select.html')


# ✅ Route to display quiz and handle submission
@app.route('/take_quiz', methods=['GET', 'POST'])
def take_quiz():
    if 'quiz' not in session:
        return redirect(url_for('quiz'))

    questions = session['quiz']
    score = None

    if request.method == 'POST':
        correct_answers = 0
        for i, q in enumerate(questions):
            selected = request.form.get(f'question_{i}')
            if selected == q['answer']:
                correct_answers += 1

        score = f"{correct_answers} / {len(questions)}"
        return render_template('quiz_page.html', questions=questions, score=score, submitted=True)

    return render_template('quiz_page.html', questions=questions, score=score, submitted=False)


@app.route("/compile", methods=["GET", "POST"])
def compiler():
    return render_template('compiler.html')


# ---------------- Main ----------------
if __name__ == "__main__":
    app.run(debug=True)
