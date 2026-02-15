from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecret"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="quiz_db"
)


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
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()
    return render_template("topics.html", topics=topics)


# ---------------- READY ----------------
@app.route('/ready/<int:topic_id>')
def ready(topic_id):
    return render_template("ready.html", topic_id=topic_id)


# ---------------- QUIZ ----------------
@app.route('/quiz/<int:topic_id>')
def quiz(topic_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, question, option1, option2, option3, option4, correct_option
        FROM questions
        WHERE topic_id=%s
        ORDER BY RAND()
        LIMIT 10
    """, (topic_id,))

    questions = cursor.fetchall()
    print("QUESTIONS DATA:", questions)

    # Ensure no NULL options
    questions = [q for q in questions if all([q['option1'], q['option2'], q['option3'], q['option4']])]

    session['question_ids'] = [q['id'] for q in questions]

    return render_template("quiz.html",
                           questions=questions,
                           topic_id=topic_id)


# ---------------- SUBMIT ----------------
@app.route('/submit/<int:topic_id>', methods=['POST'])
def submit(topic_id):

    score = 0
    question_ids = session.get('question_ids')

    if not question_ids:
        return redirect('/topics')

    cursor = db.cursor(dictionary=True)

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

    # Insert result first
    cursor2 = db.cursor()
    cursor2.execute("""
        INSERT INTO results (player_name, topic_id, score)
        VALUES (%s, %s, %s)
    """, (session['player_name'], topic_id, score))

    db.commit()

    # Now update rankings
    update_rankings(topic_id)

    return redirect(f"/leaderboard/{topic_id}")



# ---------------- UPDATE RANKINGS ----------------
def update_rankings(topic_id):

    cursor = db.cursor(dictionary=True)

    # Order by score DESC
    cursor.execute("""
        SELECT id, score
        FROM results
        WHERE topic_id = %s
        ORDER BY score DESC, created_at ASC
    """, (topic_id,))

    results = cursor.fetchall()

    rank = 1
    for row in results:
        cursor2 = db.cursor()
        cursor2.execute("""
            UPDATE results
            SET rank_position = %s
            WHERE id = %s
        """, (rank, row['id']))
        db.commit()
        rank += 1


# ---------------- DELETE RANKINGS ----------------
@app.route('/admin/delete_result/<int:result_id>')
def delete_result(result_id):

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor()
    cursor.execute("DELETE FROM results WHERE id=%s", (result_id,))
    db.commit()

    return redirect('/admin/rankings')



# ---------------- LEADERBOARD ----------------
@app.route('/leaderboard/<int:topic_id>')
def leaderboard(topic_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT player_name, score, rank_position
        FROM results
        WHERE topic_id = %s
        ORDER BY rank_position ASC
    """, (topic_id,))

    rankings = cursor.fetchall()

    return render_template("leaderboard.html", rankings=rankings)



# ---------------- ADMIN LOGIN & LOGOUT ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM admin
            WHERE username=%s AND password=%s
        """, (username, password))

        if cursor.fetchone():
            session['admin'] = True
            return redirect('/admin/dashboard')

    return render_template("admin_login.html")


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')


# ---------------- ADMIN RANKINGS ----------------
@app.route('/admin/rankings')
def admin_rankings():

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT r.player_name, r.score, r.rank_position,
               t.name AS topic_name, r.created_at
        FROM results r
        JOIN topics t ON r.topic_id = t.id
        ORDER BY t.name, r.rank_position ASC
    """)

    rankings = cursor.fetchall()

    return render_template("admin_rankings.html",
                           rankings=rankings)


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin/dashboard')
def dashboard():
    return render_template("admin_dashboard.html")


# ---------------- ADD TOPIC ----------------
@app.route('/admin/add_topic', methods=['GET', 'POST'])
def add_topic():
    if request.method == 'POST':
        name = request.form['name']
        cursor = db.cursor()
        cursor.execute("INSERT INTO topics (name) VALUES (%s)", (name,))
        db.commit()
        return redirect('/admin/dashboard')
    return render_template("add_topic.html")


# ---------------- DELETE TOPIC ----------------
@app.route('/admin/delete_topic/<int:topic_id>')
def delete_topic(topic_id):

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor()
    cursor.execute("DELETE FROM topics WHERE id=%s", (topic_id,))
    db.commit()

    return redirect('/admin/manage_topics')


# ---------------- MANAGE TOPIC ----------------
@app.route('/admin/manage_topics')
def manage_topics():

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics ORDER BY id ASC")
    topics = cursor.fetchall()

    return render_template("manage_topics.html", topics=topics)


# ---------------- MANAGE QUESTION ----------------
@app.route('/admin/manage_questions')
def manage_questions():

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT q.id, q.question, t.name AS topic_name
        FROM questions q
        JOIN topics t ON q.topic_id = t.id
    """)
    questions = cursor.fetchall()

    return render_template("manage_questions.html", questions=questions)



# ---------------- ADD QUESTION ----------------
@app.route('/admin/add_question', methods=['GET', 'POST'])
def add_question():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    if request.method == 'POST':
        cursor2 = db.cursor()
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
        db.commit()
        return redirect('/admin/dashboard')

    return render_template("add_question.html", topics=topics)


# ---------------- DELETE QUESTION ----------------
@app.route('/admin/delete_question/<int:question_id>')
def delete_question(question_id):

    if 'admin' not in session:
        return redirect('/admin')

    cursor = db.cursor()
    cursor.execute("DELETE FROM questions WHERE id=%s", (question_id,))
    db.commit()

    return redirect('/admin/manage_questions')



if __name__ == "__main__":
    app.run(debug=True)
