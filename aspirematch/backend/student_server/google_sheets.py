import gspread
import os
import sqlite3
from oauth2client.service_account import ServiceAccountCredentials

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "config/cisurvey-451710-23d971d33ee4.json")
SPREADSHEET_ID = "1Db1Kp9e94wgh4mrHpJaMHPmxzBsjS5pC-doGoRKvOjw"

def get_google_sheet_data():
    """Fetches survey responses from Google Sheets, including Timestamp."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()
    return data

def store_survey_responses():
    """Stores survey responses in the SQLite database."""
    conn = sqlite3.connect('../../database/database.db')
    cursor = conn.cursor()

    responses = get_google_sheet_data()

    for row in responses:
        exam_id = row.get("Examination ID")
        preferred_program = row.get("Preferred Program?")
        question1 = row.get("Question 1")
        question2 = row.get("Question 2")
        question3 = row.get("Question 3")
        question4 = row.get("Question 4")
        question5 = row.get("Question 5")
        question6 = row.get("Question 6")
        question7 = row.get("Question 7")
        question8 = row.get("Question 8")
        question9 = row.get("Question 9")
        question10 = row.get("Question 10")

        cursor.execute("""
            UPDATE students SET 
            preferred_program = ?, 
            q1 = ?, q2 = ?, q3 = ?, q4 = ?, q5 = ?, 
            q6 = ?, q7 = ?, q8 = ?, q9 = ?, q10 = ? 
            WHERE exam_id = ?
        """, (preferred_program, question1, question2, question3, question4, question5, 
              question6, question7, question8, question9, question10, exam_id))

    conn.commit()
    conn.close()

def delete_row_from_google_sheet(exam_id):
    """Delete a row from Google Sheets where the exam_id matches."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_values()

    for i, row in enumerate(data):
        if len(row) > 0 and str(row[0]) == str(exam_id):
            sheet.delete_rows(i + 1)
            print(f"Deleted row {i + 1} in Google Sheets for exam_id: {exam_id}")
            return True
    
    print(f"Exam ID {exam_id} not found in Google Sheets.")
    return False
