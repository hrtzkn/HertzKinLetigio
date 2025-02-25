from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from collections import Counter
from google_sheets import store_survey_responses, get_google_sheet_data

app = Flask(__name__, 
            template_folder='../../frontend/templates', 
            static_folder='../../frontend/static')

app.secret_key = "student_secret_key"

@app.route('/')
def student_login():
    return render_template('student/student_login.html')

@app.route('/student_login', methods=['POST'])
def login():
    exam_id = request.form['exam_id']
    password = request.form['password']

    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT exam_id, first_name, middle_name, last_name, email, password FROM students WHERE exam_id = ? AND password = ?", (exam_id, password))
    student = cursor.fetchone()
    conn.close()

    if student:
        session['student_id'] = student[0]
        return redirect(url_for('profile')) 
    else:
        flash('Invalid Examination ID or Password')
        return redirect(url_for('student_login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    exam_id = session['student_id']
    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        password = request.form['password']
        email = request.form['email']

        cursor.execute("""
            UPDATE students 
            SET first_name = ?, middle_name = ?, last_name = ?, password = ?, email = ? 
            WHERE exam_id = ?
        """, (first_name, middle_name, last_name, password, email, exam_id))
        conn.commit()
        flash('Profile updated successfully!')

    cursor.execute("SELECT first_name, middle_name, last_name, email, password FROM students WHERE exam_id = ?", (exam_id,))
    student = cursor.fetchone()
    conn.close()

    return render_template('student/profile.html', student={
        'first_name': student[0],
        'middle_name': student[1],
        'last_name': student[2],
        'email': student[3],
        'password': student[4]
    })

@app.route('/track_survey')
def track_survey():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    return render_template('student/track_survey.html')

@app.route('/survey')
def survey():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    exam_id = session['student_id']
    return render_template('student/survey.html', student_exam_id=exam_id)

def store_survey_responses():
    """Fetches survey data from Google Sheets and stores it in SQLite."""
    responses = get_google_sheet_data()

    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    for row in responses:
        exam_id = row.get("Examination ID")
        timestamp = row.get("Timestamp")
        preferred_program = row.get("Preferred Program?")
        question_answers = [row.get(f"Question {i}", "N/A") for i in range(1, 11)]

        cursor.execute("""
            UPDATE students SET 
            preferred_program = ?, 
            timestamp = ?, 
            q1 = ?, q2 = ?, q3 = ?, q4 = ?, q5 = ?, 
            q6 = ?, q7 = ?, q8 = ?, q9 = ?, q10 = ? 
            WHERE exam_id = ?
        """, (preferred_program, timestamp, *question_answers, exam_id))

    conn.commit()
    conn.close()

@app.route('/fetch_responses')
def fetch_responses():
    """Route to manually fetch and store responses."""
    store_survey_responses()
    return "Survey responses have been updated in the database."

@app.route('/survey_results')
def survey_results():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    exam_id = session['student_id']

    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, middle_name, last_name FROM students WHERE exam_id = ?", (exam_id,))
    student = cursor.fetchone()
    conn.close()

    if not student:
        return render_template('student/survey_results.html', student_results=None)

    responses = get_google_sheet_data()

    if not responses:
        print("No survey responses found!")
        return render_template('student/survey_results.html', student_results=None)

    formatted_responses = [{k.strip().lower(): v for k, v in row.items()} for row in responses]

    student_response = next((row for row in formatted_responses if str(row.get("exam_id")) == str(exam_id)), None)

    if not student_response:
        return render_template('student/survey_results.html', student_results=None)

    answers = [student_response.get(f"question {i}", "N/A") for i in range(1, 11)]

    letters_only = [ans.split(".")[0].strip() for ans in answers if ans != "N/A"]

    letter_counts = Counter(letters_only)

    top_letters = letter_counts.most_common(3)

    top_letters_display = ", ".join([f"{letter} ({count})" for letter, count in top_letters]) if top_letters else "N/A"

    student_results = {
        "exam_id": exam_id,
        "first_name": student[0],
        "middle_name": student[1],
        "last_name": student[2],
        "preferred_program": student_response.get("preferred program?", "N/A"),
        "answers": answers,
        "top_chosen_letters": top_letters_display
    }

    return render_template('student/survey_results.html', student_results=student_results)

@app.route('/notifications')
def notifications():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))
    return render_template('student/notifications.html')

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.pop("student_id", None)
    return redirect(url_for("student_login"))

if __name__ == '__main__':
    app.run(port=5006, debug=True)