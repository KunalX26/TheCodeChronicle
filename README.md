Markdown
# 🗞️ The Code Chronicle: Interactive Logic Quiz Platform

**The Code Chronicle** is a fully responsive, stateful quiz web application designed with a unique aesthetic that blends vintage newsprint with retro sysadmin terminal interfaces. 

It allows users to test their programming logic against a ticking clock, dynamically ranking their performance on global leaderboards. The application features a complete player-facing execution loop and a secured backend administrative dashboard for managing content.

## ✨ Core Features

* **Timed Execution Loop:** Client-side JavaScript enforces a strict 10-second timer per query, automatically advancing upon timeout to simulate high-pressure execution environments.
* **Dynamic Global Benchmarks:** Automated backend ranking engine calculates scores and dynamically updates player rankings (leaderboards) based on performance and completion time.
* **Responsive "Newsprint" UI:** Styled entirely with Tailwind CSS, featuring custom `@keyframes` animations (`inkFade`, `tickPulse`) for an immersive, tactile user experience across mobile and desktop.
* **Sysadmin Master Control:** A secured, session-based admin dashboard with full CRUD (Create, Read, Update, Delete) capabilities to manage tech stacks, logic queries (questions), and purge execution logs.

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Database:** MySQL (`mysql.connector`)
* **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript
* **Templating:** Jinja2

## 🚀 Local Installation & Setup

Follow these steps to spin up the local development server.

1. Clone the Repository
```
git clone [https://github.com/YOUR_USERNAME/the-code-chronicle.git](https://github.com/YOUR_USERNAME/the-code-chronicle.git)
cd the-code-chronicle
```
2. Set Up the Virtual Environment & Dependencies
```
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install Flask mysql-connector-python
```
3. Database Configuration
Ensure MySQL is running on your machine. Log into your MySQL server and execute the following schema to set up the quiz_db database:

SQL
```
CREATE DATABASE quiz_db;
USE quiz_db;

CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Insert your default admin credentials
INSERT INTO admin (username, password) VALUES ('admin', 'your_secure_password');

CREATE TABLE topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic_id INT NOT NULL,
    question TEXT NOT NULL,
    option1 VARCHAR(255) NOT NULL,
    option2 VARCHAR(255) NOT NULL,
    option3 VARCHAR(255) NOT NULL,
    option4 VARCHAR(255) NOT NULL,
    correct_option VARCHAR(50) NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    topic_id INT NOT NULL,
    score INT NOT NULL,
    rank_position INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);
```
4. Configure Application Variables
In app.py, update the database connection variables to match your local MySQL setup:

Python
```
db = mysql.connector.connect(
    host="localhost",
    user="root",          # Replace with your MySQL username
    password="",          # Replace with your MySQL password
    database="quiz_db"
)
```
5. Initialize the Server
```
python app.py
```
The application will boot up at http://127.0.0.1:5000/.

## 📂 Project Structure Overview

* / - Front Page: Entry point for users to input their Developer Alias.

*  /topics - Registry Index: Users select the Tech Stack they want to test.

*  /ready/<id> - Boot Sequence: A 3-second animated countdown before execution.

*  /quiz/<id> - Active Session: The 10-question timed loop.

*  /leaderboard/<id> - Benchmarks: View the top-ranked aliases for a specific stack.

*  /admin - Root Access: Secure login portal for administrators.

*  /admin/dashboard - Switchboard: Master control panel to add stacks, draft queries, and manage logs.

## 🔮 Future Development Roadmap

*  Implement connection pooling for robust multi-user database access.

*  Transition from raw plaintext admin passwords to werkzeug.security password hashing.

*  Refactor database ranking logic to utilize SQL window functions (RANK() OVER) for improved scalability.

*  Consolidate repeating UI elements using Jinja2 base.html inheritance.
