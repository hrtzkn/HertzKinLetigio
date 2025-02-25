from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pandas as pd
import os
import sys

app = Flask(__name__, 
            template_folder='../../frontend/templates', 
            static_folder='../../frontend/static')

app.secret_key = "your_secret_key"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from student_server.google_sheets import get_google_sheet_data

DEFAULT_USERNAME = "hk"
DEFAULT_PASSWORD = "hk"

UPLOAD_FOLDER = '../../database/uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_to_db(data):
    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    required_columns = {'exam_id', 'first_name', 'middle_name', 'last_name', 'email'}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        flash(f"Error: Missing required columns: {missing_columns}")
        return

    if 'preferred_program' not in data.columns:
        data['preferred_program'] = None

    for _, row in data.iterrows():
       
        cursor.execute('''
            SELECT COUNT(*) FROM students WHERE exam_id = ? AND email = ?
        ''', (row['exam_id'], row['email']))
        
        if cursor.fetchone()[0] == 0:
            try:
                cursor.execute('''
                    INSERT INTO students (exam_id, first_name, middle_name, last_name, email, password, preferred_program) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (row['exam_id'], row['first_name'], row['middle_name'], row['last_name'], row['email'], '12345', row['preferred_program']))
            except sqlite3.IntegrityError as e:
                flash(f"Error inserting data: {e}")
                conn.rollback()
                conn.close()
                return
        else:
            flash(f"Duplicate student skipped: {row['exam_id']} - {row['email']}")

    conn.commit()
    conn.close()

@app.route('/')
def admin_login():
    return render_template('admin/login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
        session['admin'] = username
        conn.close()
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM admins WHERE user_id = ? AND password = ?", (username, password))
    admin = cursor.fetchone()
    conn.close()

    if admin:
        session['admin'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('admin/login.html', error="Invalid credentials")

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    username = session['admin']
    if username == DEFAULT_USERNAME:
        first_name = "HK"
    else:
        conn = sqlite3.connect('../../database/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT first_name FROM admins WHERE user_id = ?", (username,))
        admin = cursor.fetchone()
        conn.close()
        first_name = admin[0] if admin else username

    return render_template('admin/dashboard.html', user_id=first_name)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        data = pd.read_excel(filepath)
        data.columns = data.columns.str.strip()

        save_to_db(data)
        flash('File uploaded successfully. Duplicate students were skipped.')
        return redirect(url_for('student_list'))
    else:
        flash('Invalid file format')
        return redirect(request.url)

@app.route('/add_participant', methods=['GET', 'POST'])
def add_participant():
    if request.method == 'POST':
        exam_id = request.form['exam_id']
        first_name = request.form['first_name']
        middle_name = request.form.get('middle_name', '')
        last_name = request.form['last_name']
        email = request.form['email']
        
        conn = sqlite3.connect('../../database/database.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO students (exam_id, first_name, middle_name, last_name, email, password) 
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (exam_id, first_name, middle_name, last_name, email, '12345'))
            conn.commit()
            flash('Participant added successfully!')
            return redirect(url_for('student_list'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('Error: Duplicate entry or invalid data.')
        finally:
            conn.close()

    return render_template('admin/add_participant.html')

@app.route('/student_list')
def student_list():
    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT exam_id, first_name, middle_name, last_name, email FROM students")
    students = cursor.fetchall()
    conn.close()
    return render_template('admin/student_list.html', students=students)

@app.route('/add_admin', methods=['GET', 'POST'])
def add_admin():
    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        user_id = request.form['user_id']
        email = request.form['email']
        password = request.form['password']

        try:
            conn = sqlite3.connect('../../database/database.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admins (first_name, middle_name, last_name, user_id, email, password) 
                VALUES (?, ?, ?, ?, ?, ?)''', 
                (first_name, middle_name, last_name, user_id, email, password))
            conn.commit()
            conn.close()
            flash('Admin added successfully!')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError as e:
            flash('Error: Username or Email already exists.')
            return render_template('admin/add_admin.html', error='Username or Email already exists.')

    admins = []
    if 'admin' in session and session['admin'] == DEFAULT_USERNAME:
        conn = sqlite3.connect('../../database/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, middle_name, last_name, user_id, email FROM admins")
        admins = cursor.fetchall()
        conn.close()

    return render_template('admin/add_admin.html', admins=admins)

@app.route('/view_respondent')
def view_respondent():
    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT exam_id, first_name, middle_name, last_name FROM students")
    students = cursor.fetchall()
    conn.close()

    responses = get_google_sheet_data()
    print("Google Sheets Data:", responses[:5])
    
    preferred_programs = {}

    for row in responses:
        exam_id = str(row.get("exam_id"))
        preferred_program = row.get("Preferred Program?", "N/A")
        
        if exam_id and exam_id != "None":
            preferred_programs[exam_id] = preferred_program

    print("Corrected Preferred Programs Mapping:", preferred_programs)

    student_list = [
        {
            "full_name": f"{row[1]} {row[2]} {row[3]}".strip(),
            "preferred_program": preferred_programs.get(str(row[0]), "N/A"),
            "predicted_program": ""
        }
        for row in students
    ]
    
    return render_template('admin/view_respondent.html', students=student_list)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == '__main__':
    app.run(port=5005, debug=True)
