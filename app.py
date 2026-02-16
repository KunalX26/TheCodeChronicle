import os
from flask import Flask, render_template, request, redirect, session, abort
import mysql.connector
from functools import wraps

app = Flask(__name__)
# Uses a secure key if provided by the server, otherwise falls back to local testing key
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")


# ---------------- DATABASE CONNECTION ----------------
# CRITICAL FIX: This function dynamically reads from Render's Environment Variables
# instead of hardcoding "localhost".
# ---------------- DATABASE CONNECTION ----------------
def get_db_connection():
    """Safely connects to the database for each request."""
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "quiz_db"),
        port=os.environ.get("DB_PORT", "3306")
    )


# ---------------- AUTHORIZATION ERROR ----------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            abort(403)  # Authorization error
        return f(*args, **kwargs)

    return decorated_function


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


# ---------------- HOME ----------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session['player_name'] = request.form['name']
        return redirect('/topics')
    return render_template("index.html")


# ---------------- TOPICS ----------------
@app.route('/topics')
def topics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("topics.html", topics=topics)


# ---------------- READY ----------------
@app.route('/ready/<int:topic_id>')
def ready(topic_id):
    return render_template("ready.html", topic_id=topic_id)


# ---------------- QUIZ ----------------
@app.route('/quiz/<int:topic_id>')
def quiz(topic_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, question, option1, option2, option3, option4, correct_option
        FROM questions
        WHERE topic_id=%s
        ORDER BY RAND()
        LIMIT 10
    """, (topic_id,))

    questions = cursor.fetchall()

    # Ensure no NULL options
    questions = [q for q in questions if all([q['option1'], q['option2'], q['option3'], q['option4']])]
    session['question_ids'] = [q['id'] for q in questions]

    cursor.close()
    conn.close()

    return render_template("quiz.html", questions=questions, topic_id=topic_id)


# ---------------- SUBMIT ----------------
@app.route('/submit/<int:topic_id>', methods=['POST'])
def submit(topic_id):
    score = 0
    question_ids = session.get('question_ids')

    if not question_ids:
        return redirect('/topics')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    format_ids = ",".join(str(i) for i in question_ids)
    cursor.execute(f"""
        SELECT id, correct_option
        FROM questions
        WHERE id IN ({format_ids})
    """)
    questions = cursor.fetchall()

    for q in questions:
        selected = request.form.get(str(q['id']))
        if selected == q['correct_option']:
            score += 2

    # Insert result
    cursor2 = conn.cursor()
    cursor2.execute("""
        INSERT INTO results (player_name, topic_id, score)
        VALUES (%s, %s, %s)
    """, (session['player_name'], topic_id, score))
    conn.commit()

    # Now update rankings
    update_rankings(topic_id, conn)

    cursor.close()
    cursor2.close()
    conn.close()

    return redirect(f"/leaderboard/{topic_id}")


# ---------------- UPDATE RANKINGS ----------------
def update_rankings(topic_id, conn=None):
    close_connection = False
    if conn is None:
        conn = get_db_connection()
        close_connection = True

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, score
        FROM results
        WHERE topic_id = %s
        ORDER BY score DESC, created_at ASC
    """, (topic_id,))

    results = cursor.fetchall()

    rank = 1
    for row in results:
        cursor2 = conn.cursor()
        cursor2.execute("""
            UPDATE results
            SET rank_position = %s
            WHERE id = %s
        """, (rank, row['id']))
        conn.commit()
        cursor2.close()
        rank += 1

    cursor.close()
    if close_connection:
        conn.close()


# ---------------- DELETE RANKINGS ----------------
@app.route('/admin/delete_result/<int:result_id>')
@admin_required
def delete_result(result_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get topic_id before deleting
    cursor.execute("SELECT topic_id FROM results WHERE id=%s", (result_id,))
    row = cursor.fetchone()

    if row:
        topic_id = row['topic_id']

        # Delete result
        cursor2 = conn.cursor()
        cursor2.execute("DELETE FROM results WHERE id=%s", (result_id,))
        conn.commit()
        cursor2.close()

        # Recalculate ranking
        update_rankings(topic_id, conn)

    cursor.close()
    conn.close()
    return redirect('/admin/rankings')


# ---------------- LEADERBOARD ----------------
@app.route('/leaderboard/<int:topic_id>')
def leaderboard(topic_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT player_name, score, rank_position
        FROM results
        WHERE topic_id = %s
        ORDER BY rank_position ASC
    """, (topic_id,))

    rankings = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("leaderboard.html", rankings=rankings)


# ---------------- ADMIN LOGIN & LOGOUT ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM admin
            WHERE username=%s AND password=%s
        """, (username, password))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['admin'] = True
            return redirect('/admin/dashboard')
        else:
            return render_template("admin_login.html", error="Invalid Credentials")

    return render_template("admin_login.html")


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')


# ---------------- ADMIN RANKINGS ----------------
@app.route('/admin/rankings')
@admin_required
def admin_rankings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT r.id, r.player_name, r.score, r.rank_position,
               r.topic_id,
               t.name AS topic_name, r.created_at
        FROM results r
        JOIN topics t ON r.topic_id = t.id
        ORDER BY t.name, r.rank_position ASC
    """)

    rankings = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin_rankings.html", rankings=rankings)


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin/dashboard')
@admin_required
def dashboard():
    return render_template("admin_dashboard.html")


# ---------------- ADD TOPIC ----------------
@app.route('/admin/add_topic', methods=['GET', 'POST'])
@admin_required
def add_topic():
    if request.method == 'POST':
        name = request.form['name']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO topics (name) VALUES (%s)", (name,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/admin/dashboard')
    return render_template("add_topic.html")


# ---------------- DELETE TOPIC ----------------
@app.route('/admin/delete_topic/<int:topic_id>')
@admin_required
def delete_topic(topic_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM topics WHERE id=%s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/admin/manage_topics')


# ---------------- MANAGE TOPIC ----------------
@app.route('/admin/manage_topics')
@admin_required
def manage_topics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics ORDER BY id ASC")
    topics = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("manage_topics.html", topics=topics)


# ---------------- MANAGE QUESTION ----------------
@app.route('/admin/manage_questions')
@admin_required
def manage_questions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.id, q.question, t.name AS topic_name
        FROM questions q
        JOIN topics t ON q.topic_id = t.id
    """)
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("manage_questions.html", questions=questions)


# ---------------- ADD QUESTION ----------------
@app.route('/admin/add_question', methods=['GET', 'POST'])
@admin_required
def add_question():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    if request.method == 'POST':
        cursor2 = conn.cursor()
        cursor2.execute("""
            INSERT INTO questions
            (topic_id, question, option1, option2, option3, option4, correct_option)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['topic_id'],
            request.form['question'],
            request.form['option1'],
            request.form['option2'],
            request.form['option3'],
            request.form['option4'],
            request.form['correct']
        ))
        conn.commit()
        cursor2.close()
        cursor.close()
        conn.close()
        return redirect('/admin/dashboard')

    cursor.close()
    conn.close()
    return render_template("add_question.html", topics=topics)


# ---------------- DELETE QUESTION ----------------
@app.route('/admin/delete_question/<int:question_id>')
@admin_required
def delete_question(question_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id=%s", (question_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/admin/manage_questions')


if __name__ == "__main__":
    app.run(debug=True)